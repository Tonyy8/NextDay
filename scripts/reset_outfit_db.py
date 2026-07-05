import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent.parent / "db.sqlite3"
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS outfit_clothing")
cur.execute("DELETE FROM django_migrations WHERE app='outfit'")
conn.commit()
conn.close()
print("Reset outfit tables")
