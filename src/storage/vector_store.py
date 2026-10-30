import json
from pathlib import Path
import sqlite3
from sentence_transformers import SentenceTransformer
import sqlite_vec
from text_splitter import TextSplitter


class BookmarkStore:

  def __init__(self, db_path: str = "./data/bookmarks.db"):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    self.db = sqlite3.connect(db_path, check_same_thread=False)
    self.db.execute("PRAGMA journal_mode=WAL;")
    self.db.execute("PRAGMA foreign_keys=ON;")

    # Load extension
    self.db.enable_load_extension(True)
    sqlite_vec.load(self.db)
    self.db.enable_load_extension(False)

    self._init_db()

    self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    self.splitter = TextSplitter(chunk_size=600, chunk_overlap=80)

  def _init_db(self):
    with self.db:
      self.db.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
      self.db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING vec0(
                    article_id INTEGER,
                    content TEXT,
                    embedding float[384] distance_metric=cosine
                );
            """)

  def add_article(self, url: str, title: str, full_text: str) -> int:
    """Inserts metadata once into 'articles', and chunks into 'chunks'."""
    self.delete_by_url(url)  # Clean previous version if re-adding

    chunks = self.splitter.split_text(full_text)
    if not chunks:
      return 0

    # 1. Encode all chunks in one fast vector batch
    vectors = self.embedder.encode(chunks, convert_to_numpy=True).tolist()

    with self.db:
      # 2. Insert metadata ONCE
      cur = self.db.execute(
          "INSERT INTO articles (url, title) VALUES (?, ?)",
          (url, title or "Untitled"),
      )
      article_id = cur.lastrowid

      # 3. Insert chunks paired with article_id
      for chunk, vec in zip(chunks, vectors):
        self.db.execute(
            """
                    INSERT INTO chunks (article_id, content, embedding)
                    VALUES (?, ?, ?)
                """,
            (article_id, chunk, json.dumps(vec)),
        )

    return len(chunks)

  def search(self, query: str, top_k: int = 4) -> list[dict]:
    """Finds nearest chunks and joins the article metadata."""
    query_vec = json.dumps(self.embedder.encode(query).tolist())

    sql = """
            SELECT 
                a.url,
                a.title,
                c.content,
                c.distance
            FROM chunks c
            JOIN articles a ON c.article_id = a.id
            WHERE c.embedding MATCH ? and k = ?
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

  def delete_by_url(self, url: str) -> int:
    """Deletes the article and all its associated vector chunks."""
    with self.db:
      cur = self.db.execute("SELECT id FROM articles WHERE url = ?", (url,))
      row = cur.fetchone()
      if not row:
        return 0

      article_id = row[0]
      # Clean chunks first, then article
      self.db.execute("DELETE FROM chunks WHERE article_id = ?", (article_id,))
      self.db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
      return 1

  def get_all_embeddings(self) -> list[list[float]]:
    """Fetches all chunk vectors for computing the user interest centroid."""
    cursor = self.db.execute("SELECT embedding FROM chunks")
    return [json.loads(row[0]) for row in cursor.fetchall()]

  def get_stats(self) -> dict:
    with self.db:
      articles = self.db.execute("SELECT count(*) FROM articles").fetchone()[0]
      chunks = self.db.execute("SELECT count(*) FROM chunks").fetchone()[0]
    return {"unique_articles": articles, "total_chunks": chunks}

if __name__ == "__main__":
  store = BookmarkStore("./data/test_normalized.db")

  url_a = "https://en.wikipedia.org/wiki/Convolutional_neural_network"
  title_a = "Convolutional Neural Network"
  text_a = (
      "A convolutional neural network consists of an input layer, hidden"
      " layers and an output layer. In any feed-forward neural network, any"
      " middle layers are called hidden because their inputs and outputs are"
      " masked by the activation function and final convolution. In a"
      " convolutional neural network, the hidden layers include layers that"
      " perform convolutions. Typically, this includes a layer that performs a"
      " dot product of the convolution kernel with the layer's input matrix."
      " Max pooling layers progressively reduce the spatial size of the"
      " representation to reduce the amount of parameters and computation in the"
      " network."
  )

  url_b = "https://en.wikipedia.org/wiki/B-tree"
  title_b = "B-tree Data Structure"
  text_b = (
      "In computer science, a B-tree is a self-balancing tree data structure"
      " that maintains sorted data and allows searches, sequential access,"
      " insertions, and deletions in logarithmic time. The B-tree generalizes"
      " the binary search tree, allowing for nodes with more than two children."
      " Unlike other self-balancing binary search trees, the B-tree is"
      " well-suited for storage systems that read and write relatively large"
      " blocks of data, such as databases and file systems."
  )

  print("\n[*] Indexing articles into SQLite...")
  store.add_article(url_a, title_a, text_a)
  store.add_article(url_b, title_b, text_b)

  print("Stats:", store.get_stats())
  while True:
    query=input("Enter query: ")
    hits = store.search(query)
    for h in hits:
      print(f"[{h['title']}] ({h['similarity']}): {h['content']}")