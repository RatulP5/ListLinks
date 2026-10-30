class TextSplitter:

  def __init__(self, chunk_size: int = 600, chunk_overlap: int = 80):
    self.chunk_size = chunk_size
    self.chunk_overlap = chunk_overlap

  def split_text(self, text: str) -> list[str]:
    """Splits plain text into overlapping chunks"""
    if not text or not text.strip():
      return []

    # Clean redundant whitespace
    text = " ".join(text.split())
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
      end = start + self.chunk_size
      chunk = text[start:end]

      # Prefer breaking at a sentence boundary or whitespace
      if end < text_len:
        last_punct = max(
            chunk.rfind(". "),
            chunk.rfind("! "),
            chunk.rfind("? "),
            chunk.rfind("\n"),
        )
        if last_punct != -1 and last_punct > self.chunk_size // 2:
          end = start + last_punct + 1
          chunk = text[start:end]
        else:
          last_space = chunk.rfind(" ")
          if last_space != -1 and last_space > self.chunk_size // 2:
            end = start + last_space
            chunk = text[start:end]

      chunk_str = chunk.strip()
      if chunk_str:
        chunks.append(chunk_str)

      start = end - self.chunk_overlap
      if start >= text_len or end >= text_len:
        break

    return chunks