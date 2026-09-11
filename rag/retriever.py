import os
import json

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

KNOWLEDGE_BASE_PATH = os.path.join(
    BASE_DIR,
    "data",
    "knowledge_base.json"
)


class KnowledgeRetriever:

    def __init__(self):

        self.documents = self.load_documents()

        self.texts = []

        for doc in self.documents:

            # Repeat title/category so they have more influence
            text = (
                doc["title"] + " "
                + doc["title"] + " "
                + doc["category"] + " "
                + doc["category"] + " "
                + doc["content"]
            )

            self.texts.append(text)

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )

        self.document_vectors = (
            self.vectorizer.fit_transform(
                self.texts
            )
        )


    def load_documents(self):

        if not os.path.exists(
            KNOWLEDGE_BASE_PATH
        ):
            raise FileNotFoundError(
                "knowledge_base.json not found"
            )

        with open(
            KNOWLEDGE_BASE_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            documents = json.load(file)

        return documents


    def search(
        self,
        query,
        top_k=3,
        min_relevance=0.15
    ):

        query_vector = (
            self.vectorizer.transform(
                [query]
            )
        )

        scores = cosine_similarity(
            query_vector,
            self.document_vectors
        )[0]

        ranked_indices = (
            scores.argsort()[::-1]
        )

        results = []

        for index in ranked_indices:

            score = float(
                scores[index]
            )

            if score < min_relevance:
                continue

            document = self.documents[index]

            results.append({
                "id": document["id"],
                "title": document["title"],
                "category": document["category"],
                "content": document["content"],
                "score": round(score, 4)
            })

            if len(results) >= top_k:
                break

        return results