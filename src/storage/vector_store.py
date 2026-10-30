import json
from pathlib import Path
import sqlite3
from sentence_transformers import SentenceTransformer
import sqlite_vec
from src.storage.text_splitter import TextSplitter


class BookmarkStore:

  def __init__(self, db_path: str = "./data/bookmarks.db"):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    self.db = sqlite3.connect(db_path, check_same_thread=False)
    self.db.execute("PRAGMA journal_mode=WAL;")
    self.db.execute("PRAGMA foreign_keys=ON;")

    # Enable and load sqlite-vec extension
    self.db.enable_load_extension(True)
    sqlite_vec.load(self.db)
    self.db.enable_load_extension(False)

    self._init_db()

    self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    self.splitter = TextSplitter(chunk_size=600, chunk_overlap=80)

  def _init_db(self):
    with self.db:
      self.db.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
      self.db.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(list_id) REFERENCES lists(id) ON DELETE CASCADE,
                    UNIQUE(list_id, url)
                );
            """)
      self.db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING vec0(
                    article_id INTEGER,
                    content TEXT,
                    embedding float[384] distance_metric=cosine
                );
            """)

  # --- List Management ---

  def get_or_create_list(self, list_name: str) -> int:
    """Returns the ID of an existing list or creates a new one."""
    clean_name = list_name.strip()
    with self.db:
      cur = self.db.execute(
          "SELECT id FROM lists WHERE name = ?", (clean_name,)
      )
      row = cur.fetchone()
      if row:
        return row[0]

      cur = self.db.execute(
          "INSERT INTO lists (name) VALUES (?)", (clean_name,)
      )
      return cur.lastrowid

  def get_all_lists(self) -> list[dict]:
    """Returns all created lists with article counts."""
    sql = """
            SELECT l.id, l.name, COUNT(a.id) as article_count
            FROM lists l
            LEFT JOIN articles a ON l.id = a.list_id
            GROUP BY l.id
            ORDER BY l.name ASC;
        """
    cursor = self.db.execute(sql)
    return [
        {"id": row[0], "name": row[1], "article_count": row[2]}
        for row in cursor.fetchall()
    ]

  # --- Ingestion ---

  def add_article_to_list(
      self, list_id: int, url: str, title: str, full_text: str
  ) -> int:
    """Chunks, embeds, and stores an article attached to a specific list."""
    if not full_text or not full_text.strip():
      return 0

    chunks = self.splitter.split_text(full_text)
    if not chunks:
      return 0

    # 1. Vectorize all chunks at once
    vectors = self.embedder.encode(chunks, convert_to_numpy=True).tolist()

    with self.db:
      # 2. Check if this URL already exists in this list; if so, clear its old chunks
      cur = self.db.execute(
          "SELECT id FROM articles WHERE list_id = ? AND url = ?",
          (list_id, url),
      )
      existing = cur.fetchone()

      if existing:
        article_id = existing[0]
        self.db.execute(
            "DELETE FROM chunks WHERE article_id = ?", (article_id,)
        )
        self.db.execute(
            "UPDATE articles SET title = ? WHERE id = ?",
            (title or "Untitled", article_id),
        )
      else:
        cur = self.db.execute(
            "INSERT INTO articles (list_id, url, title) VALUES (?, ?, ?)",
            (list_id, url, title or "Untitled"),
        )
        article_id = cur.lastrowid

      # 3. Store new chunks
      for chunk, vec in zip(chunks, vectors):
        self.db.execute(
            """
                    INSERT INTO chunks (article_id, content, embedding)
                    VALUES (?, ?, ?)
                """,
            (article_id, chunk, json.dumps(vec)),
        )

    return len(chunks)
  def get_articles_by_list(self, list_id: int) -> list[dict]:
    """Fetches all saved URLs and titles belonging to a specific list."""
    sql = """
          SELECT id, url, title, created_at
          FROM articles
          WHERE list_id = ?
          ORDER BY created_at DESC;
        """
    cursor = self.db.execute(sql, (list_id,))
    return [
          {
              "id": row[0],
              "url": row[1],
              "title": row[2],
              "created_at": row[3],
          }
          for row in cursor.fetchall()
    ]

  # --- Retrieval ---

  def search(
      self, query: str, list_id: int | None = None, top_k: int = 4
  ) -> list[dict]:
    """Searches chunks across all lists, or scoped strictly to a list_id."""
    query_vec = json.dumps(self.embedder.encode(query).tolist())

    if list_id is not None:
      sql = """
                SELECT 
                    a.url,
                    a.title,
                    c.content,
                    c.distance
                FROM chunks c
                JOIN articles a ON c.article_id = a.id
                WHERE a.list_id = ? AND c.embedding MATCH ? AND k = ?
                ORDER BY c.distance;
            """
      cursor = self.db.execute(sql, (list_id, query_vec, top_k))
    else:
      sql = """
                SELECT 
                    a.url,
                    a.title,
                    c.content,
                    c.distance
                FROM chunks c
                JOIN articles a ON c.article_id = a.id
                WHERE c.embedding MATCH ? AND k = ?
                ORDER BY c.distance;
            """
      cursor = self.db.execute(sql, (query_vec, top_k))

    return [
        {
            "url": row[0],
            "title": row[1],
            "content": row[2],
            "similarity": round(1.0 - float(row[3]), 4),
        }
        for row in cursor.fetchall()
    ]