from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Coming soon!"


# TODO: Add more routes
# TODO: Add database
# TODO: Add authentication
# TODO: Finish this project
