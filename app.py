import sqlite3
from flask import Flask
from flask import render_template
from flask import request
from flask import session

# Create the DB file
connection = sqlite3.connect("subscription.db")

# Creation of registration table (unique ID, name (First Last), unique email, password, account type (user or admin))
connection.execute("""
    CREATE TABLE IF NOT EXISTS user_details(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    account_type TEXT NOT NULL
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
        account_type = request.form["account_type"]

        # check empty values
        if not name or not email or not password:
            return render_template("registration.html", message="No fields can be empty, try again")

        # Formatting of email
        if "@" not in email:
            return render_template("registration.html", message="invalid email type, make sure '@' is included in email")

        # inserting user details in db
        connection = sqlite3.connect("subscription.db")
        try:
            connection.execute("INSERT INTO user_details (name, email, password, account_type) VALUES (?, ?, ?, ?)", (name, email, password, account_type))
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
        # saving session information
        session["name"] = user[1]
        session["id"] = user[0]
        session["email"] = user[2]
        session["password"] = user[3]
        session["account_type"] = user[4]
        return render_template("login.html", message="Successfully Logged in")
    
    return render_template("login.html")

@app.route('/logout', methods=['GET', 'POST'])
# Logging out for existing user
def logout():
    # clearing session if session is not empty
    if session:
        session.clear()
        return render_template("homepage.html", message="Successfully logged out")
    return render_template("homepage.html", message="Not currently logged in")

@app.route('/accmgmt', methods=['GET', 'POST'])
def account_management():
    """
    Account management page for
    Changing name and password
    """
    if "email" not in session:
        return render_template("login.html", message = "Create account first")
    return render_template("account_management.html")

@app.route('/namechange', methods=['GET', 'POST'])
def change_name():
    """
    ability to change name by asking new name and confirming new name
    """
    if "email" not in session:
        return render_template("login.html", message = "Create account first")
    if request.method == "POST":
        # ask for new name and confirm new name fields
        newname = request.form["newname"]
        newname2 = request.form["newname2"]
        if not newname or not newname2:
            return render_template("namechange.html", message="No fields can be empty, try again")
        # new name and confirm new name must match
        if newname != newname2:
            return render_template("namechange.html", message="Names must match, try again")

        # update in sql db
        connection = sqlite3.connect("subscription.db")
        user  = connection.execute("""
            UPDATE user_details SET name = ? WHERE id = ?
            """, (newname, session["id"]))
        connection.commit()
        connection.close()
        session["name"] = newname

        return render_template("namechange.html", message="Name changed successfully!")
    return render_template("namechange.html")

@app.route('/pwdchange', methods=['GET', 'POST'])
def change_password():
    """
    ability to change password by asking old pwd and asking for new pwd twice
    """
    if "email" not in session:
        return render_template("login.html", message = "Create account first")
    
    if request.method == "POST":
        # ask for old password, and new password twice
        password = request.form["password"]
        newpassword = request.form["newpassword"]
        newpassword2 = request.form["newpassword2"]

        if not password or not newpassword or not newpassword2:
            return render_template("pwdchange.html", message="No fields can be empty, try again")
        
        # Old password entered must match what is in the db
        if password != session["password"]:
            return render_template("pwdchange.html", message="Password entered is not correct, try again")
        
        # new pwd and confirm pwd must match
        if newpassword != newpassword2:
            return render_template("pwdchange.html", message="New passwords don't match, try again")

        # update in sql db
        connection = sqlite3.connect("subscription.db")
        user  = connection.execute("""
            UPDATE user_details SET password = ? WHERE id = ?
            """, (newpassword, session["id"]))
        connection.commit()
        connection.close()
        session["password"] = newpassword

        return render_template("pwdchange.html", message="Password changed successfully!")
    return render_template("pwdchange.html")

if __name__ == '__main__':
    app.run(debug=True)

