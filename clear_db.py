import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""DROP TABLE profiles;""")

conn.commit()
conn.close()

print("Baza danych została utworzona.")
