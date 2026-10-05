import os
import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(MODELS_DIR, exist_ok=True)


DATASET_PATH = os.path.join(
    DATA_DIR,
    "customer_support_tickets.csv"
)


if not os.path.exists(DATASET_PATH):
    print("Dataset file not found:")
    print(DATASET_PATH)
    exit()


df = pd.read_csv(DATASET_PATH)


print("Dataset loaded successfully")
print()
print("Dataset shape:")
print(df.shape)


df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)


print()
print("Dataset columns:")
print(df.columns.tolist())


required_columns = [
    "ticket_subject",
    "ticket_description",
    "ticket_type",
    "ticket_priority"
]


missing_columns = []

for column in required_columns:
    if column not in df.columns:
        missing_columns.append(column)


if missing_columns:
    print("Required columns are missing:")
    print(missing_columns)
    exit()


print()
print("Total rows before cleaning:")
print(len(df))


df = df.dropna(
    subset=[
        "ticket_subject",
        "ticket_description",
        "ticket_type",
        "ticket_priority"
    ]
)


df = df.drop_duplicates()


print()
print("Total rows after cleaning:")
print(len(df))


df["text"] = (
    df["ticket_subject"].astype(str)
    + " "
    + df["ticket_description"].astype(str)
)


X = df["text"]


print()
print("Ticket Type Distribution:")
print(df["ticket_type"].value_counts())


print()
print("Ticket Priority Distribution:")
print(df["ticket_priority"].value_counts())


# CATEGORY MODEL

y_category = df["ticket_type"].astype(str)


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_category,
    test_size=0.20,
    random_state=42,
    stratify=y_category
)


category_model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=15000
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=3000,
            class_weight="balanced"
        )
    )
])


print()
print("Training ticket classification model...")


category_model.fit(
    X_train,
    y_train
)


category_predictions = category_model.predict(
    X_test
)


category_accuracy = accuracy_score(
    y_test,
    category_predictions
)


print()
print("Ticket Classification Accuracy:")
print(round(category_accuracy * 100, 2), "%")


CATEGORY_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "ticket_classifier.pkl"
)


joblib.dump(
    category_model,
    CATEGORY_MODEL_PATH
)


print()
print("Ticket classification model saved:")
print(CATEGORY_MODEL_PATH)


# PRIORITY MODEL

y_priority = df["ticket_priority"].astype(str)


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_priority,
    test_size=0.20,
    random_state=42,
    stratify=y_priority
)


priority_model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=15000
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=3000,
            class_weight="balanced"
        )
    )
])


print()
print("Training priority prediction model...")


priority_model.fit(
    X_train,
    y_train
)


priority_predictions = priority_model.predict(
    X_test
)


priority_accuracy = accuracy_score(
    y_test,
    priority_predictions
)


print()
print("Priority Prediction Accuracy:")
print(round(priority_accuracy * 100, 2), "%")


PRIORITY_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "priority_classifier.pkl"
)


joblib.dump(
    priority_model,
    PRIORITY_MODEL_PATH
)


print()
print("Priority prediction model saved:")
print(PRIORITY_MODEL_PATH)


print()
print("MODEL TRAINING COMPLETED")

print()
print(
    "Ticket Classification Accuracy:",
    round(category_accuracy * 100, 2),
    "%"
)

print(
    "Priority Prediction Accuracy:",
    round(priority_accuracy * 100, 2),
    "%"
)

print()
print("Models created:")
print("models/ticket_classifier.pkl")
print("models/priority_classifier.pkl")