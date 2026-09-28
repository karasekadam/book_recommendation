"""Production entry point: serves the built React app at / and the Flask API at /api."""
from pathlib import Path

from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from app import app as api

DIST = Path(__file__).parent / "frontend" / "dist"

frontend = Flask(__name__, static_folder=DIST, static_url_path="")


@frontend.get("/")
def index():
    return frontend.send_static_file("index.html")


# Same /api prefix as the Vite dev proxy, so the frontend code works unchanged
application = DispatcherMiddleware(frontend, {"/api": api})
