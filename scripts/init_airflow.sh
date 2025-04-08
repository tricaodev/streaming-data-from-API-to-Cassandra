#!/bin/bash

pip install -r /opt/airflow/requirements.txt

airflow db init

airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com

airflow webserver