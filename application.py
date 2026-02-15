import os

from flask import Flask, render_template, request, session, flash, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__) # This is the variable that is the source of the flask app

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["GET"])
def index():
    return render_template("login.html")

@app.route("/home")
def home():
    if "username" not in session:
        return redirect("/")
    return render_template("home.html",username = session["username"])

@app.route("/authenticate", methods=["POST"])
def authenticate():
    username = request.form.get("username","").strip()
    password = request.form.get("password","")
    action = request.form.get("action")

    if not username or not password:
        flash("Please enter your username and password.")
        return redirect("/")

    if action == "login":
        query = db.execute(text("SELECT * FROM accounts WHERE username = :username"),
            {"username": username}).fetchone()

        # query is None if username not found
        # query.password contains the HASH (even though the column is named 'password')
        if query is None or not check_password_hash(query[2], password):
            flash("Invalid username or password.")
            return redirect("/")

        else:
            session["user_id"] = query[0]
            session["username"] = query[1].capitalize()
            return redirect(url_for("home"))

    elif action == "register":
        query = db.execute(text("""
        SELECT * FROM accounts WHERE username = :username
        """),{"username": username}).fetchone()

        if query is not None:
            flash("Username already exists.")
            return redirect("/")

        else:
            password_hash = generate_password_hash(password)
            db.execute(text("""
                INSERT INTO accounts (username, password)
                    VALUES (:username,:password_hash)
            """),
            {"username": username, "password_hash": password_hash})
            db.commit()
            flash("Successfully registered.")
            return redirect("/")

    flash("Unknown action.")
    return redirect("/")

@app.route("/search", methods=["POST"])
def search():
    search = request.form.get("user_search","")
    action = request.form.get("action")

    if action == "logout":
        session.clear()
        return render_template("login.html")

    if action == "search":
        if not search:
            flash("Please enter a search.")
            return redirect("/home")

        results = db.execute(text("""
            SELECT isbn, title, author, year
            FROM books
            WHERE isbn ILIKE '%' || :search || '%'
            OR title ILIKE '%' || :search || '%'
            OR author ILIKE '%' || :search || '%'
            ORDER BY year DESC
        """), {"search": search}).fetchall()

        return render_template("results.html",results=results, search=search,username=session["username"])

    flash("Unknown action.")
    return redirect("/home")

@app.route("/view_book",methods=["POST"])
def view_book():
    isbn = request.form.get("isbn", "").strip()
    action = request.form.get("action")

    if action == "info":
        book = db.execute(
            text("""
                 SELECT isbn, title, author, year
                 FROM books
                 WHERE isbn = :isbn
                 """),
            {"isbn": isbn}
            ).fetchone()
        return render_template("viewbook.html", book=book, username=session.get("username"))
        
    else:
        return redirect("/home")
    
    flash("Unknown action.")
    return redirect("/home")