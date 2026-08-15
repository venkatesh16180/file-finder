"""
ask.py — Phase 6: natural-language recommendation over the media library.

Retrieval is hybrid: semantic search (embedding cosine similarity, filtered
by MIN_SCORE) finds meaning-based matches, and an LLM-driven title extraction
step feeds a parallel keyword LIKE search for exact-name lookups semantic
search tends to miss. Results are merged (deduplicated) and handed to a
local Ollama model, constrained to only mention items from that merged list.

SPECIAL_QUERIES intercepts fixed phrases ("random movie", "surprise me", etc.)
before retrieval, bypassing the LLM/embedding pipeline entirely in favor of a
direct ORDER BY RANDOM() SQL query — genuinely random, unlike a semantic match
on the literal words, which would be deterministic.

Exact file paths are always printed directly from the database, never left
to the LLM to state in its response — see BUILD-JOURNAL.md, Phase 6.
"""

import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import ollama

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = np.load("embeddings.npy")
ids = np.load("embedding_ids.npy")
conn = sqlite3.connect("library.db")
cur = conn.cursor()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Pulls a literal title out of the question, if the user named one directly.
# Feeds the parallel keyword-search branch in find_candidate(); returns None
# for open-ended/descriptive queries with no specific name to match on.
def extract_title(question):
    prompt = f'From this request, pull out only the specific title, show, or item name the user is naming, if any. Respond with just that name, nothing else. If they aren\'t naming a specific title, respond with exactly: NONE\n\nRequest: "{question}"'
    response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
    title = response["message"]["content"].strip()
    return None if title.upper() == "NONE" else title

# Hybrid retrieval: ranked + threshold-filtered semantic matches, merged
# with an exact-title keyword pass. See BUILD-JOURNAL.md, Phase 6, for why
# semantic search alone wasn't enough for exact-title lookups.
def find_candidate(query, top_n=10, min_score = 0.35):
    query_vector = model.encode(query)
    scores = [cosine_similarity(query_vector, e) for e in embeddings]
    top_indices = np.argsort(scores)[::-1][:top_n]
    
    seen_ids = set()
    results = []
    for i in top_indices:
        if scores[i] < min_score:
            continue
        file_id = int(ids[i])
        seen_ids.add(file_id)
        cur.execute("SELECT name, drive_label, relative_path, category FROM files WHERE id = ?", (file_id,))
        results.append(cur.fetchone())
        
    title = extract_title(query)
    if title:
        cur.execute("SELECT id, name, drive_label, relative_path, category FROM files WHERE name LIKE ? LIMIT 5", (f"%{title}%",))
        for row in cur.fetchall():
            if row[0] not in seen_ids:
                results.append(row[1:]) # drop id, keep same shape as the semantic branch
                
    return results


# Fixed-phrase shortcuts that skip retrieval and the LLM entirely, going
# straight to ORDER BY RANDOM() — see BUILD-JOURNAL.md for why this exists
# separately rather than just letting "surprise me" hit semantic search.
SPECIAL_QUERIES = {
    "surprise me": None, # None = no category filter, pulls from anything indexed
    # SELECT DISTINCT category FROM files; Get the unique categories from DBBrowser.
    "random movie": "Movies",
    "random book": "Books",
    "random anime": "Anime",
    "random comic": "Comics",
    "random series": "Series",
    "random music": "Music",
    "random audiobook": "Audiobooks",
    "random cartoon": "Cartoon",
    "random course": "Courses",
    "random picture": "Pictures",
    "random game": "Games",
}

while True:
    question = input("\nAsk me anything (or 'quit'): ")
    if question.lower() == "quit":
        break
    
    normalized = question.lower().strip()
    if normalized in SPECIAL_QUERIES:
        category_filter = SPECIAL_QUERIES[normalized]
        if category_filter:
            cur.execute(
                "SELECT name, drive_label, relative_path, category FROM files WHERE category = ? ORDER BY RANDOM() LIMIT 1",
                (category_filter,),
            )
        else:
            cur.execute(
                "SELECT name, drive_label, relative_path, category FROM files ORDER BY RANDOM() LIMIT 1"
            )
        candidates = cur.fetchall()
    else:
        candidates = find_candidate(question)
        if not candidates:
            print("\nNothing in your library scores as a good match for that. Try rephrasing?")
            continue
        
    candidate_text = "\n".join(f"- [{c[3]}] {c[0]} (Drive: {c[1]}) - {c[2]}" for c in candidates)
    
    prompt = f"""A user has this personal media library. Here are the closest matching items:
    {candidate_text}
    
    The user asked: "{question}"

    Recommend the best match(es) from the list above, in plain, friendly English,
    and mention which drive it's on. Only mention items from the list."""

    response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
    print("\n" + response["message"]["content"])
    
    print("\nExact location(s):")
    for c in candidates:
        print(f" {c[1]}:\\{c[2]}")