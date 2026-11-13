
import sqlite3

# Connect to database
connection = sqlite3.connect("subscription.db")
connection.execute("PRAGMA foreign_keys = ON")

# FULL RESET: delete existing tables
connection.execute("DROP TABLE IF EXISTS user_watchlist")
connection.execute("DROP TABLE IF EXISTS media_details")
connection.execute("DROP TABLE IF EXISTS user_details")

# 1. Registration table
connection.execute("""
    CREATE TABLE user_details (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        account_type TEXT NOT NULL,
        subscription_type INTEGER NOT NULL DEFAULT 0
    )
""")

# 2. Media table
connection.execute("""
    CREATE TABLE media_details (
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

# 3. Watchlist table
connection.execute("""
    CREATE TABLE user_watchlist (
        watchlist_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        media_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user_details(id),
        FOREIGN KEY (media_id) REFERENCES media_details(media_id),
        UNIQUE(user_id, media_id)
    )
""")

# Create test user account
connection.execute("""
    INSERT INTO user_details (name, email, password, account_type, subscription_type)
    VALUES (?, ?, ?, ?, ?)
""", (
    "John Doe",
    "johndoe@gmail.com",
    "password",
    "User",
    0
))

# Create test admin account
connection.execute("""
    INSERT INTO user_details (name, email, password, account_type, subscription_type)
    VALUES (?, ?, ?, ?, ?)
""", (
    "Joana Doe",
    "joanadoe@gmail.com",
    "password",
    "Admin",
    0
))

# Sample movie/show records
media_records = [
    (
        "Once Upon a Time",
        "A young woman discovers that fairy-tale characters are living in a mysterious town.",
        "Show", "once-upon-a-time.jpg", "drama, fantasy",
        43, 7, 22
    ),
    (
        "Up",
        "An elderly widower fulfils his lifelong dream of travelling to South America.",
        "Movie", "up.jpeg", "comedy",
        96, None, None
    ),
    (
        "The Uprising",
        "A farmer joins a growing rebellion against an oppressive king.",
        "Movie", "the-uprising.jpg", "history, drama, action",
        128, None, None
    ),
    (
        "Despicable Me",
        "A supervillain's plans change after adopting three orphaned girls.",
        "Movie", "despicable-me.jpg", "comedy",
        95, None, None
    ),
    (
        "Avengers: Endgame",
        "The remaining Avengers attempt to restore the universe.",
        "Movie", "endgame.png", "sci-fi, action",
        181, None, None
    ),
    (
        "21 Jump Street",
        "Two police officers go undercover as high school students.",
        "Movie", "21 jump street.png", "comedy, action",
        109, None, None
    ),
    (
        "The Notebook",
        "A young couple's relationship faces challenges.",
        "Movie", "notebook.png", "romance, drama",
        123, None, None
    ),
    (
        "The Vampire Diaries",
        "A teenage girl becomes involved with two vampire brothers.",
        "Show", "vampire diaries.jpg", "romance, horror",
        43, 8, None
    ),
    (
        "Stranger Things",
        "A group of friends encounter supernatural mysteries.",
        "Show", "stragner things.jfif", "sci-fi, horror",
        None, 5, None
    ),
    (
        "The Idea of You",
        "A single mother unexpectedly falls in love with a popular singer.",
        "Movie", "The idea of you.png", "romance, drama",
        116, None, None
    )
]

# Insert sample records
connection.executemany("""
    INSERT INTO media_details (
        media_name, description, media_type, image_file_name,
        genre, length_minutes, num_seasons_show,
        num_episodes_per_season_show
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", media_records)

# Save and close database
connection.commit()
connection.close()

print("Database reset and initialized successfully!")
