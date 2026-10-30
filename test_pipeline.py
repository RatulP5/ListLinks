# test_pipeline.py
from src.ingestion.scraper import scrape_url
from src.storage.vector_store import BookmarkStore


def run_pipeline():
  print("[*] Initializing Database & Embedder...")
  store = BookmarkStore(db_path="./data/bookmarks.db")

  # 1. Create two distinct user lists
  ml_list_id = store.get_or_create_list("Machine Learning")
  db_list_id = store.get_or_create_list("Databases")
  print(f"[+] Lists available: {store.get_all_lists()}")

  # 2. Scrape & add an article to "Machine Learning"
  url_cnn = "https://en.wikipedia.org/wiki/Convolutional_neural_network"
  print(f"\n[*] Scraping: {url_cnn}")
  data_cnn = scrape_url(url_cnn)

  if data_cnn["success"]:
    num_chunks = store.add_article_to_list(
        list_id=ml_list_id,
        url=data_cnn["url"],
        title=data_cnn["title"],
        full_text=data_cnn["text"],
    )
    print(f"[+] Indexed {num_chunks} chunks into 'Machine Learning'")

  # 3. Add manual text to "Databases" for fast testing
  store.add_article_to_list(
      list_id=db_list_id,
      url="https://example.com/b-trees",
      title="B-Tree Fundamentals",
      full_text=(
          "A B-tree is a self-balancing search tree used extensively in"
          " databases and file systems. It optimizes reads and writes of large"
          " blocks of memory."
      ),
  )
  print("[+] Indexed B-Tree notes into 'Databases'")

  # 4. Scoped Search Test: Query "pooling layers" ONLY within "Machine Learning"
  query = "What do pooling layers do?"
  print(
      f"\n[*] Searching for: '{query}' inside 'Machine Learning' (ID:"
      f" {ml_list_id})..."
  )
  results = store.search(query=query, list_id=ml_list_id, top_k=2)

  for i, hit in enumerate(results, 1):
    print(f"\nResult #{i} [Similarity: {hit['similarity']}]:")
    print(f"Title: {hit['title']}")
    print(f"Snippet: {hit['content'][:180]}...")


if __name__ == "__main__":
  run_pipeline()