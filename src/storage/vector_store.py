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

    self.db.enable_load_extension(True)
    sqlite_vec.load(self.db)
    self.db.enable_load_extension(False)

    self._init_db()
    self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    self.splitter = TextSplitter(chunk_size=600, chunk_overlap=100)

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
                    images TEXT DEFAULT '[]',
                    videos TEXT DEFAULT '[]',
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

  def get_or_create_list(self, list_name: str) -> int:
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

  def add_article_to_list(
      self,
      list_id: int,
      url: str,
      title: str,
      full_text: str,
      images: list[str] = None,
      videos: list[str] = None,
  ) -> int:
    if not full_text or not full_text.strip():
      return 0

    chunks = self.splitter.split_text(full_text)
    if not chunks:
      return 0

    vectors = self.embedder.encode(chunks, convert_to_numpy=True).tolist()
    images_json = json.dumps(images or [])
    videos_json = json.dumps(videos or [])

    with self.db:
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
            """
                    UPDATE articles 
                    SET title = ?, images = ?, videos = ? 
                    WHERE id = ?
                """,
            (title or "Untitled", images_json, videos_json, article_id),
        )
      else:
        cur = self.db.execute(
            """
                    INSERT INTO articles (list_id, url, title, images, videos) 
                    VALUES (?, ?, ?, ?, ?)
                """,
            (
                list_id,
                url,
                title or "Untitled",
                images_json,
                videos_json,
            ),
        )
        article_id = cur.lastrowid

      for chunk, vec in zip(chunks, vectors):
        self.db.execute(
            """
                    INSERT INTO chunks (article_id, content, embedding)
                    VALUES (?, ?, ?)
                """,
            (article_id, chunk, json.dumps(vec)),
        )

    return len(chunks)

  def search(
      self, query: str, list_id: int | None = None, top_k: int = 4
  ) -> list[dict]:
    query_vec = json.dumps(self.embedder.encode(query).tolist())

    if list_id is not None:
      sql = """
                SELECT 
                    a.url,
                    a.title,
                    a.images,
                    a.videos,
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
                    a.images,
                    a.videos,
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
            "images": json.loads(row[2]) if row[2] else [],
            "videos": json.loads(row[3]) if row[3] else [],
            "content": row[4],
            "similarity": round(1.0 - float(row[5]), 4),
        }
        for row in cursor.fetchall()
    ]

  def get_articles_by_list(self, list_id: int) -> list[dict]:
    sql = """
            SELECT id, url, title, images, videos, created_at
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
            "images": json.loads(row[3]) if row[3] else [],
            "videos": json.loads(row[4]) if row[4] else [],
            "created_at": row[5],
        }
        for row in cursor.fetchall()
    ]