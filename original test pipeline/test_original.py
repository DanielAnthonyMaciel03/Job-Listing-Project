import requests
import json
import psycopg2
import math



# Our API requires authentication.
# That authentication is sent through the headers of our API call.
# These specific header fields are required, and this format is documented in the API's authentication guide.
host = "..."
user_agent = "..."  
auth_key = "..."

headers = {
    "Host": host,
    "User-Agent": user_agent,
    "Authorization-Key": auth_key
}


# Each endpoint can accept a set of parameters to narrow down the results.
# The endpoint we're using here is "/search".
# The full list of accepted parameters for this endpoint is documented on the USAJOBS developer site.
pageNum = 1
params = {
    "PositionTitle": "data analyst",
    "ResultsPerPage": 500,
    "Page": pageNum
}


# call the API with our given header and parameter
# get the json response
# and determine how many search results it yielded
response = requests.get("https://data.usajobs.gov/api/search", headers=headers, params=params)
data = response.json()
searchCountAll = data["SearchResult"]["SearchResultCountAll"]



# This helper function will help us extract job listings and the keys we desire to store in our postgreSQL DB later on
def extractJobListings(job):
    listingDetails = job["MatchedObjectDescriptor"]

    # "PositionRemuneration" is a list that holds exactly one dictionary (when salary info exists).
    # If a salary was posted, that dictionary will be sitting at index 0 of the list.
    # If no salary was posted, the list will be empty, so we fall back to an empty dictionary instead,
    # to avoid errors when we try to look up salary fields later.
    if listingDetails["PositionRemuneration"]:
        salaryInfo = listingDetails["PositionRemuneration"][0]
    else:
        salaryInfo = {}

    # Now we build a clean dictionary containing only the fields we care about.
    dictionary = {
        "listing_id": listingDetails.get("PositionID"),
        "position_title": listingDetails.get("PositionTitle"),
        "organization": listingDetails.get("OrganizationName"),
        "location": listingDetails.get("PositionLocationDisplay"),
        "listing_uri": listingDetails.get("PositionURI"),
        "min_salary": salaryInfo.get("MinimumRange"),
        "max_salary": salaryInfo.get("MaximumRange"),
        "close_date": listingDetails.get("ApplicationCloseDate"),
    }

    return dictionary


# create an empty list to hold our job listings
listings = []



# if the total amount of job listings exceeds 1 page, then pagination is required
# a single page can be defined to returned up to 500 listings set in the params variable 
if 500 < searchCountAll:

    # calculate how many pages are needed and round up
    totalPages = math.ceil(searchCountAll / 500)

    # iterate over the total number of pages there are
    for page in range(1, totalPages + 1):

        # set the page to look at
        # call the API
        # and get the json response
        params["Page"] = page
        response = requests.get("https://data.usajobs.gov/api/search", headers=headers, params=params)
        data = response.json()

        # get the job listings and extract them using helper function
        jobs = data["SearchResult"]["SearchResultItems"]
        for job in jobs:
            listings.append(extractJobListings(job))

# if only 1 page of data is returned then no pagination is required
else:
    jobs = data["SearchResult"]["SearchResultItems"]
    for job in jobs:
        listings.append(extractJobListings(job))







# Now that we've gotten all listings matching our search parameter,
# we'll filter them once more based on job title.
# Specifically, we only want postings whose title contains one of these phrases:
targetJobs = ["data analyst", "data engineer", "data scientist"]

# A new list to hold just the listings that pass our title filter.
filteredListings = []


# Go through every listing we've already extracted.
for listing in listings:

    # Normalize the title to lowercase so comparisons aren't affected by inconsistent capitalization
    # (some postings use "DATA ANALYST", others use "Data Analyst").
    jobTitle = listing["position_title"].lower()

    # If the title contains any of our target phrases, keep this listing.
    if any(target in jobTitle for target in targetJobs):
        filteredListings.append(listing)


# Job listing salaries are currently stored as strings, they need to be converted to integers
for listing in filteredListings:
    if listing["min_salary"] is not None:
        listing["min_salary"] = float(listing["min_salary"])
    if listing["max_salary"] is not None:
        listing["max_salary"] = float(listing["max_salary"])
    if listing["close_date"] is not None:
        listing["close_date"] = listing["close_date"].split("T")[0]



# We want to create a separate dimension table for job category.
# The raw "title" field can't be used directly for this, since it often contains
# extra details beyond just the role type (seniority, hiring event notes, etc.),
# so titles rarely repeat in a clean, consistent way.
# Instead, we'll derive a normalized category (Data Engineer / Data Analyst / etc.)
# that DOES repeat across listings, making it a proper dimension.

# This function takes in a single job's title and returns its normalized category.
def get_job_category(title):
    
    # then the function normalizes the title to all lowwer case
    titleLower = title.lower()

    if "data engineer" in titleLower:
        return "data engineer"
    if "data analyst" in titleLower:
        return "data analyst"
    if "data scientist" in titleLower:
        return "data scientist"
    else:
        return "other"

