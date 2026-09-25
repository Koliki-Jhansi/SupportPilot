import os
from datetime import timedelta

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
    save_ticket,
    get_all_tickets,
    get_ticket_by_id,
    create_user,
    get_user_by_email,
    get_user_by_id
)

from classifier import classify_ticket
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

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)

app.config["JWT_TOKEN_LOCATION"] = ["cookies"]

app.config["JWT_ACCESS_COOKIE_NAME"] = "supportpilot_token"

# Local development
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False


jwt = JWTManager(app)


# ============================================================
# DATABASE
# ============================================================

create_table()
create_users_table()


# ============================================================
# MILESTONE 3 SERVICES
# ============================================================

multi_agent_system = MultiAgentSupportPilot()
jira_service = JiraService()
email_service = EmailService()


# ============================================================
# HELPERS
# ============================================================

def is_api_request():
    return request.path.startswith("/api/")


def json_error(message, status_code=400):
    return jsonify({
        "success": False,
        "message": str(message)
    }), status_code


# ============================================================
# JWT ERROR HANDLERS
# ============================================================

@jwt.unauthorized_loader
def unauthorized_callback(reason):

    # AJAX/API-style requests should receive JSON.
    if is_api_request() or request.path == "/submit-ticket":
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    return redirect(url_for("login"))


