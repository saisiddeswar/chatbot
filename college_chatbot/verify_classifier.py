import pandas as pd
import joblib
import os

print("--- Data Verification ---")
try:
    df = pd.read_csv("data/classifier_data.csv")
    print(f"Dataset Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    col = "category" if "category" in df.columns else "Category"
    print("\nCategory Distribution:")
    print(df[col].value_counts())
except Exception as e:
    print(f"Error reading dataset: {e}")

print("\n--- Model Verification ---")
if os.path.exists("classifier/classifier.pkl"):
    print("classifier.pkl exists.")
    try:
        model = joblib.load("classifier/classifier.pkl")
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
else:
    print("classifier.pkl NOT found.")
