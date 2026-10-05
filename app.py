import os
import time
import logging

from datetime import timedelta
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify
)

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    set_access_cookies,
    unset_jwt_cookies
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import (
    create_table,
    create_users_table,
    create_analytics_table,

    save_ticket,
    save_ticket_analytics,
    save_customer_rating,

    get_all_tickets,
    get_ticket_by_id,
    get_ticket_analytics,

    create_user,
    get_user_by_email,
    get_user_by_id,

    increment_repeated_attempts,
    set_customer_requested_human,
    mark_resolution_outcome,
    save_classification_result,

    get_dashboard_metrics,
    get_category_analytics,
    get_priority_analytics,
    get_workflow_analytics,
    get_escalated_tickets,
    get_escalation_statistics,
    get_complete_dashboard_data,
    get_classifier_performance
)

from classifier import (
    classify_ticket,
    evaluate_category_model
)

from rag.pipeline import run_rag_pipeline

from agents import MultiAgentSupportPilot
from jira_service import JiraService
from email_service import EmailService


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# JWT CONFIGURATION
# ============================================================

app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY",
    "supportpilot-development-secret-key"
)

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
    hours=2
)

app.config["JWT_TOKEN_LOCATION"] = [
    "cookies"
]

app.config["JWT_ACCESS_COOKIE_NAME"] = (
    "supportpilot_token"
)

app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False

jwt = JWTManager(app)


# ============================================================
# MILESTONE 4 LOGGING
# ============================================================

os.makedirs(
    "logs",
    exist_ok=True
)

log_handler = RotatingFileHandler(
    "logs/supportpilot.log",
    maxBytes=1_000_000,
    backupCount=5
)

log_handler.setLevel(
    logging.INFO
)

log_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
)

app.logger.addHandler(
    log_handler
)

app.logger.setLevel(
    logging.INFO
)


# ============================================================
# DATABASE
# ============================================================

create_users_table()
create_table()
create_analytics_table()


# ============================================================
# SERVICES
# ============================================================

multi_agent_system = MultiAgentSupportPilot()

jira_service = JiraService()

email_service = EmailService()


# ============================================================
# HELPERS
# ============================================================

def is_api_request():

    return request.path.startswith(
        "/api/"
    )


def json_error(
    message,
    status_code=400
):

    return jsonify({
        "success": False,
        "message": str(message)
    }), status_code


def normalize_boolean_result(
    result
):

    if not isinstance(
        result,
        dict
    ):
        return False

    return bool(
        result.get(
            "success",
            False
        )
    )


def get_jira_details(
    jira_result
):

    if not isinstance(
        jira_result,
        dict
    ):

        return (
            None,
            None
        )

    issue_key = (
        jira_result.get(
            "issue_key"
        )
        or jira_result.get(
            "jira_key"
        )
        or jira_result.get(
            "ticket_id"
        )
    )

    issue_url = (
        jira_result.get(
            "issue_url"
        )
        or jira_result.get(
            "jira_url"
        )
        or jira_result.get(
            "url"
        )
    )

    return (
        issue_key,
        issue_url
    )


def safe_float(
    value,
    default=0.0
):

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return default


def normalize_confidence(
    value
):

    confidence = safe_float(
        value,
        0.0
    )

    if (
        confidence > 0
        and confidence <= 1
    ):

        confidence *= 100

    return round(
        confidence,
        2
    )


def parse_boolean(
    value,
    default=False
):

    if value is None:

        return default

    if isinstance(
        value,
        bool
    ):

        return value

    if isinstance(
        value,
        (
            int,
            float
        )
    ):

        return value != 0

    value = str(
        value
    ).strip().lower()

    if value in (
        "true",
        "1",
        "yes",
        "y",
        "on"
    ):

        return True

    if value in (
        "false",
        "0",
        "no",
        "n",
        "off"
    ):

        return False

    return default


def extract_resolution_text(
    resolution
):

    if isinstance(
        resolution,
        dict
    ):

        return str(
            resolution.get(
                "response"
            )
            or resolution.get(
                "resolution"
            )
            or resolution.get(
                "answer"
            )
            or ""
        ).strip()

    if resolution is None:

        return ""

    return str(
        resolution
    ).strip()


