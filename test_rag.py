from rag.pipeline import run_rag_pipeline


ticket = {
    "id": 1,
    "title": "VPN connection failing",
    "description": "I cannot connect to the corporate VPN. Authentication keeps failing.",
    "category": "Network Connectivity",
    "priority": "P2"
}


result = run_rag_pipeline(ticket)


print("\n--- ANALYSIS ---")
print(result["analysis"])

print("\n--- RETRIEVED DOCUMENTS ---")

for doc in result["retrieved_documents"]:
    print(
        doc["id"],
        "-",
        doc["title"],
        "- score:",
        doc["score"]
    )

print("\n--- GENERATED RESOLUTION ---")
print(result["resolution"])

print("\n--- STATUS ---")
print(result["status"])