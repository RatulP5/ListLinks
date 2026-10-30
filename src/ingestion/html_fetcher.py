import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_html(url: str, timeout: int = 10) -> str | None:
  """Fetches raw HTML string from a URL.

  Returns None if request fails or status code is not 200.
  """
  try:
    response = requests.get(
        url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True
    )
    if response.status_code == 200:
      return response.text
    print(
        f"[html_fetcher] Received status {response.status_code} for URL: {url}"
    )
    return None
  except requests.RequestException as e:
    print(f"[html_fetcher] Request failed for {url}: {e}")
    return None