import sqlite3


DATABASE = "tickets.db"


# ============================================================
# HELPERS
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def _column_exists(
    connection,
    table_name,
    column_name
):

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def _add_column_if_missing(
    connection,
    table_name,
    column_name,
    definition
):

    if not _column_exists(
        connection,
        table_name,
        column_name
    ):

        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


def _to_db_boolean(
    value
):

    if value is None:
        return None

    if isinstance(
        value,
        str
    ):

        value = (
            value
            .strip()
            .lower()
        )

        if value in (
            "true",
            "1",
            "yes",
            "y",
            "on"
        ):
            return 1

        if value in (
            "false",
            "0",
            "no",
            "n",
            "off"
        ):
            return 0

    return 1 if bool(value) else 0


def _safe_float(
    value,
    default=None
):

    if value is None:
        return default

    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError
    ):
        return default


def _safe_int(
    value,
    default=0
):

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError
    ):
        return default


def _dict_rows(
    rows
):

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# TICKETS TABLE
# ============================================================

def create_table():

    connection = get_connection()

    try:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                employee_name TEXT,

                email TEXT,

                title TEXT NOT NULL,

                description TEXT NOT NULL,

                department TEXT,

                category TEXT,

                severity TEXT,

                priority TEXT,

                confidence REAL,

                user_id INTEGER,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP

            )
            """
        )


        # Migration-safe support for older databases.

        _add_column_if_missing(
            connection,
            "tickets",
            "employee_name",
            "TEXT"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "email",
            "TEXT"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "department",
            "TEXT"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "category",
            "TEXT"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "severity",
            "TEXT"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "priority",
            "TEXT"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "confidence",
            "REAL"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "user_id",
            "INTEGER"
        )

        _add_column_if_missing(
            connection,
            "tickets",
            "created_at",
            "TIMESTAMP"
        )


        connection.commit()

    finally:

        connection.close()


# ============================================================
# SAVE TICKET
# Supports original Milestone 1 call AND updated app.py call.
# ============================================================

def save_ticket(
    employee_name=None,
    email=None,
    title=None,
    description=None,
    department=None,
    category=None,
    severity=None,
    priority=None,
    confidence=None,
    user_id=None
):

    connection = get_connection()

    try:

        # If updated app.py only supplies user_id,
        # recover user information automatically.

        if user_id is not None:

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE id = ?
                """,
                (
                    user_id,
                )
            ).fetchone()

            if user:

                if not employee_name:
                    employee_name = (
                        user["full_name"]
                    )

                if not email:
                    email = (
                        user["email"]
                    )

                if not department:
                    department = (
                        user["department"]
                    )


        employee_name = (
            employee_name
            or "SupportPilot User"
        )

        email = (
            email
            or ""
        )

        department = (
            department
            or ""
        )


        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO tickets (

                employee_name,
                email,
                title,
                description,
                department,
                category,
                severity,
                priority,
                confidence,
                user_id

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee_name,
                email,
                title,
                description,
                department,
                category,
                severity,
                priority,
                confidence,
                user_id
            )
        )

        ticket_id = (
            cursor.lastrowid
        )

        connection.commit()

        return ticket_id

    finally:

        connection.close()


# ============================================================
# ALL TICKETS
# ============================================================

def get_all_tickets():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM tickets
            ORDER BY id DESC
            """
        ).fetchall()

        return _dict_rows(
            rows
        )

    finally:

        connection.close()


# ============================================================
# ONE TICKET
# ============================================================

def get_ticket_by_id(
    ticket_id
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM tickets
            WHERE id = ?
            """,
            (
                ticket_id,
            )
        ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    finally:

        connection.close()


# ============================================================
# USERS TABLE
# ============================================================

