import requests
import json
import math

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

def extractJobListing(job):
    listingDetails = job["MatchedObjectDescriptor"]

    if listingDetails["PositionRemuneration"]:
        salaryInfo = listingDetails["PositionRemuneration"][0]
    else:
        salaryInfo = {}

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

    if dictionary["position_title"] is None or dictionary["listing_uri"] is None:
        logging.warning(f"Listing {dictionary.get('listing_id')} missing critical field (title or URI)")
        dictionary = {}

    return dictionary



def extractAllJobListings():
    host = "data.usajobs.gov"
    user_agent = os.getenv("userAgent")                                       
    auth_key = os.getenv("authKey")      

    headers = {
        "Host": host,                                               
        "User-Agent": user_agent,                                   
        "Authorization-Key": auth_key                               
    }

    pageNum = 1
    params = {
        "PositionTitle": "data analyst",
        "ResultsPerPage": 500,
        "Page": pageNum
    }

    logging.info("Beginning pipeline process")
    logging.info("Attempting to call API")

    try:
        response = requests.get("https://data.usajobs.gov/api/search", headers=headers, params=params)

    except Exception as error:
        logging.error(f"API call failed: {error}")
        raise
    
    logging.info("API call sucessful")

    data = response.json()
    searchCountAll = data["SearchResult"]["SearchResultCountAll"]

    listings = []


    if 500 < searchCountAll:

        totalPages = math.ceil(searchCountAll / 500)

        logging.info(f"Pagination required: {totalPages} pages to retrieve")
        logging.info("Starting job listing extraction")

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
                listings.append(extractJobListing(job))

    else:

        logging.info("No pagination required: 1 page to retrieve")
        logging.info("Starting job listing extraction")

        jobs = data["SearchResult"]["SearchResultItems"]

        for job in jobs:

            listing = extractJobListing(job)

            if listing != {}:
                listings.append(listing)
    
    return listings