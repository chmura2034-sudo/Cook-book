import sqlite3

conn = sqlite3.connect("recipes.db")
cursor = conn.cursor()

cursor.execute(""" INSERT INTO TAGS (name) VALUES
    ('wegańskie'),
    ('wegetariańskie'),          
    ('śniadanie'),
    ('obiad'),
    ('kolacja'),
    ('deser'),
    ('szybkie')""")

conn.commit()
conn.close()

print("Done")
