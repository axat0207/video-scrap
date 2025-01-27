import pandas as pd
import json
from pymongo import MongoClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("json_to_excel.log"),  # Log to a file
        logging.StreamHandler()  # Log to the console
    ]
)

def json_to_excel(json_file, excel_file, mongodb_uri, db_name, collection_name):
    """
    Convert a JSON file to an Excel file, prevent duplicates by 'name', and store data in MongoDB.
    
    Args:
        json_file (str): Path to the input JSON file.
        excel_file (str): Path to the output Excel file.
        mongodb_uri (str): MongoDB connection URI.
        db_name (str): Name of the MongoDB database.
        collection_name (str): Name of the MongoDB collection.
    """
    try:
        # Log the start of the process
        logging.info("Starting JSON to Excel and MongoDB processing...")
        
        # Load JSON data
        logging.info(f"Loading JSON data from {json_file}")
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Convert JSON to DataFrame
        logging.info("Converting JSON data to DataFrame")
        df = pd.DataFrame(data)
        
        # Remove duplicates based on the 'name' field
        logging.info("Removing duplicates based on the 'name' field")
        df.drop_duplicates(subset=['name'], keep='first', inplace=True)
        
        # Connect to MongoDB
        logging.info(f"Connecting to MongoDB: {mongodb_uri}")
        client = MongoClient(mongodb_uri)
        db = client[db_name]
        collection = db[collection_name]
        
        # Insert only unique records into MongoDB
        logging.info("Inserting unique records into MongoDB")
        unique_records = []
        for record in df.to_dict('records'):
            if not collection.find_one({"name": record["name"]}):
                collection.insert_one(record)
                unique_records.append(record)
                logging.info(f"Inserted record: {record['name']}")
            else:
                logging.warning(f"Duplicate found, skipping record: {record['name']}")
        
        # Convert unique records back to DataFrame
        logging.info("Converting unique records to DataFrame")
        unique_df = pd.DataFrame(unique_records)
        
        # Save DataFrame to Excel
        logging.info(f"Saving DataFrame to Excel file: {excel_file}")
        unique_df.to_excel(excel_file, index=False, engine='openpyxl')
        logging.info(f"JSON data successfully written to {excel_file}")
    
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        # Close the MongoDB connection
        logging.info("Closing MongoDB connection")
        client.close()

# Example Usage
# Provide the path to your JSON file, desired Excel output file, and MongoDB details
json_file_path = "final-output.json"  # Input JSON file
excel_file_path = "final-output.xlsx"  # Output Excel file
mongodb_uri = "mongodb+srv://1234:1234@cluster0.wir5xrk.mongodb.net/final-scrap-with-profile"  # MongoDB URI
db_name = "final-scrap-with-profile"  # MongoDB database name
collection_name = "stir-filmmakers"  # MongoDB collection name

json_to_excel(json_file_path, excel_file_path, mongodb_uri, db_name, collection_name)