def analyze_ticket(ticket):

    title = str(ticket.get("title", ""))

    description = str(ticket.get("description", ""))

    category = str(ticket.get("category", ""))

    priority = str(ticket.get("priority", ""))


    text = (
        title + " " + description
    ).lower()


    possible_keywords = [

        "vpn",
        "network",
        "firewall",
        "authentication",
        "timeout",
        "connection",
        "dns",
        "password",
        "login",
        "software",
        "installation",
        "hardware",
        "printer",
        "email",
        "wifi",
        "internet",
        "server",
        "system",
        "crash",
        "slow"

    ]


    keywords = []


    for keyword in possible_keywords:

        if keyword in text:

            keywords.append(keyword)


    query = " ".join(
        [
            title,
            description,
            category,
            " ".join(keywords)
        ]
    )


    return {

        "ticket_id": ticket.get("id"),

        "category": category,

        "priority": priority,

        "keywords": keywords,

        "query": query.strip()

    }