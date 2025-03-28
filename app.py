import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, render_template, redirect, url_for, flash

app = Flask(__name__)

POSTGRES_CONNECTION_STRING = os.environ.get("NEON_POSTGRESQL_CONNECTIONSTRING")
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "A_SECRET_KEY")


def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        raise


def create_todos_table_if_not_exists(conn):
    """Creates the todos table if it doesn't exist."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    task TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
            )
            conn.commit()
            print("Checked/created 'todos' table.")
    except psycopg2.Error as e:
        print(f"Error creating table: {e}")
        conn.rollback()
        raise


def get_todos():
    """Fetches all todos from the database. Creates table if it doesn't exist."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id, task FROM todos ORDER BY created_at DESC;")
            todos = cur.fetchall()
            return [dict(row) for row in todos]

    except psycopg2.errors.UndefinedTable:
        print("Table 'todos' not found. Attempting to create it.")
        if conn:
            conn.rollback()
            try:
                create_todos_table_if_not_exists(conn)
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT id, task FROM todos ORDER BY created_at DESC;")
                    todos = cur.fetchall()
                    return [dict(row) for row in todos]
            except Exception as create_e:
                print(f"Failed to create table or retry fetching: {create_e}")
                if conn:
                    conn.close()
                return []
        else:
            print("Cannot create table: No database connection.")
            return []

    except psycopg2.Error as e:
        print(f"Database error in get_todos: {e}")
        if conn:
            conn.rollback()
        return []

    finally:
        if conn:
            conn.close()


@app.route("/")
def index():
    """Displays the list of todos."""
    todos = get_todos()
    return render_template("index.html", todos=todos)


@app.route("/add", methods=["POST"])
def add_todo():
    """Adds a new todo item."""
    task = request.form.get("task")
    if not task:
        flash("Task cannot be empty!", "error")
        return redirect(url_for("index"))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO todos (task) VALUES (%s);", (task,))
            conn.commit()
        flash("Task added successfully!", "success")
    except psycopg2.Error as e:
        print(f"Database error adding task: {e}")
        flash(f"Error adding task: {e}", "error")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Unexpected error adding task: {e}")
        flash(f"An unexpected error occurred: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete_todo(todo_id):
    """Deletes a todo item."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM todos WHERE id = %s;", (todo_id,))
            conn.commit()
            if cur.rowcount == 0:
                flash(f"Task with ID {todo_id} not found.", "warning")
            else:
                flash("Task deleted successfully!", "success")
    except psycopg2.Error as e:
        print(f"Database error deleting task: {e}")
        flash(f"Error deleting task: {e}", "error")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Unexpected error deleting task: {e}")
        flash(f"An unexpected error occurred: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    try:
        conn = get_db_connection()
        create_todos_table_if_not_exists(conn)
        conn.close()
        print("Database connection successful.")
    except Exception as e:
        print(f"Database connection failed on startup: {e}")
        exit(1)

    app.run(host="0.0.0.0", port=8080, debug=True)
