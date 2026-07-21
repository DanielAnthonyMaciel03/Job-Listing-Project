import requests
import json
import math

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# This function extracts a single job listing and stores its data into a dictionary
def extractJobListing(job):
    listingDetails = job["MatchedObjectDescriptor"]

    if listingDetails["PositionRemuneration"]:
        salaryInfo = listingDetails["PositionRemuneration"][0]
    else:
        salaryInfo = {}

    jobCategoryList = listingDetails.get("JobCategory", [])
    if jobCategoryList:
        categoryName = jobCategoryList[0].get("Name")
    else:
        categoryName = None

    # .get() returns None when a key is missing (since no default value is specified here),
    # which psycopg2 later translates into SQL NULL when inserting into PostgreSQL
    dictionary = {
        "listing_id": listingDetails.get("PositionID"),
        "position_title": listingDetails.get("PositionTitle"),
        "organization": listingDetails.get("OrganizationName"),
        "location": listingDetails.get("PositionLocationDisplay"),
        "listing_uri": listingDetails.get("PositionURI"),
        "min_salary": salaryInfo.get("MinimumRange"),
        "max_salary": salaryInfo.get("MaximumRange"),
        "close_date": listingDetails.get("ApplicationCloseDate"),
        "job_category": categoryName
    }

    # Listings missing a position title or listing URI are removed entirely, since without either
    # field the listing can't be meaningfully identified or viewed by the end user
    if dictionary["position_title"] is None or dictionary["listing_uri"] is None:
        logging.warning(f"Listing {dictionary.get('listing_id')} missing critical field (title or URI)")
        dictionary = {}

    return dictionary



# This function handles the entire loop process of extracting all the job listings on USAJOBS
def extractAllJobListings():

    logging.info("Beginning pipeline process")

    host = "..."
    user_agent = "..."                                       
    auth_key = "..."      

    headers = {
        "Host": host,                                               
        "User-Agent": user_agent,                                   
        "Authorization-Key": auth_key                               
    }

    # This is the set of JobFamily codes that any job on USAJOBS falls under
    # The API caps SearchResultCountAll at 10,000 per query, so querying each
    # family individually keeps every request safely under that limit.
    jobFamilies = ["0000", "0100", "0200", "0300", "0400", "0500", "0600", "0700", "0800", "0900",
                 "1000", "1100", "1200", "1300", "1400", "1500", "1600", "1700", "1800", "1900",
                 "2000", "2100", "2200", "2300", "2500", "2600", "2800",
                 "3100", "3300", "3400", "3500", "3600", "3700", "3800", "3900",
                 "4000", "4100", "4200", "4300", "4400", "4600", "4700", "4800",
                 "5000", "5200", "5300", "5400", "5700", "5800",
                 "6500", "6600", "6900",
                 "7000", "7300", "7400", "7600",
                 "8200", "8600", "8800",
                 "9000", "9900"]

    listings = []

    logging.info("Beginning API calls")

    for family in jobFamilies:

        params = {
            "JobCategoryCode": family,
            "ResultsPerPage": 500
        }

        try:
            response = requests.get("https://data.usajobs.gov/api/search", headers=headers, params=params)

        except Exception as error:
            logging.error(f"API call failed: {error}")
            raise

        data = response.json()
        searchCountAll = data["SearchResult"]["SearchResultCountAll"]


        # Pagination Logic
        if 500 < searchCountAll:

            totalPages = math.ceil(searchCountAll / 500)

            for page in range(1, totalPages + 1):
    
                params["Page"] = page

                try:
                    response = requests.get("https://data.usajobs.gov/api/search", headers=headers, params=params)
                except Exception as error:
                    logging.error(f"API call failed within pagination: {error}")
                    raise
                    
                data = response.json()
                jobs = data["SearchResult"]["SearchResultItems"]

                for job in jobs:
                    listing = (extractJobListing(job))
                    if listing != {}:
                        listings.append(listing)

        else:

            jobs = data["SearchResult"]["SearchResultItems"]

            for job in jobs:

                listing = extractJobListing(job)

                if listing != {}:
                    listings.append(listing)
    
    logging.info("API calls sucessful")

    return listings
