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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Explicitly set NLTK data path to a known location
NLTK_DATA_PATH = 'C:/Users/ASUS/nltk_data'
if NLTK_DATA_PATH not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DATA_PATH)  # Add to the start of the path list
print("NLTK data path set to:", nltk.data.path)

# Ensure NLTK data is downloaded
def ensure_nltk_data():
    try:
        stopwords.words('english')
        word_tokenize("test sentence")
        print("NLTK data is ready.")
    except Exception as e:
        print(f"NLTK data not found or corrupted: {e}")
        print("Attempting to download NLTK data to", NLTK_DATA_PATH)
        nltk.download('stopwords', download_dir=NLTK_DATA_PATH, quiet=False)
        nltk.download('punkt', download_dir=NLTK_DATA_PATH, quiet=False)
        try:
            stopwords.words('english')
            word_tokenize("test sentence")
            print("NLTK data downloaded and verified successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize NLTK data: {e}. Please check your NLTK installation.")

# Load environment variables from .env file
load_dotenv()

# Gmail credentials from .env
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')

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

# Create table if it doesn’t exist
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
                slot_date DATE,
                slot_time TIME,
                booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        cursor.close()
        connection.close()
    else:
        print("Failed to connect to database during initialization")

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
    required_fields = ['patient_name', 'email', 'disease', 'test_name', 'slot_date', 'slot_time']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    patient_name = data['patient_name']
    email = data['email']
    phone = data.get('phone', '')
    disease = data['disease']
    test_name = data['test_name']
    slot_date = data['slot_date']
    slot_time = data['slot_time']

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO blood_test_bookings (patient_name, email, phone, disease, test_name, slot_date, slot_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (patient_name, email, phone, disease, test_name, slot_date, slot_time))
            connection.commit()
            cursor.close()
            connection.close()

            # Send confirmation email
            if GMAIL_USER and GMAIL_PASSWORD:  # Check if credentials are provided
                subject = "Blood Test Booking Confirmation"
                body = f"""
                Dear {patient_name},

                Your blood test booking has been successfully scheduled:
                - Test: {test_name}
                - Disease: {disease}
                - Date: {slot_date}
                - Time: {slot_time}
                - Contact Phone: {phone if phone else 'Not provided'}

                Thank you for using HealthSync!
                Regards,
                The HealthSync Team
                """
                
                msg = MIMEMultipart()
                msg['From'] = GMAIL_USER
                msg['To'] = email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                try:
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(GMAIL_USER, GMAIL_PASSWORD)
                    server.sendmail(GMAIL_USER, email, msg.as_string())
                    server.quit()
                    print(f"Email sent to {email}")
                except Exception as e:
                    print(f"Failed to send email: {e}")
            else:
                print("Gmail credentials not found in .env; skipping email.")

            return jsonify({"message": "Blood test booked successfully!"}), 200
        except Error as e:
            print(f"Error inserting into database: {e}")
            return jsonify({"error": "Failed to book the test"}), 500
    else:
        return jsonify({"error": "Database connection failed"}), 500

if __name__ == '__main__':
    ensure_nltk_data()  # Ensure NLTK data is ready before starting the app
    init_db()
    app.run(debug=True)