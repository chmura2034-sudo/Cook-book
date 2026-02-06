import sqlite3

conn = sqlite3.connect("recipes.db")
cursor = conn.cursor()

cursor.execute(""" 
PRAGMA foreign_keys = ON;
               """)
cursor.execute("""

-- ============================
--  USERS
-- ============================
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    password_salt  TEXT NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);""")
cursor.execute("""

-- ============================
--  RECIPES
-- ============================
CREATE TABLE IF NOT EXISTS recipes (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    rating        REAL,
    is_size     BOOLEAN DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);""")
cursor.execute("""
-- ============================
--  Size Options
-- ============================
CREATE TABLE IF NOT EXISTS size (
    id               INTEGER PRIMARY KEY,
    recipe_id        INTEGER NOT NULL,
    is_size_round    BOOLEAN DEFAULT 0,   -- 1 = okrągła forma, 0 = prostokątna
    vessel_diameter  TEXT,                -- używane gdy is_size_round = 1
    vessel_length    TEXT,                -- używane gdy is_size_round = 0
    vessel_width     TEXT,                -- używane gdy is_size_round = 0
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        ON DELETE CASCADE
);""")
cursor.execute("""
-- ============================
--  INGREDIENTS
-- ============================
CREATE TABLE IF NOT EXISTS ingredients (
    id           INTEGER PRIMARY KEY,
    recipe_id    INTEGER NOT NULL,
    name         TEXT NOT NULL,
    amount       REAL,
    unit         TEXT,
    order_index  INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        ON DELETE CASCADE
);
""")
cursor.execute("""
-- ============================
--  STEPS
-- ============================
CREATE TABLE IF NOT EXISTS steps (
    id           INTEGER PRIMARY KEY,
    recipe_id    INTEGER NOT NULL,
    instruction  TEXT NOT NULL,
    order_index  INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        ON DELETE CASCADE
);
""")
cursor.execute("""
-- ============================
--  TAGS
-- ============================
CREATE TABLE IF NOT EXISTS tags (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);
""")
cursor.execute("""
-- ============================
--  RECIPE_TAGS (many-to-many)
-- ============================
CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id  INTEGER NOT NULL,
    tag_id     INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, tag_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
""")
cursor.execute("""
-- ============================
--  COMMENTS
-- ============================
CREATE TABLE IF NOT EXISTS comments (
    id          INTEGER PRIMARY KEY,
    recipe_id   INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    content     TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
""")
cursor.execute("""
-- ============================
--  RECIPE_PHOTOS (full + thumbnail)
-- ============================
CREATE TABLE IF NOT EXISTS recipe_photos (
    id          INTEGER PRIMARY KEY,
    recipe_id   INTEGER NOT NULL,
    file_path   TEXT NOT NULL,
    thumb_path  TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        ON DELETE CASCADE
);
 """)

conn.commit()
conn.close()

print("Baza danych została utworzona.")