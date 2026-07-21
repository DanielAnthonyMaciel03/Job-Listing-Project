import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def filterListings(listings):
    targetJobs = ["data analyst", "data engineer", "data scientist"]
    filteredListings = []

    logging.info(f"Beginning filtering for jobs: {targetJobs}")

    for listing in listings:

        jobTitle = listing["position_title"].lower()

        if any(target in jobTitle for target in targetJobs):
            filteredListings.append(listing)   

    logging.info(f"Total listings filtered: {len(filteredListings)}")
    return filteredListings




def convertSalaryDataType(listings):
    for listing in listings:
        if listing["min_salary"] is not None:
            listing["min_salary"] = float(listing["min_salary"])
        if listing["max_salary"] is not None:
            listing["max_salary"] = float(listing["max_salary"])
        if listing["close_date"] is not None:
            listing["close_date"] = listing["close_date"].split("T")[0]

    return listings


def addJobCategory(listings):
    for listing in listings:
        titleLower = listing["position_title"].lower()

        if "data engineer" in titleLower:
            listing["job_category"] = "data engineer"
        elif "data analyst" in titleLower:
            listing["job_category"] = "data analyst"
        elif "data scientist" in titleLower:
            listing["job_category"] = "data scientist"
        else:
            listing["job_category"] = "other"
    
    return listings

