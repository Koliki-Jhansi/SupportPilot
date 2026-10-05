import re


def extract_steps(content):

    steps = re.findall(
        r"\d+\.\s*(.*?)(?=\s+\d+\.|$)",
        content
    )

    cleaned = []

    if steps:

        for step in steps:

            step = step.strip()

            if step:
                cleaned.append(step)

    else:

        sentences = content.split(".")

        for sentence in sentences:

            sentence = sentence.strip()

            if sentence:
                cleaned.append(sentence)

    return cleaned


def calculate_step_score(
    step,
    keywords,
    ticket_words
):

    step_lower = step.lower()

    score = 0

    # Strong preference for detected issue keywords
    for keyword in keywords:

        if keyword.lower() in step_lower:
            score += 4

    # Also compare important words from ticket
    for word in ticket_words:

        if word in step_lower:
            score += 1

    return score


def generate_resolution(
    ticket,
    retrieved_documents,
    analysis=None
):

    if not retrieved_documents:

        return {
            "status": "INSUFFICIENT_KNOWLEDGE",
            "resolution": (
                "No sufficiently relevant knowledge-base "
                "information was found for this issue.\n\n"
                "The ticket should be escalated to the "
                "appropriate IT support team."
            ),
            "sources": []
        }


    if analysis is None:
        analysis = {}


    keywords = analysis.get(
        "keywords",
        []
    )


    title = str(
        ticket.get("title", "")
    ).lower()

    description = str(
        ticket.get("description", "")
    ).lower()


    raw_words = re.findall(
        r"\b[a-zA-Z]{4,}\b",
        title + " " + description
    )


    ignored_words = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "cannot",
        "could",
        "would",
        "there",
        "their",
        "issue",
        "problem",
        "please",
        "when",
        "after",
        "before"
    }


    ticket_words = set()

    for word in raw_words:

        word = word.lower()

        if word not in ignored_words:
            ticket_words.add(word)


    candidate_steps = []

    sources = []


    top_score = retrieved_documents[0]["score"]


    for document in retrieved_documents:

        # Ignore documents much weaker than the best match
        if (
            top_score > 0
            and document["score"] < top_score * 0.50
        ):
            continue


        sources.append({
            "id": document["id"],
            "title": document["title"],
            "score": document["score"]
        })


        steps = extract_steps(
            document["content"]
        )


        # Avoid taking every step from every article
        for step in steps[:5]:

            step_score = calculate_step_score(
                step,
                keywords,
                ticket_words
            )

            candidate_steps.append({
                "text": step,
                "score": step_score,
                "document_score":
                    document["score"],
                "source":
                    document["id"]
            })


    # Sort issue-specific steps first
    candidate_steps.sort(
        key=lambda item: (
            item["score"],
            item["document_score"]
        ),
        reverse=True
    )


    final_steps = []

    seen = set()


    for item in candidate_steps:

        normalized = (
            item["text"]
            .lower()
            .strip()
        )

        if normalized in seen:
            continue

        seen.add(normalized)

        final_steps.append(
            item["text"]
        )

        if len(final_steps) >= 6:
            break


    if not final_steps:

        return {
            "status": "INSUFFICIENT_KNOWLEDGE",
            "resolution": (
                "Relevant knowledge-base documents were "
                "found, but no reliable troubleshooting "
                "steps could be generated.\n\n"
                "Please escalate this ticket."
            ),
            "sources": sources
        }


    primary_document = (
        retrieved_documents[0]
    )


    resolution_lines = [
        "Recommended Resolution",
        "",
        (
            "Most relevant knowledge article: "
            f"{primary_document['id']} - "
            f"{primary_document['title']}"
        ),
        "",
        "Troubleshooting steps:"
    ]


    for number, step in enumerate(
        final_steps,
        start=1
    ):

        resolution_lines.append(
            f"{number}. {step}"
        )


    resolution_lines.extend([
        "",
        (
            "Verify whether the reported issue "
            "is resolved after completing these steps."
        ),
        (
            "If the problem continues, escalate "
            "the ticket with the troubleshooting "
            "results and relevant logs."
        )
    ])


    return {
        "status": "RESOLUTION_GENERATED",
        "resolution": "\n".join(
            resolution_lines
        ),
        "sources": sources
    }