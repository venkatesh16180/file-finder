import sqlite3
from sentence_transformers import SentenceTransformer
import numpy as np

GENERIC_NAMES = {
    "movies", "movie", "series", "show", "games", "game", "music", "comics", "comic", "books", "book", "audiobook",
    "audiobooks", "courses", "course", "download", "downloads", "others", "pictures", "photos", "photo", 
}

model = SentenceTransformer("all-MiniLM-L6-v2")

conn = sqlite3.connect("library.db")
cur = conn.cursor()
cur.execute("SELECT id, name, category FROM files WHERE is_folder = 1")
rows = [r for r in cur.fetchall() if r[1].strip().lower() not in GENERIC_NAMES]

texts = [f"{category}: {name}" for _, name, category in rows]
embeddings = model.encode(texts, show_progress_bar=True)

np.save("embeddings.npy", embeddings)
ids = [row[0] for row in rows]
np.save("embedding_ids.npy", np.array(ids))

print(f"Created embeddings for {len(rows)} folders")