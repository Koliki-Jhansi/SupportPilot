from rag.analyzer import analyze_ticket
from rag.retriever import KnowledgeRetriever
from rag.generator import generate_resolution


retriever = KnowledgeRetriever()


def run_rag_pipeline(ticket):

    # ----------------------------------
    # STEP 1
    # Analyze ticket
    # ----------------------------------

    analysis = analyze_ticket(
        ticket
    )


    # ----------------------------------
    # STEP 2
    # Retrieve relevant knowledge
    # ----------------------------------

    retrieved_documents = (
        retriever.search(
            analysis["query"],
            top_k=3,
            min_relevance=0.15
        )
    )


    # ----------------------------------
    # STEP 3
    # Build RAG context
    # ----------------------------------

    context_parts = []


    for document in retrieved_documents:

        context_parts.append(
            (
                f"Source: {document['id']}\n"
                f"Title: {document['title']}\n"
                f"Category: "
                f"{document['category']}\n"
                f"Relevance: "
                f"{document['score']}\n"
                f"Content: "
                f"{document['content']}"
            )
        )


    context = "\n\n".join(
        context_parts
    )


    # ----------------------------------
    # STEP 4
    # Generate issue-specific resolution
    # ----------------------------------

    generated = generate_resolution(
        ticket,
        retrieved_documents,
        analysis
    )


    return {
        "ticket": ticket,
        "analysis": analysis,
        "retrieved_documents":
            retrieved_documents,
        "context": context,
        "resolution":
            generated["resolution"],
        "status":
            generated["status"],
        "sources":
            generated["sources"]
    }