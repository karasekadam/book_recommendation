import { useEffect, useState } from "react";

import { api } from "../api.js";
import BookCard from "./BookCard.jsx";

export default function Recommendations({ userId }) {
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("");
  const [books, setBooks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api
      .getRecommenders()
      .then((names) => {
        setModels(names);
        setModel(names[0] ?? "");
      })
      .catch((e) => setError(e.message));
  }, []);

  const recommend = async () => {
    setLoading(true);
    setError("");
    setBooks([]);
    try {
      const { isbns } = await api.getRecommendations(userId, model);
      // Some recommended ISBNs are missing from Books.csv, so show those by ISBN only
      const details = await Promise.allSettled(isbns.map(api.getBook));
      setBooks(details.map((d, i) => (d.status === "fulfilled" ? d.value : { isbn: isbns[i] })));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const retrain = async () => {
    setRetraining(true);
    setError("");
    setStatus("Retraining models with the latest ratings…");
    try {
      const { seconds } = await api.reloadRecommenders();
      setStatus(`Models retrained in ${seconds} s`);
      setBooks([]);
    } catch (e) {
      setStatus("");
      setError(e.message);
    } finally {
      setRetraining(false);
    }
  };

  return (
    <>
      <div className="row">
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {models.map((m) => (
            <option key={m} value={m}>
              {m.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <button onClick={recommend} disabled={!model || loading || retraining}>
          {loading ? "Loading…" : "Recommend"}
        </button>
        <button className="secondary" onClick={retrain} disabled={retraining}>
          {retraining ? "Retraining…" : "Retrain models"}
        </button>
      </div>
      {status && <p className="muted">{status}</p>}
      {error && <p className="error">{error}</p>}
      <div className="book-list">
        {books.map((book) => (
          <BookCard key={book.isbn} book={book} />
        ))}
      </div>
    </>
  );
}
