from flask import Flask, render_template
from pymongo import MongoClient


app = Flask(__name__)

# MongoDB connection for future feature work.
mongo_client = MongoClient("mongodb://localhost:27017")
database = mongo_client["wellness_tracker"]


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
