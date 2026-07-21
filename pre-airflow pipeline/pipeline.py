from extract import extractAllJobListings
from transform import cleanData
from load import loadToDataBase

listings = extractAllJobListings()
listings = cleanData(listings)
loadToDataBase(listings)




