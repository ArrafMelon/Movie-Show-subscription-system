import sqlite3
from flask import Flask
from flask import render_template
from flask import request
from flask import session
from flask import redirect, url_for, flash
from datetime import datetime

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

# table to store complaints made by users (status 1 is unresolved, status 2 is resolved)
connection.execute("""
    CREATE TABLE IF NOT EXISTS contact_support(
    complaint_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    user_email TEXT NOT NULL,
    user_complaint TEXT NOT NULL,
    status INTEGER DEFAULT 1 CHECK (status IN (1,2)),
    FOREIGN KEY (user_id) REFERENCES user_details(id),
    FOREIGN KEY (user_email) REFERENCES user_details(email)
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
        
        flash("Successfully registered", 'success')
        return redirect(url_for("login"))
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
        flash("Successfully logged in", 'success')
        return redirect(url_for("page"))
    return render_template("login.html")

@app.route('/logout', methods=['GET', 'POST'])
# Logging out for existing user
def logout():
    # clearing session if session is not empty
    if session:
        session.clear()
        flash("Successfully logged out", 'success')
    else:
        flash("You are not currently logged in", 'success')
        
    return redirect(url_for("page"))

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
        
        flash("Name changed successfully!", 'success')
        return redirect(url_for("change_name"))
    
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
        
        flash("Password changed successfully!", 'success')
        return redirect(url_for("change_password"))
        
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
        
        flash("Successfully added media", 'success')
        return redirect(url_for("add_media"))
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
            flash("Added to watchlist", 'success')
        except sqlite3.IntegrityError:
            flash("Already in your Watchlist", 'success')
        all_media=connection.execute("SELECT * FROM media_details").fetchall()
        connection.close()
        #return redirect(next_page + ('&' if "?" in next_page else '?')+"added=1")
        
        return redirect(next_page)
    
    return redirect(url_for('search_media'))
       
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
        
        flash("Removed from your watchlist", 'success')
        return redirect(url_for("my_watchlist"))
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
        
        if subscription_type not in (1, 2):
            return render_template("subscription_plans.html", message="Invalid Subscription Plan", sub_prices=sub_prices)
        
        #check if user already has the selected plan
        curr_subs = session.get("subscription_type", 0)
        if subscription_type == curr_subs:
            return render_template("subscription_plans.html", 
                message="You are already subscribed to the plan", sub_prices=sub_prices)
        
        card_number=request.form["card_number"].replace("-","")
        expiry = request.form["expiry"]
        cvv = request.form["cvv"]
        student_number = request.form["student_number"]

        # checking student number (9 digit)
        if subscription_type == 1:
            if not student_number.isdigit() or len(student_number) != 9:
                return render_template("subscription_plans.html", message="Invalid Student Number",sub_prices=sub_prices)

        # checking card details for plans (i.e if length, cvv, and date are valid numbner formats)
        if not card_number.isdigit() or len(card_number) != 16 or not cvv.isdigit() or len(cvv) != 3:
            return render_template("subscription_plans.html", message="Invalid Card Details",sub_prices=sub_prices)

        # check expiry date (MM/YY)
        try:
            month, year = expiry.split("/")
            month=int(month)
            year=2000+int(year)
            if month <1 or month >12:
                raise ValueError
            curr_date = datetime.now()
            
            if (year, month) <(curr_date.year, curr_date.month):
                raise ValueError
            
        except ValueError:
            return render_template("subscription_plans.html", message="Invalid or Expired Card Date", sub_prices=sub_prices)

        # update user subs
        connection = sqlite3.connect("subscription.db")
        connection.execute("UPDATE user_details SET subscription_type=? WHERE id=?",
                            (subscription_type,session["id"]))
        connection.commit()
        connection.close()
        session["subscription_type"]=subscription_type
        
        flash("Successfully Subscribed!", "success")
        return redirect(url_for("subscription_plan"))
    
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
    
    flash("Successfully cancelled subscription!", "success")
    return redirect(url_for('subscription_plan'))


@app.route('/user_support', methods=['GET','POST'])
def contact_support():
    if "email" not in session:
        return render_template("login.html", message="Log into account")
    # Allows user to submit a complaint to admins using db that stores complaints, user id, user email
    if request.method=="POST":
        user_complaint = request.form["user_complaint"]

        if not user_complaint:
            return render_template("contact_support.html", message="Complaint cannot be empty")
        connection = sqlite3.connect("subscription.db")
        connection.execute("INSERT INTO contact_support (user_id, user_email, user_complaint) VALUES (?, ?, ?)",
                           (session["id"], session["email"], user_complaint))
        connection.commit()
        connection.close()
        return render_template("contact_support.html", message="Complaint submitted")
    return render_template("contact_support.html")
        
@app.route('/dashboard')
def dashboard():
    # sends users and admins to their own dashboard
    if "email" not in session:
        return render_template("login.html", message = "Log into account first")
    if session["account_type"] == "Admin":
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/yourdashboard')
def user_dashboard():
    # Dashboard for regular users
    if "email" not in session:
        return render_template("login.html", message = "Log into account first")
    
    if session["account_type"] == "Admin":
        return redirect(url_for('admin_dashboard'))

    connection = sqlite3.connect("subscription.db")

    # media the user is subscribed to (newest first)
    my_media = connection.execute("SELECT media_details.* FROM user_watchlist JOIN media_details ON user_watchlist.media_id=media_details.media_id WHERE user_watchlist.user_id=? ORDER BY user_watchlist.watchlist_id DESC",
                                  (session["id"],)).fetchall()

    # media the user is not subscribed to yet
    other_media = connection.execute("SELECT * FROM media_details WHERE media_id NOT IN (SELECT media_id FROM user_watchlist WHERE user_id=?)",
                                     (session["id"],)).fetchall()
    connection.close()

    # counting movies, shows, watch time and genres
    movies = 0
    shows = 0
    total_minutes = 0
    genre_counts = {}

    for media in my_media:
        if media[3] == "Movie":
            movies += 1
            total_minutes += media[6] or 0
        elif media[3] =='Show':
            shows += 1
            # shows: length x seasons x episodes per season
            total_minutes += (media[6] or 0) *(media[7] or 0) * (media[8] or 0)

        for genre in (media[5] or "").split(", "):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    watch_time = str(total_minutes // 60) + "h " + str(total_minutes % 60) + "m"

    # top 5 genres, most subscribed first
    top_genres = sorted(genre_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    max_genre_count = 1
    if top_genres:
        max_genre_count = top_genres[0][1]

    # recommend media that has a genre the user already likes
    recommended = []
    for media in other_media:
        for genre in media[5].split(", "):
            if genre in genre_counts:
                recommended.append(media)
                break

    heading = "Recommended for You"
    # new users have no genres yet so just show some media
    if not recommended:
        recommended = other_media
        heading = "Discover Something New"

    return render_template("user_dashboard.html", total=len(my_media), movies=movies,
                           shows=shows, watch_time=watch_time, recent=my_media[:5],
                           top_genres=top_genres, max_genre_count=max_genre_count,
                           recommended=recommended[:6], heading=heading)

@app.route('/admindashboard')
def admin_dashboard():
    # Dashboard for admins
    if "email" not in session:
        return render_template("login.html", message = "Log into account first")
    if session["account_type"] != "Admin":
        return redirect(url_for('user_dashboard'))

    connection = sqlite3.connect("subscription.db")

    # all media with how many users subscribed to each one (most subscribed first)
    all_media = connection.execute("SELECT media_details.*, COUNT(user_watchlist.watchlist_id) FROM media_details LEFT JOIN user_watchlist ON media_details.media_id=user_watchlist.media_id GROUP BY media_details.media_id ORDER BY COUNT(user_watchlist.watchlist_id) DESC").fetchall()

    total_movies = connection.execute("SELECT COUNT(*) FROM media_details WHERE media_type='Movie'").fetchone()[0]
    total_shows = connection.execute("SELECT COUNT(*) FROM media_details WHERE media_type='Show'").fetchone()[0]
    total_users = connection.execute("SELECT COUNT(*) FROM user_details WHERE account_type='User'").fetchone()[0]
    total_subs = connection.execute("SELECT COUNT(*) FROM user_details WHERE account_type='User' AND subscription_type IN (1,2)").fetchone()[0]

    # last 5 media added and last 5 people who registered (no passwords)
    recent_media = connection.execute("SELECT * FROM media_details ORDER BY media_id DESC LIMIT 5").fetchall()
    new_members = connection.execute("SELECT name, email, account_type FROM user_details ORDER BY id DESC LIMIT 5").fetchall()
    plan_prices = connection.execute("SELECT subscription_type, subscription_price FROM subscription_details ORDER BY subscription_type").fetchall()
    all_users = connection.execute("SELECT id, name, email, subscription_type FROM user_details WHERE account_type='User' ORDER BY id").fetchall()
    connection.close()

    # average subscriptions per user
    avg_subs = 0
    if total_users > 0:
        avg_subs = round(total_subs / total_users, 1)

    # most subscribed media (used for the bars)
    top_subs = 1
    if all_media and all_media[0][9] > 0:
        top_subs = all_media[0][9]

    # media that nobody has subscribed to
    no_subs = []
    for media in all_media:
        if media[9] == 0:
            no_subs.append(media)
            
    #subscriber rate
    subs_rate = 0
    if total_users >0: subs_rate=round((total_subs / total_users) *100,1)

    # subscriptions per genre
    genre_subs = {}
    for media in all_media:
        for genre in media[5].split(", "):
            genre_subs[genre] = genre_subs.get(genre, 0) + media[9]

    top_genres = sorted(genre_subs.items(), key=lambda item: item[1], reverse=True)[:6]
    max_genre_subs = 1
    if top_genres and top_genres[0][1] > 0:
        max_genre_subs = top_genres[0][1]

    return render_template("admin_dashboard.html", total_media=len(all_media),
                           total_movies=total_movies, total_shows=total_shows,
                           total_users=total_users, total_subs=total_subs, subs_rate=subs_rate,
                           top_media=all_media[:5], top_subs=top_subs,
                           top_genres=top_genres, max_genre_subs=max_genre_subs,
                           recent_media=recent_media, no_subs=no_subs[:5],
                           new_members=new_members, plan_prices=plan_prices, all_users=all_users)

@app.route('/update_subscription_price', methods=['POST'])
def update_subscription_price():
    # Admin access only
    if 'email' not in session: return render_template('login.html', message="Please log into account first")
    if session['account_type'] != 'Admin': return redirect(url_for('user_dashboard'))
    
    subscription_type = request.form['subscription_type']
    
    try: 
        new_price = float(request.form['subscription_price'])
    
        if new_price <= 0: raise ValueError
    except ValueError: return redirect(url_for('admin_dashboard'))
        
    if subscription_type not in ("1", "2"): return redirect(url_for('admin_dashboard'))
    connection = sqlite3.connect('subscription.db')
    
    connection.execute('UPDATE subscription_details SET subscription_price=? WHERE subscription_type=?', 
                       (new_price, subscription_type))
    connection.commit()
    connection.close()
    flash("Subscription price updated successfully!", "Success")
    return redirect(url_for('admin_dashboard'))


@app.route('/update_user_subscription', methods=['POST'])
def update_user_subscription():
    if 'email' not in session: return render_template('login.html', message="Please log into account first")
    if session['account_type'] != 'Admin': return redirect(url_for('user_dashboard'))
    
    try:
        user_id = int(request.form['user_id'])
        subscription_type = int(request.form['subscription_type'])
        if subscription_type not in (0,1,2): return redirect(url_for('admin_dashboard'))
        
    except (ValueError, KeyError): return redirect(url_for('admin_dashboard'))
    
    connection = sqlite3.connect('subscription.db')
    cursor = connection.execute("UPDATE user_details SET subscription_type=? WHERE id=? AND account_type=?",
                       (subscription_type, user_id, "User"))
    connection.commit()
    connection.close()

    if cursor.rowcount >0:
        if subscription_type==0: flash("Selected user's subscription has been cancelled successfully", "Success")
        else: flash("Selected user's subscription has been updated successfully", "Success")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

