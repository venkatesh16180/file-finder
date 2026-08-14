import sqlite3
import csv
import glob

conn = sqlite3.connect("library.db")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_label TEXT,
        relative_path TEXT,
        name TEXT,
        is_folder INTEGER,
        size_bytes INTEGER,
        category TEXT,
        scanned_at TEXT
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS drives (
        drive_label TEXT PRIMARY KEY,
        last_scanned TEXT,
        item_count INTEGER,
        total_size_bytes INTEGER
    )
""")

for csv_path in glob.glob("inventory_*.csv"):
    with open(csv_path, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    if not reader:
        continue
    
    drive_label = reader[0]["drive_label"]
    
    #wipe this drive's old rows first, so a rescan replaces rather than duplicates
    cur.execute("DELETE FROM files WHERE drive_label = ?", (drive_label,))
    
    total_size = 0
    for row in reader:
        size = int(row["size_bytes"]) if row["size_bytes"] else None
        total_size += size or 0
        cur.execute(
            """INSERT INTO files (drive_label, relative_path, name, is_folder, size_bytes, scanned_at) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (row["drive_label"], row["relative_path"], row["name"], row["is_folder"] == "True", size, row["scanned_at"])
        )
        
    cur.execute(
        "INSERT OR REPLACE INTO drives (drive_label, last_scanned, item_count, total_size_bytes) VALUES (?, ?, ?, ?)", (drive_label, reader[0]["scanned_at"], len(reader), total_size)
    )
    print(f"Loaded {len(reader)} items for drive '{drive_label}")

conn.commit()
conn.close()
print("Database updated.")