def create_users_table():

    connection = get_connection()

    try:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                full_name TEXT NOT NULL,

                email TEXT UNIQUE NOT NULL,

                department TEXT,

                password TEXT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP

            )
            """
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# CREATE USER
# Supports original:
# create_user(full_name, email, department, password)
#
# Also supports:
# create_user(name, email, password)
# ============================================================

def create_user(
    full_name,
    email,
    department=None,
    password=None
):

    # Updated app.py may call:
    # create_user(name, email, password_hash)
    #
    # In that case the third positional argument
    # is actually the password.

    if password is None:

        password = department

        department = ""


    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (

                full_name,
                email,
                department,
                password

            )

            VALUES (?, ?, ?, ?)
            """,
            (
                full_name,
                email,
                department,
                password
            )
        )

        user_id = (
            cursor.lastrowid
        )

        connection.commit()

        return user_id

    finally:

        connection.close()


# ============================================================
# USER BY EMAIL
# ============================================================

def get_user_by_email(
    email
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = LOWER(?)
            """,
            (
                email,
            )
        ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    finally:

        connection.close()


# ============================================================
# USER BY ID
# ============================================================

def get_user_by_id(
    user_id
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (
                user_id,
            )
        ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    finally:

        connection.close()


# ============================================================
# MILESTONE 4 ANALYTICS TABLE
# ============================================================

def create_analytics_table():

    connection = get_connection()

    try:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_analytics (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ticket_id INTEGER UNIQUE NOT NULL,

                workflow_status TEXT,

                ai_confidence REAL,

                ai_resolved INTEGER DEFAULT 0,

                escalated INTEGER DEFAULT 0,

                resolution_success INTEGER,

                resolution_outcome_recorded
                    INTEGER DEFAULT 0,

                kb_found INTEGER,

                ai_response_time REAL,

                resolution_time REAL,

                classification_correct INTEGER,

                classification_verified
                    INTEGER DEFAULT 0,

                predicted_category TEXT,

                actual_category TEXT,

                customer_rating REAL,

                jira_issue_key TEXT,

                jira_issue_url TEXT,

                email_sent INTEGER DEFAULT 0,

                escalation_reason TEXT,

                resolution_failed INTEGER DEFAULT 0,

                customer_requested_human
                    INTEGER DEFAULT 0,

                repeated_attempts INTEGER DEFAULT 0,

                processed_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(ticket_id)
                    REFERENCES tickets(id)

            )
            """
        )


        # ====================================================
        # MIGRATION-SAFE COLUMNS
        # Existing tickets.db does NOT need to be deleted.
        # ====================================================

        columns = {

            "workflow_status":
                "TEXT",

            "ai_confidence":
                "REAL",

            "ai_resolved":
                "INTEGER DEFAULT 0",

            "escalated":
                "INTEGER DEFAULT 0",

            "resolution_success":
                "INTEGER",

            "resolution_outcome_recorded":
                "INTEGER DEFAULT 0",

            "kb_found":
                "INTEGER",

            "ai_response_time":
                "REAL",

            "resolution_time":
                "REAL",

            "classification_correct":
                "INTEGER",

            "classification_verified":
                "INTEGER DEFAULT 0",

            "predicted_category":
                "TEXT",

            "actual_category":
                "TEXT",

            "customer_rating":
                "REAL",

            "jira_issue_key":
                "TEXT",

            "jira_issue_url":
                "TEXT",

            "email_sent":
                "INTEGER DEFAULT 0",

            "escalation_reason":
                "TEXT",

            "resolution_failed":
                "INTEGER DEFAULT 0",

            "customer_requested_human":
                "INTEGER DEFAULT 0",

            "repeated_attempts":
                "INTEGER DEFAULT 0",

            "processed_at":
                "TIMESTAMP"

        }


        for (
            column_name,
            definition
        ) in columns.items():

            _add_column_if_missing(
                connection,
                "ticket_analytics",
                column_name,
                definition
            )


        connection.commit()

    finally:

        connection.close()


# ============================================================
# ENSURE ANALYTICS ROW
# ============================================================

def _ensure_analytics_row(
    connection,
    ticket_id
):

    connection.execute(
        """
        INSERT INTO ticket_analytics (
            ticket_id
        )

        VALUES (?)

        ON CONFLICT(ticket_id)
        DO NOTHING
        """,
        (
            ticket_id,
        )
    )


