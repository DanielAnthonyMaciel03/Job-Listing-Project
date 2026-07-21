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

- [`airflow DAG code`](airflow%20DAG%20code) — This folder contains the single DAG file used by Airflow to orchestrate the entire pipeline. The DAG file relies on `extract.py`, `transform.py`, and `load.py` (which are located [`pre-airflow pipeline`](pre-airflow%20pipeline)) in being present in the same directory for Airflow to run correctly.
- [`pre-airflow pipeline`](pre-airflow%20pipeline) — The contents in this folder were used to test and confirm the pipeline worked via manual, single-run execution before Airflow was introduced. Once confirmed working, only `extract.py`, `transform.py`, and `load.py` needed to be referenced by the DAG file.
- [`sql`](sql) — Contains the SQL used to create the tables.

---

# Pipeline Explanation

## Extraction

- The extraction process relies on the USAJOBS public REST API.
- Specifically, I used the `/search` endpoint, which exposes the same search functionality available on the USAJOBS website itself.
- A major challenge I ran into was the API's hard result limit: an unfiltered search maxes out at 10,000 listings (`SearchResultCountAll`), regardless of how many jobs are actually posted.
- To work around this, I methodically split the searches to cover all listings, using a specific parameter: `JobCategoryCode`.
- The idea was that every federal job posting is assigned to a job family. For example, a broad occupational grouping (e.g., `2200` for Information Technology, `0800` for Engineering and Architecture). By querying each job family individually, I could stay well under the 10,000-result cap for every single request.
- This meant iterating over every job family code, pulling all current listings under that code, and repeating the process until every publicly listed job family had been queried. This effectively captures the full breadth of current USAJOBS postings.
- This extraction also handles pagination, since only 500 listings can be returned per API call (`ResultsPerPage`). For any job family returning more than 500 listings, the extraction automatically pages through the remaining results until everything for that family is retrieved.
- Each listing is stored as a dictionary containing its relevant metadata (title, organization, location, salary, close date, etc.), and all listings are collected into a single list for the next stage of the pipeline.

## Cleaning

- For this cleaning process, I did not want to remove a listing just because it had NULL values.
- Specifically, I only remove a listing if it's missing values for two key columns: `position_title` or `listing_uri`. This choice was deliberate. Without a title or a link back to the original posting, there would be no way to identify or view the job on USAJOBS, making the listing effectively useless for analysis.
- Listings with NULL values in any other field (like salary or close date) are kept as-is, since that missing data still leaves the listing meaningful and usable. This just reflects that the employer didn't disclose that particular detail.
- All text fields also have leading and trailing whitespace removed.


## Loading

- Loading was handled with the `psycopg2` library, which provides native PostgreSQL support within Python, allowing queries, inserts, and deletions to run directly from the pipeline script.
- To reduce overhead and avoid unnecessary work, the pipeline includes a check for new listings, ensuring that data already present in the database is never reprocessed or re-queried unnecessarily.
- Duplicate listings are checked at two levels: within the extracted list of dictionaries itself, and against what already exists in the database, before any insertion takes place. This was necessary because the broad market extraction pulls listings across many overlapping job category codes, meaning the same job posting can occasionally be captured more than once within a single run.

### Snippet of postgreSQL data

![dimension table job category](dimTableJobCategory.PNG)
![dimension table location](dimTableLocation.PNG)
![dimension table organization](dimTableOrganization.PNG)
![fact table listings](factTableListings.PNG)

## Airflow Orchestration

- Airflow allowed me to automate the entire process of extracting, cleaning, and loading the data.
- I used a DAG file to define the automation process, made up of three major tasks, each corresponding to one of the core pipeline files: extract, transform, and load.
- Airflow executes these tasks in the defined order every day at 8:00 AM PST.
- Note: since my dataset is relatively small (currently around 13,000 listings), I made the deliberate choice to hand off data directly between tasks using XCom, rather than writing to and reading from a shared storage location. I understand that in a typical production workflow with much larger datasets, this approach would introduce significant overhead and slow performance, since XComs aren't designed to handle large payloads efficiently. In that scenario, the standard practice is for each task to write its output to a shared location (such as a staging table), with the next task reading from that same location.
- I also implemented retry logic, so tasks automatically retry on transient failures (such as a temporary API timeout) before being marked as failed.
- Since Airflow captures and stores logs from any task automatically, I made sure to implement logging throughout my scripts to catch exactly where potential issues might arise, such as failed API calls, database connection problems, or data insertion errors. This means that when a task runs, whether successfully or not, Airflow's UI shows a clear, timestamped record of what happened at each step, rather than just a pass/fail status with no context.

### Airflow run and local run
![Airflow Complete Run](screenshots/airflowCompleteRun.PNG)
![Local Test Run](screenshots/localTest.PNG)