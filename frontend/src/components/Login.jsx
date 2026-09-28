import { useState } from "react";

import { api } from "../api.js";

export default function Login({ onLogin }) {
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (action) => {
    setBusy(true);
    setError("");
    try {
      const { user_id } = await action();
      onLogin(user_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const submit = (event) => {
    event.preventDefault();
    const id = Number(input);
    if (!Number.isInteger(id) || id <= 0) {
      setError("Enter a valid user ID");
      return;
    }
    run(() => api.login(id));
  };

  return (
    <div className="login">
      <div className="panel login-card">
        <h1>Book Recommender</h1>
        <form onSubmit={submit} className="row">
          <input
            type="number"
            placeholder="Your user ID"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" disabled={busy}>
            Log in
          </button>
        </form>
        <div className="divider">or</div>
        <button className="secondary wide" disabled={busy} onClick={() => run(api.createUser)}>
          Create a new user
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