# ============================================================
# GET TICKET ANALYTICS
# ============================================================

def get_ticket_analytics(
    ticket_id
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM ticket_analytics
            WHERE ticket_id = ?
            """,
            (
                ticket_id,
            )
        ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    finally:

        connection.close()


# ============================================================
# SAVE / UPDATE ANALYTICS
#
# Supports the new app.py keywords:
# ai_confidence
# ai_response_time
# kb_found
# resolution_failed
# customer_requested_human
# repeated_attempts
# workflow_status
# escalation_reason
# jira_key
# jira_url
#
# Also keeps old fields.
# ============================================================

def save_ticket_analytics(
    ticket_id,
    workflow_status=None,
    ai_confidence=None,
    ai_resolved=None,
    escalated=None,
    resolution_success=None,
    kb_found=None,
    ai_response_time=None,
    resolution_time=None,
    classification_correct=None,
    customer_rating=None,
    jira_issue_key=None,
    jira_issue_url=None,
    email_sent=None,
    escalation_reason=None,
    resolution_failed=None,
    customer_requested_human=None,
    repeated_attempts=None,
    jira_key=None,
    jira_url=None
):

    connection = get_connection()

    try:

        _ensure_analytics_row(
            connection,
            ticket_id
        )


        if jira_issue_key is None:
            jira_issue_key = jira_key

        if jira_issue_url is None:
            jira_issue_url = jira_url


        # Derive workflow booleans only when
        # workflow status was actually supplied.

        if workflow_status is not None:

            status = str(
                workflow_status
            ).strip().upper()

            if ai_resolved is None:
                ai_resolved = (
                    status == "AUTO_RESOLVE"
                )

            if escalated is None:
                escalated = (
                    status == "ESCALATE"
                )


        updates = {

            "workflow_status":
                workflow_status,

            "ai_confidence":
                _safe_float(
                    ai_confidence
                ),

            "ai_resolved":
                _to_db_boolean(
                    ai_resolved
                ),

            "escalated":
                _to_db_boolean(
                    escalated
                ),

            "resolution_success":
                _to_db_boolean(
                    resolution_success
                ),

            "kb_found":
                _to_db_boolean(
                    kb_found
                ),

            "ai_response_time":
                _safe_float(
                    ai_response_time
                ),

            "resolution_time":
                _safe_float(
                    resolution_time
                ),

            "classification_correct":
                _to_db_boolean(
                    classification_correct
                ),

            "customer_rating":
                _safe_float(
                    customer_rating
                ),

            "jira_issue_key":
                jira_issue_key,

            "jira_issue_url":
                jira_issue_url,

            "email_sent":
                _to_db_boolean(
                    email_sent
                ),

            "escalation_reason":
                escalation_reason,

            "resolution_failed":
                _to_db_boolean(
                    resolution_failed
                ),

            "customer_requested_human":
                _to_db_boolean(
                    customer_requested_human
                ),

            "repeated_attempts":
                (
                    _safe_int(
                        repeated_attempts
                    )
                    if repeated_attempts
                    is not None
                    else None
                )

        }


        assignments = []

        values = []


        for (
            column,
            value
        ) in updates.items():

            if value is not None:

                assignments.append(
                    f"{column} = ?"
                )

                values.append(
                    value
                )


        if assignments:

            assignments.append(
                "processed_at = CURRENT_TIMESTAMP"
            )

            values.append(
                ticket_id
            )

            connection.execute(
                f"""
                UPDATE ticket_analytics
                SET {", ".join(assignments)}
                WHERE ticket_id = ?
                """,
                values
            )

        if ai_confidence is not None:
            connection.execute(
                """
                UPDATE tickets
                SET confidence = ?
                WHERE id = ?
                """,
                (
                    _safe_float(ai_confidence),
                    ticket_id
                )
            )

        connection.commit()

        return True

    finally:

        connection.close()


# ============================================================
# CUSTOMER RATING
# UPSERT - works even if analytics row doesn't exist yet.
# ============================================================

def save_customer_rating(
    ticket_id,
    rating
):

    rating = _safe_float(
        rating
    )

    if (
        rating is None
        or rating < 1
        or rating > 5
    ):

        raise ValueError(
            "Rating must be between 1 and 5."
        )


    connection = get_connection()

    try:

        _ensure_analytics_row(
            connection,
            ticket_id
        )

        connection.execute(
            """
            UPDATE ticket_analytics

            SET
                customer_rating = ?,
                processed_at = CURRENT_TIMESTAMP

            WHERE ticket_id = ?
            """,
            (
                rating,
                ticket_id
            )
        )

        connection.commit()

        return True

    finally:

        connection.close()


# ============================================================
# RESOLUTION OUTCOME
# ============================================================

def mark_resolution_outcome(
    ticket_id,
    successful,
    resolution_time=None
):

    connection = get_connection()

    try:

        _ensure_analytics_row(
            connection,
            ticket_id
        )

        success_value = (
            _to_db_boolean(
                successful
            )
        )


        if resolution_time is None:

            connection.execute(
                """
                UPDATE ticket_analytics

                SET
                    resolution_success = ?,
                    resolution_outcome_recorded = 1,
                    processed_at = CURRENT_TIMESTAMP

                WHERE ticket_id = ?
                """,
                (
                    success_value,
                    ticket_id
                )
            )

        else:

            connection.execute(
                """
                UPDATE ticket_analytics

                SET
                    resolution_success = ?,
                    resolution_outcome_recorded = 1,
                    resolution_time = ?,
                    processed_at = CURRENT_TIMESTAMP

                WHERE ticket_id = ?
                """,
                (
                    success_value,
                    _safe_float(
                        resolution_time,
                        0.0
                    ),
                    ticket_id
                )
            )


        connection.commit()

        return True

    finally:

        connection.close()


# ============================================================
# CUSTOMER REQUESTED HUMAN
# ============================================================

def set_customer_requested_human(
    ticket_id,
    requested=True
):

    connection = get_connection()

    try:

        _ensure_analytics_row(
            connection,
            ticket_id
        )

        connection.execute(
            """
            UPDATE ticket_analytics

            SET
                customer_requested_human = ?,
                processed_at = CURRENT_TIMESTAMP

            WHERE ticket_id = ?
            """,
            (
                _to_db_boolean(
                    requested
                ),
                ticket_id
            )
        )

        connection.commit()

        return True

    finally:

        connection.close()


# ============================================================
# REPEATED ATTEMPTS
# ============================================================

def get_repeated_attempts(
    ticket_id
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT repeated_attempts
            FROM ticket_analytics
            WHERE ticket_id = ?
            """,
            (
                ticket_id,
            )
        ).fetchone()

        if not row:
            return 0

        return _safe_int(
            row["repeated_attempts"],
            0
        )

    finally:

        connection.close()


