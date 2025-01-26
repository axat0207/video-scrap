import os
import cv2
from PIL import Image
import pytesseract
from openai import OpenAI
import pandas as pd
import json
import re
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
import cloudinary
import cloudinary.uploader

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s: %(message)s')

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGODB_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['video_participants']
collection = db['extracted_data']

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)
# OpenAI Client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def upload_image_to_cloudinary(local_image_path):
    try:
        # Upload image to Cloudinary
        upload_result = cloudinary.uploader.upload(
            local_image_path, 
            folder='video_participants',
            overwrite=True
        )
        return upload_result['secure_url']
    except Exception as e:
        logging.error(f"Cloudinary upload error: {e}")
        return None

def extract_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    frame_count = 0
    extracted_frames = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_name = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
        cv2.imwrite(frame_name, frame)
        extracted_frames.append(frame_name)
        
        frame_count += 1

    cap.release()
    return extracted_frames

def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"Error extracting text from {image_path}: {e}")
        return ""

def ask_chatgpt(text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract structured participant information precisely."},
                {"role": "user", "content": f"""
Strictly extract details ONLY if 'Participation on-site' is present.
Required Fields: Name, Title, Organization, Website, Location, Participation Type

Important: Return a VALID JSON. If no details found, return an empty JSON {{}}.

Text to analyze:
{text}
"""}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"ChatGPT API error: {e}")
        return "{}"

def clean_and_validate_json(json_str):
    try:
        # Remove code block markers if present
        json_str = re.sub(r'^```json\n', '', json_str)
        json_str = re.sub(r'\n```$', '', json_str)
        
        # Parse JSON
        parsed_data = json.loads(json_str.strip())
        
        # Validate required fields
        required_fields = ['Name', 'Title', 'Organization', 'Website', 'Location']
        if not all(field in parsed_data for field in required_fields):
            logging.warning("Missing required fields")
            return None
        
        return parsed_data
    except (json.JSONDecodeError, Exception) as e:
        logging.error(f"JSON parsing error: {e}")
        return None

def process_video(video_path, output_folder, 
                  raw_data_file="../data/raw-data.txt", 
                  ai_output_file="../data/ai-output.txt", 
                  excel_output_file="../data/ai-output.xlsx"):
    frames = extract_frames(video_path, output_folder)
    
    processed_data = []
    raw_data = []
    ai_processed_data = []

    for frame in frames:
        logging.info(f"Processing frame: {frame}")
        
        # Upload frame to Cloudinary
        cloudinary_url = upload_image_to_cloudinary(frame)
        
        raw_text = extract_text_from_image(frame)
        logging.info(f"Extracted text: {raw_text[:100]}...")
        
        if 'on-site' in raw_text.lower():
            # Collect raw data with Cloudinary URL instead of local path
            raw_data.append(f"--- Frame: {cloudinary_url} ---\n{raw_text}\n\n")
            
            ai_response = ask_chatgpt(raw_text)
            logging.info(f"ChatGPT Response: {ai_response}")
            
            # Collect AI processed data with Cloudinary URL
            ai_processed_data.append(f"--- Frame: {cloudinary_url} ---\n{ai_response}\n\n")
            
            participant_data = clean_and_validate_json(ai_response)
            
            if participant_data:
                # Replace local frame path with Cloudinary URL
                participant_data['frame_path'] = cloudinary_url
                
                # Prevent duplicate users
                existing_user = collection.find_one({
                    'Name': participant_data['Name'],
                    'Organization': participant_data['Organization']
                })
                
                if not existing_user:
                    # Insert into MongoDB only if user doesn't exist
                    collection.insert_one(participant_data)
                    processed_data.append(participant_data)
                    logging.info(f"Added new participant: {participant_data.get('Name', 'Unknown')}")
                else:
                    logging.info(f"Duplicate user skipped: {participant_data.get('Name', 'Unknown')}")
    
    # Write raw data to file
    with open(raw_data_file, 'w', encoding='utf-8') as f:
        f.writelines(raw_data)
    
    # Write AI processed data to file
    with open(ai_output_file, 'w', encoding='utf-8') as f:
        f.writelines(ai_processed_data)
    
    # Export to Excel
    if processed_data:
        df = pd.DataFrame(processed_data)
        df.to_excel(excel_output_file, index=False)
        logging.info(f"Exported {len(processed_data)} participants to {excel_output_file}")
    
    return processed_data

def main():
    video_path = "dataVideo.mp4"
    output_folder = "../data/frames"
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Process video and store in MongoDB
    processed_data = process_video(video_path, output_folder)
    
    logging.info(f"Processed {len(processed_data)} participants")

if __name__ == "__main__":
    main()