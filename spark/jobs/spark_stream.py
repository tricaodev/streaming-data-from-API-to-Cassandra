from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DateType
from cassandra.cluster import Cluster

KEY_SPACE = "streaming_data"
TABLE = "users"

def connect_cassandra():
    cluster = Cluster(["cassandra"])
    session = cluster.connect()
    return session

def create_keyspace(session):
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEY_SPACE}
        WITH replication = {{ 'class': 'SimpleStrategy', 'replication_factor': 1 }}
    """)

def create_table(session):
    session.execute(f"""
        CREATE TABLE IF NOT EXISTS {KEY_SPACE}.{TABLE} (
            id UUID PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            gender TEXT,
            address TEXT,
            post_code INT,
            email TEXT,
            username TEXT,
            dob TIMESTAMP,
            registered_date TIMESTAMP,
            phone TEXT,
            picture TEXT
        )
    """)


def stream_data():
    session = connect_cassandra()
    create_keyspace(session)
    create_table(session)

    # Create SparkSession
    spark = SparkSession.builder \
        .appName("spark_stream") \
        .master("spark://spark-master:7077") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,com.datastax.spark:spark-cassandra-connector_2.12:3.5.1") \
        .config("spark.cassandra.connection.host", "cassandra") \
        .getOrCreate()

    # Schema of user datum
    schema = StructType([
        StructField("id", StringType(), False),
        StructField("first_name", StringType(), False),
        StructField("last_name", StringType(), False),
        StructField("gender", StringType(), True),
        StructField("address", StringType(), True),
        StructField("post_code", IntegerType(), True),
        StructField("email", StringType(), False),
        StructField("username", StringType(), False),
        StructField("dob", DateType(), True),
        StructField("registered_date", DateType(), False),
        StructField("phone", StringType(), False),
        StructField("picture", StringType(), True)
    ])

    # Read message from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", TABLE) \
        .option("startingOffsets", "earliest") \
        .load()

    df = df.selectExpr("CAST(key AS STRING) key", "CAST(value AS STRING) value") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")

    # Write message to Cassandra
    query = df.writeStream \
        .format("org.apache.spark.sql.cassandra") \
        .option("checkpointLocation", "/tmp/checkpoint") \
        .option("keyspace", KEY_SPACE) \
        .option("table", TABLE) \
        .outputMode("append") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    stream_data()