def increment_repeated_attempts(
    ticket_id
):

    connection = get_connection()

    try:

        _ensure_analytics_row(
            connection,
            ticket_id
        )

        connection.execute(
            """
            UPDATE ticket_analytics

            SET
                repeated_attempts =
                    COALESCE(
                        repeated_attempts,
                        0
                    ) + 1,

                processed_at =
                    CURRENT_TIMESTAMP

            WHERE ticket_id = ?
            """,
            (
                ticket_id,
            )
        )

        row = connection.execute(
            """
            SELECT repeated_attempts
            FROM ticket_analytics
            WHERE ticket_id = ?
            """,
            (
                ticket_id,
            )
        ).fetchone()

        connection.commit()

        return _safe_int(
            row["repeated_attempts"],
            0
        )

    finally:

        connection.close()


# ============================================================
# CLASSIFICATION RESULT
# ============================================================

def save_classification_result(
    ticket_id,
    predicted_category=None,
    actual_category=None,
    correct=None,
    confidence=None
):

    connection = get_connection()

    try:

        _ensure_analytics_row(
            connection,
            ticket_id
        )


        # If an actual label exists,
        # this becomes a verified classifier sample.

        verified = (
            actual_category is not None
            and str(
                actual_category
            ).strip() != ""
        )


        if (
            verified
            and correct is None
            and predicted_category is not None
        ):

            correct = (
                str(
                    predicted_category
                ).strip().lower()
                ==
                str(
                    actual_category
                ).strip().lower()
            )


        updates = {

            "predicted_category":
                predicted_category,

            "actual_category":
                actual_category,

            "classification_correct":
                (
                    _to_db_boolean(
                        correct
                    )
                    if verified
                    else None
                ),

            "classification_verified":
                (
                    1
                    if verified
                    else None
                ),

            "ai_confidence":
                _safe_float(
                    confidence
                )

        }


        assignments = []

        values = []


        for (
            column,
            value
        ) in updates.items():

            if value is not None:

                assignments.append(
                    f"{column} = ?"
                )

                values.append(
                    value
                )


        if assignments:

            assignments.append(
                "processed_at = CURRENT_TIMESTAMP"
            )

            values.append(
                ticket_id
            )

            connection.execute(
                f"""
                UPDATE ticket_analytics
                SET {", ".join(assignments)}
                WHERE ticket_id = ?
                """,
                values
            )


        connection.commit()

        return True

    finally:

        connection.close()


