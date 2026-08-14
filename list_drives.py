import sqlite3

conn = sqlite3.connect("library.db")
cur=conn.cursor()
cur.execute("SELECT drive_label,last_scanned, item_count, total_size_bytes FROM drives ORDER BY drive_label")

for label, last_scanned, count, size in cur.fetchall():
    gb = (size or 0) / (1024 ** 3)
    print(f"{label:15} last scanned {last_scanned}  -  {count} items, {gb:.1f}GB")