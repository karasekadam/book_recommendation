import BookCard from "./BookCard.jsx";

export default function RatedBooks({ ratings }) {
  if (ratings.length === 0) {
    return <p className="muted">You haven't rated any books yet.</p>;
  }

  return (
    <div className="book-list">
      {ratings.map((r) => (
        <BookCard key={r.isbn} book={r}>
          <span className="badge">{r.rating === 0 ? "Read" : `${r.rating} / 10`}</span>
        </BookCard>
      ))}
    </div>
  );
}