# ============================================================
# ALL ANALYTICS
# ============================================================

def get_all_ticket_analytics():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT

                a.*,

                t.employee_name,
                t.email,
                t.title,
                t.description,
                t.department,
                t.category,
                t.severity,
                t.priority,
                t.confidence,
                t.created_at

            FROM ticket_analytics a

            JOIN tickets t
                ON t.id = a.ticket_id

            ORDER BY
                COALESCE(
                    a.processed_at,
                    t.created_at
                ) DESC
            """
        ).fetchall()

        return _dict_rows(
            rows
        )

    finally:

        connection.close()


# ============================================================
# DASHBOARD METRICS
#
# IMPORTANT:
# Milestone 4 PPT formulas use TOTAL TICKETS
# as denominator for:
#
# AI Resolution Rate
# Resolution Success Rate
# KB Coverage
#
# Unmeasured metrics return None, not fake 0/100.
# ============================================================

def get_dashboard_metrics():

    connection = get_connection()

    try:

        total_tickets = connection.execute(
            """
            SELECT COUNT(*)
            FROM tickets
            """
        ).fetchone()[0]


        processed_tickets = connection.execute(
            """
            SELECT COUNT(*)
            FROM ticket_analytics

            WHERE workflow_status IS NOT NULL
            """
        ).fetchone()[0]


        ai_resolved = connection.execute(
            """
            SELECT COUNT(*)
            FROM ticket_analytics
            WHERE ai_resolved = 1
            """
        ).fetchone()[0]


        escalated = connection.execute(
            """
            SELECT COUNT(*)
            FROM ticket_analytics
            WHERE escalated = 1
            """
        ).fetchone()[0]


        successful = connection.execute(
            """
            SELECT COUNT(*)
            FROM ticket_analytics
            WHERE resolution_success = 1
            """
        ).fetchone()[0]


        kb_found = connection.execute(
            """
            SELECT COUNT(*)
            FROM ticket_analytics
            WHERE kb_found = 1
            """
        ).fetchone()[0]


        rated_row = connection.execute(
            """
            SELECT
                COUNT(*) AS count,
                AVG(customer_rating) AS average

            FROM ticket_analytics

            WHERE customer_rating IS NOT NULL
            """
        ).fetchone()


        ai_time_row = connection.execute(
            """
            SELECT
                COUNT(*) AS count,
                AVG(ai_response_time) AS average

            FROM ticket_analytics

            WHERE ai_response_time IS NOT NULL
              AND ai_response_time >= 0
            """
        ).fetchone()


        resolution_time_row = connection.execute(
            """
            SELECT
                COUNT(*) AS count,
                AVG(resolution_time) AS average

            FROM ticket_analytics

            WHERE resolution_time IS NOT NULL
              AND resolution_time >= 0
            """
        ).fetchone()


        classifier = (
            _get_classifier_performance_with_connection(
                connection
            )
        )


        if total_tickets > 0:

            ai_resolution_rate = round(
                (
                    ai_resolved
                    /
                    total_tickets
                )
                *
                100,
                2
            )

            escalation_rate = round(
                (
                    escalated
                    /
                    total_tickets
                )
                *
                100,
                2
            )

            resolution_success_rate = round(
                (
                    successful
                    /
                    total_tickets
                )
                *
                100,
                2
            )

            kb_coverage = round(
                (
                    kb_found
                    /
                    total_tickets
                )
                *
                100,
                2
            )

        else:

            ai_resolution_rate = 0.0

            escalation_rate = 0.0

            resolution_success_rate = 0.0

            kb_coverage = 0.0


        return {

            "total_tickets":
                total_tickets,

            "processed_tickets":
                processed_tickets,

            "ai_resolved":
                ai_resolved,

            "escalated":
                escalated,

            "ai_resolution_rate":
                ai_resolution_rate,

            "escalation_rate":
                escalation_rate,

            "resolution_success_rate":
                resolution_success_rate,

            "kb_coverage":
                kb_coverage,

            "classification_accuracy":
                classifier.get(
                    "accuracy"
                ),

            "average_ai_response_time":
                (
                    round(
                        float(
                            ai_time_row[
                                "average"
                            ]
                        ),
                        3
                    )
                    if (
                        ai_time_row["count"] > 0
                        and
                        ai_time_row["average"]
                        is not None
                    )
                    else None
                ),

            "average_resolution_time":
                (
                    round(
                        float(
                            resolution_time_row[
                                "average"
                            ]
                        ),
                        3
                    )
                    if (
                        resolution_time_row[
                            "count"
                        ] > 0
                        and
                        resolution_time_row[
                            "average"
                        ] is not None
                    )
                    else None
                ),

            "customer_satisfaction":
                (
                    round(
                        float(
                            rated_row[
                                "average"
                            ]
                        ),
                        2
                    )
                    if (
                        rated_row["count"] > 0
                        and
                        rated_row["average"]
                        is not None
                    )
                    else None
                ),

            "rated_tickets":
                rated_row["count"],

            # Historical uptime monitoring has
            # not been implemented yet.
            # Do NOT fake 100%.
            "system_uptime":
                None,

            "system_uptime_status":
                "NOT_MEASURED"

        }

    finally:

        connection.close()


# ============================================================
# CATEGORY ANALYTICS
# ============================================================

def get_category_analytics():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT

                COALESCE(
                    NULLIF(
                        category,
                        ''
                    ),
                    'Unknown'
                ) AS category,

                COUNT(*) AS total

            FROM tickets

            GROUP BY
                COALESCE(
                    NULLIF(
                        category,
                        ''
                    ),
                    'Unknown'
                )

            ORDER BY total DESC
            """
        ).fetchall()

        return _dict_rows(
            rows
        )

    finally:

        connection.close()


