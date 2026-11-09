import sqlite3
from flask import Flask
from flask import render_template
from flask import request
from flask import session
from flask import redirect, url_for, flash

# Create the DB file
connection = sqlite3.connect("subscription.db")

# Creation of registration table (unique ID, name (First Last), unique email, password, account type (user or admin))
# Subscription type also included for users only (0 default, no plan. 1, student plan. 2, individual plan)
connection.execute("""
    CREATE TABLE IF NOT EXISTS user_details(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    account_type TEXT NOT NULL,
    subscription_type INTEGER NOT NULL DEFAULT 0 CHECK (subscription_type IN (0,1,2))
    )
""")

# Media Table to store details for movies/ shows
connection.execute("""
    CREATE TABLE IF NOT EXISTS media_details(
    media_id INTEGER PRIMARY KEY,
    media_name TEXT NOT NULL,
    description TEXT NOT NULL,
    media_type TEXT NOT NULL,
    image_file_name TEXT NOT NULL,
    genre TEXT NOT NULL,
    length_minutes INTEGER CHECK (length_minutes > 0),
    num_seasons_show INTEGER CHECK (num_seasons_show > 0),
    num_episodes_per_season_show INTEGER CHECK (num_episodes_per_season_show > 0)
    )
""")

# Table to store watchlist per user
connection.execute("""
    CREATE TABLE IF NOT EXISTS user_watchlist(
    watchlist_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_details(id),
    FOREIGN KEY (media_id) REFERENCES media_details(media_id),
    UNIQUE(user_id,media_id)
    )
""")

# Table to store subscription details (primarily for Admins to be able to change prices of plans)
connection.execute("""
    CREATE TABLE IF NOT EXISTS subscription_details(
    subscription_id INTEGER PRIMARY KEY,
    subscription_type INTEGER NOT NULL UNIQUE CHECK (subscription_type IN (1,2)),
    subscription_price FLOAT NOT NULL
    )
""")

# add default prices if subscription_details is empty(won't be overwritten by any other changes admin makes)
connection.execute("INSERT OR IGNORE INTO subscription_details (subscription_type, subscription_price) VALUES (1, 7.99)")
connection.execute("INSERT OR IGNORE INTO subscription_details (subscription_type, subscription_price) VALUES (2, 12.99)")

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
        return render_template("registration.html", message="Successfully registered!",
            redirect_after_register=True)
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
        session["subscription_type"] = user[5]
        #redirecting to dashboard after successful logiin
        return render_template("login.html", message="Successfully Logged in!", 
            redirect_after_login=True)
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
        return render_template("login.html", message = "Log into account first")
    return render_template("account_management.html")

@app.route('/namechange', methods=['GET', 'POST'])
def change_name():
    """
    ability to change name by asking new name and confirming new name
    """
    if "email" not in session:
        return render_template("login.html", message = "Log into account first")
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
        
        return redirect(url_for("change_name", changed=1))
        #return render_template("namechange.html", message="Name changed successfully!")
    return render_template("namechange.html")

@app.route('/pwdchange', methods=['GET', 'POST'])
def change_password():
    """
    ability to change password by asking old pwd and asking for new pwd twice
    """
    if "email" not in session:
        return render_template("login.html", message = "Log into account first")
    
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
        return redirect(url_for("change_password", changed=1))
        #return render_template("pwdchange.html", message="Password changed successfully!")
    return render_template("pwdchange.html")