# Apply the function across every listing, adding a new "job_category" field to each.
for listing in filteredListings:
    listing["job_category"] = get_job_category(listing["position_title"])










# The following code shows connection to the DB, and inserting our data into it

conn = psycopg2.connect(database="...", user="...", password="...")

cur = conn.cursor()


#issue: we have to create a way to find out which value goes in which table
# "listing_id" -- fact table
# "position_title" -- fact table
# "organization" -- dim_table   DONE
# "location" -- dim_table       DONE
# "listing_uri" -- fact table
# "min_salary" -- fact table
# "max_salary" -- fact table
# "close_date" -- fact table
# "job_category" -- dim table   DONE


# filling dim_table_organization
for listing in filteredListings:

    # first we need to check if the organization we are putting into our dimension table already exists
    # we will use the LOWER() string fucntion to make sure to catch case sensitive names
    # example: FTC or ftc .. same org different case
    cur.execute("""
        SELECT organization
        FROM dim_table_organization
        WHERE LOWER(organization) = LOWER(%s);
        """, (listing["organization"],))

    # we will then grab one query object
    # it doesnt matter if we use fetchall() becuase only 1 should exist or none
    query = cur.fetchone()

    # if the query came back with nothing we are free to insert this organization into the dimension table
    if query is None:
        cur.execute("""
            INSERT INTO dim_table_organization (organization)
            VALUES (%(str)s);
            """, {'str': listing["organization"]})  



# filling dim_table_location
for listing in filteredListings:
    cur.execute("""
        SELECT location
        FROM dim_table_location
        WHERE LOWER(location) = LOWER(%s);
        """, (listing["location"],))
    
    query = cur.fetchone()

    if query is None:
        cur.execute("""
        INSERT INTO dim_table_location (location)
        VALUES (%(str)s); 
        """,{'str': listing["location"]})


# filling dim_table_job_category
for listing in filteredListings:
    cur.execute("""
        SELECT job_category
        FROM dim_table_job_category
        WHERE LOWER(job_category) = LOWER(%s);
        """,(listing["job_category"],))
    
    query = cur.fetchone()

    if query is None:
        cur.execute("""
        INSERT INTO dim_table_job_category (job_category)
        VALUES (%(str)s); 
        """,{'str': listing["job_category"]})




#filling fact_table_listings
for listing in filteredListings:

    # find the id for organization
    cur.execute("""
        SELECT organization_id
        FROM dim_table_organization
        WHERE LOWER(organization) = LOWER(%s);      
        """,(listing["organization"],))
    
    organization_id = cur.fetchone()[0]

    # find the id for location
    cur.execute("""
        SELECT location_id
        FROM dim_table_location
        WHERE LOWER(location) = LOWER(%s);
        """,(listing["location"],))
    
    location_id = cur.fetchone()[0]


    # find the id for job_category
    cur.execute("""
        SELECT job_category_id
        FROM dim_table_job_category
        WHERE LOWER(job_category) = LOWER(%s)
        """,(listing["job_category"],))
    
    job_category_id = cur.fetchone()[0]


    # find the current job listing id
    cur.execute("""
        SELECT listing_id
        FROM fact_table_listings
        WHERE listing_id = (%s)
                """,(listing["listing_id"],))
    
    query = cur.fetchone()

    # if the job listing doesnt exist we can add this listing into our DB
    if query is None:
        cur.execute("""
            INSERT INTO fact_table_listings (listing_id, position_title, job_category_id, organization_id, location_id, min_salary, max_salary, close_date, listing_uri)
            VALUES (%(listing_id)s, %(position_title)s, %(job_category_id)s, %(organization_id)s, %(location_id)s, %(min_salary)s, %(max_salary)s, %(close_date)s, %(listing_uri)s)
            """, {
            
            'listing_id': listing["listing_id"],
            'position_title': listing["position_title"],
            'job_category_id': job_category_id,
            'organization_id': organization_id,
            'location_id': location_id,
            'min_salary': listing["min_salary"],
            'max_salary': listing["max_salary"],
            'close_date': listing["close_date"],
            'listing_uri': listing["listing_uri"]
            
            })




conn.commit()

print(f"Total listings extracted: {len(listings)}")
print(f"Total after filtering: {len(filteredListings)}")



# Notes:
# this is for government jobs only
# hadnled pagination
# using psycopg2 lib for moving data to postgrese ddatabase
# null values were taken into considderation only for salary becuase null values for uri and postion title can pracitaclly never be none
# also if any other fields had null values the listing wouldd still be of use to me so i made sure null values were propely inserted
# https://developer.usajobs.gov/api-reference/get-api-search





# modualrized code
# added logging features to catch API call fails
# - catch listings that have null values in important columns and not extract them (position title, uri)