# ============================================================
# PRIORITY ANALYTICS
# ============================================================

def get_priority_analytics():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT

                COALESCE(
                    NULLIF(
                        priority,
                        ''
                    ),
                    'Unknown'
                ) AS priority,

                COUNT(*) AS total

            FROM tickets

            GROUP BY
                COALESCE(
                    NULLIF(
                        priority,
                        ''
                    ),
                    'Unknown'
                )

            ORDER BY total DESC
            """
        ).fetchall()

        return _dict_rows(
            rows
        )

    finally:

        connection.close()


# ============================================================
# WORKFLOW ANALYTICS
# ============================================================

def get_workflow_analytics():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT

                COALESCE(
                    NULLIF(
                        workflow_status,
                        ''
                    ),
                    'UNKNOWN'
                ) AS status,

                COUNT(*) AS total

            FROM ticket_analytics

            WHERE workflow_status IS NOT NULL

            GROUP BY
                COALESCE(
                    NULLIF(
                        workflow_status,
                        ''
                    ),
                    'UNKNOWN'
                )

            ORDER BY total DESC
            """
        ).fetchall()

        return _dict_rows(
            rows
        )

    finally:

        connection.close()


# ============================================================
# HUMAN INTERVENTION MONITOR
# ============================================================

def get_escalated_tickets():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT

                t.id AS ticket_id,
                t.id,

                t.employee_name,
                t.email,
                t.title,
                t.description,
                t.category,
                t.severity,
                t.priority,

                COALESCE(
                    a.ai_confidence,
                    t.confidence
                ) AS ai_confidence,

                COALESCE(
                    a.ai_confidence,
                    t.confidence
                ) AS confidence,

                a.workflow_status,

                a.resolution_failed,

                a.customer_requested_human,

                a.repeated_attempts,

                a.escalation_reason,

                a.jira_issue_key,

                a.jira_issue_url,

                a.processed_at

            FROM ticket_analytics a

            JOIN tickets t
                ON t.id = a.ticket_id

            WHERE
                a.escalated = 1

                OR
                UPPER(
                    COALESCE(
                        a.workflow_status,
                        ''
                    )
                ) = 'ESCALATE'

                OR
                a.customer_requested_human = 1

            ORDER BY
                COALESCE(
                    a.processed_at,
                    t.created_at
                ) DESC
            """
        ).fetchall()

        return _dict_rows(
            rows
        )

    finally:

        connection.close()


# ============================================================
# ESCALATION STATISTICS
# Reasons can overlap.
# ============================================================

def get_escalation_statistics():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT

                a.escalation_reason,

                a.resolution_failed,

                a.customer_requested_human,

                a.repeated_attempts,

                a.ai_confidence,

                t.priority

            FROM ticket_analytics a

            JOIN tickets t
                ON t.id = a.ticket_id

            WHERE
                a.escalated = 1

                OR
                UPPER(
                    COALESCE(
                        a.workflow_status,
                        ''
                    )
                ) = 'ESCALATE'
            """
        ).fetchall()


        statistics = {

            "total_escalated":
                len(rows),

            "critical_priority":
                0,

            "low_confidence":
                0,

            "resolution_failed":
                0,

            "customer_requested_human":
                0,

            "repeated_attempts":
                0

        }


        for row in rows:

            priority = str(
                row["priority"]
                or ""
            ).strip().lower()

            confidence = _safe_float(
                row["ai_confidence"],
                None
            )


            if priority == "critical":

                statistics[
                    "critical_priority"
                ] += 1


            if (
                confidence is not None
                and confidence < 70
            ):

                statistics[
                    "low_confidence"
                ] += 1


            if _safe_int(
                row[
                    "resolution_failed"
                ],
                0
            ) == 1:

                statistics[
                    "resolution_failed"
                ] += 1


            if _safe_int(
                row[
                    "customer_requested_human"
                ],
                0
            ) == 1:

                statistics[
                    "customer_requested_human"
                ] += 1


            if _safe_int(
                row[
                    "repeated_attempts"
                ],
                0
            ) >= 3:

                statistics[
                    "repeated_attempts"
                ] += 1


        statistics["reasons"] = [

            {
                "reason":
                    "Critical Priority",

                "count":
                    statistics[
                        "critical_priority"
                    ]
            },

            {
                "reason":
                    "AI Confidence Below 70%",

                "count":
                    statistics[
                        "low_confidence"
                    ]
            },

            {
                "reason":
                    "Resolution Failed",

                "count":
                    statistics[
                        "resolution_failed"
                    ]
            },

            {
                "reason":
                    "Customer Requested Human",

                "count":
                    statistics[
                        "customer_requested_human"
                    ]
            },

            {
                "reason":
                    "Repeated Attempts >= 3",

                "count":
                    statistics[
                        "repeated_attempts"
                    ]
            }

        ]


        return statistics

    finally:

        connection.close()


