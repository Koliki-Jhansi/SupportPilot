def assign_priority(severity):

severity = str(severity).strip().lower()

priority_map = {
    "critical": "P1",
    "high": "P1",
    "medium": "P2",
    "low": "P3"
}

return priority_map.get(
    severity,
    "P3"
)