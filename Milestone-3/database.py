import sqlite3


DATABASE = "tickets.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    connection = (
        sqlite3.connect(
            DATABASE
        )
    )


    connection.row_factory = (
        sqlite3.Row
    )


    return connection


# ============================================================
# TICKETS TABLE
# ============================================================

def create_table():

    connection = (
        get_connection()
    )


    cursor = (
        connection.cursor()
    )


    cursor.execute(
        """
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
        """
    )


    connection.commit()

    connection.close()


# ============================================================
# SAVE TICKET
# ============================================================

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

    connection = (
        get_connection()
    )


    cursor = (
        connection.cursor()
    )


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

            confidence
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            confidence
        )
    )


    ticket_id = (
        cursor.lastrowid
    )


    connection.commit()

    connection.close()


    return ticket_id


# ============================================================
# ALL TICKETS
# ============================================================

def get_all_tickets():

    connection = (
        get_connection()
    )


    tickets = (
        connection.execute(
            """
            SELECT *
            FROM tickets
            ORDER BY id DESC
            """
        )
        .fetchall()
    )


    connection.close()


    return tickets


# ============================================================
# ONE TICKET
# ============================================================

def get_ticket_by_id(
    ticket_id
):

    connection = (
        get_connection()
    )


    ticket = (
        connection.execute(
            """
            SELECT *
            FROM tickets
            WHERE id = ?
            """,

            (ticket_id,)
        )
        .fetchone()
    )


    connection.close()


    return ticket


# ============================================================
# USERS TABLE
# ============================================================

def create_users_table():

    connection = (
        get_connection()
    )


    cursor = (
        connection.cursor()
    )


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            full_name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            department TEXT,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


    connection.commit()

    connection.close()


# ============================================================
# CREATE USER
# ============================================================

def create_user(
    full_name,
    email,
    department,
    password
):

    connection = (
        get_connection()
    )


    try:

        cursor = (
            connection.cursor()
        )


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

    connection = (
        get_connection()
    )


    user = (
        connection.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = LOWER(?)
            """,

            (email,)
        )
        .fetchone()
    )


    connection.close()


    return user


# ============================================================
# USER BY ID
# ============================================================

def get_user_by_id(
    user_id
):

    connection = (
        get_connection()
    )


    user = (
        connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,

            (user_id,)
        )
        .fetchone()
    )


    connection.close()


    return user