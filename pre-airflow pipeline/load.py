import psycopg2
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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


# This helper function helps detect any duplicate listings and remove them if needed to prevent errors when inserting into postgrese
def checkForDupeListings(listings):
    seen_ids = set()
    uniqueListings = []
    for listing in listings:
        if listing["listing_id"] not in seen_ids:
            seen_ids.add(listing["listing_id"])
            uniqueListings.append(listing)
    
    dupes = len(listings) - len(uniqueListings)
    logging.info(f"Duplicate listings detected: {dupes}")
    return uniqueListings

# This function is used to load any new listings into the data base
def loadToDataBase(listings):
    try:
        logging.info("Attempting to open database connection and create cursor")

        conn = psycopg2.connect(
            host="...",
            database="...", 
            user="...", 
            password="..."
        )

        cur = conn.cursor()
    except Exception as error:
        logging.error(f"Failed to open database connection or create cursor: {error}")
        raise


    logging.info("Succesfully created database connection and created cursor")
    logging.info("Checking for new job listings")

    # if there are no new listings for the day, i can avoid querying the database multiple times
    newListings = checkForNewListings(cur, listings)
    newListings = checkForDupeListings(newListings)

    if newListings:
        logging.info("Inserting new listings into the database") 

        # Each dimension table load checks for existing entries before inserting,
        # using LOWER() to catch case-variant duplicates (e.g. "FDA" vs "fda").
        # For the fact table, listing_id uniqueness is handled upstream — by this point,
        # newListings has already been filtered by checkForNewListings() (removes listings
        # already in the database) and checkForDupeListings() (removes duplicate listing_ids
        # within this batch), so no additional check is needed before inserting.

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