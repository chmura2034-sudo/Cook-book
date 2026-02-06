import os 
import requests
import uuid 
import sqlite3 
from pathlib import Path 
from flask import Flask, request, jsonify, abort,  render_template, request
from flask import send_from_directory
from PIL import Image 
from flask import send_file
import hmac
from PIL import Image
import hashlib
import jwt
import json
from werkzeug.utils import secure_filename
import secrets
from functools import wraps
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()





SECRET_KEY_RECAPTCHA = os.getenv("SECRET_KEY_reCAPTCHA")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALG = "HS256"
DB_PATH = Path("recipes.db") 
UPLOAD_DIR = Path("uploads") 
FULL_DIR = UPLOAD_DIR / "full" 
THUMB_DIR = UPLOAD_DIR / "thumbs" 
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
UPLOAD_DIR.mkdir(exist_ok=True) 
FULL_DIR.mkdir(exist_ok=True) 
THUMB_DIR.mkdir(exist_ok=True)

app = Flask(__name__)


def get_db(): 
    conn = sqlite3.connect(DB_PATH, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row 
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;") 
    return conn

def hash_password(password, salt): 
    """PBKDF2-HMAC-SHA256""" 
    return hashlib.pbkdf2_hmac( "sha256", password.encode(), salt.encode(), 200000 ).hex()

def verify_password(password, salt, stored_hash):
    return hmac.compare_digest( hash_password(password, salt), stored_hash )

def create_jwt(user_id, username):
    payload = {
        "sub": str(user_id),
        "username": str(username),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    if isinstance(token, bytes):
        token = token.decode()
    return token

def decode_jwt(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Brak tokenu"}), 401

        token = auth.split(" ")[1]

        try:
            payload = decode_jwt(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token wygasł"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Niepoprawny token"}), 401

        request.user_id = int(payload["sub"])
        request.username = payload["username"]

        return f(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def create_thumbnail(src_path, dest_path, size=(400, 400)):
    img = Image.open(src_path)
    img.thumbnail(size)
    img.save(dest_path)

@app.get("/add_recipe")
def add_recipe_page():
    return render_template("add_recipe.html")


@app.get("/account") 
def account_page(): 
    return send_from_directory("templates", "account.html")

@app.get("/")
def welcome():
    return render_template("index.html", year=datetime.now().year)

@app.get("/recipes")
def recipes_page():
    return render_template("recipes.html")

@app.get("/recipe/<int:recipe_id>")
def recipe_page(recipe_id):
    return app.send_static_file("recipe.html")


@app.route('/uploads/full/<path:filename>')
def serve_full(filename):
    return send_from_directory(FULL_DIR, filename)

@app.route('/uploads/thumbs/<path:filename>')
def serve_thumbs(filename):
    return send_from_directory(THUMB_DIR, filename)

@app.post("/api/register")
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    recaptcha_response = request.form.get("g-recaptcha-response")

    if not recaptcha_response:
        return {"error": "Potwierdź, że nie jesteś robotem"}, 400

    verify = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": SECRET_KEY_RECAPTCHA,
            "response": recaptcha_response
        }
    ).json()

    if not verify.get("success"):
        return {"error": "Błąd reCAPTCHA"}, 400

    if not username or not password:
        return {"error": "Brak danych"}, 400

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    try:
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash, password_salt) VALUES (?, ?, ?)",
            (username, password_hash, salt)
        )
        db.commit()
        return {"status": "ok"}
    except sqlite3.IntegrityError:
        return {"error": "Użytkownik już istnieje"}, 409


