import streamlit as st
from src.ingestion.scraper import scrape_url
from src.storage.vector_store import BookmarkStore

st.set_page_config(page_title="ListLinks", page_icon="🔖", layout="wide")


@st.cache_resource
def get_store():
  return BookmarkStore(db_path="./data/bookmarks.db")


store = get_store()

# --- SIDEBAR: LIST & LINK MANAGEMENT ---
with st.sidebar:
  st.header("🗂️ Manage Collections")

  # 1. Create a new List
  new_list_name = st.text_input("New List Name", placeholder="e.g. AI Research")
  if st.button("Create List", use_container_width=True):
    if new_list_name.strip():
      store.get_or_create_list(new_list_name.strip())
      st.success(f"Created '{new_list_name.strip()}'")
      st.rerun()

  st.divider()

  # 2. Select Active List
  all_lists = store.get_all_lists()
  if not all_lists:
    st.info("Create a list above to get started.")
    selected_list_id = None
  else:
    list_options = {
        f"{item['name']} ({item['article_count']} docs)": item["id"]
        for item in all_lists
    }
    selected_label = st.selectbox(
        "Select Active List", list(list_options.keys())
    )
    selected_list_id = list_options[selected_label]

    st.divider()

    # 3. Add Link to Active List
    st.subheader("🔗 Add Link")
    url_to_add = st.text_input("Page URL", placeholder="https://...")
    if st.button("Scrape & Index", use_container_width=True):
      if url_to_add.strip():
        with st.spinner("Scraping page content..."):
          scraped = scrape_url(url_to_add.strip())

        if scraped.get("success"):
          with st.spinner("Chunking & embedding..."):
            chunks_count = store.add_article_to_list(
                list_id=selected_list_id,
                url=scraped["url"],
                title=scraped["title"],
                full_text=scraped["text"],
            )
          st.success(f"Indexed '{scraped['title']}' ({chunks_count} chunks)")
          st.rerun()
        else:
          st.error(f"Failed to fetch URL: {scraped.get('error')}")

    st.divider()

    # 4. Show URLs in the Selected List
    saved_articles = store.get_articles_by_list(selected_list_id)
    with st.expander(f"📑 Saved URLs ({len(saved_articles)})", expanded=True):
      if not saved_articles:
        st.caption("No URLs added to this list yet.")
      else:
        for article in saved_articles:
          st.markdown(f"- [{article['title']}]({article['url']})")


# --- MAIN PANEL: SCOPED SEARCH ---
st.title("🔖 ListLinks Search")

if not selected_list_id:
  st.write("👈 Create or pick a list from the sidebar to start searching.")
else:
  active_list_name = [
      item["name"] for item in all_lists if item["id"] == selected_list_id
  ][0]
  st.caption(f"Currently searching inside: **{active_list_name}**")

  query = st.text_input(
      "Search query", placeholder="What are pooling layers used for?"
  )

  col1, col2 = st.columns([1, 4])
  with col1:
    top_k = st.slider("Top results", min_value=1, max_value=8, value=3)

  if query.strip():
    with st.spinner("Searching semantic vectors..."):
      results = store.search(
          query=query.strip(), list_id=selected_list_id, top_k=top_k
      )

    if not results:
      st.warning("No matching snippets found in this list.")
    else:
      st.write(f"### Top {len(results)} Matches")
      for i, hit in enumerate(results, 1):
        with st.container(border=True):
          st.markdown(f"**{i}. [{hit['title']}]({hit['url']})**")
          st.caption(f"Cosine Similarity Score: `{hit['similarity']}`")
          st.write(hit["content"])