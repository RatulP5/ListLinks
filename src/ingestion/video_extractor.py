import re
from bs4 import BeautifulSoup


def normalize_youtube_url(url: str) -> str | None:
  """Converts various YouTube link formats to a standard watch or embed URL."""
  yt_regex = (
      r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
  )
  match = re.search(yt_regex, url)
  if match:
    video_id = match.group(1)
    return f"https://www.youtube.com/watch?v={video_id}"
  return None


def extract_videos(html: str, max_videos: int = 2) -> list[str]:
  """Finds YouTube and standard HTML5 video links from raw HTML."""
  if not html:
    return []

  soup = BeautifulSoup(html, "html.parser")
  candidates = []

  # 1. Inspect <iframe> sources
  for iframe in soup.find_all("iframe"):
    src = iframe.get("src", "")
    yt_norm = normalize_youtube_url(src)
    if yt_norm and yt_norm not in candidates:
      candidates.append(yt_norm)

  # 2. Inspect anchor links pointing to YouTube
  for a in soup.find_all("a", href=True):
    href = a["href"]
    yt_norm = normalize_youtube_url(href)
    if yt_norm and yt_norm not in candidates:
      candidates.append(yt_norm)

  # 3. Native <video> tag sources
  for video in soup.find_all("video"):
    src = video.get("src")
    if src and src.startswith("http") and src not in candidates:
      candidates.append(src)
    for source in video.find_all("source"):
      src_tag = source.get("src")
      if src_tag and src_tag.startswith("http") and src_tag not in candidates:
        candidates.append(src_tag)

  return candidates[:max_videos]