@app.route('/addmedia', methods=['GET', 'POST'])
def add_media():
    # Admins being able to add shows or movies
    if request.method == "POST":
        media_name = request.form["media_name"]
        description = request.form["description"]
        media_type = request.form["media_type"]
        image = request.files["image_file_name"]
        image_file_name = image.filename
        #multigenre
        genres = request.form.getlist("genre")
        genre=', '.join(genres)
        length_minutes = request.form["length_minutes"]
        

        # check empty values
        if not media_name or not image_file_name or not description or not genre or not length_minutes:
            return render_template("add_media.html", message="No fields can be empty, try again")
        
        # at least 1 genre
        if not genres:
            return render_template("add_media.html", message = "Please select at least one genre.")
        
        # check whether media is show or movie (with a show you can add seasons and episodes)
        if media_type == "Show":
            num_seasons_show = request.form["num_seasons_show"]
            num_episodes_per_season_show = request.form["num_episodes_per_season_show"]

            if not num_seasons_show or not num_episodes_per_season_show:
                return render_template("add_media.html", message="No fields can be empty, try again")

        elif media_type == "Movie":
            num_seasons_show = None
            num_episodes_per_season_show = None

        # save image onto static/images
        image.save("static/images/" + image_file_name)

        # inserting media details in db
        connection = sqlite3.connect("subscription.db")
        try:
            connection.execute("INSERT INTO media_details (media_name, description, media_type, image_file_name, genre,length_minutes,num_seasons_show,num_episodes_per_season_show) VALUES (?, ?, ?, ?, ?, ?,?,?)", 
                               (media_name, description, media_type, image_file_name, genre, length_minutes,num_seasons_show,num_episodes_per_season_show))
            
            connection.commit()
        # error handling for duplicate media when registered
        except sqlite3.IntegrityError:
            connection.close()
            return render_template("add_media.html", message="Media Already Exists!")
        connection.close()
        return render_template("add_media.html", message="Successfully Added!")
    return render_template("add_media.html")

@app.route('/search_media', methods=['GET', 'POST'])
def search_media():
    if session.get("account_type") == "User" and session.get("subscription_type") == 0:
        return redirect(url_for("subscription_plan"))

    # Users and admins being able to search media, filter, and users should be able to add to watchlist
    if request.method == "GET":
        genre = request.args.get("genre")
        media_type = request.args.get("media_type")
        search = request.args.get("search")

        # fetching media from db using filters (genre filtre first)
        connection = sqlite3.connect("subscription.db")
        if genre:
            all_media = connection.execute("""SELECT * FROM media_details WHERE ',' || REPLACE(genre, ', ', ',') || ',' LIKE ?""",(f"%,{genre},%",)).fetchall()
        # media type filter
        elif media_type:
            all_media = connection.execute("SELECT * FROM media_details WHERE media_type=?",(media_type,)).fetchall()
        # search filter
        elif search:
            all_media = connection.execute("SELECT * FROM media_details WHERE media_name LIKE ?",("%"+search+"%",)).fetchall()
        else:
            all_media = connection.execute("SELECT * FROM media_details").fetchall()

        #already added to watchlist
        watchlisted_ids =[]
        if session.get("account_type")=="User":
            user_id= session['id']
            watchlisted_ids = [
                row[0] for row in connection.execute(
                    "SELECT media_id FROM user_watchlist WHERE user_id=?", (user_id,)
                ).fetchall()
            ]
            
        connection.close()
        return render_template("search_media.html", all_media=all_media, watchlisted_ids=watchlisted_ids)
    return render_template("search_media.html")

@app.route('/media/<int:media_id>')
def media_details(media_id):
    connection = sqlite3.connect("subscription.db")
    
    media = connection.execute(
        "SELECT * FROM media_details WHERE media_id = ?", (media_id,)
    ).fetchone()
    
    is_watchlisted=False
    if "id" in session and session.get("account_type") == "User":
        result= connection.execute(
            "SELECT * FROM user_watchlist WHERE user_id=? AND media_id=?",
            (session["id"], media_id)
        ).fetchone()
        
        if result: is_watchlisted=True
    
    connection.close()
    
    if media is None: return "Media not found", 404
    
    return render_template("media_details.html", media=media, is_watchlisted=is_watchlisted)

@app.route('/watchlist', methods=['GET', 'POST'])
def add_watchlist():
    """
    When a user clicks on the 'add to watchlist' button in search media tab, their watchlist
    should store automatically in the my_watchlist list
    """
    # Note that only regular users should be able to add watchlist, not admiins
    if session.get("account_type") != "User":
        #return render_template("search_media.html", message = "Accessible by users only")
        return redirect(url_for('search_media'))
    if request.method == "POST":
        media_id = request.form["media_id"]
        #reads destination sent by form (watchlisted from search pg or details pg)
        next_page = request.form.get('next', url_for('search_media')) 

    # adding watchlisted media onto users watchlist
        connection = sqlite3.connect("subscription.db")
        try:
            connection.execute("INSERT INTO user_watchlist (user_id, media_id) VALUES (?,?)",(session["id"],media_id))
            connection.commit()
            message="Added to watchlist :)"
        except sqlite3.IntegrityError:
            message = "Already in your Watchlist"
        all_media=connection.execute("SELECT * FROM media_details").fetchall()
        connection.close()
        return redirect(next_page + ('&' if "?" in next_page else '?')+"added=1")
    return redirect(url_for('search_media'))
        #return render_template("search_media.html", all_media=all_media, message=message)
    #return render_template("search_media.html")

