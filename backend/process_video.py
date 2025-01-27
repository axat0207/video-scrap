import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
import pandas as pd
import json
import re
from dotenv import load_dotenv
import logging
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
from gemini import GeminiClient  

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s: %(message)s')

# Load environment variables
load_dotenv()

cloudinary.config(
    cloud_name="dhw31jiof",
    api_key="324693876994192",
    api_secret="jeZ3fD-FTIG3Vf15-pvkKXelSY4"
)

# Gemini Client
gemini_client = GeminiClient(api_key=os.getenv('GEMINI_API_KEY'))
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def is_valid_image(image_path):
    """
    Check if the image is not mostly white and contains meaningful content.
    Returns True if the image is valid (contains non-white content, face, or placeholder).
    """
    try:
        # Read image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate the average pixel value
        avg_pixel = np.mean(gray)
        
        # Calculate standard deviation of pixel values
        std_dev = np.std(gray)
        
        # Check if image is mostly white (high average pixel value)
        # and has low variation (low standard deviation)
        if avg_pixel > 240 and std_dev < 20:
            logging.info(f"Image {image_path} appears to be mostly white (avg: {avg_pixel:.2f}, std: {std_dev:.2f})")
            return False
        
        # Check for faces in the image
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            logging.info(f"Image {image_path} contains a face.")
            return True
        
        # Check for placeholder (e.g., a simple icon or default image)
        # You can add more sophisticated checks here if needed
        if is_placeholder(img):
            logging.info(f"Image {image_path} contains a placeholder.")
            return True
        
        return False
    except Exception as e:
        logging.error(f"Error analyzing image {image_path}: {e}")
        return False

def is_placeholder(img):
    """
    Check if the image is a placeholder.
    This is a simple example; you can enhance it based on your needs.
    """
    # Example: Check if the image is a solid color or contains a specific pattern
    # This is a basic check; you might need a more sophisticated approach
    unique_colors = np.unique(img.reshape(-1, img.shape[2]), axis=0)
    if len(unique_colors) < 10:  # Arbitrary threshold for unique colors
        return True
    return False

def upload_image_to_cloudinary(local_image_path):
    try:
        # Crop the image to include only the top 10% to 60%
        img = Image.open(local_image_path)
        width, height = img.size
        top = int(height * 0.10)
        bottom = int(height * 0.60)
        cropped_img = img.crop((0, top, width, bottom))
        
        # Save the cropped image temporarily
        cropped_image_path = local_image_path.replace(".jpg", "_cropped.jpg")
        cropped_img.save(cropped_image_path)
        
        # Check if the cropped image is valid
        if not is_valid_image(cropped_image_path):
            os.remove(cropped_image_path)
            return None
        
        # Upload cropped image to Cloudinary
        upload_result = cloudinary.uploader.upload(
            cropped_image_path, 
            folder='video_participants',
            overwrite=True
        )
        
        # Clean up the temporary cropped image
        os.remove(cropped_image_path)
        
        return upload_result['secure_url']
    except Exception as e:
        logging.error(f"Cloudinary upload error: {e}")
        if os.path.exists(cropped_image_path):
            os.remove(cropped_image_path)
        return None

def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"Error extracting text from {image_path}: {e}")
        return ""

def process_raw_data_with_gemini(raw_text):
    try:
        response = gemini_client.process_text(
            text=raw_text,
            instructions="Extract structured participant information precisely. Required Fields: Name, Title, Organization, Website, Location, Participation Type"
        )
        return response
    except Exception as e:
        logging.error(f"Gemini processing error: {e}")
        return "{}"

def process_video(video_path, output_folder):
    # Get the list of frames
    frames = [os.path.join(output_folder, f) for f in os.listdir(output_folder) if f.endswith('.jpg')]
    # frames = frames[:50]  # Process only first 50 frames
    
    raw_data = []
    processed_frames = 0
    
    # First pass: Generate raw-data.txt with Cloudinary URLs
    for frame in frames:
        logging.info(f"Processing frame: {frame}")
        
        # Upload and get Cloudinary URL
        cloudinary_url = upload_image_to_cloudinary(frame)
        if not cloudinary_url:
            logging.info(f"Skipping frame {frame} - invalid image or upload failed")
            continue
            
        # Extract text
        raw_text = extract_text_from_image(frame)
        
        if 'on-site' in raw_text.lower():
            # Store raw data with Cloudinary URL
            frame_data = {
                'image_url': cloudinary_url,
                'raw_text': raw_text
            }
            raw_data.append(frame_data)
            processed_frames += 1
            logging.info(f"Successfully processed frame {processed_frames}")
    
    if not raw_data:
        logging.warning("No valid frames were processed. raw-data.txt will not be created.")
        return
    
    # Write raw data to file
    with open('raw-data.txt', 'w', encoding='utf-8') as f:
        for data in raw_data:
            f.write(f"=== Frame URL: {data['image_url']} ===\n")
            f.write(f"{data['raw_text']}\n\n")
    
    # Second pass: Process raw data with Gemini and generate final-output.json
    with open('raw-data.txt', 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    # Process the entire raw data file with Gemini
    structured_data = process_raw_data_with_gemini(raw_content)
    
    # Write structured data to final-output.json
    with open('final-output.json', 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=4)
    
    # Store data in MongoDB
    mongodb_uri = "mongodb+srv://1234:1234@cluster0.wir5xrk.mongodb.net/scrap-with-profile"  # MongoDB URI
    db_name = "scrap-with-profile"  # MongoDB database name
    collection_name = "create-stir-filmmakers"  # MongoDB collection name
    
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    collection = db[collection_name]
    
    # Insert structured data into MongoDB
    if isinstance(structured_data, list):
        collection.insert_many(structured_data)
    else:
        collection.insert_one(structured_data)
    
    logging.info(f"Processing complete. Processed {processed_frames} valid frames.")
    logging.info("Check raw-data.txt and final-output.json for results.")
    logging.info("Data has been stored in MongoDB.")

def main():
    video_path = "dataVideo.mp4"
    output_folder = "../data/frames"
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Process video and generate both files
    process_video(video_path, output_folder)

if __name__ == "__main__":
    main()
