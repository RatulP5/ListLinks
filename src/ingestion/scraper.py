from src.ingestion.html_fetcher import fetch_html
from src.ingestion.image_extractor import extract_images
from src.ingestion.text_cleaner import extract_content


def scrape_url(url: str, max_images: int = 3) -> dict:
  """Coordinates downloading, text extraction, and image discovery.

  """
  print(f"[scraper] Fetching: {url}")
  html = fetch_html(url)

  if not html:
    return {
        "url": url,
        "success": False,
        "error": "Failed to retrieve page HTML",
    }

  content = extract_content(html)
  images = extract_images(html, base_url=url, max_images=max_images)

  return {
      "url": url,
      "success": True,
      "title": content["title"],
      "author": content["author"],
      "date": content["date"],
      "text": content["text"],
      "images": images,
      "text_char_count": len(content["text"]),
  }


# ==========================================
# Direct Test Runner
# ==========================================
if __name__ == "__main__":
  test_links = [
      "https://en.wikipedia.org/wiki/Convolutional_neural_network",
      "https://distill.pub/2016/augmented-rnns/",
  ]

  for link in test_links:
    data = scrape_url(link, max_images=3)
    print("\n" + "=" * 60)
    print(f"SUCCESS: {data['success']}")
    print(f"TITLE:   {data.get('title')}")
    print(f"AUTHOR:  {data.get('author')}")
    print(f"DATE:    {data.get('date')}")
    print(f"CHARS:   {data.get('text_char_count')}")
    print(f"IMAGES:  {data.get('images')}")
    print("-" * 60)
    preview = data.get("text", "")[:250].replace("\n", " ")
    print(f"PREVIEW: {preview}...")
    print("=" * 60)