from flask import Flask, render_template, request, redirect, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
import requests
import sys

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine("postgres://eevrrfxwebpzmo:c08d8cb7f24d62eaccccc63bb727369ff40b4a2e5535c18af6b5eaa07563bc68@ec2-54-235-247-209.compute-1.amazonaws.com:5432/daq0tjud2ca80u")
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()

    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    if request.method == "POST":

        if not request.form.get("username") or not request.form.get("password"):
            return render_template("error.html", message="Please enter fields")


        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchall()

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("error.html", message="Invalid username/password")

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        repassword = request.form.get("repassword")

        if not username or not password or not repassword:
            return render_template("error.html", message="Please enter fields")
        if password != repassword:
            return render_template("error.html", message="Password do not match")

        hash = generate_password_hash(password)

        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchall()
        if rows:
            return render_template("error.html", message="Username already taken")

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", {"username": username, "hash": hash})

        db.commit()

        rows = db.execute("SELECT id FROM users WHERE username = :username", {"username": username}).fetchall()


        session["user_id"] = rows[0]["id"]

        return redirect("/")

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect("/")
    else:
        OGtitle = request.form.get("title")
        title = "%" + OGtitle + "%"
        books = db.execute("SELECT * FROM books WHERE title LIKE :title OR isbn LIKE :title OR author LIKE title", {"title": title}).fetchall()

        if not books or not title:
            return render_template("error.html", message="No such book")

        return render_template("search.html", books=books, OGtitle=OGtitle)



@app.route("/api/<isbn>")
def api(isbn):
    info = db.execute("SELECT title, author, year FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    title = info[0]['title']
    author = info[0]['author']
    year = info[0]['year']
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "UtauKBEM7Nz0Mj0mPAPNg", "isbns": isbn})
    book = res.json()
    if book is None:
        return render_template("error.html", message="No such book")
    alreadyposted = None
    try:
        if session['user_id']:
            print("test", file=sys.stderr)
            username = db.execute("SELECT username FROM users WHERE id = :id", {"id": session['user_id']}).fetchall()
            for review in reviews:
                if username[0]['username'] == review['username']:
                    alreadyposted = True
                    break
    except KeyError:
        pass

    return render_template("api.html", book=book, reviews=reviews, title=title, author=author, year=year, alreadyposted=alreadyposted, isbn=isbn)


@app.route("/review", methods=["POST"])
def review():
    rating = int(request.form.get("rating"))
    title = request.form.get("title")
    review = request.form.get("review")
    isbn = request.form.get("isbn")
    if not rating or not title or not review:
        return render_template("error.html", message="Please enter fields!")
    try:
        username = db.execute("SELECT username FROM users WHERE id = :id", {"id": session['user_id']}).fetchall()
    except KeyError:
        return render_template("error.html", message="You have to be logged in to post a review!")
    db.execute("INSERT INTO reviews (username, rating, title, review, isbn) VALUES (:username, :rating, :title, :review, :isbn)", {"username": username[0]['username'], "rating": rating, "title": title, "review": review, "isbn": isbn})
    db.commit()
    return redirect(f"/api/{isbn}")
