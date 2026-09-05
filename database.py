import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "tickets.db"
)


def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def create_table():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_name TEXT NOT NULL,

            email TEXT NOT NULL,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            department TEXT,

            category TEXT,

            severity TEXT,

            priority TEXT,

            confidence REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.commit()

    conn.close()

    print("Database table created successfully")


def save_ticket(

    employee_name,
    email,
    title,
    description,
    department,
    category,
    severity,
    priority,
    confidence

):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

        INSERT INTO tickets (

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

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        employee_name,
        email,
        title,
        description,
        department,
        category,
        severity,
        priority,
        confidence

    ))

    conn.commit()

    ticket_id = cursor.lastrowid

    conn.close()

    return ticket_id


def get_all_tickets():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

        SELECT *
        FROM tickets
        ORDER BY id DESC

    """)

    tickets = cursor.fetchall()

    conn.close()

    return tickets


def get_ticket_by_id(ticket_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT * FROM tickets WHERE id = ?",

        (ticket_id,)

    )

    ticket = cursor.fetchone()

    conn.close()

    return ticket


def get_dashboard_stats():

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute(

        "SELECT COUNT(*) FROM tickets"

    )

    total_tickets = cursor.fetchone()[0]


    cursor.execute("""

        SELECT COUNT(*)
        FROM tickets
        WHERE severity = 'High'
        OR severity = 'Critical'

    """)

    high_severity = cursor.fetchone()[0]


    cursor.execute("""

        SELECT COUNT(*)
        FROM tickets
        WHERE priority IN (
            'P1',
            'Critical',
            'High'
        )

    """)

    high_priority = cursor.fetchone()[0]


    conn.close()


    return {

        "total_tickets": total_tickets,

        "high_severity": high_severity,

        "high_priority": high_priority

    }