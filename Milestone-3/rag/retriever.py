import os
import json
import math
import re
from collections import Counter


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

        self.document_tokens = []

        for doc in self.documents:

            text = (
                doc["title"]
                + " "
                + doc["category"]
                + " "
                + doc["content"]
            )

            self.document_tokens.append(
                self.tokenize(text)
            )

        self.idf = self.calculate_idf()


    # =====================================================
    # LOAD KNOWLEDGE BASE
    # =====================================================

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

            return json.load(file)


    # =====================================================
    # TOKENIZE TEXT
    # =====================================================

    def tokenize(self, text):

        text = text.lower()

        words = re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text
        )

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "is",
            "are",
            "to",
            "of",
            "for",
            "in",
            "on",
            "with",
            "this",
            "that",
            "be",
            "if",
            "it"
        }

        return [
            word
            for word in words
            if word not in stop_words
        ]


    # =====================================================
    # CALCULATE IDF
    # =====================================================

    def calculate_idf(self):

        total_documents = len(
            self.document_tokens
        )

        document_frequency = Counter()

        for tokens in self.document_tokens:

            unique_words = set(tokens)

            for word in unique_words:

                document_frequency[word] += 1


        idf = {}

        for word, frequency in (
            document_frequency.items()
        ):

            idf[word] = (
                math.log(
                    (total_documents + 1)
                    /
                    (frequency + 1)
                )
                + 1
            )

        return idf


    # =====================================================
    # TF-IDF VECTOR
    # =====================================================

    def tfidf_vector(self, tokens):

        term_frequency = Counter(tokens)

        total_terms = len(tokens)

        vector = {}

        if total_terms == 0:

            return vector


        for word, count in (
            term_frequency.items()
        ):

            tf = count / total_terms

            idf = self.idf.get(
                word,
                0
            )

            vector[word] = tf * idf


        return vector


    # =====================================================
    # COSINE SIMILARITY
    # =====================================================

    def cosine_similarity(
        self,
        vector1,
        vector2
    ):

        common_words = (
            set(vector1.keys())
            &
            set(vector2.keys())
        )

        dot_product = sum(
            vector1[word]
            *
            vector2[word]
            for word in common_words
        )


        magnitude1 = math.sqrt(
            sum(
                value ** 2
                for value
                in vector1.values()
            )
        )


        magnitude2 = math.sqrt(
            sum(
                value ** 2
                for value
                in vector2.values()
            )
        )


        if (
            magnitude1 == 0
            or
            magnitude2 == 0
        ):

            return 0.0


        return (
            dot_product
            /
            (
                magnitude1
                *
                magnitude2
            )
        )


    # =====================================================
    # SEARCH KNOWLEDGE BASE
    # =====================================================

    def search(
        self,
        query,
        top_k=3,
        min_relevance=0.05
    ):

        query_tokens = self.tokenize(
            query
        )

        query_vector = self.tfidf_vector(
            query_tokens
        )

        results = []


        for index, tokens in enumerate(
            self.document_tokens
        ):

            document_vector = (
                self.tfidf_vector(
                    tokens
                )
            )

            score = self.cosine_similarity(
                query_vector,
                document_vector
            )


            if score < min_relevance:

                continue


            document = self.documents[
                index
            ]


            results.append({

                "id":
                    document["id"],

                "title":
                    document["title"],

                "category":
                    document["category"],

                "content":
                    document["content"],

                "score":
                    round(score, 4)

            })


        results.sort(
            key=lambda item:
                item["score"],
            reverse=True
        )


        return results[:top_k]