def extract_documents(
    retrieval
):

    if not isinstance(
        retrieval,
        dict
    ):

        return []

    documents = (
        retrieval.get(
            "documents"
        )
        or retrieval.get(
            "retrieved_documents"
        )
        or retrieval.get(
            "sources"
        )
        or []
    )

    if isinstance(
        documents,
        list
    ):

        return documents

    if documents:

        return [
            documents
        ]

    return []


def extract_escalation_reasons(
    result,
    confidence,
    ticket_data,
    resolution_failed,
    customer_requested_human,
    repeated_attempts
):

    reasons = []

    escalation = result.get(
        "escalation",
        {}
    )

    if isinstance(
        escalation,
        dict
    ):

        agent_reasons = (
            escalation.get(
                "reasons"
            )
            or escalation.get(
                "reason"
            )
            or escalation.get(
                "escalation_reason"
            )
        )

        if isinstance(
            agent_reasons,
            list
        ):

            for reason in agent_reasons:

                reason = str(
                    reason
                ).strip()

                if (
                    reason
                    and reason not in reasons
                ):

                    reasons.append(
                        reason
                    )

        elif agent_reasons:

            reason = str(
                agent_reasons
            ).strip()

            if (
                reason
                and reason not in reasons
            ):

                reasons.append(
                    reason
                )

    # ========================================================
    # MILESTONE 4 EXACT ESCALATION RULES
    # ========================================================

    if str(
        ticket_data.get(
            "priority",
            ""
        )
    ).strip().lower() == "critical":

        reason = (
            "Critical priority"
        )

        if reason not in reasons:

            reasons.append(
                reason
            )

    if confidence < 70:

        reason = (
            "AI confidence below 70%"
        )

        if reason not in reasons:

            reasons.append(
                reason
            )

    if resolution_failed:

        reason = (
            "AI resolution failed"
        )

        if reason not in reasons:

            reasons.append(
                reason
            )

    if customer_requested_human:

        reason = (
            "Customer requested human support"
        )

        if reason not in reasons:

            reasons.append(
                reason
            )

    if repeated_attempts >= 3:

        reason = (
            "Repeated attempts reached 3"
        )

        if reason not in reasons:

            reasons.append(
                reason
            )

    return reasons


def build_escalation_reason(
    reasons
):

    if not reasons:

        return (
            "AI workflow requested "
            "human intervention."
        )

    return "; ".join(
        reasons
    )


# ============================================================
# JWT ERROR HANDLERS
# ============================================================

@jwt.unauthorized_loader
def unauthorized_callback(
    reason
):

    if (
        is_api_request()
        or request.path == "/submit-ticket"
    ):

        return jsonify({
            "success": False,
            "message":
                "Authentication required."
        }), 401

    return redirect(
        url_for(
            "login"
        )
    )


@jwt.invalid_token_loader
def invalid_token_callback(
    reason
):

    if (
        is_api_request()
        or request.path == "/submit-ticket"
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid authentication token."
        }), 401

    return redirect(
        url_for(
            "login"
        )
    )


