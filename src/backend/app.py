from flask import Flask

app = Flask(__name__)

@app.route("/health")
def health():
    return "<p>Server is up!</p>"


if __name__ == "__main__":
    app.run(debug=True)