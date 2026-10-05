import sqlite3
from flask import Flask
from flask import render_template
from flask import request
from flask import session

# Create the DB file
connection = sqlite3.connect("subscription.db")

# Creation of registration table (unique ID, name (First Last), unique email, password)
connection.execute("""
    CREATE TABLE IF NOT EXISTS user_details(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
    )
""")

connection.close()

# Flask app
app = Flask(__name__)
app.secret_key = "secret-key"
@app.route('/')
def page():
    return render_template("homepage.html")

@app.route('/register', methods=['GET', 'POST'])
# function for registering a user
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # check empty values
        if not name or not email or not password:
            return render_template("registration.html", message="No fields can be empty, try again")

        # Formatting of email
        if "@" not in email:
            return render_template("registration.html", message="invalid email type, make sure '@' is included in email")

        # inserting user details in db
        connection = sqlite3.connect("subscription.db")
        try:
            connection.execute("INSERT INTO user_details (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            connection.commit()
        # error handling for duplicate emails when registered
        except sqlite3.IntegrityError:
            connection.close()
            return render_template("registration.html", message="Email already exists")
        connection.close()
        return render_template("registration.html", message="Successfully registered!")
    return render_template("registration.html")

@app.route('/login', methods=['GET', 'POST'])
# Login for existing user
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # check empty values
        if not email or not password:
            return render_template("login.html", message="No fields can be empty, try again")

        # Formatting of email
        if "@" not in email:
            return render_template("login.html", message="invalid email type, make sure '@' is included in email")

        # getting values from db
        connection = sqlite3.connect("subscription.db")
        user  = connection.execute("""
        SELECT * FROM user_details where email = ? AND password = ?
        """, (email, password)).fetchone()

        connection.close()
        if user is None:
            return render_template("login.html", message="Invalid email or password")
        # for homepage to show what user is logged in
        session["name"] = user[1]
        return render_template("login.html", message="Successfully Logged in")
    
    return render_template("login.html")

if __name__ == '__main__':
    app.run(debug=True)

