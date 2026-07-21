CREATE TABLE dim_table_organization (
    organization_id SERIAL PRIMARY KEY,
    organization TEXT
);

CREATE TABLE dim_table_job_category (
    job_category_id SERIAL PRIMARY KEY,
    job_category TEXT
);

CREATE TABLE dim_table_location (
    location_id SERIAL PRIMARY KEY,
    location TEXT
);

CREATE TABLE fact_table_listings (
    listing_id TEXT PRIMARY KEY,
    position_title TEXT,
    job_category_id INTEGER REFERENCES dim_table_job_category(job_category_id),
    organization_id INTEGER REFERENCES dim_table_organization(organization_id),
    location_id INTEGER REFERENCES dim_table_location(location_id),
    min_salary INTEGER,
    max_salary INTEGER,
    close_date DATE,
    listing_uri TEXT
);