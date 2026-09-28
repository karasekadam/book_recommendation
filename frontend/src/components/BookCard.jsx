import { useState } from "react";

// Many Book-Crossing image URLs are dead, so fall back to a plain placeholder
export default function BookCard({ book, children }) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <div className="book">
      {book.image_url && !imageFailed ? (
        <img src={book.image_url} alt="" onError={() => setImageFailed(true)} />
      ) : (
        <div className="cover-placeholder">📖</div>
      )}
      <div className="book-info">
        <div className="book-title">{book.title ?? `Unknown book (${book.isbn})`}</div>
        {book.author && <div className="book-author">{book.author}</div>}
        {children}
      </div>
    </div>
  );
}
