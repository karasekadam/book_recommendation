import { useState } from "react";

import { api } from "../api.js";
import BookCard from "./BookCard.jsx";

const SCORES = Array.from({ length: 11 }, (_, i) => i);

function RateControl({ userId, isbn, onRated }) {
  const [score, setScore] = useState(0);
  const [status, setStatus] = useState("");

  const save = async () => {
    try {
      await api.addRating(userId, isbn, score);
      setStatus("Saved ✓");
      onRated();
    } catch (e) {
      setStatus(e.message);
    }
  };

  return (
    <div className="row rate">
      <select value={score} onChange={(e) => setScore(Number(e.target.value))}>
        {SCORES.map((s) => (
          <option key={s} value={s}>
            {s === 0 ? "Read (no score)" : s}
          </option>
        ))}
      </select>
      <button onClick={save}>Rate</button>
      {status && <span className="muted">{status}</span>}
    </div>
  );
}

export default function BookSearch({ userId, onRated }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const search = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;
    setError("");
    try {
      setResults(await api.searchBooks(query.trim()));
      setSearched(true);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <>
      <form onSubmit={search} className="row">
        <input
          placeholder="Search by title or author"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit">Search</button>
      </form>
      {error && <p className="error">{error}</p>}
      {searched && results.length === 0 && <p className="muted">No books found.</p>}
      <div className="book-list">
        {results.map((book) => (
          <BookCard key={book.isbn} book={book}>
            <RateControl userId={userId} isbn={book.isbn} onRated={onRated} />
          </BookCard>
        ))}
      </div>
    </>
  );
}
