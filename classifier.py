import os
import joblib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS_DIR = os.path.join(
    BASE_DIR,
    "models"
)


CATEGORY_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "ticket_classifier.pkl"
)


PRIORITY_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "priority_classifier.pkl"
)


category_model = None
priority_model = None


def load_models():

    global category_model
    global priority_model

    if not os.path.exists(CATEGORY_MODEL_PATH):

        raise FileNotFoundError(
            "ticket_classifier.pkl not found. Run train_model.py first."
        )


    if not os.path.exists(PRIORITY_MODEL_PATH):

        raise FileNotFoundError(
            "priority_classifier.pkl not found. Run train_model.py first."
        )


    category_model = joblib.load(
        CATEGORY_MODEL_PATH
    )


    priority_model = joblib.load(
        PRIORITY_MODEL_PATH
    )


    print("Ticket classification model loaded successfully")

    print("Priority prediction model loaded successfully")


def get_severity(priority, text):

    priority = str(priority).lower()

    text = text.lower()


    urgent_words = [

        "urgent",
        "immediately",
        "critical",
        "important",
        "meeting",
        "client",
        "cannot work",
        "can't work",
        "system down",
        "not working"

    ]


    if any(word in text for word in urgent_words):

        return "High"


    if "critical" in priority or priority == "p1":

        return "Critical"


    if "high" in priority or priority == "p2":

        return "High"


    if "medium" in priority or priority == "p3":

        return "Medium"


    if "low" in priority or priority == "p4":

        return "Low"


    if priority == "urgent":

        return "High"


    return "Medium"


def classify_ticket(title, description):

    global category_model
    global priority_model


    if category_model is None or priority_model is None:

        load_models()


    text = (
        str(title)
        + " "
        + str(description)
    )


    category = category_model.predict(
        [text]
    )[0]


    category_probabilities = category_model.predict_proba(
        [text]
    )[0]


    confidence = round(

        max(category_probabilities) * 100,

        2

    )


    priority = priority_model.predict(
        [text]
    )[0]


    severity = get_severity(

        priority,

        text

    )


    return {

        "category": str(category),

        "severity": str(severity),

        "priority": str(priority),

        "confidence": confidence

    }