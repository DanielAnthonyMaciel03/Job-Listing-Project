import sys
import os

sys.path.append(os.path.dirname(__file__))

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pendulum

from extract import extractAllJobListings
from transform import filterListings, convertSalaryDataType, addJobCategory
from load import loadToDataBase


# How to hand off data to tasks using Xcom, other option included TaskFlow API, but it used Xcom underneath the hood
# ideally i should write to a sharelocation then have the next task read from that same location and repeat
# this is acceptable since a small amount of data is being transfered between each task

def extract_wrapper(**kwargs):
    # This is the return value from the extractAllJobListings()
    returnValue = extractAllJobListings() 

    # Then we push the return value into "task instance" under the key 
    # "listings" with the variable from "returnValue"
    kwargs['ti'].xcom_push(key='listings', value=returnValue)


def filter_wrapper(**kwargs):
    # This is where we now pull the return value specifcally from task1
    # This is so now task2 can use it as an input value
    inputValue = kwargs['ti'].xcom_pull(task_ids='extract_all_job_listings', key='listings')

    # We repeat again, we store the return value
    returnValue = filterListings(inputValue)

    # Then we push it into the task instance udner the key "listing" with this tasks return value
    kwargs['ti'].xcom_push(key='listings', value=returnValue)


def convert_wrapper(**kwargs):
    inputValue = kwargs['ti'].xcom_pull(task_ids='filter_listings', key='listings')
    returnValue = convertSalaryDataType(inputValue)
    kwargs['ti'].xcom_push(key='listings', value=returnValue)


def category_wrapper(**kwargs):
    inputValue = kwargs['ti'].xcom_pull(task_ids='convert_salary_data_type', key='listings')
    returnValue = addJobCategory(inputValue)
    kwargs['ti'].xcom_push(key='listings', value=returnValue)


def load_wrapper(**kwargs):
    inputValue = kwargs['ti'].xcom_pull(task_ids='add_job_category', key='listings')
    loadToDataBase(inputValue)



# Handles time zone and daylight saving issue
localTimeZone = pendulum.timezone("America/Los_Angeles")



with DAG(
    # DAG name that will show in airflow
    dag_id="job_listings_pipeline",
    start_date=datetime(2026, 7, 20, tzinfo=localTimeZone),

    # runs every day at 8:00 AM pacific
    schedule="0 8 * * *",
    catchup=False,

    # retry logic
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
) as dag:

    task1 = PythonOperator(
        task_id="extract_all_job_listings", 
        python_callable=extract_wrapper
    )

    task2 = PythonOperator(
        task_id="filter_listings", 
        python_callable=filter_wrapper
    )

    task3 = PythonOperator(
        task_id="convert_salary_data_type", 
        python_callable=convert_wrapper
    
    )

    task4 = PythonOperator(
        task_id="add_job_category", 
        python_callable=category_wrapper
    
    )

    task5 = PythonOperator(
        task_id="load_to_data_base", 
        python_callable=load_wrapper
    )


    # explicitly state which tasks to run in which order
    task1 >> task2 >> task3 >> task4 >> task5