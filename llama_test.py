import os
from pathlib import Path
from llama_cpp import Llama

# Find the Ollama blob directory
blobs_dir = Path(__file__).parent.resolve() / "model"

# Grab the largest blob file in that directory (the model weights)
model_blob = max(blobs_dir.glob("sha256-*"), key=lambda f: f.stat().st_size)
print(
    f"Loading existing Ollama weight file: {model_blob.name} ("
    f"{model_blob.stat().st_size / 1024 / 1024:.1f} MB)"
)

llm = Llama(
    model_path=str(model_blob),
    n_ctx=2048,
    n_threads=4,
    verbose=False,
)

# Ready to generate
response = llm.create_chat_completion(
    messages=[{"role": "user", "content": "Explain vector search briefly."}]
)
print(response["choices"][0]["message"]["content"])