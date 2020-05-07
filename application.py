import os, json

from flask import Flask, render_template, request, session, redirect, jsonify, flash, Markup
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import requests

app = Flask(__name__)

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


@app.route("/")
def index():


    #return "Project 1: TODO"
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    
    """New user."""
    
    # Forget any user_id
    session.clear()
    
    if request.method == "POST":

        # Get Form Information
        name = request.form.get("name")
        username = request.form.get("uname")
        password = request.form.get("pswd")

        rows = db.execute("SELECT * FROM tbluser WHERE username = :username",{"username": username}).fetchone()

        if rows:
            return render_template("error.html", message = "Username already exist. Please, try agan.")
        
        db.execute("INSERT INTO tbluser (name, username, password) VALUES (:name, :username,:password)",
            {"name": name, "username": username,"password": password})
        db.commit()
        return render_template("login.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



@app.route("/login", methods=["GET","POST"])
def login():

    # Forget any user_id
    session.clear()
    

    if request.method == "POST":
        
        username = request.form.get("uname")
        pswd= request.form.get("pswd")

        userinfo = db.execute("SELECT * FROM tbluser WHERE username = :username",{"username": username}).fetchone()
    
        # Ensure username exists and password is correct
        if userinfo is None or not pswd != userinfo[2]:
            return render_template("error.html", message="invalid username and/or password")

        
        # Remember which user has logged in
        session["user_id"] = userinfo[0]
        session["user_fullname"] = userinfo[1]
        session["user_name"] = userinfo[2]

        # Redirect user to home page
        return redirect("/")

         # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/search", methods=["POST"])
def search():
   
    
    if request.method == "POST":
        
        search = request.form.get("bookisbn")
        
        if not search:
            return render_template("error.html", message="Please enter a value to search")

        else: 
        
            search = "%" + search + "%"

            books = db.execute("SELECT * FROM tblbooks WHERE isbn LIKE :search OR title LIKE :search OR author LIKE :search OR year LIKE :search LIMIT 20", {"search": search})
        
            # Ensure the book exist
            if books is None:
                return render_template("error.html", message="The book is not part of our inventory")

            
            # return the books
            books = books.fetchall()
            
            return render_template("bookresults.html", books=books)

         # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/book/<isbn>", methods=['GET','POST'])

def book(isbn):
     
    if request.method == "POST":
            
            rating = request.form.get("rating")
            comment = request.form.get("comment")
            sessionUserid = session["user_id"]

            #getting the book id
            bookInfo = db.execute("SELECT id FROM tblbooks WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
            book_id = bookInfo[0]

            # Verify that book has one review for user
            bookreview = db.execute("SELECT * FROM tblreviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": sessionUserid,
                     "book_id": book_id})

            # A review already exists
            if bookreview.rowcount == 1:
                
                flash('you have already entered a comment for this book','message')
                return redirect("/book/" + isbn)
              
            # Convert to save into DB
            rating = int(rating)

            db.execute("INSERT INTO tblreviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": sessionUserid, 
                    "book_id": book_id, 
                    "comment": comment, 
                    "rating": rating})

            # Commit transactions to DB and close the connection
            db.commit()

            flash('Your review was submited', 'message')
            #flash(Markup(render_template("book.html" +"/" + isbn, message="Review submitted!"))
            #return render_template("book.html" +"/" + isbn)

            return redirect("/book/" + isbn)
     
      # Take the book ISBN and redirect to his page (GET)
    else:
        
        result = db.execute("SELECT isbn, title, author, year FROM tblbooks WHERE isbn = :isbn" ,{"isbn": isbn})
        bookDetail = result.fetchall()

        """ GOODREADS reviews """
        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")
                 
        # Query the api with key and ISBN as parameters
        queryApi = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn})
        
        if not queryApi:
            return render_template("error.html", message="Error 404")
      
        # Convert the response to JSON
        response = queryApi.json()
            
        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

            # Append it as the second element on the list. [1]
        bookDetail.append(response)
            
        """ Users reviews """

         # Search book_id by ISBN
        book_result = db.execute("SELECT id FROM tblbooks WHERE isbn = :isbn",
                        {"isbn": isbn}).fetchone()

        # Save id into variable
        book_id = book_result[0]

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)
        results = db.execute("SELECT tbluser.username, comment, rating \
                            FROM tbluser \
                            INNER JOIN tblreviews \
                            ON tbluser.user_id = tblreviews.user_id \
                            WHERE book_id = :book_id \
                            ORDER BY rating",
                            {"book_id": book_id})
        
        reviews = results.fetchall()

        return render_template("bookdetail.html", bookInfo=bookDetail, reviews=reviews)

@app.route("/api/<isbn>", methods=['GET'])
def book_api(isbn):
    """Return details about the book."""

    # Make sure book exists.
    book = db.execute("SELECT title, author, year, isbn, \
                    COUNT(tblreviews.book_id) as review_count, \
                    AVG(tblreviews.rating) as average_score \
                    FROM tblbooks \
                    INNER JOIN tblreviews \
                    ON tblbooks.id = tblreviews.book_id \
                    WHERE tblbooks.isbn = :isbn \
                    GROUP BY title, author, year, isbn",
                    {"isbn": isbn})

    if book.rowcount !=1:
        return jsonify({"error": "Invalid ISBN"}), 422

    # Get all passengers.
    return jsonify({
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "review_account": book.review_count,
            "average_score": float('%.2f'%(book.average_score))
        })

@app.route("/logout")
def logout():
    """ Log out """

    # removing any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")