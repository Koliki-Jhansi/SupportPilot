import os
import joblib

BASE_DIR = os.path.dirname(
os.path.abspath(file)
)

MODELS_DIR = os.path.join(
BASE_DIR,
"models"
)

VECTORIZER_PATH = os.path.join(
MODELS_DIR,
"tfidf_vectorizer.pkl"
)

SEVERITY_MODEL_PATH = os.path.join(
MODELS_DIR,
"severity_model.pkl"
)

_vectorizer = None
_severity_model = None

def load_models():

global _vectorizer
global _severity_model

if _vectorizer is None:

    _vectorizer = joblib.load(
        VECTORIZER_PATH
    )

if _severity_model is None:

    _severity_model = joblib.load(
        SEVERITY_MODEL_PATH
    )

def predict_severity(title, description):

load_models()

text = f"{title} {description}"

vector = _vectorizer.transform(
    [text]
)

prediction = _severity_model.predict(
    vector
)[0]

probabilities = (
    _severity_model.predict_proba(
        vector
    )[0]
)

confidence = (
    max(probabilities) * 100
)

return {
    "severity": str(prediction),
    "confidence": round(
        float(confidence),
        2
    )
}