@app.post("/api/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    db = get_db()
    row = db.execute(
        "SELECT id, password_hash, password_salt FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not row:
        return {"error": "Niepoprawne dane logowania"}, 401

    user_id, stored_hash, salt = row

    if not verify_password(password, salt, stored_hash):
        return {"error": "Niepoprawne dane logowania"}, 401

    token = create_jwt(user_id, username)

    return {
        "status": "ok",
        "token": token,
        "user": {
            "id": user_id,
            "username": username
        }
    }


@app.get("/api/me")
def me():
    auth = request.headers.get("Authorization")

    if not auth or not auth.startswith("Bearer "):
        return {"error": "Brak tokenu"}, 401

    token = auth.split(" ")[1]

    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return {"error": "Token wygasł"}, 401
    except jwt.InvalidTokenError:
        return {"error": "Niepoprawny token"}, 401

    user_id = payload["sub"]

    db = get_db()
    row = db.execute(
        "SELECT id, username, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not row:
        return {"error": "Użytkownik nie istnieje"}, 404

    uid, username, created_at = row

    return {
        "id": uid,
        "username": username,
        "created_at": created_at
    }

@app.post("/api/add_recipe")
def add_recipe():
    # ============================
    # 1. Autoryzacja JWT
    # ============================
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return jsonify({"error": "Brak tokenu"}), 401

    token = auth.split(" ")[1]

    try:
        payload = decode_jwt(token)
    except:
        return jsonify({"error": "Niepoprawny token"}), 401

    user_id = payload["sub"]

    # ============================
    # 2. Pobranie danych JSON
    # ============================
    raw = request.form.get("data")
    if not raw:
        return jsonify({"error": "Brak danych"}), 400

    data = json.loads(raw)

    title = data["title"]
    description = data["description"]
    ingredients = data["ingredients"]
    steps = data["steps"]
    tags = data["tags"]
    size = data["size"]

    # ============================
    # 3. Połączenie z bazą
    # ============================
    conn = get_db()
    cur = conn.cursor()

    # ============================
    # 4. Zapis przepisu
    # ============================
    cur.execute("""
        INSERT INTO recipes (user_id, title, description, is_size)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        title,
        description,
        1 if size["type"] != "none" else 0
    ))

    recipe_id = cur.lastrowid

    # ============================
    # 5. Zapis rozmiaru naczynia
    # ============================
    if size["type"] == "round":
        cur.execute("""
            INSERT INTO size (recipe_id, is_size_round, vessel_diameter)
            VALUES (?, 1, ?)
        """, (recipe_id, size["diameter"]))

    elif size["type"] == "rect":
        cur.execute("""
            INSERT INTO size (recipe_id, is_size_round, vessel_length, vessel_width)
            VALUES (?, 0, ?, ?)
        """, (recipe_id, size["length"], size["width"]))

    # ============================
    # 6. Składniki
    # ============================
    for i, ing in enumerate(ingredients):
        cur.execute("""
            INSERT INTO ingredients (recipe_id, name, amount, unit, order_index)
            VALUES (?, ?, ?, ?, ?)
        """, (
            recipe_id,
            ing["name"],
            ing["amount"],
            ing["unit"],
            i
        ))

    # ============================
    # 7. Kroki
    # ============================
    for i, step in enumerate(steps):
        cur.execute("""
            INSERT INTO steps (recipe_id, instruction, order_index)
            VALUES (?, ?, ?)
        """, (recipe_id, step, i))

    # ============================
    # 8. Tagi (many-to-many)
    # ============================
    for tag_name in tags:
        cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        row = cur.fetchone()

        if row:
            tag_id = row[0]
            cur.execute("""
                INSERT INTO recipe_tags (recipe_id, tag_id)
                VALUES (?, ?)
            """, (recipe_id, tag_id))

    # ============================
    # 9. Zdjęcia + miniaturki
    # ============================
    photos = request.files.getlist("photos")
    saved_files = []

    photos = request.files.getlist("photos")
    saved_files = []

    for photo in photos:
        if not photo.filename:
            continue

        if not allowed_file(photo.filename):
            return jsonify({"error": "Niedozwolony format pliku"}), 400

        filename = secure_filename(photo.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"

        # Path objects
        full_path = FULL_DIR / unique_name
        thumb_path = THUMB_DIR / unique_name

        # Save original
        photo.save(str(full_path))

        # Create thumbnail
        create_thumbnail(str(full_path), str(thumb_path))

        saved_files.append(unique_name)

        # Save relative paths to DB
        cur.execute("""
            INSERT INTO recipe_photos (recipe_id, file_path, thumb_path)
            VALUES (?, ?, ?)
        """, (
            recipe_id,
            f"uploads/full/{unique_name}",
            f"uploads/thumbs/{unique_name}"
        ))




    # ============================
    # 10. Zatwierdzenie zmian
    # ============================
    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "recipe_id": recipe_id,
        "saved_photos": saved_files
    }), 200

@app.get("/api/tags")
def get_tags():
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("SELECT name FROM tags").fetchall()
    conn.close()

    tags = [r[0] for r in rows]

    return jsonify({"tags": tags})

@app.get("/api/recipes")
def get_recipes():
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT r.id, r.title, r.description, r.rating,
               (SELECT thumb_path FROM recipe_photos WHERE recipe_id = r.id LIMIT 1) AS thumb
        FROM recipes r
        ORDER BY r.created_at DESC
    """).fetchall()

    recipes = []
    for r in rows:
        # pobranie tagów
        tags = cur.execute("""
            SELECT t.name FROM tags t
            JOIN recipe_tags rt ON rt.tag_id = t.id
            WHERE rt.recipe_id = ?
        """, (r["id"],)).fetchall()

        recipes.append({
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "rating": r["rating"],
            "thumb": r["thumb"],
            "tags": [t[0] for t in tags]
        })

    conn.close()
    return jsonify({"recipes": recipes})

@app.get("/api/recipe/<int:recipe_id>")
def get_recipe(recipe_id):
    conn = get_db()
    cur = conn.cursor()

    r = cur.execute("""
        SELECT r.id, r.title, r.description, r.rating,
               r.created_at, r.user_id,
               u.username
        FROM recipes r
        JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
    """, (recipe_id,)).fetchone()

    if not r:
        return jsonify({"error": "Przepis nie istnieje"}), 404

    # składniki
    ingredients = cur.execute("""
        SELECT name, amount, unit, order_index
        FROM ingredients
        WHERE recipe_id = ?
        ORDER BY order_index
    """, (recipe_id,)).fetchall()

    # kroki
    steps = cur.execute("""
        SELECT instruction, order_index
        FROM steps
        WHERE recipe_id = ?
        ORDER BY order_index
    """, (recipe_id,)).fetchall()

    # tagi
    tags = cur.execute("""
        SELECT t.name
        FROM tags t
        JOIN recipe_tags rt ON rt.tag_id = t.id
        WHERE rt.recipe_id = ?
    """, (recipe_id,)).fetchall()

    # zdjęcia
    photos = cur.execute("""
        SELECT file_path, thumb_path
        FROM recipe_photos
        WHERE recipe_id = ?
    """, (recipe_id,)).fetchall()

    # rozmiar naczynia
    size_row = cur.execute("""
        SELECT is_size_round, vessel_diameter, vessel_length, vessel_width
        FROM size
        WHERE recipe_id = ?
    """, (recipe_id,)).fetchone()

    conn.close()

    # NORMALIZACJA SIZE
    if size_row:
        if size_row["is_size_round"] == 1:
            size = {
                "type": "round",
                "diameter": size_row["vessel_diameter"]
            }
        else:
            size = {
                "type": "rect",
                "length": size_row["vessel_length"],
                "width": size_row["vessel_width"]
            }
    else:
        size = {"type": "none"}

    return jsonify({
        "id": r["id"],
        "title": r["title"],
        "description": r["description"],
        "rating": r["rating"] or 0,
        "author": r["username"],
        "created_at": r["created_at"],
        "ingredients": [dict(row) for row in ingredients],
        "steps": [dict(row) for row in steps],
        "tags": [t[0] for t in tags],
        "photos": [dict(row) for row in photos],
        "size": size
    })





if __name__ == "__main__":
    app.run(debug=True, port=5000)
