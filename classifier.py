import os
import joblib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

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


# ============================================================
# LOAD MODELS
# ============================================================

def load_models():

    global category_model
    global priority_model

    if not os.path.exists(CATEGORY_MODEL_PATH):

        raise FileNotFoundError(
            "ticket_classifier.pkl not found. "
            "Run train_model.py first."
        )

    if not os.path.exists(PRIORITY_MODEL_PATH):

        raise FileNotFoundError(
            "priority_classifier.pkl not found. "
            "Run train_model.py first."
        )

    category_model = joblib.load(
        CATEGORY_MODEL_PATH
    )

    priority_model = joblib.load(
        PRIORITY_MODEL_PATH
    )

    print(
        "Ticket classification model loaded successfully"
    )

    print(
        "Priority prediction model loaded successfully"
    )


# ============================================================
# SEVERITY
# ============================================================

def get_severity(priority, text):

    priority = str(priority).lower()
    text = str(text).lower()

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
        "not working",
    ]

    if any(
        word in text
        for word in urgent_words
    ):
        return "High"

    if (
        "critical" in priority
        or priority == "p1"
    ):
        return "Critical"

    if (
        "high" in priority
        or priority == "p2"
    ):
        return "High"

    if (
        "medium" in priority
        or priority == "p3"
    ):
        return "Medium"

    if (
        "low" in priority
        or priority == "p4"
    ):
        return "Low"

    if priority == "urgent":
        return "High"

    return "Medium"


# ============================================================
# CLASSIFY TICKET
# ============================================================

def classify_ticket(title, description):

    global category_model
    global priority_model

    if (
        category_model is None
        or priority_model is None
    ):
        load_models()

    text = (
        str(title)
        + " "
        + str(description)
    )

    category = category_model.predict(
        [text]
    )[0]

    category_probabilities = (
        category_model.predict_proba(
            [text]
        )[0]
    )

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
        "confidence": confidence,
    }


# ============================================================
# MILESTONE 4
# CLASSIFIER EVALUATION
# ============================================================

def evaluate_category_predictions(
    actual_categories,
    predicted_categories
):

    actual_categories = [
        str(value)
        for value in (
            actual_categories
            or []
        )
    ]

    predicted_categories = [
        str(value)
        for value in (
            predicted_categories
            or []
        )
    ]

    if (
        len(actual_categories)
        != len(predicted_categories)
    ):

        raise ValueError(
            "actual_categories and predicted_categories "
            "must contain the same number of values."
        )

    if not actual_categories:

        return {
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "sample_count": 0,
            "correct_predictions": 0,
            "incorrect_predictions": 0,
            "labels": [],
            "confusion_matrix": [],
        }

    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix,
    )

    labels = sorted(
        set(
            actual_categories
            +
            predicted_categories
        )
    )

    accuracy = accuracy_score(
        actual_categories,
        predicted_categories
    )

    precision = precision_score(
        actual_categories,
        predicted_categories,
        average="weighted",
        zero_division=0
    )

    recall = recall_score(
        actual_categories,
        predicted_categories,
        average="weighted",
        zero_division=0
    )

    f1 = f1_score(
        actual_categories,
        predicted_categories,
        average="weighted",
        zero_division=0
    )

    matrix = confusion_matrix(
        actual_categories,
        predicted_categories,
        labels=labels
    ).tolist()

    correct_predictions = sum(
        1
        for actual, predicted
        in zip(
            actual_categories,
            predicted_categories
        )
        if actual == predicted
    )

    return {
        "accuracy":
            round(float(accuracy) * 100, 2),

        "precision":
            round(float(precision) * 100, 2),

        "recall":
            round(float(recall) * 100, 2),

        "f1_score":
            round(float(f1) * 100, 2),

        "sample_count":
            len(actual_categories),

        "correct_predictions":
            correct_predictions,

        "incorrect_predictions":
            len(actual_categories)
            - correct_predictions,

        "labels":
            labels,

        "confusion_matrix":
            matrix,
    }


def evaluate_category_model(
    test_samples
):

    global category_model

    if category_model is None:
        load_models()

    actual_categories = []
    predicted_categories = []
    prediction_details = []

    for sample in (
        test_samples
        or []
    ):

        if not isinstance(
            sample,
            dict
        ):
            continue

        actual_category = (
            sample.get(
                "actual_category"
            )
        )

        if (
            actual_category is None
            or not str(
                actual_category
            ).strip()
        ):
            continue

        title = sample.get(
            "title",
            ""
        )

        description = sample.get(
            "description",
            ""
        )

        text = (
            str(title)
            + " "
            + str(description)
        )

        predicted_category = (
            category_model.predict(
                [text]
            )[0]
        )

        probabilities = (
            category_model.predict_proba(
                [text]
            )[0]
        )

        confidence = round(
            max(probabilities) * 100,
            2
        )

        actual_category = str(
            actual_category
        )

        predicted_category = str(
            predicted_category
        )

        actual_categories.append(
            actual_category
        )

        predicted_categories.append(
            predicted_category
        )

        prediction_details.append(
            {
                "title":
                    str(title),

                "description":
                    str(description),

                "actual_category":
                    actual_category,

                "predicted_category":
                    predicted_category,

                "confidence":
                    confidence,

                "correct":
                    actual_category
                    ==
                    predicted_category,
            }
        )

    evaluation = (
        evaluate_category_predictions(
            actual_categories,
            predicted_categories
        )
    )

    evaluation["predictions"] = (
        prediction_details
    )

    return evaluation


def verify_classification(
    predicted_category,
    actual_category
):

    if (
        predicted_category is None
        or actual_category is None
    ):
        return None

    predicted = str(
        predicted_category
    ).strip().lower()

    actual = str(
        actual_category
    ).strip().lower()

    if (
        not predicted
        or not actual
    ):
        return None

    return (
        predicted
        ==
        actual
    )


def get_classifier_info():

    global category_model
    global priority_model

    if (
        category_model is None
        or priority_model is None
    ):
        load_models()

    category_classes = (
        [
            str(value)
            for value
            in category_model.classes_
        ]
        if hasattr(
            category_model,
            "classes_"
        )
        else []
    )

    priority_classes = (
        [
            str(value)
            for value
            in priority_model.classes_
        ]
        if hasattr(
            priority_model,
            "classes_"
        )
        else []
    )

    return {
        "category_model_loaded":
            category_model is not None,

        "priority_model_loaded":
            priority_model is not None,

        "category_classes":
            category_classes,

        "priority_classes":
            priority_classes,

        "category_model_path":
            CATEGORY_MODEL_PATH,

        "priority_model_path":
            PRIORITY_MODEL_PATH,
    }


if __name__ == "__main__":

    load_models()

    print(
        get_classifier_info()
    )