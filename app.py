import sqlite3
from flask import Flask
from flask import render_template
from flask import request

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
@app.route('/')
def page():
    return render_template("homepage.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template("registration.html")

if __name__ == '__main__':
    app.run(debug=True)