@jwt.expired_token_loader
def expired_token_callback(
    jwt_header,
    jwt_payload
):

    if (
        is_api_request()
        or request.path == "/submit-ticket"
    ):

        return jsonify({
            "success": False,
            "message":
                "Login session expired. Please log in again."
        }), 401

    return redirect(
        url_for(
            "login"
        )
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=[
        "GET",
        "POST"
    ]
)
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        email = str(
            data.get(
                "email",
                ""
            )
        ).strip().lower()

        password = str(
            data.get(
                "password",
                ""
            )
        )

        if (
            not email
            or not password
        ):

            return jsonify({
                "success": False,
                "message":
                    "Email and password are required."
            }), 400

        user = get_user_by_email(
            email
        )

        if user is None:

            return jsonify({
                "success": False,
                "message":
                    "Invalid email or password."
            }), 401

        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "success": False,
                "message":
                    "Invalid email or password."
            }), 401

        access_token = create_access_token(
            identity=str(
                user["id"]
            )
        )

        response = jsonify({
            "success": True,
            "message":
                "Login successful.",
            "redirect":
                "/dashboard"
        })

        set_access_cookies(
            response,
            access_token
        )

        app.logger.info(
            "User login successful: user_id=%s",
            user["id"]
        )

        return (
            response,
            200
        )

    except Exception as error:

        app.logger.exception(
            "Login Error"
        )

        return jsonify({
            "success": False,
            "message":
                str(error)
        }), 500


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=[
        "GET",
        "POST"
    ]
)
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )

    try:

        if request.is_json:

            data = (
                request.get_json(
                    silent=True
                )
                or {}
            )

        else:

            data = request.form

        full_name = str(
            data.get(
                "full_name",
                ""
            )
        ).strip()

        email = str(
            data.get(
                "email",
                ""
            )
        ).strip().lower()

        department = str(
            data.get(
                "department",
                ""
            )
        ).strip()

        password = str(
            data.get(
                "password",
                ""
            )
        )

        if (
            not full_name
            or not email
            or not password
        ):

            message = (
                "Name, email and password are required."
            )

            if request.is_json:

                return jsonify({
                    "success": False,
                    "message":
                        message
                }), 400

            return render_template(
                "register.html",
                error=message
            )

        existing_user = get_user_by_email(
            email
        )

        if existing_user:

            message = (
                "An account with this email already exists."
            )

            if request.is_json:

                return jsonify({
                    "success": False,
                    "message":
                        message
                }), 409

            return render_template(
                "register.html",
                error=message
            )

        password_hash = generate_password_hash(
            password
        )

        create_user(
            full_name,
            email,
            department,
            password_hash
        )

        if request.is_json:

            return jsonify({
                "success": True,
                "message":
                    "Registration successful.",
                "redirect":
                    "/login"
            }), 201

        return redirect(
            url_for(
                "login"
            )
        )

    except Exception as error:

        app.logger.exception(
            "Registration Error"
        )

        if request.is_json:

            return jsonify({
                "success": False,
                "message":
                    str(error)
            }), 500

        return render_template(
            "register.html",
            error=str(
                error
            )
        )


# ============================================================
# LOGOUT
# ============================================================

@app.route(
    "/logout"
)
def logout():

    response = redirect(
        url_for(
            "login"
        )
    )

    unset_jwt_cookies(
        response
    )

    return response


# ============================================================
# NEW TICKET PAGE
# ============================================================

@app.route("/")
@jwt_required()
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route(
    "/dashboard"
)
@jwt_required()
def dashboard():

    try:

        user_id = get_jwt_identity()

        user = get_user_by_id(
            user_id
        )

        tickets = get_all_tickets()

        high_count = sum(
            1
            for ticket in tickets
            if str(
                ticket.get(
                    "priority",
                    ""
                )
            ).lower() == "high"
        )

        medium_count = sum(
            1
            for ticket in tickets
            if str(
                ticket.get(
                    "priority",
                    ""
                )
            ).lower() == "medium"
        )

        low_count = sum(
            1
            for ticket in tickets
            if str(
                ticket.get(
                    "priority",
                    ""
                )
            ).lower() == "low"
        )

        return render_template(
            "dashboard.html",
            tickets=tickets,
            user=user,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count
        )

    except Exception as error:

        app.logger.exception(
            "Dashboard Error"
        )

        return render_template(
            "dashboard.html",
            tickets=[],
            user=None,
            high_count=0,
            medium_count=0,
            low_count=0,
            error=str(
                error
            )
        )


# ============================================================
# AI AGENT VIEW
# ============================================================

@app.route(
    "/ai-agent"
)
@jwt_required()
def ai_agent():

    return redirect(
        "/dashboard#ai-agents"
    )


# ============================================================
# SUBMIT TICKET
# ============================================================

