import sqlite3
import os

CATEGORY_KEYWORDS = {
    "Anime" : ["anime", "[judas]", "[animerg]", "dual audio", "fansub", "[anime time]"], 
    "Cartoon" : ["cartoon"], 
    "Comics" : ["comics", "comic", "manga"], 
    "Games" : ["game", "games", "repack", "fitgirl", "dodi", "r.g. mechanics", "gog", "elamigos", "codex", "cpy", "skidrow"], 
    "Audiobooks" : ["audiobooks", "audiobook"], 
    "Books" : ["book", "books", "ebook"], 
    "Courses" : ["course", "courses", "udemy"], 
    "Music" : ["music"], 
    "Pictures" : ["picture", "pictures", "photo"], 
    "Download" : ["download"], 
    "Movies" : ["movie", "movies", "film", "bluray", "brrip", "web-dl", "webdl"], 
    "Series" : ["series", "show", "drama", "season"], 
}

EXTENSION_FALLBACK = {
    "Movies": [".mkv", ".mp4", ".avi", ".mov", ".wmv"],
    "Music": [".mp3", ".flac", ".wav", ".m4a", ".ogg"],
    "Pictures": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "Books": [".pdf", ".epub", ".mobi", ".azw3"],
    "Comics": [".cbz", ".cbrr"],
}

# Build an extension -> category lookup from the category -> extensions dict above.
# guess_extension_category() needs to look up BY extension, so this flips
# the structure - looking extensions up directly against EXTENSION_FALLBACK
# would fail silently everytime, since extensions are buried in the value lists, not the keys.
EXTENSION_TO_CATEGORY ={}

for category, extensions in EXTENSION_FALLBACK.items():
    for ext in extensions:
        EXTENSION_TO_CATEGORY[ext] = category
        
def guess_extension_category(name):
    _, ext = os.path.splitext(name.lower())
    return EXTENSION_TO_CATEGORY.get(ext)

def guess_category(relative_path):
    # Check the path on folder at a time, root to leaf, and stop at the 
    # FIRST match. This makes a parent folder's category win over anyting
    # in the filename itself - e.g. a Comics folder containing "Game of
    # Familia" correctly stays Comics, since "Games" never even gets checked.
    segments = relative_path.replace("\\","/").split("/")
    for segment in segments:
        segment_lower = segment.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in segment_lower for keyword in keywords):
                return category
    return "Others"

conn = sqlite3.connect("library.db")
cur = conn.cursor()
cur.execute("SELECT id, relative_path, name, is_folder FROM files")
rows = cur.fetchall()

for file_id, relative_path, name, is_folder in rows:
    category = guess_category(relative_path)
    if category == "Others" and not is_folder:
        # Folders never have this info to fall back on (used in guess_category already);
        # only try extension-based guessing for actual files with no folder-level signal.
        category = guess_extension_category(name) or "Others"
    cur.execute("UPDATE files SET category = ? WHERE id = ?", (category,file_id))

conn.commit()
conn.close()
print("Categorized all files!")


# ---- Handy queries for checking results in DB Browser (Execute SQL Tab) ----

# Overall breakdown: how many files landed in each category, biggest first.
# SELECT category, COUNT(*) FROM files GROUP BY category ORDER BY COUNT(*) DESC;

# Inside "Others" specifically: split between folders (0) and actual files(1).
# Folders can't use the extension fallback, so a high folder count there is
# expected and ot fixable by this script alone.
# SELECT is_folder, COUNT(*) FROM files WHERE category = 'Others' GROUP BY is_folder;

# Sanity check for the extension fallback: should return 0. Any number above 0
# means a real file with a known extension is STILL sitting in "Others" -
# meaning guess_extension_category isn't matching it and is worth a look.

# SELECT COUNT(*) FROM files WHERE category = 'Others' AND is_folder = 0 AND (name LIKE '%.mkv' OR name LIKE '%.mp4' OR name LIKE '%.jpg' 
#   OR name LIKE '%.png' OR name LIKE '%.mp3' OR name LIKE '%.pdf' 
#   OR name LIKE '%.cbz');