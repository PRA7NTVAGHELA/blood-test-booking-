from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Download required NLTK data
try:
    nltk.data.find('corpora/stopwords')
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK data...")
    nltk.download('stopwords')
    nltk.download('punkt')

# Load environment variables from .env file
load_dotenv()

# Load the model and vectorizer
model = joblib.load('symptom_checker_model.pkl')
vectorizer = joblib.load('tfidf_vectorizer.pkl')

# Load the dataset
try:
    df = pd.read_csv('Symptom2Disease_Final.csv')
    if not all(col in df.columns for col in ['disease', 'recommended_tests', 'medications']):
        raise ValueError("CSV is missing required columns: 'disease', 'recommended_tests', 'medications'")
except Exception as e:
    print(f"Error loading dataset: {e}")
    df = None

# Initialize the Flask app
app = Flask(__name__)

# MySQL Configuration using environment variables
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Function to connect to MySQL
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Create table if it doesn't exist
def init_db():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blood_test_bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                disease VARCHAR(255),
                test_name VARCHAR(255),
                booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        cursor.close()
        connection.close()

# Text cleaning function
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    return ' '.join(tokens)

@app.route('/predict', methods=['POST'])
def predict():
    if df is None:
        return jsonify({"error": "Dataset not loaded. Check 'symptom_data.csv' file."}), 500

    data = request.json
    if 'symptoms' not in data:
        return jsonify({"error": "Missing 'symptoms' field in request."}), 400

    user_input = data['symptoms']
    cleaned_input = clean_text(user_input)
    input_vec = vectorizer.transform([cleaned_input])

    prediction_prob = model.predict_proba(input_vec)
    predicted_label = model.classes_[prediction_prob.argmax()]
    confidence = round(prediction_prob.max(), 2)

    disease_info = df[df['disease'] == predicted_label]
    if disease_info.empty:
        return jsonify({"predicted_disease": predicted_label, "confidence": confidence, "message": "No additional data available."})

    disease_info = disease_info.iloc[0]
    recommended_tests = eval(disease_info['recommended_tests']) if 'recommended_tests' in disease_info else []
    medications = eval(disease_info['medications']) if 'medications' in disease_info else []

    return jsonify({
        "predicted_disease": predicted_label,
        "confidence": confidence,
        "recommended_tests": recommended_tests,
        "medications": medications
    })

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/book_blood_test', methods=['POST'])
def book_blood_test():
    data = request.json
    required_fields = ['patient_name', 'email', 'disease', 'test_name']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    patient_name = data['patient_name']
    email = data['email']
    phone = data.get('phone', '')
    disease = data['disease']
    test_name = data['test_name']

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO blood_test_bookings (patient_name, email, phone, disease, test_name)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (patient_name, email, phone, disease, test_name))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({"message": "Blood test booked successfully!"}), 200
        except Error as e:
            print(f"Error inserting into database: {e}")
            return jsonify({"error": "Failed to book the test"}), 500
    else:
        return jsonify({"error": "Database connection failed"}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)