@app.route(
    "/submit-ticket",
    methods=[
        "POST"
    ]
)
@jwt_required()
def submit_ticket():

    try:

        user_id = get_jwt_identity()

        employee_name = str(
            request.form.get(
                "employee_name",
                ""
            )
        ).strip()

        email = str(
            request.form.get(
                "email",
                ""
            )
        ).strip()

        department = str(
            request.form.get(
                "department",
                ""
            )
        ).strip()

        title = str(
            request.form.get(
                "title",
                ""
            )
        ).strip()

        description = str(
            request.form.get(
                "description",
                ""
            )
        ).strip()

        if (
            not title
            or not description
        ):

            return jsonify({
                "success": False,
                "message":
                    "Title and description are required."
            }), 400

        classification = classify_ticket(
            title,
            description
        )

        category = classification.get(
            "category",
            "Unknown"
        )

        severity = classification.get(
            "severity",
            "Medium"
        )

        priority = classification.get(
            "priority",
            "Medium"
        )

        confidence = normalize_confidence(
            classification.get(
                "confidence",
                0
            )
        )

        ticket_id = save_ticket(
            employee_name=employee_name,
            email=email,
            title=title,
            description=description,
            department=department,
            category=category,
            severity=severity,
            priority=priority,
            confidence=confidence,
            user_id=user_id
        )

        app.logger.info(
            "Ticket created: ticket_id=%s category=%s priority=%s confidence=%s",
            ticket_id,
            category,
            priority,
            confidence
        )

        return jsonify({
            "success": True,
            "ticket_id":
                ticket_id,
            "category":
                category,
            "severity":
                severity,
            "priority":
                priority,
            "confidence":
                confidence
        }), 201

    except Exception as error:

        app.logger.exception(
            "Ticket Submission Error"
        )

        return jsonify({
            "success": False,
            "message":
                str(error)
        }), 500


# ============================================================
# GET ALL TICKETS API
# ============================================================

