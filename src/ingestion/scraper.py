from urllib.parse import urlparse
from src.ingestion.html_fetcher import fetch_html
from src.ingestion.image_extractor import extract_images
from src.ingestion.pdf_extractor import extract_pdf_content
from src.ingestion.text_cleaner import extract_content
from src.ingestion.video_extractor import extract_videos


def is_pdf_url(url: str) -> bool:
  parsed = urlparse(url)
  return parsed.path.lower().endswith(".pdf")


def scrape_resource(url: str, max_images: int = 3, max_videos: int = 2) -> dict:
  """Coordinates fetching and parsing for either PDFs or HTML pages."""
  if is_pdf_url(url):
    print(f"[scraper] Detected PDF URL: {url}")
    return extract_pdf_content(url)

  print(f"[scraper] Fetching HTML: {url}")
  html = fetch_html(url)
  if not html:
    return {
        "url": url,
        "success": False,
        "error": "Failed to retrieve page HTML",
    }

  content = extract_content(html)
  images = extract_images(html, base_url=url, max_images=max_images)
  videos = extract_videos(html, max_videos=max_videos)

  return {
      "url": url,
      "success": True,
      "title": content["title"],
      "author": content.get("author"),
      "date": content.get("date"),
      "text": content["text"],
      "images": images,
      "videos": videos,
      "text_char_count": len(content["text"]),
  }