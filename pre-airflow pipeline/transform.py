import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Salary is seen as a string in the API so this function converts its data type to integer
# Salary is also a yearly salary so float is not needed as a data type
def convertSalaryDataType(listings):
    for listing in listings:
        if listing["min_salary"] is not None:
            listing["min_salary"] = float(listing["min_salary"])
        if listing["max_salary"] is not None:
            listing["max_salary"] = float(listing["max_salary"])
        if listing["close_date"] is not None:
            listing["close_date"] = listing["close_date"].split("T")[0]

    return listings

# Cleans any trailing or leading white space in values
def cleanTextFields(listings):
    for listing in listings:
        if listing["position_title"] is not None:
            listing["position_title"] = listing["position_title"].strip()
        if listing["organization"] is not None:
            listing["organization"] = listing["organization"].strip()
        if listing["location"] is not None:
            listing["location"] = listing["location"].strip()
        if listing["job_category"] is not None:
            listing["job_category"] = listing["job_category"].strip()

    return listings


def cleanData(listings):
    logging.info("Starting cleaning process")
    listings = convertSalaryDataType(listings)
    listings = cleanTextFields(listings)
    logging.info("Finished cleaning process")
    return listings