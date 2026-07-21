# Project Description

This project is an automated ETL pipeline built around the [USAJOBS](https://developer.usajobs.gov) public REST API. It extracts federal job postings related to data roles, cleans and transforms the data, and loads it into a normalized PostgreSQL database built with a star schema. The entire pipeline is orchestrated end-to-end with Apache Airflow, running in Docker.

The pipeline runs on a daily schedule (every morning at 8:00 AM PST), detects and loads only new listings (no duplicates on repeat runs), and sends an automated email summary after every run. Along the way, it handles real-world data engineering challenges, including API pagination, NULL/missing field handling, and reliable task orchestration with retry logic.

This README walks through my thought process behind the key decisions I made throughout this project, along with several implementations that reflect real-world data engineering problem-solving.


# Data pipeline architecture
![Pipeline Architecture](screenshots/pipeline_architecture.png)