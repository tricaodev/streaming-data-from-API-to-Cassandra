import json
import time
import uuid
from datetime import datetime
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from kafka import KafkaProducer

def format_data(res):
    data = {}
    location = res['location']
    data['id'] = str(uuid.uuid4())
    data['first_name'] = res['name']['first']
    data['last_name'] = res['name']['last']
    data['gender'] = res['gender']
    data['address'] = f"{location['street']['number']} {location['street']['name']}, {location['city']}, {location['state']}, {location['country']}"
    data['post_code'] = location['postcode']
    data['email'] = res['email']
    data['username'] = res['login']['username']
    data['dob'] = res['dob']['date']
    data['registered_date'] = res['registered']['date']
    data['phone'] = res['phone']
    data['picture'] = res['picture']['large']

    return data

def get_data_from_api():
    current_time = time.time()
    while True:
        if time.time() > current_time + 60: # Get data from API within 60 seconds
            break

        res = requests.get('https://randomuser.me/api/').json()
        res = res['results'][0]
        data = format_data(res)

        # stream to kafka
        producer = KafkaProducer(
            bootstrap_servers='kafka:29092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_block_ms=30000
        )

        producer.send("users", data)
        producer.flush()


default_args = {
    'owner': 'tricao',
    'start_date': datetime(2025, 4, 2)
}

with DAG(
    'kafka_stream',
    default_args = default_args,
    description='stream user data from API to kafka',
    schedule_interval="0 * * * *",
    catchup=False
) as dag:
    task = PythonOperator(
        task_id="created_user",
        python_callable=get_data_from_api
    )