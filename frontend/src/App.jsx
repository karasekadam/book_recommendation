import { useCallback, useEffect, useState } from "react";

import { api } from "./api.js";
import BookSearch from "./components/BookSearch.jsx";
import Login from "./components/Login.jsx";
import RatedBooks from "./components/RatedBooks.jsx";
import Recommendations from "./components/Recommendations.jsx";

function readStoredUser() {
  try {
    const stored = localStorage.getItem("userId");
    return stored ? Number(stored) : null;
  } catch {
    return null;
  }
}

function storeUser(userId) {
  try {
    if (userId === null) localStorage.removeItem("userId");
    else localStorage.setItem("userId", String(userId));
  } catch {
    // Storage unavailable (e.g. private mode): the login just won't be remembered
  }
}

export default function App() {
  const [userId, setUserId] = useState(readStoredUser);
  const [ratings, setRatings] = useState([]);

  const changeUser = (id) => {
    storeUser(id);
    setUserId(id);
    setRatings([]);
  };

  const refreshRatings = useCallback(() => {
    if (userId !== null) api.getRatings(userId).then(setRatings).catch(() => setRatings([]));
  }, [userId]);

  useEffect(refreshRatings, [refreshRatings]);

  if (userId === null) {
    return <Login onLogin={changeUser} />;
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Book Recommender</h1>
        <div className="header-user">
          <span>User #{userId}</span>
          <button className="secondary" onClick={() => changeUser(null)}>
            Log out
          </button>
        </div>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>Rate a book</h2>
          <BookSearch userId={userId} onRated={refreshRatings} />
        </section>

        <section className="panel">
          <h2>Recommendations</h2>
          <Recommendations userId={userId} />
        </section>

        <section className="panel">
          <h2>Your rated books ({ratings.length})</h2>
          <RatedBooks ratings={ratings} />
        </section>
      </main>
    </div>
  );
}
