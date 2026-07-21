import psycopg2
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


import smtplib
from email.mime.text import MIMEText

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


# this function sends an email to myself 
# the contents depend on if the pipeline found any new job listings
def sendEmail(newListings):

    gmailAddress = os.getenv("gmail")
    gmailPassword = os.getenv("gmailPass")

    if len(newListings) == 0:

        msg = MIMEText(f"No new job listings were posted today.")
        
    else:
        listingsToMail = []

        for listing in newListings:
            line = f"{listing['position_title']} | {listing['listing_uri']}"
            listingsToMail.append(line)
        
        allNewListingsText = "\n".join(listingsToMail)
        msg = MIMEText(f"{len(newListings)} new job listings were found today: \n\n {allNewListingsText}")
        
    
    msg["Subject"] = "Job Listings Pipeline: Daily Digest"
    msg["From"] = gmailAddress
    msg["To"] = gmailAddress

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmailAddress, gmailPassword)
        server.send_message(msg)




# this helper function checks to find any new listings 
def checkForNewListings(cur, listings):
    cur.execute("""
    SELECT listing_id 
    FROM fact_table_listings;
    """)
    query = cur.fetchall()
    jobIDs = []
    newListings = []

    for listing in query:
        jobIDs.append(listing[0])

    for listing in listings:
        if listing["listing_id"] not in jobIDs:
            newListings.append(listing)

    logging.info(f"Found {len(newListings)} new listings out of {len(listings)} total")
    
    return newListings
            


# This function is used to load any new listings into the data base
def loadToDataBase(listings):
    try:
        logging.info("Attempting to open database connection and create cursor")

        conn = psycopg2.connect(
            host=os.getenver("hostName"),
            database=os.getenv("databaseName"), 
            user=os.getenv("userName"), 
            password=os.getenv("passwordPostgreSQL")
        )

        cur = conn.cursor()
    except Exception as error:
        logging.error(f"Failed to open database connection or create cursor: {error}")
        raise
    


    logging.info("Succesfully created database connection and created cursor")
    logging.info("Checking for new job listings")

    # if there are no new listings for the day, i can avoid querying the database multiple times
    newListings = checkForNewListings(cur, listings)

    # ill send my self the email digest if any jobs were found
    sendEmail(newListings)

    if newListings:
        logging.info("Inserting new listings into the database") 

        # fill dim_table_organization
        for listing in newListings:
            cur.execute("""
                SELECT organization
                FROM dim_table_organization
                WHERE LOWER(organization) = LOWER(%s);
                """, (listing["organization"],))

            query = cur.fetchone()

            if query is None:
                cur.execute("""
                    INSERT INTO dim_table_organization (organization)
                    VALUES (%(str)s);
                    """, {'str': listing["organization"]})  



        # fill dim_table_location
        for listing in newListings:
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


        # fill dim_table_job_category
        for listing in newListings:
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
        for listing in newListings:

            cur.execute("""
                SELECT organization_id
                FROM dim_table_organization
                WHERE LOWER(organization) = LOWER(%s);      
                """,(listing["organization"],))
            organization_id = cur.fetchone()[0]

            cur.execute("""
                SELECT location_id
                FROM dim_table_location
                WHERE LOWER(location) = LOWER(%s);
                """,(listing["location"],))
            location_id = cur.fetchone()[0]

            cur.execute("""
                SELECT job_category_id
                FROM dim_table_job_category
                WHERE LOWER(job_category) = LOWER(%s)
                """,(listing["job_category"],))
            job_category_id = cur.fetchone()[0]

            
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
    else:
        logging.info("No new listings found")

    logging.info("Attempting to commit changes and close connections database")
    try:
        conn.commit()
        cur.close()
        conn.close()
    except Exception as error:
        logging.error(f"Failed to commit changes, close cursor, or close database connection: {error}")
        raise

    logging.info("Succesfully commited changes and closed all connections to database")
    logging.info("End of pipeline process")