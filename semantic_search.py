import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = np.load("embeddings.npy")
ids = np.load("embedding_ids.npy")

conn = sqlite3.connect("library.db")
cur = conn.cursor()

def run_random_query(sql):
    cur.execute(sql)
    row = cur.fetchone()
    if row:
        name, drive_label, relative_path, category = row
        print(f"[{category}] {name}\n Drive:{drive_label} -> {relative_path}")
    else:
        print("Nothing found for that one.")

SPECIAL_QUERIES = {
    "surprise me": "SELECT name, drive_label, relative_path, category FROM files WHERE is_folder = 1 ORDER BY RANDOM() LIMIT 1",
    "random movie": "SELECT name, drive_label, relative_path, category FROM files WHERE category = 'Movies' AND is_folder = 1 ORDER BY RANDOM() LIMIT 1",
}

def cosine_similarity(a, b):
    return np.dot(a,b) / (np.linalg.norm(a) * np.linalg.norm(b))

while True:
    query = input("\nDescribe what you want (or 'quit'): ")
    if query.lower() == "quit":
        break
    if query.lower() in SPECIAL_QUERIES:
        run_random_query(SPECIAL_QUERIES[query.lower()])
        continue
    query_vector = model.encode(query)
    scores = [cosine_similarity(query_vector, e) for e in embeddings]
    
    MIN_SCORE = 0.35
    
    top_indices = np.argsort(scores)[::-1][:10]
    top_indices = [i for i in top_indices if scores[i] >= MIN_SCORE]
    
    for i in top_indices:
        file_id = int(ids[i])
        cur.execute("SELECT name, drive_label, relative_path, category FROM files WHERE id = ?", (int(file_id),))
        name, drive_label, relative_path, category = cur.fetchone()
        print(f"[{category}] {name} (match: {scores[i]:.2f})\n Drive:{drive_label}  ->  {relative_path}")