import threading
import time

from flask import Flask, abort, jsonify, request
from werkzeug.exceptions import HTTPException

from database import get_connection, load_ratings
from recommender_model import (
    RecommenderBestRatedBookMean,
    RecommenderBestRatedBookSum,
    RecommenderClusters,
    RecommenderCommonHistory,
    RecommenderMostReadBook,
)

app = Flask(__name__)

RECOMMENDER_CLASSES = {
    "most_read": RecommenderMostReadBook,
    "best_rated_sum": RecommenderBestRatedBookSum,
    "best_rated_mean": RecommenderBestRatedBookMean,
    "common_history": RecommenderCommonHistory,
    "clusters": RecommenderClusters,
}
# models to reload after users submits their ratings
RELOADABLE = ["common_history", "clusters"]


def build_recommenders(names: list[str]) -> dict:
    ratings = load_ratings()
    recommenders = {name: RECOMMENDER_CLASSES[name](ratings) for name in names}
    for recommender in recommenders.values():
        recommender.load()
    return recommenders


RECOMMENDERS = build_recommenders(list(RECOMMENDER_CLASSES))
reload_lock = threading.Lock()


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    # Return JSON instead of Flask's HTML error page so the frontend can show the message
    return jsonify({"error": error.description}), error.code


def query(sql: str, params: tuple = ()) -> list[dict]:
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


@app.get("/recommenders")
def list_recommenders():
    return jsonify(list(RECOMMENDERS))


@app.post("/recommenders/reload")
def reload_recommenders():
    """Recreate customized recommenders after new ratings"""
    global RECOMMENDERS
    if not reload_lock.acquire(blocking=False):
        abort(409, "Models are already being retrained")
    try:
        start = time.perf_counter()
        RECOMMENDERS = {**RECOMMENDERS, **build_recommenders(RELOADABLE)}
    finally:
        reload_lock.release()
    return jsonify({"models": RELOADABLE, "seconds": round(time.perf_counter() - start, 1)})


@app.get("/users/<int:user_id>/recommendations")
def get_recommendations(user_id: int):
    name = request.args.get("model", "most_read")
    if name not in RECOMMENDERS:
        abort(400, f"Unknown model '{name}', choose from {list(RECOMMENDERS)}")
    try:
        isbns = RECOMMENDERS[name].predict(user_id)
    except KeyError:
        abort(404, f"User {user_id} has no ratings")
    return jsonify({"user_id": user_id, "model": name, "isbns": isbns})


@app.get("/books/search")
def search_books():
    q = request.args.get("q", "").strip()
    if not q:
        abort(400, "Missing query parameter 'q'")
    limit = request.args.get("limit", 20, type=int)
    return jsonify(query(
        """SELECT isbn, title, author, year, image_url FROM books
           WHERE title LIKE ? OR author LIKE ? LIMIT ?""",
        (f"%{q}%", f"%{q}%", limit),
    ))


@app.get("/books/<isbn>")
def get_book(isbn: str):
    rows = query("SELECT isbn, title, author, image_url FROM books WHERE isbn = ?", (isbn,))
    if not rows:
        abort(404)
    return jsonify(rows[0])


@app.post("/users")
def create_user():
    with get_connection() as conn:
        user_id = conn.execute("INSERT INTO users (user_id) VALUES (NULL)").lastrowid
    return jsonify({"user_id": user_id}), 201


@app.get("/users/<int:user_id>")
def login_user(user_id: int):
    if not query("SELECT 1 FROM users WHERE user_id = ?", (user_id,)):
        abort(404, f"User {user_id} not found")
    return jsonify({"user_id": user_id})


@app.get("/users/<int:user_id>/ratings")
def get_user_ratings(user_id: int):
    return jsonify(query(
        """SELECT r.isbn, r.rating, b.title, b.author, b.image_url
           FROM ratings r LEFT JOIN books b ON b.isbn = r.isbn
           WHERE r.user_id = ? ORDER BY r.rowid DESC""",
        (user_id,),
    ))


@app.post("/ratings")
def add_rating():
    """Body: {"user_id": int, "isbn": str, "rating": 0-10}. Rating 0 means read but not scored."""
    data = request.get_json(silent=True) or {}
    isbn, rating, user_id = data.get("isbn"), data.get("rating"), data.get("user_id")
    if not isinstance(rating, int) or not 0 <= rating <= 10:
        abort(400, "'rating' must be an integer between 0 and 10")
    if not query("SELECT 1 FROM users WHERE user_id = ?", (user_id,)):
        abort(404, f"User {user_id} not found")
    if not query("SELECT 1 FROM books WHERE isbn = ?", (isbn,)):
        abort(404, f"Book {isbn} not found")

    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO ratings VALUES (?, ?, ?)", (user_id, isbn, rating))
    return jsonify({"user_id": user_id, "isbn": isbn, "rating": rating}), 201


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
