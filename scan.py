import os
import csv
from datetime import datetime

def safe(text):
    return text.encode("utf-8", errors = "replace").decode("utf-8")
drive_label = input("Label for this drive (e.g. HD1, HD2, NoTape): ").strip()
root_folder = input("Drive letter or path to scan (e.g. D:/): ").strip()
root_folder = root_folder.rstrip("/\\") + "/"

rows = []
skipped = 0
scan_time = datetime.now().isoformat(timespec="seconds")

for current_folder, subfolders, files in os.walk(root_folder):
    try:
        for name in subfolders + files:
            full_path = os.path.join(current_folder, name)
            try:
                is_dir = os.path.isdir(full_path)
                size = os.path.getsize(full_path) if not is_dir else None
            except OSError:
                skipped += 1
                continue
            relative_path = os.path.relpath(full_path, root_folder)
            rows.append({
                "drive_label": drive_label,
                "relative_path": safe(relative_path),
                "name": safe(name),
                "is_folder": is_dir,
                "size_bytes": size,
                "scanned_at": scan_time,
                })
    except PermissionError:
            skipped += 1
            continue
output_file = f"inventory_{drive_label}.csv"
fields = ["drive_label", "relative_path", "name", "is_folder", "size_bytes", "scanned_at"]
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Done! Found {len(rows)} items on '{drive_label}' ({skipped} skipped). Saved to {output_file}")