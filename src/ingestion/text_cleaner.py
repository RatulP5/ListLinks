import trafilatura


def extract_content(html: str) -> dict:
  """Extracts clean article text and metadata from raw HTML.
  """
  if not html:
    return {
        "title": "Untitled",
        "author": None,
        "date": None,
        "text": "",
    }

  # 1. Metadata (title, author, publication date)
  meta = trafilatura.extract_metadata(html)
  title = meta.title if (meta and meta.title) else "Untitled"
  author = meta.author if meta else None
  date = meta.date if meta else None

  # 2. Main content extraction
  clean_text = trafilatura.extract(
      html,
      include_comments=False,  # Exclude comment threads
      include_tables=False,  # Exclude complex tables
      no_fallback=False,  # Allow readability fallback if needed
  )

  return {
      "title": title.strip(),
      "author": author,
      "date": date,
      "text": clean_text.strip() if clean_text else "",
  }