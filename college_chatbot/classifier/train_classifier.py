import joblib
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Load dataset
df = pd.read_csv("data/classifier_data.csv")

# Ensure column names map correctly if they differ
# The new dataset has 'text' and 'category'. Let's handle both or rename.
if 'text' in df.columns:
    X = df["text"]
else:
    X = df["Question"]
    
if 'category' in df.columns:
    y = df["category"]
else:
    y = df["Category"]

# Pipeline: Vectorizer + Multinomial Naive Bayes
model = Pipeline([
    ("vectorizer", CountVectorizer(
        lowercase=True,
        stop_words="english"
    )),
    ("classifier", MultinomialNB())
])

# Train model
model.fit(X, y)

# Save trained classifier
joblib.dump(model, "classifier/classifier.pkl")

print("[OK] Classifier trained and classifier.pkl created successfully")
