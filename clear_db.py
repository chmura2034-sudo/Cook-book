import sqlite3

conn = sqlite3.connect("recipes.db")
cursor = conn.cursor()

cursor.execute(""" DROP  TABLE IF EXISTS recipes; """)

conn.commit()
conn.close()

print("Done")
