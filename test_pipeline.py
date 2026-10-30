# test_pipeline.py
from src.ingestion.scraper import scrape_url
from src.storage.vector_store import BookmarkStore


def run_pipeline_test():
  # 1. Initialize store
  store = BookmarkStore(persist_directory="./data/chroma_db")

  # 2. Scrape a real link
  test_url = "https://en.wikipedia.org/wiki/Convolutional_neural_network"
  print(f"\n--- STEP 1: SCRAPING ---")
  scraped_data = scrape_url(test_url, max_images=2)

  if not scraped_data["success"]:
    print("Scraping failed. Exiting.")
    return

  # 3. Index text into ChromaDB (we can pass dummy image captions for now)
  print(f"\n--- STEP 2: CHUNKING & INDEXING ---")
  mock_captions = [{
      "image_url": (
          scraped_data["images"][0] if scraped_data["images"] else "none"
      ),
      "caption": (
          "A diagram illustrating convolutional layers, pooling layers, and"
          " feature maps."
      ),
  }]

  count = store.add_article(
      url=scraped_data["url"],
      title=scraped_data["title"],
      full_text=scraped_data["text"],
      image_captions=mock_captions if scraped_data["images"] else None,
  )

  print(f"Total entries in DB now: {store.get_total_count()}")

  # 4. Semantic Search Test
  print(f"\n--- STEP 3: SEMANTIC SEARCH TEST ---")
  query = "What is pooling used for in CNNs?"
  print(f"Search Query: '{query}'\n")

  results = store.search(query=query, top_k=2)
  for i, hit in enumerate(results, 1):
    print(f"Result #{i} [Score: {hit['similarity_score']}]:")
    print(f"Source: {hit['metadata']['title']} ({hit['metadata']['type']})")
    print(f"Snippet: {hit['content'][:220]}...\n")


if __name__ == "__main__":
  run_pipeline_test()