@app.route('/mywatchlist', methods=['GET','POST'])
def my_watchlist():
    # watchlist page for users to see their watchlist
    # redirect to subscription plans if user does not have a plan 
    if session.get("account_type")=="User" and session.get("subscription_type")==0:
        return redirect(url_for("subscription_plan"))
    if "email" not in session:
        return render_template("login.html", message = "Log into account first")
    if request.method == "GET":
        user_id = session["id"]

        connection = sqlite3.connect("subscription.db")
        all_media = connection.execute("SELECT media_details.* FROM user_watchlist JOIN media_details ON user_watchlist.media_id=media_details.media_id WHERE user_watchlist.user_id=?",
                                   (user_id,)).fetchall()
        connection.close()
        return render_template("mywatchlist.html", all_media=all_media)
    return render_template("mywatchlist.html")

@app.route('/remove-watchlist', methods=['GET','POST'])
def remove_watchlist():
    # removed show off of your watchlist page
    if request.method == "POST":
        media_id = request.form["media_id"]
        user_id = session["id"]

    # adding watchlisted media onto users watchlist
        connection = sqlite3.connect("subscription.db")
        
        connection.execute("DELETE FROM user_watchlist WHERE user_id=? and media_id=?",
                           (session["id"],media_id))
        connection.commit()
        #message="Removed from your watchlist"
        
        all_media = connection.execute("SELECT media_details.* FROM user_watchlist JOIN media_details ON user_watchlist.media_id=media_details.media_id WHERE user_watchlist.user_id=?",
                                           (user_id,)).fetchall()
        connection.close()
        return redirect(url_for("my_watchlist", removed=1))
    return render_template("mywatchlist.html")

@app.route('/subscription_plan_user', methods=['GET','POST'])
def subscription_plan():
    # Users can select student or individual plan
    if session.get("account_type") != "User":
        return render_template("login.html",message="Plans for users only")

    connection = sqlite3.connect("subscription.db")
    # pull price details
    sub_prices = dict(connection.execute("SELECT subscription_type, subscription_price FROM subscription_details").fetchall())
    connection.close()

    if request.method=="POST":
        subscription_type=int(request.form["subscription_type"])
        card_number=request.form["card_number"].replace(" ","")
        expiry = request.form["expiry"].replace("/","")
        cvv = request.form["cvv"]
        student_number = request.form["student_number"]

        # checking student number (9 digit)
        if subscription_type == 1 and (not student_number.isdigit() or len(student_number) != 9):
            return render_template("subscription_plans.html", message="Invalid Student Number!",sub_prices=sub_prices)

        # checking card details for plans (i.e if length, cvv, and date are valid numbner formats)
        if not card_number.isdigit() or len(card_number) != 16 or not cvv.isdigit() or len(cvv) != 3 or not expiry.isdigit() or len(expiry)!=4:
            return render_template("subscription_plans.html", message="Invalid Card Number!",sub_prices=sub_prices)

        connection = sqlite3.connect("subscription.db")
        connection.execute("UPDATE user_details SET subscription_type=? WHERE id=?",
                            (subscription_type,session["id"]))
        connection.commit()
        connection.close()
        session["subscription_type"]=subscription_type
        return render_template("subscription_plans.html", message="Successfully changed subscription",sub_prices=sub_prices)
    return render_template("subscription_plans.html",sub_prices=sub_prices)

@app.route('/cancel_subscription', methods=['GET','POST'])
# cancelling user subscription
def cancel_subscription():
    if session.get("account_type") != "User":
        return render_template("login.html",message="Plans for users only")
    connection = sqlite3.connect("subscription.db")
    sub_prices = dict(connection.execute("SELECT subscription_type, subscription_price FROM subscription_details").fetchall())
    connection.execute("UPDATE user_details SET subscription_type=0 WHERE id=?",
                            (session["id"],))
    connection.commit()
    connection.close()
    session["subscription_type"]=0
    return render_template("subscription_plans.html", message="Successfully cancelled subscription",sub_prices=sub_prices)


if __name__ == '__main__':
    app.run(debug=True)

