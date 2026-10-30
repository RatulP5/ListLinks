from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Substrings commonly present in non-content images
DISALLOWED_PATTERNS = [
    "avatar",
    "logo",
    "icon",
    "favicon",
    "badge",
    "spacer",
    "tracker",
    "ad-",
    "pixel",
]


def is_valid_image(url: str) -> bool:
  """Filters out tiny icons, SVGs, base64 blobs, and tracking pixels."""
  url_lower = url.lower()

  if url_lower.startswith("data:"):  # Skip inline base64 blobs
    return False

  if url_lower.endswith((".svg", ".ico")):  # Skip icons/vectors
    return False

  for pattern in DISALLOWED_PATTERNS:
    if pattern in url_lower:
      return False

  return True


def extract_images(html: str, base_url: str, max_images: int = 4) -> list[str]:
  """Finds key content images, prioritizing social OpenGraph image then in-body images."""
  if not html:
    return []

  soup = BeautifulSoup(html, "html.parser")
  candidate_urls = []

  # Priority 1: OpenGraph social preview image (usually the article's hero banner)
  og_img = soup.find("meta", property="og:image")
  if og_img and og_img.get("content"):
    full_url = urljoin(base_url, og_img["content"].strip())
    if is_valid_image(full_url):
      candidate_urls.append(full_url)

  # Priority 2: In-article <img> tags
  for img in soup.find_all("img"):
    # Check standard attributes and common lazy-loading tags
    src = (
        img.get("src")
        or img.get("data-src")
        or img.get("data-original")
    )
    if not src:
      continue

    full_url = urljoin(base_url, src.strip())

    if is_valid_image(full_url) and full_url not in candidate_urls:
      candidate_urls.append(full_url)

    if len(candidate_urls) >= max_images:
      break

  return candidate_urls