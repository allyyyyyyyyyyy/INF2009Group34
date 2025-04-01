from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"accelerometer": {}, "webcam": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/", methods=["GET", "POST"])
def index():
    config = load_config()

    if request.method == "POST":
        updated_config = {"accelerometer": {}, "webcam": {}}

        for key in request.form:
            value = request.form.get(key)
            try:
                converted = float(value) if "." in value else int(value)
            except ValueError:
                continue  # Skip invalid input

            if key.startswith("accelerometer-"):
                actual_key = key.replace("accelerometer-", "")
                updated_config["accelerometer"][actual_key] = converted
            elif key.startswith("webcam-"):
                actual_key = key.replace("webcam-", "")
                updated_config["webcam"][actual_key] = converted

        save_config(updated_config)
        return redirect(url_for("index"))

    return render_template("index.html", config=config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
