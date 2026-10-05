from rag.pipeline import run_rag_pipeline


# ============================================================
# DIAGNOSIS AGENT
# ============================================================

class DiagnosisAgent:

    def analyze(self, ticket):

        title = str(
            ticket.get(
                "title",
                ""
            )
            or ""
        )


        description = str(
            ticket.get(
                "description",
                ""
            )
            or ""
        )


        text = (
            f"{title} {description}"
        ).lower()


        category = (
            "General IT Issue"
        )


        diagnosis = (
            "General IT support issue detected."
        )


        confidence = 0.80


        # ====================================================
        # NETWORK / VPN
        # ====================================================

        if any(
            word in text
            for word in [
                "vpn",
                "network",
                "internet",
                "connection",
                "wifi",
                "wi-fi",
                "dns",
                "firewall"
            ]
        ):

            category = (
                "Network / VPN"
            )

            diagnosis = (
                "Network or VPN connectivity "
                "problem detected."
            )


        # ====================================================
        # AUTHENTICATION
        # ====================================================

        elif any(
            word in text
            for word in [
                "password",
                "login",
                "authentication",
                "authenticate",
                "credential",
                "credentials"
            ]
        ):

            category = (
                "Authentication"
            )

            diagnosis = (
                "Authentication or login "
                "problem detected."
            )


        # ====================================================
        # EMAIL
        # ====================================================

        elif any(
            word in text
            for word in [
                "email",
                "outlook",
                "mailbox",
                "mail"
            ]
        ):

            category = "Email"

            diagnosis = (
                "Email access or mailbox "
                "problem detected."
            )


        # ====================================================
        # PRINTER
        # ====================================================

        elif any(
            word in text
            for word in [
                "printer",
                "printing",
                "print"
            ]
        ):

            category = "Printer"

            diagnosis = (
                "Printer or printing "
                "problem detected."
            )


        # ====================================================
        # PERFORMANCE
        # ====================================================

        elif any(
            word in text
            for word in [
                "slow",
                "performance",
                "cpu",
                "memory",
                "lag",
                "freezing",
                "freeze"
            ]
        ):

            category = "Performance"

            diagnosis = (
                "Computer performance "
                "problem detected."
            )


        # ====================================================
        # SOFTWARE
        # ====================================================

        elif any(
            word in text
            for word in [
                "software",
                "installation",
                "install",
                "application",
                "app",
                "crash"
            ]
        ):

            category = "Software"

            diagnosis = (
                "Software or application "
                "problem detected."
            )


        # ====================================================
        # HARDWARE
        # ====================================================

        elif any(
            word in text
            for word in [
                "hardware",
                "keyboard",
                "mouse",
                "monitor",
                "screen"
            ]
        ):

            category = "Hardware"

            diagnosis = (
                "Computer hardware "
                "problem detected."
            )


        return {

            "diagnosis": diagnosis,

            "category": category,

            "confidence": confidence
        }


# ============================================================
# RETRIEVAL AGENT
# ============================================================

class RetrievalAgent:

    def search(self, ticket):

        try:

            # Reuse Milestone 2 RAG
            rag_result = (
                run_rag_pipeline(
                    ticket
                )
            )


            if not isinstance(
                rag_result,
                dict
            ):

                rag_result = {}


            documents = (

                rag_result.get(
                    "retrieved_documents"
                )

                or

                rag_result.get(
                    "documents"
                )

                or

                []
            )


            similarity = 0.0


            if documents:

                first_document = (
                    documents[0]
                )


                if isinstance(
                    first_document,
                    dict
                ):

                    raw_score = (

                        first_document.get(
                            "score"
                        )

                        or

                        first_document.get(
                            "relevance"
                        )

                        or

                        first_document.get(
                            "similarity"
                        )

                        or

                        0
                    )


                    try:

                        similarity = float(
                            raw_score
                        )


                    except (
                        TypeError,
                        ValueError
                    ):

                        similarity = 0.0


                    if similarity > 1:

                        similarity = (
                            similarity / 100
                        )


            similarity = max(
                0.0,
                min(
                    similarity,
                    1.0
                )
            )


            return {

                "documents": documents,

                "similarity": similarity,

                "rag_result": rag_result
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

                "error": str(error)
            }


# ============================================================
# RESOLUTION AGENT
# ============================================================

