from flask import Flask, render_template, request, jsonify

from database import (
    create_table,
    save_ticket,
    get_all_tickets
)

from classifier import (
    load_models,
    classify_ticket
)

from rag.pipeline import run_rag_pipeline


app = Flask(__name__)


# ==========================================
# INITIALIZE DATABASE AND ML MODELS
# ==========================================

create_table()
load_models()


# ==========================================
# HOME / SUBMIT TICKET PAGE
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# SUBMIT TICKET
# ==========================================

@app.route(
    "/submit-ticket",
    methods=["POST"]
)
def submit_ticket():

    try:

        employee_name = request.form.get(
            "employee_name"
        )

        email = request.form.get(
            "email"
        )

        title = request.form.get(
            "title"
        )

        description = request.form.get(
            "description"
        )

        department = request.form.get(
            "department"
        )


        # Validate required fields

        if not all([
            employee_name,
            email,
            title,
            description
        ]):

            return jsonify({

                "success": False,

                "message":
                    "Please fill all required fields"

            }), 400


        # ==========================================
        # MILESTONE 1
        # AI TICKET CLASSIFICATION
        # ==========================================

        result = classify_ticket(
            title,
            description
        )


        category = result["category"]

        severity = result["severity"]

        priority = result["priority"]

        confidence = result["confidence"]


        # ==========================================
        # SAVE TO DATABASE
        # ==========================================

        save_ticket(

            employee_name,

            email,

            title,

            description,

            department,

            category,

            severity,

            priority,

            confidence

        )


        return jsonify({

            "success": True,

            "message":
                "Ticket submitted successfully",

            "result": result

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    tickets = get_all_tickets()

    return render_template(
        "dashboard.html",
        tickets=tickets
    )


# ==========================================
# AI RESOLUTION
# MILESTONE 2 - RAG PIPELINE
# ==========================================

@app.route(
    "/ai-resolution/<int:ticket_id>"
)
def ai_resolution(ticket_id):

    try:

        # Get all tickets

        tickets = get_all_tickets()


        selected_ticket = None


        # Find requested ticket

        for ticket in tickets:

            if int(ticket["id"]) == ticket_id:

                selected_ticket = dict(ticket)

                break


        # Ticket not found

        if selected_ticket is None:

            return render_template(

                "ai_resolution.html",

                ticket=None,

                analysis={},

                retrieved_documents=[],

                resolution=(
                    "Ticket could not be found."
                ),

                status="TICKET_NOT_FOUND",

                sources=[]

            ), 404


        # ==========================================
        # RUN RAG PIPELINE
        # ==========================================

        rag_result = run_rag_pipeline(
            selected_ticket
        )


        # ==========================================
        # DISPLAY AI RESOLUTION
        # ==========================================

        return render_template(

            "ai_resolution.html",

            ticket=rag_result["ticket"],

            analysis=rag_result["analysis"],

            retrieved_documents=(
                rag_result[
                    "retrieved_documents"
                ]
            ),

            resolution=(
                rag_result["resolution"]
            ),

            status=(
                rag_result["status"]
            ),

            sources=(
                rag_result["sources"]
            )

        )


    except Exception as e:

        return render_template(

            "ai_resolution.html",

            ticket=None,

            analysis={},

            retrieved_documents=[],

            resolution=(
                "AI resolution could not be generated. "
                + str(e)
            ),

            status="ERROR",

            sources=[]

        ), 500


# ==========================================
# API - ALL TICKETS
# ==========================================

@app.route("/api/tickets")
def api_tickets():

    tickets = get_all_tickets()

    data = []


    for ticket in tickets:

        data.append({

            "id":
                ticket["id"],

            "employee_name":
                ticket["employee_name"],

            "email":
                ticket["email"],

            "title":
                ticket["title"],

            "description":
                ticket["description"],

            "department":
                ticket["department"],

            "category":
                ticket["category"],

            "severity":
                ticket["severity"],

            "priority":
                ticket["priority"],

            "confidence":
                ticket["confidence"],

            "created_at":
                ticket["created_at"]

        })


    return jsonify(data)


# ==========================================
# SEVERITY GUIDE
# ==========================================

@app.route("/severity-guide")
def severity_guide():

    return render_template(
        "severity_guide.html"
    )


# ==========================================
# LOGIN
# ==========================================

@app.route("/login")
def login():

    return render_template(
        "login.html"
    )


# ==========================================
# REGISTER
# ==========================================

@app.route("/register")
def register():

    return render_template(
        "register.html"
    )


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    print(
        "Starting SupportPilot..."
    )

    print(
        "Open: http://127.0.0.1:5001"
    )

    print(
        "Dashboard: "
        "http://127.0.0.1:5001/dashboard"
    )

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5001

    )