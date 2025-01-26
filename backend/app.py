from flask import Flask, render_template
from pymongo import MongoClient
import os

app = Flask(__name__)

# Modify the MongoDB connection to use the new database and collection
client = MongoClient(os.getenv('MONGODB_URI'))
filmmakers_db = client['filmmakers']
participants_collection = filmmakers_db['participants']

@app.route('/')
def index():
    # Fetch all participants from the filmmakers collection
    filmmakers = list(participants_collection.find())
    
    # Convert MongoDB ObjectId to string for JSON serialization
    for filmmaker in filmmakers:
        filmmaker['_id'] = str(filmmaker['_id'])
    
    return render_template('index.html', filmmakers=filmmakers)

if __name__ == '__main__':
    app.run(debug=True)

