# Project Description

This project is an automated ETL pipeline built around the [USAJOBS](https://developer.usajobs.gov) public REST API. It extracts all available federal job postings, cleans and transforms the data, and loads it into a normalized PostgreSQL database built with a star schema. The entire pipeline is orchestrated end-to-end with Apache Airflow, running in Docker.

The pipeline runs on a daily schedule (every morning at 8:00 AM PST), detects and loads only new listings (no duplicates on repeat runs). The pipeline handles real-world data engineering challenges, including API pagination, NULL/missing field handling, and reliable task orchestration with retry logic.

This README walks through my thought process behind the key decisions I made throughout this project, along with several implementations that reflect real-world data engineering problem-solving.

---

# Data pipeline architecture
![Pipeline Architecture](screenshots/techArchitecture.PNG)

- **REST API:** [USAJOBS](https://developer.usajobs.gov) was used to source new job listings for extraction.
- **Extract/Transform/Load:** Python, using the `psycopg2` library, handled extracting, cleaning, and loading the data into the database.
- **Storage:** PostgreSQL was used for data storage, structured as a star schema.
- **Orchestration:** Apache Airflow (running via Docker) automates the entire pipeline end-to-end, including scheduling and retry logic.

---

# Database Design
![Database Design](screenshots/DataBaseDiagram.PNG)

- The diagram above shows the database's star schema design. This approach was chosen because several fields in the raw data were highly repetitive. organization, location and job_category, repeated across many listings, making them strong candidates for normalization into separate dimension tables.

## Data Dictionary

| Column | Description |
|---|---|
| `listing_id`  | Unique identifier for the job posting, sourced directly from the USAJOBS API's PositionID |
| `position_title`  | The original, unmodified job title as listed by the employer |
| `job_category_id`  | Foreign key referencing the derived job category |
| `organization_id`  | Foreign key referencing the hiring organization/agency |
| `location_id` | Foreign key referencing the job's posted location |
| `min_salary` / `max_salary`  | The posted salary range, in USD. May be NULL if the employer didn't provide salary information |
| `close_date`  | The date the application window for this posting closes |
| `listing_uri`  | Direct link to the original USAJOBS posting |
| `organization` | The name of the hiring federal agency/organization |
| `location`  | The posted job location (city, state, or "Multiple Locations") |
| `job_category` | The specific occupational category |

---

# Important Folders

- [`airflow DAG code`](airflow%20DAG%20code) — This folder contains the single DAG file used by Airflow to orchestrate the entire pipeline. The DAG file relies on `extract.py`, `transform.py`, and `load.py` (which are located [`pre-airflow pipeline`](pre-airflow%20pipeline) in being present in the same directory for Airflow to run correctly.
- [`pre-airflow pipeline`](pre-airflow%20pipeline) — The contents in this folder were used to test and confirm the pipeline worked via manual, single-run execution before Airflow was introduced. Once confirmed working, only `extract.py`, `transform.py`, and `load.py` needed to be referenced by the DAG file.
- [`sql`](sql) — Contains the SQL used to create the tables, following the star schema design.

---


