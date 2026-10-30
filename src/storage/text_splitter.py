import re

class TextSplitter:
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_into_sentences(self, text: str) -> list[str]:
        # Regex splits on sentence-ending punctuation followed by whitespace,
        # preserving common abbreviations like "e.g.", "i.e.", "Dr."
        sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'`])')
        sentences = [s.strip() for s in sentence_end.split(text) if s.strip()]
        return sentences

    def split_text(self, text: str) -> list[str]:
        """Splits text into cohesive chunks without cutting sentences in half."""
        if not text or not text.strip():
            return []

        # Normalize redundant spaces and newlines
        clean_text = " ".join(text.split())
        sentences = self._split_into_sentences(clean_text)

        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_len = 0

        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sent_len = len(sentence)

            # If a single sentence exceeds chunk_size, append it directly
            if sent_len > self.chunk_size and not current_chunk:
                chunks.append(sentence)
                i += 1
                continue

            # If adding this sentence exceeds chunk_size, finalize the current chunk
            if current_len + sent_len + (1 if current_chunk else 0) > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))

                # Step backwards to create a clean overlap of full sentences
                overlap_len = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if overlap_len + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s) + 1
                    else:
                        break

                current_chunk = overlap_sentences
                current_len = sum(len(s) for s in current_chunk) + max(0, len(current_chunk) - 1)

            current_chunk.append(sentence)
            current_len += sent_len + (1 if len(current_chunk) > 1 else 0)
            i += 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks