"""
app.py — Phase 7: Streamlit web interface for the media library finder.

Same hybrid retrieval and Ollama logic as ask.py (semantic search + threshold
filtering + LLM title extraction + keyword fallback + SPECIAL_QUERIES), ported
to a request/response model instead of a REPL loop. See ask.py's docstring and
BUILD-JOURNAL.md Phase 6 for why retrieval works the way it does.

Model, DB connection, and embedding arrays are cached with @st.cache_resource /
@st.cache_data so they load once per session, not once per question — Streamlit
reruns this whole script on every interaction. The full retrieval-and-generation
block runs inside a single spinner, since it can involve two sequential Ollama
calls (title extraction, then the recommendation itself).

A ModuleNotFoundError for torchvision may print in the terminal on startup —
that's Streamlit's file watcher probing an unused transformers submodule, not
a real dependency gap. See BUILD-JOURNAL.md, Phase 7.
"""
import streamlit as st
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import ollama

@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def get_db_connection():
    return sqlite3.connect("library.db", check_same_thread=False)

@st.cache_data
def load_embeddings():
    return np.load("embeddings.npy"), np.load("embedding_ids.npy")

model = load_model()
embeddings, ids = load_embeddings()
conn = get_db_connection()
cur = conn.cursor()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def extract_title(question):
    prompt = f'From this request, pull out only the specific title, show, or item name the user is naming, if any. Respond with just that name, nothing else. If they aren\'t naming a specific title, respond with exactly: NONE\n\nRequest: "{question}"'
    response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
    title = response["message"]["content"].strip()
    return None if title.upper() == "NONE" else title

def find_candidate(query, top_n=10, min_score=0.35):
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
                results.append(row[1:])

    return results

SPECIAL_QUERIES = {
    "surprise me": None,
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

st.title("My Library Finder")
question = st.text_input("What are you looking for?")

if question:
    normalized = question.lower().strip()

    with st.spinner("Thinking..."):
        if normalized in SPECIAL_QUERIES:
            category_filter = SPECIAL_QUERIES[normalized]
            if category_filter:
                cur.execute(
                    "SELECT name, drive_label, relative_path, category FROM files WHERE category = ? ORDER BY RANDOM() LIMIT 1",
                    (category_filter,),
                )
            else:
                cur.execute("SELECT name, drive_label, relative_path, category FROM files ORDER BY RANDOM() LIMIT 1")
            candidates = cur.fetchall()
        else:
            candidates = find_candidate(question)

        if not candidates:
            st.write("Nothing in your library scores as a good match for that. Try rephrasing?")
        else:
            candidate_text = "\n".join(f"- [{c[3]}] {c[0]} (Drive: {c[1]})" for c in candidates)
            prompt = f"""A user has this personal media library. Here are the closest matching items:
{candidate_text}

The user asked: "{question}"

Recommend the best match(es) from the list above, in plain, friendly English,
and mention which drive it's on. Only mention items from the list."""

            response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])

    if candidates:
        st.write(response["message"]["content"])
        st.subheader("Matching items")
        for name, drive_label, relative_path, category in candidates:
            st.write(f"**[{category}]** {name} — Drive: {drive_label}")
            st.caption(relative_path)