# ============================================================
# CLASSIFIER PERFORMANCE
#
# IMPORTANT:
# Only verified classifications count.
#
# No verified labels = None metrics.
# ============================================================

def _get_classifier_performance_with_connection(
    connection
):

    rows = connection.execute(
        """
        SELECT

            predicted_category,

            actual_category,

            classification_correct

        FROM ticket_analytics

        WHERE
            classification_verified = 1

            AND predicted_category
                IS NOT NULL

            AND actual_category
                IS NOT NULL
        """
    ).fetchall()


    if not rows:

        return {

            "accuracy":
                None,

            "precision":
                None,

            "recall":
                None,

            "f1_score":
                None,

            "sample_count":
                0,

            "correct_predictions":
                0,

            "incorrect_predictions":
                0,

            "labels":
                [],

            "confusion_matrix":
                []

        }


    actual = [

        str(
            row[
                "actual_category"
            ]
        )

        for row in rows
    ]


    predicted = [

        str(
            row[
                "predicted_category"
            ]
        )

        for row in rows
    ]


    try:

        from sklearn.metrics import (
            accuracy_score,
            precision_score,
            recall_score,
            f1_score,
            confusion_matrix
        )


        labels = sorted(
            set(
                actual
                +
                predicted
            )
        )


        accuracy = accuracy_score(
            actual,
            predicted
        )


        precision = precision_score(
            actual,
            predicted,
            average="weighted",
            zero_division=0
        )


        recall = recall_score(
            actual,
            predicted,
            average="weighted",
            zero_division=0
        )


        f1 = f1_score(
            actual,
            predicted,
            average="weighted",
            zero_division=0
        )


        matrix = confusion_matrix(
            actual,
            predicted,
            labels=labels
        ).tolist()


    except ImportError:

        # Accuracy still remains measurable.
        # Precision/recall/F1 require sklearn.

        labels = sorted(
            set(
                actual
                +
                predicted
            )
        )

        correct = sum(
            1
            for (
                actual_value,
                predicted_value
            ) in zip(
                actual,
                predicted
            )
            if (
                actual_value
                ==
                predicted_value
            )
        )

        accuracy = (
            correct
            /
            len(actual)
        )

        precision = None

        recall = None

        f1 = None

        matrix = []


    correct_predictions = sum(
        1

        for (
            actual_value,
            predicted_value
        ) in zip(
            actual,
            predicted
        )

        if (
            actual_value
            ==
            predicted_value
        )
    )


    return {

        "accuracy":
            round(
                float(
                    accuracy
                )
                *
                100,
                2
            ),

        "precision":
            (
                round(
                    float(
                        precision
                    )
                    *
                    100,
                    2
                )
                if precision
                is not None
                else None
            ),

        "recall":
            (
                round(
                    float(
                        recall
                    )
                    *
                    100,
                    2
                )
                if recall
                is not None
                else None
            ),

        "f1_score":
            (
                round(
                    float(
                        f1
                    )
                    *
                    100,
                    2
                )
                if f1
                is not None
                else None
            ),

        "sample_count":
            len(
                actual
            ),

        "correct_predictions":
            correct_predictions,

        "incorrect_predictions":
            (
                len(
                    actual
                )
                -
                correct_predictions
            ),

        "labels":
            labels,

        "confusion_matrix":
            matrix

    }


def get_classifier_performance():

    connection = get_connection()

    try:

        return (
            _get_classifier_performance_with_connection(
                connection
            )
        )

    finally:

        connection.close()


# ============================================================
# COMPLETE DASHBOARD DATA
# ============================================================

def get_complete_dashboard_data():

    return {

        "metrics":
            get_dashboard_metrics(),

        "categories":
            get_category_analytics(),

        "priorities":
            get_priority_analytics(),

        "workflow":
            get_workflow_analytics(),

        "escalated_tickets":
            get_escalated_tickets(),

        "human_intervention":
            get_escalated_tickets(),

        "escalation_statistics":
            get_escalation_statistics(),

        "classifier_performance":
            get_classifier_performance()

    }


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    create_users_table()

    create_table()

    create_analytics_table()


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print(
        "SupportPilot database initialized successfully."
    )

    print(
        get_complete_dashboard_data()
    )