@jwt.invalid_token_loader
def invalid_token_callback(reason):

    if is_api_request() or request.path == "/submit-ticket":
        return jsonify({
            "success": False,
            "message": "Invalid authentication token."
        }), 401

    return redirect(url_for("login"))


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):

    if is_api_request() or request.path == "/submit-ticket":
        return jsonify({
            "success": False,
            "message": "Login session expired. Please log in again."
        }), 401

    return redirect(url_for("login"))


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    try:

        data = request.get_json(silent=True) or {}

        email = str(
            data.get("email", "")
        ).strip().lower()

        password = str(
            data.get("password", "")
        )

        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required."
            }), 400

        user = get_user_by_email(email)

        if user is None:
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        if not check_password_hash(
            user["password"],
            password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        access_token = create_access_token(
            identity=str(user["id"])
        )

        response = jsonify({
            "success": True,
            "message": "Login successful.",
            "redirect": "/dashboard"
        })

        set_access_cookies(
            response,
            access_token
        )

        return response, 200

    except Exception as error:

        print(
            "Login Error:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    try:

        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form

        full_name = str(
            data.get("full_name", "")
        ).strip()

        email = str(
            data.get("email", "")
        ).strip().lower()

        department = str(
            data.get("department", "")
        ).strip()

        password = str(
            data.get("password", "")
        )

        if not full_name or not email or not password:

            message = (
                "Name, email and password are required."
            )

            if request.is_json:
                return jsonify({
                    "success": False,
                    "message": message
                }), 400

            return render_template(
                "register.html",
                error=message
            )

        existing_user = get_user_by_email(email)

        if existing_user:

            message = (
                "An account with this email already exists."
            )

            if request.is_json:
                return jsonify({
                    "success": False,
                    "message": message
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
                "message": "Registration successful.",
                "redirect": "/login"
            }), 201

        return redirect(url_for("login"))

    except Exception as error:

        print(
            "Registration Error:",
            repr(error)
        )

        if request.is_json:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

        return render_template(
            "register.html",
            error=str(error)
        )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    response = redirect(
        url_for("login")
    )

    unset_jwt_cookies(response)

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
# SUBMIT TICKET
# MILESTONE 1
#
# IMPORTANT:
# This endpoint is called with JavaScript fetch().
# Therefore ALL POST responses are JSON.
# ============================================================

@app.route(
    "/submit-ticket",
    methods=["POST"]
)
@jwt_required()
def submit_ticket():

    try:

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

        # --------------------------------------------------------
        # VALIDATION
        # --------------------------------------------------------

        if (
            not employee_name
            or not email
            or not title
            or not description
        ):

            return jsonify({
                "success": False,
                "message": (
                    "Please complete all required fields."
                )
            }), 400

        # --------------------------------------------------------
        # CLASSIFICATION
        # --------------------------------------------------------

        try:

            prediction = classify_ticket(
                title,
                description
            )

        except TypeError:

            combined_text = (
                f"{title} {description}"
            )

            prediction = classify_ticket(
                combined_text
            )

        # Defaults
        category = "General IT Issue"
        severity = "Medium"
        priority = "Medium"
        confidence = 0.0

        # --------------------------------------------------------
        # NORMALIZE CLASSIFIER RESPONSE
        # --------------------------------------------------------

        if isinstance(prediction, dict):

            category = (
                prediction.get("category")
                or prediction.get("prediction")
                or prediction.get("ticket_type")
                or category
            )

            severity = (
                prediction.get("severity")
                or prediction.get("priority")
                or severity
            )

            priority = (
                prediction.get("priority")
                or severity
            )

            confidence = (
                prediction.get("confidence")
                or prediction.get("score")
                or 0
            )

        elif isinstance(
            prediction,
            (list, tuple)
        ):

            if len(prediction) >= 1:
                category = prediction[0]

            if len(prediction) >= 2:
                severity = prediction[1]

            if len(prediction) >= 3:
                priority = prediction[2]

            if len(prediction) >= 4:
                confidence = prediction[3]

        elif isinstance(prediction, str):

            category = prediction

        # --------------------------------------------------------
        # NORMALIZE CONFIDENCE
        # --------------------------------------------------------

        try:

            confidence = float(confidence)

        except (
            TypeError,
            ValueError
        ):

            confidence = 0.0

        # --------------------------------------------------------
        # SAVE TICKET
        # --------------------------------------------------------

        ticket_id = save_ticket(
            employee_name,
            email,
            title,
            description,
            department,
            str(category),
            str(severity),
            str(priority),
            confidence
        )

        print(
            f"Ticket #{ticket_id} submitted successfully."
        )

        # --------------------------------------------------------
        # IMPORTANT FIX:
        # RETURN JSON - DO NOT RENDER index.html HERE
        # --------------------------------------------------------

        return jsonify({
            "success": True,
            "message": "Ticket submitted successfully.",
            "ticket_id": ticket_id,
            "result": {
                "category": str(category),
                "severity": str(severity),
                "priority": str(priority),
                "confidence": confidence
            }
        }), 200

    except Exception as error:

        print(
            "Ticket Submission Error:",
            repr(error)
        )

        # IMPORTANT:
        # JavaScript expects JSON even when an error occurs.
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@jwt_required()
def dashboard():

    tickets = get_all_tickets()

    user_id = get_jwt_identity()

    user = get_user_by_id(
        user_id
    )

    return render_template(
        "dashboard.html",
        tickets=tickets,
        user=user
    )


# ============================================================
# AI AGENT PAGE
# MILESTONE 3 IS INSIDE DASHBOARD
# ============================================================

@app.route("/ai-agent")
@jwt_required()
def ai_agent():

    return redirect(
        url_for("dashboard")
        + "#ai-agents"
    )


# ============================================================
# MILESTONE 2
# AI RESOLUTION
# ============================================================

@app.route(
    "/ai-resolution/<int:ticket_id>"
)
@jwt_required()
def ai_resolution(ticket_id):

    try:

        ticket = get_ticket_by_id(
            ticket_id
        )

        if ticket is None:

            return redirect(
                url_for("dashboard")
            )

        ticket_data = dict(ticket)

        result = run_rag_pipeline(
            ticket_data
        )

        if not isinstance(result, dict):
            result = {}

        return render_template(
            "ai_resolution.html",

            ticket=ticket_data,

            analysis=result.get(
                "analysis",
                {}
            ),

            retrieved_documents=result.get(
                "retrieved_documents",
                []
            ),

            context=result.get(
                "context",
                ""
            ),

            resolution=result.get(
                "resolution",
                "No AI resolution available."
            ),

            status=result.get(
                "status",
                "PENDING"
            ),

            sources=result.get(
                "sources",
                []
            )
        )

    except Exception as error:

        print(
            "AI Resolution Error:",
            repr(error)
        )

        return render_template(
            "ai_resolution.html",

            ticket={},

            analysis={},

            retrieved_documents=[],

            context="",

            resolution=(
                "Unable to generate AI resolution."
            ),

            status="ERROR",

            sources=[],

            error=str(error)
        )


# ============================================================
# MILESTONE 3
# MULTI-AGENT API
# ============================================================

@app.route(
    "/api/multi-agent/<int:ticket_id>",
    methods=["POST"]
)
@jwt_required()
def multi_agent(ticket_id):

    try:

        print(
            "\n===================================="
        )

        print(
            f" MILESTONE 3 - TICKET #{ticket_id}"
        )

        print(
            "===================================="
        )

        # --------------------------------------------------------
        # GET TICKET
        # --------------------------------------------------------

        ticket = get_ticket_by_id(
            ticket_id
        )

        if ticket is None:

            return jsonify({
                "success": False,
                "message": "Ticket not found."
            }), 404

        ticket_data = dict(ticket)

        # --------------------------------------------------------
        # RUN FIVE AGENTS
        # --------------------------------------------------------

        result = (
            multi_agent_system
            .process_ticket(
                ticket_data
            )
        )

        if not isinstance(result, dict):

            return jsonify({
                "success": False,
                "message": (
                    "Multi-agent system returned "
                    "an invalid response."
                )
            }), 500

        # --------------------------------------------------------
        # VALIDATION
        # --------------------------------------------------------

        validation = result.get(
            "validation",
            {}
        )

        if not isinstance(validation, dict):
            validation = {}

        try:

            confidence = float(
                validation.get(
                    "confidence",
                    0
                )
                or 0
            )

        except (
            TypeError,
            ValueError
        ):

            confidence = 0.0

        status = str(
            validation.get(
                "status",
                "ESCALATE"
            )
        ).strip().upper()

        if status not in (
            "AUTO_RESOLVE",
            "ESCALATE"
        ):
            status = "ESCALATE"

        email_result = None
        jira_result = None

        # --------------------------------------------------------
        # DIAGNOSIS / RESOLUTION
        # --------------------------------------------------------

        diagnosis = result.get(
            "diagnosis",
            {}
        )

        if not isinstance(diagnosis, dict):
            diagnosis = {}

        resolution = result.get(
            "resolution",
            {}
        )

        if not isinstance(resolution, dict):

            resolution = {
                "response": str(resolution)
            }

        resolution_text = (
            resolution.get("response")
            or resolution.get("resolution")
            or ""
        )

        # --------------------------------------------------------
        # AUTO RESOLVE
        # --------------------------------------------------------

        if status == "AUTO_RESOLVE":

            print(
                "Decision: AUTO_RESOLVE"
            )

            email_subject = (
                "SupportPilot Resolution - "
                f"Ticket #{ticket_id}"
            )

            email_body = f"""
Hello {ticket_data.get('employee_name', 'User')},

SupportPilot has analyzed your IT support ticket.

Ticket ID:
#{ticket_id}

Issue:
{ticket_data.get('title', '')}

Description:
{ticket_data.get('description', '')}

AI Diagnosis:
{diagnosis.get('diagnosis', '')}

AI Category:
{diagnosis.get('category', '')}

Recommended Resolution:

{resolution_text}

AI Confidence:
{confidence}%

Status:
AUTO_RESOLVE

Regards,
SupportPilot AI Support
"""

            # EmailService safely reports "not configured"
            # when SMTP credentials are blank.
            email_result = (
                email_service.send_email(
                    ticket_data.get(
                        "email",
                        ""
                    ),
                    email_subject,
                    email_body
                )
            )

        # --------------------------------------------------------
        # ESCALATE
        # --------------------------------------------------------

        else:

            print(
                "Decision: ESCALATE"
            )

            jira_summary = (
                f"SupportPilot Ticket "
                f"#{ticket_id}: "
                f"{ticket_data.get('title', '')}"
            )

            jira_description = f"""
SUPPORTPILOT AI ESCALATION

Ticket ID:
{ticket_id}

Employee:
{ticket_data.get('employee_name', '')}

Email:
{ticket_data.get('email', '')}

Department:
{ticket_data.get('department', '')}

Title:
{ticket_data.get('title', '')}

Description:
{ticket_data.get('description', '')}

AI Diagnosis:
{diagnosis.get('diagnosis', '')}

AI Category:
{diagnosis.get('category', '')}

AI Resolution:
{resolution_text}

Final Confidence:
{confidence}%

Automatic Resolution Threshold:
70%

Reason:
The final AI confidence was below the
automatic resolution threshold.
"""

            # JiraService safely reports "not configured"
            # when Jira credentials are blank.
            jira_result = (
                jira_service.create_ticket(
                    jira_summary,
                    jira_description,
                    priority="High"
                )
            )

        # --------------------------------------------------------
        # RESPONSE
        # --------------------------------------------------------

        response_data = {
            "success": True,
            "ticket_id": ticket_id,
            "status": status,
            "confidence": confidence,
            "result": result,
            "email": email_result,
            "jira": jira_result
        }

        print(
            f"Final Confidence: {confidence}%"
        )

        print(
            f"Final Status: {status}"
        )

        return jsonify(
            response_data
        ), 200

    except Exception as error:

        print(
            "MULTI-AGENT ERROR:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# ============================================================
# TICKETS API
# ============================================================

@app.route("/api/tickets")
@jwt_required()
def api_tickets():

    try:

        tickets = get_all_tickets()

        ticket_list = [
            dict(ticket)
            for ticket in tickets
        ]

        return jsonify({
            "success": True,
            "tickets": ticket_list
        }), 200

    except Exception as error:

        print(
            "Tickets API Error:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# ============================================================
# CURRENT USER API
# ============================================================

@app.route("/api/me")
@jwt_required()
def api_me():

    try:

        user_id = get_jwt_identity()

        user = get_user_by_id(
            user_id
        )

        if user is None:

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        return jsonify({
            "success": True,
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "department": user["department"]
            }
        }), 200

    except Exception as error:

        print(
            "Current User API Error:",
            repr(error)
        )

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# ============================================================
# SEVERITY GUIDE
# ============================================================

@app.route("/severity-guide")
@jwt_required()
def severity_guide():

    return render_template(
        "severity_guide.html"
    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "success": True,
        "status": "ok",
        "service": "SupportPilot"
    }), 200


# ============================================================
# JSON ERROR HANDLERS FOR API REQUESTS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    if is_api_request() or request.path == "/submit-ticket":

        return jsonify({
            "success": False,
            "message": "Endpoint not found."
        }), 404

    return (
        "<h1>404 - Page Not Found</h1>",
        404
    )


@app.errorhandler(405)
def method_not_allowed(error):

    if is_api_request() or request.path == "/submit-ticket":

        return jsonify({
            "success": False,
            "message": "Method not allowed."
        }), 405

    return (
        "<h1>405 - Method Not Allowed</h1>",
        405
    )


@app.errorhandler(500)
def internal_server_error(error):

    if is_api_request() or request.path == "/submit-ticket":

        return jsonify({
            "success": False,
            "message": "Internal server error."
        }), 500

    return (
        "<h1>500 - Internal Server Error</h1>",
        500
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print(
        "\n===================================="
    )

    print(
        " SupportPilot AI Ticket Resolution"
    )

    print(
        "===================================="
    )

    print(
        "\nLogin:     "
        "http://127.0.0.1:5001/login"
    )

    print(
        "Dashboard: "
        "http://127.0.0.1:5001/dashboard"
    )

    print(
        "AI Agents: "
        "http://127.0.0.1:5001/ai-agent"
    )

    print(
        "Health:    "
        "http://127.0.0.1:5001/health\n"
    )

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )