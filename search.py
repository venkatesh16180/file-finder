import sqlite3

conn = sqlite3.connect("library.db")
cur = conn.cursor()

while True:
    query = input("\nSeacrch for (or type 'quit'): ")
    if query.lower() == "quit":
        break
    cur.execute(
        "SELECT name, drive_label, relative_path, category FROM files WHERE name LIKE ? LIMIT 50", (f"%{query}%",)
    )
    results = cur.fetchall()
    if not results:
        print("no match found.")
    for name, drive_label, relative_path, category in results:
        print(f"[{category}] {name}\n Drive: {drive_label}  ->  {relative_path}")

conn.close()