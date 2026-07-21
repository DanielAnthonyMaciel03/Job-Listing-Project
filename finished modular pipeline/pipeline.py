from extract import extractAllJobListings
from transform import filterListings, convertSalaryDataType, addJobCategory
from load import loadToDataBase

listings = extractAllJobListings()
listings = filterListings(listings)
listings = convertSalaryDataType(listings)
listings = addJobCategory(listings)
loadToDataBase(listings)



