# train_model.py
import pandas as pd  
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib

# Load dataset
try:
    df = pd.read_csv("Symptom2Disease.csv")
    print("Dataset loaded successfully!")
except FileNotFoundError:
    print("Error: Place Symptom2Disease.csv in the same directory as this script!")
    exit()

# Preprocess text
df['cleaned_symptoms'] = df['Symptoms'].str.lower().str.replace('[^a-z\s]', '', regex=True)

# Create TF-IDF vectors
tfidf = TfidfVectorizer(max_features=1000)
X = tfidf.fit_transform(df['cleaned_symptoms'])
y = df['Disease']

# Train and save model
model = MultinomialNB()
model.fit(X, y)

joblib.dump(model, 'symptom_checker_model.pkl')
joblib.dump(tfidf, 'tfidf_vectorizer.pkl')

print("Model files generated successfully!")
print("Files created:")
print("- symptom_checker_model.pkl")
print("- tfidf_vectorizer.pkl")