class ResolutionAgent:

    def generate(
        self,
        retrieval
    ):

        rag_result = (
            retrieval.get(
                "rag_result"
            )
            or {}
        )


        resolution = (

            rag_result.get(
                "resolution"
            )

            or

            rag_result.get(
                "response"
            )

            or

            ""
        )


        if isinstance(
            resolution,
            list
        ):

            steps = [

                str(step).strip()

                for step in resolution

                if str(step).strip()
            ]


            response = "\n".join(

                f"{index}. {step}"

                for index, step

                in enumerate(
                    steps,
                    start=1
                )
            )


        else:

            response = str(
                resolution
                or ""
            ).strip()


            steps = (
                self._extract_steps(
                    response
                )
            )


        if not response:

            response = (
                "No suitable troubleshooting "
                "resolution could be generated "
                "from the knowledge base."
            )


        return {

            "response": response,

            "steps": steps[:8],

            "step_count": len(
                steps[:8]
            )
        }


    def _extract_steps(
        self,
        response
    ):

        if not response:

            return []


        steps = []


        for line in (
            response.splitlines()
        ):

            cleaned = (
                line.strip()
            )


            if not cleaned:

                continue


            cleaned = (
                cleaned.lstrip(
                    "-•* "
                )
            )


            parts = (
                cleaned.split(
                    ".",
                    1
                )
            )


            if (
                len(parts) == 2
                and
                parts[0]
                .strip()
                .isdigit()
            ):

                cleaned = (
                    parts[1]
                    .strip()
                )


            else:

                parts = (
                    cleaned.split(
                        ")",
                        1
                    )
                )


                if (
                    len(parts) == 2
                    and
                    parts[0]
                    .strip()
                    .isdigit()
                ):

                    cleaned = (
                        parts[1]
                        .strip()
                    )


            if cleaned:

                steps.append(
                    cleaned
                )


        if len(steps) <= 1:

            sentence_steps = []


            for sentence in (
                response.split(".")
            ):

                sentence = (
                    sentence.strip()
                )


                if (
                    len(sentence) > 10
                ):

                    sentence_steps.append(
                        sentence
                    )


            if sentence_steps:

                steps = (
                    sentence_steps
                )


        return steps[:8]


# ============================================================
# VALIDATION AGENT
# ============================================================

class ValidationAgent:

    def validate(
        self,
        diagnosis,
        retrieval,
        resolution
    ):

        diagnosis_confidence = float(

            diagnosis.get(
                "confidence",
                0
            )

            or 0
        )


        retrieval_similarity = float(

            retrieval.get(
                "similarity",
                0
            )

            or 0
        )


        steps = (

            resolution.get(
                "steps"
            )

            or []
        )


        completeness = min(

            len(steps) / 6,

            1
        )


        # ====================================================
        # MILESTONE 3 FORMULA
        #
        # 40% Diagnosis
        # 40% Retrieval
        # 20% Resolution Completeness
        # ====================================================

        final_score = (

            diagnosis_confidence
            * 0.40

            +

            retrieval_similarity
            * 0.40

            +

            completeness
            * 0.20
        )


        confidence = round(

            final_score
            * 100,

            2
        )


        status = (

            "AUTO_RESOLVE"

            if confidence >= 70

            else

            "ESCALATE"
        )


        return {

            "confidence":
                confidence,

            "status":
                status,

            "threshold":
                70,

            "diagnosis_score":
                round(
                    diagnosis_confidence
                    * 100,
                    2
                ),

            "retrieval_score":
                round(
                    retrieval_similarity
                    * 100,
                    2
                ),

            "completeness_score":
                round(
                    completeness
                    * 100,
                    2
                )
        }


# ============================================================
# ESCALATION AGENT
# ============================================================

class EscalationAgent:

    def should_escalate(
        self,
        validation
    ):

        required = (

            validation.get(
                "status"
            )

            ==

            "ESCALATE"
        )


        return {

            "required":
                required,

            "decision":
                (
                    "ESCALATE"

                    if required

                    else

                    "NOT_REQUIRED"
                )
        }


# ============================================================
# MULTI AGENT ORCHESTRATOR
# ============================================================

class MultiAgentSupportPilot:

    def __init__(self):

        self.diagnosis_agent = (
            DiagnosisAgent()
        )

        self.retrieval_agent = (
            RetrievalAgent()
        )

        self.resolution_agent = (
            ResolutionAgent()
        )

        self.validation_agent = (
            ValidationAgent()
        )

        self.escalation_agent = (
            EscalationAgent()
        )


    def process_ticket(
        self,
        ticket
    ):

        print(
            "1. Diagnosis Agent"
        )

        diagnosis = (
            self.diagnosis_agent
            .analyze(
                ticket
            )
        )


        print(
            "2. Retrieval Agent"
        )

        retrieval = (
            self.retrieval_agent
            .search(
                ticket
            )
        )


        print(
            "3. Resolution Agent"
        )

        resolution = (
            self.resolution_agent
            .generate(
                retrieval
            )
        )


        print(
            "4. Validation Agent"
        )

        validation = (
            self.validation_agent
            .validate(
                diagnosis,
                retrieval,
                resolution
            )
        )


        print(
            "5. Escalation Agent"
        )

        escalation = (
            self.escalation_agent
            .should_escalate(
                validation
            )
        )


        return {

            "diagnosis":
                diagnosis,

            "retrieval":
                retrieval,

            "resolution":
                resolution,

            "validation":
                validation,

            "escalation":
                escalation
        }