@app.route(
    "/api/tickets",
    methods=[
        "GET"
    ]
)
@jwt_required()
def api_tickets():

    try:

        tickets = get_all_tickets()

        return jsonify({
            "success": True,
            "tickets":
                tickets
        })

    except Exception as error:

        app.logger.exception(
            "Get Tickets Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# GET ONE TICKET API
# ============================================================

@app.route(
    "/api/tickets/<int:ticket_id>",
    methods=[
        "GET"
    ]
)
@jwt_required()
def api_ticket(
    ticket_id
):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        analytics = get_ticket_analytics(
            ticket_id
        )

        return jsonify({
            "success": True,
            "ticket":
                ticket,
            "analytics":
                analytics
        })

    except Exception as error:

        app.logger.exception(
            "Get Ticket Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# RAG
# ============================================================

@app.route(
    "/api/tickets/<int:ticket_id>/rag",
    methods=[
        "POST"
    ]
)
@jwt_required()
def ticket_rag(
    ticket_id
):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        query = (
            str(
                ticket.get(
                    "title",
                    ""
                )
            )
            + " "
            + str(
                ticket.get(
                    "description",
                    ""
                )
            )
        ).strip()

        start_time = time.perf_counter()

        result = run_rag_pipeline(
            query
        )

        elapsed = (
            time.perf_counter()
            -
            start_time
        )

        return jsonify({
            "success": True,
            "ticket_id":
                ticket_id,
            "rag":
                result,
            "response_time":
                round(
                    elapsed,
                    3
                )
        })

    except Exception as error:

        app.logger.exception(
            "RAG Error: ticket_id=%s",
            ticket_id
        )

        return json_error(
            error,
            500
        )


# ============================================================
# AI RESOLUTION PAGE
# ============================================================

@app.route(
    "/ai-resolution/<int:ticket_id>"
)
@jwt_required()
def ai_resolution(
    ticket_id
):

    ticket = get_ticket_by_id(
        ticket_id
    )

    if not ticket:

        return redirect(
            url_for(
                "dashboard"
            )
        )

    return render_template(
        "ai_resolution.html",
        ticket=ticket
    )# ============================================================
# RUN MULTI-AGENT WORKFLOW
# MILESTONE 3 + MILESTONE 4
# ============================================================

@app.route(
    "/api/agents/run/<int:ticket_id>",
    methods=[
        "POST"
    ]
)
@jwt_required()
def run_agents(
    ticket_id
):

    workflow_start = time.perf_counter()

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        previous_analytics = (
            get_ticket_analytics(
                ticket_id
            )
            or {}
        )

        repeated_attempts = (
            increment_repeated_attempts(
                ticket_id
            )
        )

        customer_requested_human = (
            parse_boolean(
                previous_analytics.get(
                    "customer_requested_human"
                ),
                False
            )
        )

        ticket_data = dict(
            ticket
        )

        ticket_data[
            "repeated_attempts"
        ] = repeated_attempts

        ticket_data[
            "customer_requested_human"
        ] = customer_requested_human

        app.logger.info(
            "Multi-agent workflow started: ticket_id=%s attempt=%s",
            ticket_id,
            repeated_attempts
        )

        ticket_data[
            "attempt_count"
        ] = repeated_attempts

        ticket_data[
            "resolution_attempts"
        ] = repeated_attempts

        ticket_data[
            "human_requested"
        ] = customer_requested_human

        result = (
            multi_agent_system.process_ticket(
                ticket_data
            )
        )

        if not isinstance(
            result,
            dict
        ):

            result = {
                "result":
                    result
            }

        diagnosis = result.get(
            "diagnosis",
            {}
        )

        retrieval = result.get(
            "retrieval",
            {}
        )

        resolution = result.get(
            "resolution",
            {}
        )

        validation = result.get(
            "validation",
            {}
        )

        if not isinstance(
            diagnosis,
            dict
        ):
            diagnosis = {}

        if not isinstance(
            retrieval,
            dict
        ):
            retrieval = {}

        if not isinstance(
            validation,
            dict
        ):
            validation = {}

        confidence = normalize_confidence(
            result.get(
                "confidence",
                validation.get(
                    "confidence",
                    validation.get(
                        "final_confidence",
                        validation.get(
                            "final_score",
                            0
                        )
                    )
                )
            )
        )

        resolution_text = (
            extract_resolution_text(
                resolution
            )
        )

        resolution_failed = (
            parse_boolean(
                result.get(
                    "resolution_failed"
                ),
                False
            )
        )

        if isinstance(
            resolution,
            dict
        ):

            resolution_failed = (
                resolution_failed
                or parse_boolean(
                    resolution.get(
                        "failed"
                    ),
                    False
                )
                or parse_boolean(
                    resolution.get(
                        "resolution_failed"
                    ),
                    False
                )
            )

        if not resolution_text:

            resolution_failed = True

        documents = extract_documents(
            retrieval
        )

        kb_found = bool(
            documents
        )

        if isinstance(
            retrieval,
            dict
        ):

            if (
                "kb_found"
                in retrieval
            ):

                kb_found = parse_boolean(
                    retrieval.get(
                        "kb_found"
                    ),
                    kb_found
                )

        # ====================================================
        # EXACT MILESTONE 4 ESCALATION RULES
        #
        # Escalate if ANY:
        # 1. priority = Critical
        # 2. AI confidence < 70
        # 3. resolution_failed = True
        # 4. customer_requested_human = True
        # 5. repeated_attempts >= 3
        # ====================================================

        escalation_reasons = (
            extract_escalation_reasons(
                result=result,
                confidence=confidence,
                ticket_data=ticket_data,
                resolution_failed=resolution_failed,
                customer_requested_human=
                    customer_requested_human,
                repeated_attempts=
                    repeated_attempts
            )
        )

        should_escalate = bool(
            escalation_reasons
        )

        if should_escalate:

            workflow_status = (
                "ESCALATE"
            )

        else:

            workflow_status = (
                "AUTO_RESOLVE"
            )

        jira_issue_key = None
        jira_issue_url = None
        jira_status = "Not Required"
        jira_error = None

        email_sent = False

        # ====================================================
        # ESCALATION -> JIRA
        # ====================================================

        if workflow_status == "ESCALATE":

            escalation_reason = (
                build_escalation_reason(
                    escalation_reasons
                )
            )

            # Prevent duplicate Jira tickets if already associated
            existing_jira_key = previous_analytics.get("jira_issue_key")
            existing_jira_url = previous_analytics.get("jira_issue_url")

            if existing_jira_key:
                jira_issue_key = existing_jira_key
                jira_issue_url = existing_jira_url
                jira_status = "Created"
                app.logger.info(
                    "Ticket already escalated to Jira: ticket_id=%s jira=%s",
                    ticket_id,
                    jira_issue_key
                )
            else:
                try:

                    jira_result = (
                        jira_service.create_ticket(
                            ticket_data,
                            result
                        )
                    )

                    (
                        jira_issue_key,
                        jira_issue_url
                    ) = get_jira_details(
                        jira_result
                    )

                    if jira_issue_key:
                        jira_status = "Created"
                        app.logger.info(
                            "Ticket escalated: ticket_id=%s jira=%s reasons=%s",
                            ticket_id,
                            jira_issue_key,
                            escalation_reason
                        )
                    else:
                        jira_status = "Failed"
                        jira_error = (
                            jira_result.get("message")
                            if isinstance(jira_result, dict)
                            else "Jira ticket creation failed."
                        )
                        app.logger.warning(
                            "Jira creation failed: ticket_id=%s message=%s",
                            ticket_id,
                            jira_error
                        )

                except Exception as jira_err:
                    jira_status = "Failed"
                    jira_error = str(jira_err)
                    app.logger.exception(
                        "Jira Error: ticket_id=%s error=%s",
                        ticket_id,
                        jira_err
                    )

        else:

            escalation_reason = None
            jira_status = "Not Required"

            # =================================================
            # AUTO RESOLUTION -> EMAIL
            # =================================================

            try:

                email_result = (
                    email_service.send_resolution_email(
                        ticket_data,
                        result
                    )
                )

                email_sent = (
                    normalize_boolean_result(
                        email_result
                    )
                )

                app.logger.info(
                    "Auto-resolution email: ticket_id=%s sent=%s",
                    ticket_id,
                    email_sent
                )

            except Exception as email_error:

                app.logger.exception(
                    "Email Error: ticket_id=%s error=%s",
                    ticket_id,
                    email_error
                )

        workflow_time = (
            time.perf_counter()
            -
            workflow_start
        )

        # ====================================================
        # SAVE MILESTONE 4 ANALYTICS
        # ====================================================

        save_ticket_analytics(
            ticket_id=ticket_id,
            workflow_status=
                workflow_status,
            ai_confidence=
                confidence,
            ai_resolved=(
                workflow_status
                == "AUTO_RESOLVE"
            ),
            escalated=(
                workflow_status
                == "ESCALATE"
            ),
            kb_found=
                kb_found,
            ai_response_time=
                workflow_time,
            jira_issue_key=
                jira_issue_key,
            jira_issue_url=
                jira_issue_url,
            email_sent=
                email_sent,
            escalation_reason=
                escalation_reason,
            resolution_failed=
                resolution_failed,
            customer_requested_human=
                customer_requested_human,
            repeated_attempts=
                repeated_attempts
        )

        # ====================================================
        # RETURN AGENT RESULTS
        # ====================================================

        result[
            "ticket_id"
        ] = ticket_id

        result[
            "status"
        ] = workflow_status

        result[
            "workflow_status"
        ] = workflow_status

        result[
            "confidence"
        ] = confidence

        if isinstance(result.get("validation"), dict):
            result["validation"]["confidence"] = confidence

        result[
            "repeated_attempts"
        ] = repeated_attempts

        result[
            "customer_requested_human"
        ] = customer_requested_human

        result[
            "resolution_failed"
        ] = resolution_failed

        result[
            "kb_found"
        ] = kb_found

        result[
            "ai_response_time"
        ] = round(
            workflow_time,
            3
        )

        result[
            "escalation_reasons"
        ] = escalation_reasons

        result[
            "escalation_reason"
        ] = escalation_reason

        result[
            "jira_status"
        ] = jira_status

        result[
            "jira_issue_key"
        ] = jira_issue_key

        result[
            "jira_key"
        ] = jira_issue_key

        result[
            "jira_issue_url"
        ] = jira_issue_url

        result[
            "jira_url"
        ] = jira_issue_url

        result[
            "jira_error"
        ] = jira_error

        result[
            "email_sent"
        ] = email_sent

        return jsonify(
            result
        )

    except Exception as error:

        app.logger.exception(
            "Multi-Agent Workflow Error: ticket_id=%s",
            ticket_id
        )

        return json_error(
            error,
            500
        )


# ============================================================
# CUSTOMER REQUESTS HUMAN SUPPORT
# ============================================================

@app.route(
    "/api/tickets/<int:ticket_id>/request-human",
    methods=[
        "POST"
    ]
)
@jwt_required()
def request_human_support(
    ticket_id
):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        set_customer_requested_human(
            ticket_id,
            True
        )

        save_ticket_analytics(
            ticket_id=ticket_id,
            workflow_status=
                "ESCALATE",
            ai_resolved=False,
            escalated=True,
            customer_requested_human=True,
            escalation_reason=
                "Customer requested human support"
        )

        app.logger.info(
            "Customer requested human support: ticket_id=%s",
            ticket_id
        )

        return jsonify({
            "success": True,
            "ticket_id":
                ticket_id,
            "customer_requested_human":
                True,
            "status":
                "ESCALATE"
        })

    except Exception as error:

        app.logger.exception(
            "Request Human Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# RESOLUTION OUTCOME
# ============================================================

@app.route(
    "/api/tickets/<int:ticket_id>/resolution-outcome",
    methods=[
        "POST"
    ]
)
@app.route(
    "/api/ticket/<int:ticket_id>/resolution-outcome",
    methods=[
        "POST"
    ]
)
@jwt_required()
def resolution_outcome(
    ticket_id
):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        success_val = None
        if "success" in data:
            success_val = data.get("success")
        elif "resolution_success" in data:
            success_val = data.get("resolution_success")
        elif "resolved" in data:
            success_val = data.get("resolved")

        if success_val is None:

            return json_error(
                "Resolution outcome is required.",
                400
            )

        success = parse_boolean(
            success_val,
            False
        )

        resolution_time = (
            data.get(
                "resolution_time"
            )
        )

        mark_resolution_outcome(
            ticket_id,
            success,
            resolution_time
        )

        app.logger.info(
            "Resolution outcome saved: ticket_id=%s success=%s",
            ticket_id,
            success
        )

        return jsonify({
            "success": True,
            "ticket_id":
                ticket_id,
            "resolution_success":
                success
        })

    except Exception as error:

        app.logger.exception(
            "Resolution Outcome Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# CUSTOMER RATING
# ============================================================

@app.route(
    "/api/tickets/<int:ticket_id>/rating",
    methods=[
        "POST"
    ]
)
@app.route(
    "/api/ticket/<int:ticket_id>/rating",
    methods=[
        "POST"
    ]
)
@app.route(
    "/api/tickets/<int:ticket_id>/customer-rating",
    methods=[
        "POST"
    ]
)
@app.route(
    "/api/ticket/<int:ticket_id>/customer-rating",
    methods=[
        "POST"
    ]
)
@jwt_required()
def customer_rating(
    ticket_id
):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        rating_val = (
            data.get("rating")
            if data.get("rating") is not None
            else data.get("customer_rating")
        )

        rating = safe_float(
            rating_val,
            0
        )

        if (
            rating < 1
            or rating > 5
        ):

            return json_error(
                "Rating must be between 1 and 5.",
                400
            )

        save_customer_rating(
            ticket_id,
            rating
        )

        app.logger.info(
            "Customer rating saved: ticket_id=%s rating=%s",
            ticket_id,
            rating
        )

        return jsonify({
            "success": True,
            "ticket_id":
                ticket_id,
            "rating":
                rating
        })

    except Exception as error:

        app.logger.exception(
            "Customer Rating Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# CLASSIFICATION VERIFICATION
# ============================================================

@app.route(
    "/api/tickets/<int:ticket_id>/classification",
    methods=[
        "POST"
    ]
)
@jwt_required()
def classification_verification(
    ticket_id
):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if not ticket:

            return json_error(
                "Ticket not found.",
                404
            )

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        actual_category = str(
            data.get(
                "actual_category",
                ""
            )
        ).strip()

        if not actual_category:

            return json_error(
                "actual_category is required.",
                400
            )

        predicted_category = str(
            ticket.get(
                "category",
                ""
            )
        ).strip()

        correct = (
            predicted_category.lower()
            ==
            actual_category.lower()
        )

        save_classification_result(
            ticket_id=ticket_id,
            predicted_category=
                predicted_category,
            actual_category=
                actual_category,
            correct=
                correct,
            confidence=
                ticket.get(
                    "confidence"
                )
        )

        app.logger.info(
            "Classification verified: ticket_id=%s predicted=%s actual=%s correct=%s",
            ticket_id,
            predicted_category,
            actual_category,
            correct
        )

        return jsonify({
            "success": True,
            "ticket_id":
                ticket_id,
            "predicted_category":
                predicted_category,
            "actual_category":
                actual_category,
            "correct":
                correct
        })

    except Exception as error:

        app.logger.exception(
            "Classification Verification Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# MILESTONE 4 CLASSIFIER EVALUATION
# Accuracy + Precision + Recall + F1 + Confusion Matrix
# ============================================================

@app.route(
    "/api/classifier/evaluate",
    methods=[
        "POST"
    ]
)
@jwt_required()
def classifier_evaluation():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        samples = data.get(
            "samples",
            []
        )

        if not isinstance(
            samples,
            list
        ):

            return json_error(
                "samples must be a list.",
                400
            )

        if not samples:

            return json_error(
                "At least one evaluation sample is required.",
                400
            )

        evaluation = (
            evaluate_category_model(
                samples
            )
        )

        app.logger.info(
            "Classifier evaluation completed: samples=%s accuracy=%s precision=%s recall=%s f1=%s",
            evaluation.get(
                "sample_count"
            ),
            evaluation.get(
                "accuracy"
            ),
            evaluation.get(
                "precision"
            ),
            evaluation.get(
                "recall"
            ),
            evaluation.get(
                "f1_score"
            )
        )

        return jsonify({
            "success": True,
            "evaluation":
                evaluation
        })

    except Exception as error:

        app.logger.exception(
            "Classifier Evaluation Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# MILESTONE 4 ANALYTICS API
# ============================================================

@app.route(
    "/api/analytics",
    methods=[
        "GET"
    ]
)
@jwt_required()
def analytics():

    try:

        return jsonify({

            "success": True,

            "metrics":
                get_dashboard_metrics(),

            "categories":
                get_category_analytics(),

            "priorities":
                get_priority_analytics(),

            "workflow":
                get_workflow_analytics(),

            "escalations":
                get_escalated_tickets(),

            "escalation_statistics":
                get_escalation_statistics(),

            "classifier_performance":
                get_classifier_performance()

        })

    except Exception as error:

        app.logger.exception(
            "Analytics API Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# COMPLETE DASHBOARD DATA
# ============================================================

@app.route(
    "/api/dashboard-data",
    methods=[
        "GET"
    ]
)
@jwt_required()
def dashboard_data():

    try:

        data = (
            get_complete_dashboard_data()
        )

        return jsonify({
            "success": True,
            **data
        })

    except Exception as error:

        app.logger.exception(
            "Dashboard Data Error"
        )

        return json_error(
            error,
            500
        )


# ============================================================
# HEALTH / MONITORING
# ============================================================

@app.route(
    "/health",
    methods=[
        "GET"
    ]
)
def health():

    return jsonify({

        "status":
            "healthy",

        "service":
            "SupportPilot",

        "milestone":
            4

    }), 200


# ============================================================
# 404
# ============================================================

@app.errorhandler(
    404
)
def page_not_found(
    error
):

    if is_api_request():

        return jsonify({
            "success": False,
            "message":
                "Endpoint not found."
        }), 404

    return (
        "Page not found",
        404
    )


# ============================================================
# 500
# ============================================================

@app.errorhandler(
    500
)
def internal_server_error(
    error
):

    app.logger.exception(
        "Unhandled Server Error"
    )

    if is_api_request():

        return jsonify({
            "success": False,
            "message":
                "Internal server error."
        }), 500

    return (
        "Internal server error",
        500
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.logger.info(
        "SupportPilot starting on http://127.0.0.1:5001"
    )

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )