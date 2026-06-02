from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"


# =========================
# DATABASE CONNECTION
# =========================
def db():
    conn = sqlite3.connect("tournament.db")
    conn.row_factory = sqlite3.Row
    return conn

# =========================
# INIT DATABASE
# =========================
def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT,
        role TEXT DEFAULT 'player',
        rank_points INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_name TEXT,
        captain TEXT,
        game TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tournaments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_name TEXT,
        game_name TEXT,
        prize_pool TEXT,
        start_date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team1 TEXT,
        team2 TEXT,
        score1 INTEGER DEFAULT 0,
        score2 INTEGER DEFAULT 0,
        winner TEXT,
        bracket TEXT,
        match_date TEXT,
        status TEXT DEFAULT 'Upcoming'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS match_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team1 TEXT,
        team2 TEXT,
        score1 INTEGER,
        score2 INTEGER,
        winner TEXT,
        bracket TEXT,
        match_date TEXT,
        status TEXT,
        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ADMIN ACCOUNT
    admin = cur.execute(
        "SELECT * FROM users WHERE email=?",
        ("admin@mlbb.com",)
    ).fetchone()

    if admin is None:
        cur.execute("""
        INSERT INTO users(username,email,password,role)
        VALUES (?,?,?,?)
        """, ("Administrator", "admin@mlbb.com", "admin123", "admin"))

        print("ADMIN ACCOUNT CREATED")

    conn.commit()
    conn.close()

init_db()

# =========================
# HOME
# =========================
@app.route("/")
def home():
    conn = db()

    tournaments = conn.execute("SELECT * FROM tournaments").fetchall()
    matches = conn.execute("SELECT * FROM matches").fetchall()
    history = conn.execute("SELECT * FROM match_history ORDER BY id DESC").fetchall()

    conn.close()

    return render_template(
        "index.html",
        tournaments=tournaments,
        matches=matches,
        history=history
    )

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = db()

    teams = conn.execute("SELECT * FROM teams").fetchall()
    rankings = conn.execute("""
        SELECT * FROM users ORDER BY rank_points DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        teams=teams,
        rankings=rankings
    )

# =========================
# CREATE TOURNAMENT (FIXED)
# =========================
@app.route("/create_tournament", methods=["GET", "POST"])
def create_tournament():

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = db()

    if request.method == "POST":

        conn.execute("""
            INSERT INTO tournaments
            (tournament_name, game_name, prize_pool, start_date)
            VALUES(?,?,?,?)
        """, (
            request.form["tournament_name"],
            request.form["game_name"],
            request.form["prize_pool"],
            request.form["start_date"]
        ))

        conn.commit()

    tournaments = conn.execute(
        "SELECT * FROM tournaments ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "create_tournament.html",
        tournaments=tournaments
    )

# =========================
# EDIT TOURNAMENT
# =========================
@app.route("/edit_tournament/<int:id>", methods=["GET", "POST"])
def edit_tournament(id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = db()

    if request.method == "POST":

        conn.execute("""
            UPDATE tournaments
            SET tournament_name=?, game_name=?, prize_pool=?, start_date=?
            WHERE id=?
        """, (
            request.form["tournament_name"],
            request.form["game_name"],
            request.form["prize_pool"],
            request.form["start_date"],
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/create_tournament")

    tournament = conn.execute(
        "SELECT * FROM tournaments WHERE id=?",
        (id,)
    ).fetchone()

    conn.close()

    return render_template("edit_tournament.html", tournament=tournament)

# =========================
# DELETE TOURNAMENT
# =========================
@app.route("/delete_tournament/<int:id>")
def delete_tournament(id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = db()
    conn.execute("DELETE FROM tournaments WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/create_tournament")

# =========================
# CREATE MATCH
# =========================
@app.route("/create_match", methods=["GET", "POST"])
def create_match():

    if session.get("role") != "admin":
        return redirect("/dashboard")

    if request.method == "POST":

        conn = db()
        conn.execute("""
            INSERT INTO matches(team1, team2, bracket, match_date)
            VALUES(?,?,?,?)
        """, (
            request.form["team1"],
            request.form["team2"],
            request.form["bracket"],
            request.form["match_date"]
        ))

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("create_match.html")

# =========================
# CREATE TEAM
# =========================
@app.route("/create_team", methods=["GET", "POST"])
def create_team():

    if request.method == "POST":

        conn = db()
        conn.execute("""
            INSERT INTO teams(team_name, captain, game)
            VALUES(?,?,?)
        """, (
            request.form["team_name"],
            request.form["captain"],
            request.form["game"]
        ))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("create_team.html")

# =========================
# ADMIN
# =========================
@app.route("/admin")
def admin():

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = db()

    users = conn.execute("SELECT * FROM users").fetchall()
    tournaments = conn.execute("SELECT * FROM tournaments").fetchall()
    matches = conn.execute("SELECT * FROM matches").fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        tournaments=tournaments,
        matches=matches
    )

# =========================
# UPDATE MATCH
# =========================
@app.route("/update_match/<int:id>", methods=["GET", "POST"])
def update_match(id):

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = db()

    if request.method == "POST":

        conn.execute("""
            UPDATE matches
            SET score1=?, score2=?, winner=?, status=?
            WHERE id=?
        """, (
            request.form["score1"],
            request.form["score2"],
            request.form["winner"],
            request.form["status"],
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/admin")

    match = conn.execute(
        "SELECT * FROM matches WHERE id=?",
        (id,)
    ).fetchone()

    conn.close()

    return render_template("update_match.html", match=match)

# =========================
# DELETE MATCH → HISTORY
# =========================
@app.route("/delete_match/<int:id>")
def delete_match(id):

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = db()
    cur = conn.cursor()

    match = cur.execute(
        "SELECT * FROM matches WHERE id=?",
        (id,)
    ).fetchone()

    if match:

        cur.execute("""
            INSERT INTO match_history
            (team1, team2, score1, score2, winner, bracket, match_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match["team1"],
            match["team2"],
            match["score1"],
            match["score2"],
            match["winner"],
            match["bracket"],
            match["match_date"],
            match["status"]
        ))

        cur.execute("DELETE FROM matches WHERE id=?", (id,))

        conn.commit()

    conn.close()

    return redirect("/admin")

# =========================
# MATCH HISTORY
# =========================
@app.route("/match_history")
def match_history():

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = db()
    history = conn.execute(
        "SELECT * FROM match_history ORDER BY deleted_at DESC"
    ).fetchall()

    conn.close()

    return render_template("match_history.html", history=history)

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        conn = db()
        user = conn.execute("""
            SELECT * FROM users
            WHERE email=? AND password=?
        """, (
            request.form["email"],
            request.form["password"]
        )).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")

            return redirect("/dashboard")

        return "Invalid Email or Password"

    return render_template("login.html")

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        conn = db()
        conn.execute("""
            INSERT INTO users(username,email,password)
            VALUES(?,?,?)
        """, (
            request.form["username"],
            request.form["email"],
            request.form["password"]
        ))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run()