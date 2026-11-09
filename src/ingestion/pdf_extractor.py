import io
from pathlib import Path
import pypdfium2 as pdfium
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}


def extract_pdf_content(
    source: str | bytes | io.BytesIO, file_name: str = "Uploaded Document"
) -> dict:
  """Extracts plain text and page metadata from a PDF URL, local path, or file bytes."""
  try:
    if isinstance(source, str) and (
        source.startswith("http://") or source.startswith("https://")
    ):
      response = requests.get(
          source, headers=DEFAULT_HEADERS, timeout=15, allow_redirects=True
      )
      if response.status_code != 200:
        return {
            "success": False,
            "error": f"Failed to download PDF. Status: {response.status_code}",
        }
      pdf = pdfium.PdfDocument(response.content)
      doc_url = source
      doc_title = Path(source).name.split("?")[0] or "Web PDF"
    elif isinstance(source, (bytes, io.BytesIO)):
      pdf = pdfium.PdfDocument(source)
      doc_url = f"file://{file_name}"
      doc_title = file_name
    else:
      # Local file path
      pdf = pdfium.PdfDocument(source)
      doc_url = f"file://{Path(source).name}"
      doc_title = Path(source).name

    full_text = []
    for page in pdf:
      textpage = page.get_textpage()
      text = textpage.get_text_range()
      if text and text.strip():
        full_text.append(text.strip())

    extracted_str = "\n\n".join(full_text).strip()

    return {
        "url": doc_url,
        "title": doc_title,
        "success": bool(extracted_str),
        "text": extracted_str,
        "images": [],
        "videos": [],
        "error": None if extracted_str else "No readable text found in PDF.",
    }
  except Exception as e:
    return {"success": False, "error": f"PDF extraction failed: {str(e)}"}