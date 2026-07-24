"""Flask storefront — reads store_data.json fresh on every request so publish_node's
writes (from workflow.py) show up on the next page load without restarting the server."""

import json
import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)

STORE_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store_data.json")


def load_catalog() -> list:
    with open(STORE_DATA_PATH) as f:
        return json.load(f)


@app.route("/")
def index():
    catalog = load_catalog()
    return render_template("index.html", watches=catalog)


@app.route("/api/catalog")
def api_catalog():
    return jsonify(load_catalog())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
