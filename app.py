from flask import Flask, render_template

from dotenv import load_dotenv
import os




load_dotenv()

API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

app = Flask(__name__)


app.secret_key = SECRET_KEY



@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
