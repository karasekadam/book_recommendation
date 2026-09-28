import os
import sqlite3
from pathlib import Path

import polars as pl

DATA_DIR = Path(__file__).parent / "archive"
DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent / "books.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    city    TEXT,
    state   TEXT,
    country TEXT,
    age     INTEGER
);
CREATE TABLE IF NOT EXISTS books (
    isbn      TEXT PRIMARY KEY,
    title     TEXT,
    author    TEXT,
    year      INTEGER,
    publisher TEXT,
    image_url TEXT
);
CREATE TABLE IF NOT EXISTS ratings (
    user_id INTEGER,
    isbn    TEXT,
    rating  INTEGER,
    PRIMARY KEY (user_id, isbn)
);
CREATE INDEX IF NOT EXISTS idx_ratings_isbn ON ratings (isbn);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_ratings() -> pl.DataFrame:
    # Column names match Ratings.csv so the recommenders work with either source
    with get_connection() as conn:
        return pl.read_database(
            'SELECT user_id AS "User-ID", isbn AS "ISBN", rating AS "Book-Rating" FROM ratings',
            conn,
        )


def parse_location(location: str | None) -> tuple[str | None, str | None, str | None]:
    # Processing dense location to atomic values
    parts = [p.strip() for p in (location or "").split(",")]
    parts = [None if p in ("", "n/a") else p for p in parts]
    if len(parts) < 3:
        parts = parts + [None] * (3 - len(parts))
        return parts[0], parts[1], parts[2]
    return parts[0], parts[-2], parts[-1]


def build_database() -> None:
    DB_PATH.unlink(missing_ok=True)
    users = pl.read_csv(DATA_DIR / "Users.csv")
    books = pl.read_csv(DATA_DIR / "Books.csv", infer_schema_length=0).with_columns(
        pl.col("Year-Of-Publication").cast(pl.Int64, strict=False)
    )
    ratings = pl.read_csv(DATA_DIR / "Ratings.csv")

    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
            (
                (user_id, *parse_location(location), int(age) if age is not None else None)
                for user_id, location, age in users.iter_rows()
            ),
        )
        conn.executemany(
            "INSERT INTO books VALUES (?, ?, ?, ?, ?, ?)",
            books.select(
                "ISBN", "Book-Title", "Book-Author", "Year-Of-Publication", "Publisher", "Image-URL-M"
            ).iter_rows(),
        )
        conn.executemany("INSERT INTO ratings VALUES (?, ?, ?)", ratings.iter_rows())
    conn.close()


if __name__ == "__main__":
    build_database()
    print(f"Database created at {DB_PATH}")
