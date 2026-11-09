from pathlib import Path
from typing import Generator
from llama_cpp import Llama

# Default project paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "model"


class LocalLLM:

  def __init__(self, model_path: str | None = None, n_ctx: int = 2048):
    if model_path:
      target_blob = Path(model_path)
    else:
      # Find the largest weight file in model/ (supporting both sha256-* blobs and .gguf files)
      candidates = list(MODEL_DIR.glob("sha256-*")) + list(
          MODEL_DIR.glob("*.gguf")
      )
      if not candidates:
        raise FileNotFoundError(
            f"No model weight file found in {MODEL_DIR}. "
        )
      target_blob = max(candidates, key=lambda f: f.stat().st_size)

    print(
        f"[LLM] Loading weights: {target_blob.name} ("
        f"{target_blob.stat().st_size / (1024 * 1024):.1f} MB)"
    )

    self.llm = Llama(
        model_path=str(target_blob),
        n_ctx=n_ctx,
        n_threads=4,
        verbose=False,
    )

  def generate_answer_stream(
      self, query: str, context_chunks: list[dict]
  ) -> Generator[str, None, None]:
    """Builds a grounded prompt from retrieved chunks and streams tokens."""
    # Format context blocks
    context_text = "\n\n".join([
        f"[Snippet from '{c['title']}']:\n{c['content']}"
        for c in context_chunks
    ])

    system_prompt = (
        "Answer user's question using ONLY the provided context below"
        "If the answer cannot be found in the context, say: 'I cannot find that in the saved documents.' "
    )

    user_prompt = (
        f"Context :\n{context_text}\n\n" f"Question: {query}\n\nExplain everything the context says regarding: {query}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response_stream = self.llm.create_chat_completion(
    messages=messages,
    max_tokens=1024,  # High ceiling so long answers are never cut off mid-sentence
    temperature=0.1,  # near greedy to stay grounded
    top_p=0.9,
    repeat_penalty=1.12,  # Breaks out of infinite repeating loops
    stream=True,
    )

    for chunk in response_stream:
      delta = chunk["choices"][0].get("delta", {})
      token = delta.get("content", "")
      if token:
        yield token