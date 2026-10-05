
from rag.pipeline import run_rag_pipeline
import re


# ============================================================
# HELPERS
# ============================================================

AUTO_RESOLVE_THRESHOLD = 70


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_score(value):
    """Convert either a 0–1 score or a 0–100 score to 0–1."""
    score = safe_float(value)

    if score > 1:
        score /= 100

    return max(0.0, min(score, 1.0))


def is_truthy(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true", "1", "yes", "y"
    }


# ============================================================
# 1. DIAGNOSIS AGENT
# ============================================================

class DiagnosisAgent:

    def analyze(self, ticket):

        title = str(ticket.get("title") or "")
        description = str(ticket.get("description") or "")
        text = f"{title} {description}".lower()

        category = "General IT Issue"
        diagnosis = "General IT support issue detected."
        confidence = 0.80

        if any(word in text for word in [
            "vpn", "network", "internet",
            "connection", "wifi", "wi-fi",
            "dns", "firewall"
        ]):
            category = "Network / VPN"
            diagnosis = (
                "Network or VPN connectivity "
                "problem detected."
            )

        elif any(word in text for word in [
            "password", "login", "authentication",
            "authenticate", "credential", "credentials"
        ]):
            category = "Authentication"
            diagnosis = (
                "Authentication or login "
                "problem detected."
            )

        elif any(word in text for word in [
            "email", "outlook", "mailbox", "mail"
        ]):
            category = "Email"
            diagnosis = (
                "Email access or mailbox "
                "problem detected."
            )

        elif any(word in text for word in [
            "printer", "printing", "print"
        ]):
            category = "Printer"
            diagnosis = (
                "Printer or printing problem detected."
            )

        elif any(word in text for word in [
            "slow", "performance", "cpu",
            "memory", "lag", "freezing", "freeze"
        ]):
            category = "Performance"
            diagnosis = (
                "Computer performance problem detected."
            )

        elif any(word in text for word in [
            "software", "installation", "install",
            "application", "app", "crash"
        ]):
            category = "Software"
            diagnosis = (
                "Software or application problem detected."
            )

        elif any(word in text for word in [
            "hardware", "keyboard", "mouse",
            "monitor", "screen"
        ]):
            category = "Hardware"
            diagnosis = (
                "Computer hardware problem detected."
            )

        return {
            "diagnosis": diagnosis,
            "category": category,
            "confidence": confidence
        }


# ============================================================
# 2. RETRIEVAL AGENT
# ============================================================

class RetrievalAgent:

    def search(self, ticket):

        try:
            # Reuse the existing Milestone 2 RAG pipeline.
            rag_result = run_rag_pipeline(ticket)

            if not isinstance(rag_result, dict):
                rag_result = {}

            documents = (
                rag_result.get("retrieved_documents")
                or rag_result.get("documents")
                or []
            )

            similarity = 0.0

            if documents:
                first_document = documents[0]

                if isinstance(first_document, dict):
                    raw_score = first_document.get("score")

                    if raw_score is None:
                        raw_score = first_document.get(
                            "relevance"
                        )

                    if raw_score is None:
                        raw_score = first_document.get(
                            "similarity"
                        )

                    similarity = normalize_score(raw_score)

            return {
                "documents": documents,
                "similarity": similarity,
                "rag_result": rag_result,
                "kb_found": bool(documents)
            }

        except Exception as error:

            print(
                "Retrieval Agent Error:",
                repr(error)
            )

            return {
                "documents": [],
                "similarity": 0.0,
                "rag_result": {},
                "kb_found": False,
                "error": str(error)
            }


# ============================================================
# 3. RESOLUTION AGENT
# ============================================================

class ResolutionAgent:

    def generate(self, retrieval):

        rag_result = (
            retrieval.get("rag_result") or {}
        )

        resolution = (
            rag_result.get("resolution")
            or rag_result.get("response")
            or ""
        )

        if isinstance(resolution, dict):
            resolution = (
                resolution.get("response")
                or resolution.get("resolution")
                or resolution.get("steps")
                or ""
            )

        if isinstance(resolution, list):

            steps = [
                str(step).strip()
                for step in resolution
                if str(step).strip()
            ]

            response = "\n".join(
                f"{index}. {step}"
                for index, step in enumerate(
                    steps,
                    start=1
                )
            )

        else:

            response = str(resolution).strip()
            steps = self._extract_steps(response)

        generated = bool(response)

        if not generated:
            response = (
                "No suitable troubleshooting resolution "
                "could be generated from the knowledge base."
            )

        steps = steps[:8]

        return {
            "response": response,
            "steps": steps,
            "step_count": len(steps),
            "generated": generated
        }

    def _extract_steps(self, response):

        if not response:
            return []

        steps = []

        for line in response.splitlines():

            cleaned = line.strip()

            if not cleaned:
                continue

            cleaned = cleaned.lstrip("-•* ")

            parts = cleaned.split(".", 1)

            if (
                len(parts) == 2
                and parts[0].strip().isdigit()
            ):
                cleaned = parts[1].strip()

            else:
                parts = cleaned.split(")", 1)

                if (
                    len(parts) == 2
                    and parts[0].strip().isdigit()
                ):
                    cleaned = parts[1].strip()

            if cleaned:
                steps.append(cleaned)

        if len(steps) <= 1:

            sentence_steps = []

            for sentence in response.split("."):

                sentence = sentence.strip()

                if len(sentence) > 10:
                    sentence_steps.append(sentence)

            if sentence_steps:
                steps = sentence_steps

        return steps[:8]


# ============================================================
# 4. VALIDATION AGENT
# ============================================================

class ValidationAgent:

    def validate(
        self,
        diagnosis,
        retrieval,
        resolution
    ):

        diagnosis_confidence = normalize_score(
            diagnosis.get("confidence", 0)
        )

        retrieval_similarity = normalize_score(
            retrieval.get("similarity", 0)
        )

        steps = resolution.get("steps") or []

        completeness = min(
            len(steps) / 6,
            1.0
        )

        # Milestone 3 confidence formula:
        #
        # Diagnosis:               40%
        # Retrieval:               40%
        # Resolution completeness: 20%

        final_score = (
            diagnosis_confidence * 0.40
            + retrieval_similarity * 0.40
            + completeness * 0.20
        )

        confidence = round(
            final_score * 100,
            2
        )

        status = (
            "AUTO_RESOLVE"
            if confidence >= AUTO_RESOLVE_THRESHOLD
            else "ESCALATE"
        )

        return {
            "confidence": confidence,
            "status": status,
            "threshold": AUTO_RESOLVE_THRESHOLD,
            "diagnosis_score": round(
                diagnosis_confidence * 100,
                2
            ),
            "retrieval_score": round(
                retrieval_similarity * 100,
                2
            ),
            "completeness_score": round(
                completeness * 100,
                2
            )
        }


# ============================================================
# 5. ESCALATION AGENT
# MILESTONE 4: ADDITIONAL ESCALATION RULES
# ============================================================

class EscalationAgent:

    HUMAN_SUPPORT_PATTERNS = [
        r"\bhuman support\b",
        r"\bhuman agent\b",
        r"\bhuman technician\b",
        r"\breal person\b",
        r"\bspeak to (a |an )?(person|human|agent)\b",
        r"\bneed (a |an )?(person|human|technician)\b",
        r"\bmanual support\b",
        r"\bescalate (this |my )?(ticket|issue)\b"
    ]

    def should_escalate(
        self,
        validation,
        ticket=None,
        resolution=None
    ):

        ticket = ticket or {}
        resolution = resolution or {}

        reasons = []

        confidence = safe_float(
            validation.get("confidence"),
            0.0
        )

        # Rule 1: Low confidence
        if confidence < AUTO_RESOLVE_THRESHOLD:
            reasons.append(
                "AI confidence below 70% threshold."
            )

        # Rule 2: Critical priority
        priority = str(
            ticket.get("priority") or ""
        ).strip().lower()

        if priority == "critical":
            reasons.append(
                "Critical-priority ticket."
            )

        # Rule 3: Failed resolution
        #
        # A missing generated answer counts as a failure.
        # Explicit failure flags can also be supplied
        # by the application after a troubleshooting attempt.

        resolution_failed = (
            resolution.get("generated") is False
            or is_truthy(
                ticket.get("resolution_failed")
            )
            or str(
                ticket.get("resolution_status") or ""
            ).strip().upper() in {
                "FAILED",
                "UNRESOLVED"
            }
        )

        if resolution_failed:
            reasons.append(
                "AI resolution failed or was unavailable."
            )

        # Rule 4: Explicit request for human support
        title = str(ticket.get("title") or "")
        description = str(
            ticket.get("description") or ""
        )

        text = f"{title} {description}".lower()

        human_requested = (
            is_truthy(ticket.get("human_requested"))
            or any(
                re.search(pattern, text)
                for pattern in self.HUMAN_SUPPORT_PATTERNS
            )
        )

        if human_requested:
            reasons.append(
                "User requested human support."
            )

        # Rule 5: Three or more attempts
        try:
            attempts = int(
                ticket.get("attempt_count")
                or ticket.get("resolution_attempts")
                or 0
            )
        except (TypeError, ValueError):
            attempts = 0

        if attempts >= 3:
            reasons.append(
                "Three or more resolution attempts."
            )

        required = bool(reasons)

        return {
            "required": required,
            "decision": (
                "ESCALATE"
                if required
                else "NOT_REQUIRED"
            ),
            "reasons": reasons,
            "reason": (
                "; ".join(reasons)
                if reasons
                else None
            ),
            "attempt_count": attempts,
            "human_requested": human_requested
        }


# ============================================================
# 6. MULTI-AGENT ORCHESTRATOR
# ============================================================

class MultiAgentSupportPilot:

    def __init__(self):

        self.diagnosis_agent = DiagnosisAgent()
        self.retrieval_agent = RetrievalAgent()
        self.resolution_agent = ResolutionAgent()
        self.validation_agent = ValidationAgent()
        self.escalation_agent = EscalationAgent()

    def process_ticket(self, ticket):

        print("1. Diagnosis Agent")

        diagnosis = self.diagnosis_agent.analyze(
            ticket
        )

        print("2. Retrieval Agent")

        retrieval = self.retrieval_agent.search(
            ticket
        )

        print("3. Resolution Agent")

        resolution = self.resolution_agent.generate(
            retrieval
        )

        print("4. Validation Agent")

        validation = self.validation_agent.validate(
            diagnosis,
            retrieval,
            resolution
        )

        print("5. Escalation Agent")

        escalation = (
            self.escalation_agent.should_escalate(
                validation,
                ticket,
                resolution
            )
        )

        # Apply Milestone 4 escalation rules to the final
        # workflow status consumed by the existing Flask API.

        if escalation["required"]:
            validation["status"] = "ESCALATE"
        else:
            validation["status"] = "AUTO_RESOLVE"

        validation["escalation_reasons"] = (
            escalation["reasons"]
        )

        return {
            "diagnosis": diagnosis,
            "retrieval": retrieval,
            "resolution": resolution,
            "validation": validation,
            "escalation": escalation,
            "confidence": validation.get("confidence"),
            "status": validation.get("status")
        }

    def run(self, ticket):
        return self.process_ticket(ticket)

