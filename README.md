# Filmmakers Directory

## Project Overview
A Flask web application that displays a directory of filmmakers extracted from video frames using computer vision and AI technologies.

## Features
- Extract participant information from video frames
- OCR text extraction
- AI-powered data parsing
- MongoDB storage
- Cloudinary image hosting
- Responsive web interface

## Prerequisites
- Python 3.8+
- MongoDB
- Cloudinary account
- OpenAI API key
- Tesseract OCR

## Installation

### Dependencies
```bash
pip install flask pymongo opencv-python-headless Pillow pytesseract openai pandas python-dotenv python-multipart cloudinary
```

### Environment Variables
Create a `.env` file with:
```
MONGODB_URI=your_mongodb_connection_string
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
OPENAI_API_KEY=your_openai_api_key
```

## Workflow
1. Video processing script extracts frames
2. Tesseract OCR performs text extraction
3. OpenAI processes extracted text
4. Data stored in MongoDB
5. Flask application renders web interface

## Deployment
Recommended platforms:
- Render
- Heroku
- PythonAnywhere

## Technologies
- Flask
- MongoDB
- OpenAI GPT
- Cloudinary
- Tesseract OCR
- Tailwind CSS

## License
MIT License
