import streamlit as st
from src.ingestion.pdf_extractor import extract_pdf_content
from src.ingestion.scraper import scrape_resource
from src.llm.client import LocalLLM
from src.storage.vector_store import BookmarkStore

st.set_page_config(page_title="ListLinks", page_icon="🔖", layout="wide")


@st.cache_resource
def get_store():
  return BookmarkStore(db_path="./data/bookmarks.db")


@st.cache_resource
def get_llm():
  return LocalLLM()


store = get_store()
llm = get_llm()

# --- SIDEBAR: LIST & RESOURCE MANAGEMENT ---
with st.sidebar:
  st.header("🗂️ Manage Collections")

  new_list_name = st.text_input("New List Name", placeholder="e.g. Papers & Pods")
  if st.button("Create List", width='stretch'):
    if new_list_name.strip():
      store.get_or_create_list(new_list_name.strip())
      st.success(f"Created '{new_list_name.strip()}'")
      st.rerun()

  st.divider()

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

    # --- INGESTION TABS: URL vs PDF ---
    st.subheader("📥 Add Content")
    tab_url, tab_pdf = st.tabs(["Web URL / PDF Link", "Upload PDF"])

    with tab_url:
      url_to_add = st.text_input(
          "Enter URL", placeholder="https://...", key="url_input"
      )
      if st.button("Index URL", width='stretch'):
        if url_to_add.strip():
          with st.spinner("Fetching and extracting media..."):
            res = scrape_resource(url_to_add.strip())
          if res.get("success"):
            chunks_count = store.add_article_to_list(
                list_id=selected_list_id,
                url=res["url"],
                title=res["title"],
                full_text=res["text"],
                images=res.get("images", []),
                videos=res.get("videos", []),
            )
            st.success(f"Indexed '{res['title']}' ({chunks_count} chunks)")
            st.rerun()
          else:
            st.error(res.get("error"))

    with tab_pdf:
      uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
      if (
          st.button("Index PDF File", width='stretch')
          and uploaded_file
      ):
        with st.spinner("Parsing PDF with pypdfium2..."):
          res = extract_pdf_content(
              uploaded_file.getvalue(), file_name=uploaded_file.name
          )
        if res.get("success"):
          chunks_count = store.add_article_to_list(
              list_id=selected_list_id,
              url=res["url"],
              title=res["title"],
              full_text=res["text"],
              images=[],
              videos=[],
          )
          st.success(f"Indexed '{res['title']}' ({chunks_count} chunks)")
          st.rerun()
        else:
          st.error(res.get("error"))


# --- MAIN PANEL: SCOPED RAG & GROUPED MEDIA DISPLAY ---
st.title("🔖 ListLinks AI & Media Assistant")

if not selected_list_id:
  st.write("👈 Select or create a collection on the left.")
else:
  active_list_name = [
      item["name"] for item in all_lists if item["id"] == selected_list_id
  ][0]
  st.caption(f"Active collection: **{active_list_name}**")

  query = st.text_input(
      "Ask a question or search within this collection:",
      placeholder="e.g. What is a Neural Network",
  )

  if query.strip():
    with st.spinner("Searching..."):
      results = store.search(
          query=query.strip(), list_id=selected_list_id, top_k=4
      )

    if not results:
      st.warning("No relevant information found in this list.")
    else:
      # 1. LLM Answer Stream
      st.subheader("🤖 Qwen Response")
      with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text = ""
        for token in llm.generate_answer_stream(query.strip(), results):
          full_text += token
          placeholder.markdown(full_text + "▌")
        placeholder.markdown(full_text)

      st.divider()

      # 2. Group Results by Link / URL
      grouped_hits = {}
      for hit in results:
        u = hit["url"]
        if u not in grouped_hits:
          grouped_hits[u] = {
              "title": hit["title"],
              "images": hit["images"],
              "videos": hit["videos"],
              "snippets": [],
          }
        grouped_hits[u]["snippets"].append(
            (hit["content"], hit["similarity"])
        )

      # 3. Display Grouped Sources with Visuals and Videos
      st.subheader(f"📚 Derived Sources ({len(grouped_hits)} Documents)")

      for url, data in grouped_hits.items():
        with st.container(border=True):
          col_left, col_right = st.columns([1.6, 1.0])

          # Left: Text snippets and title
          with col_left:
            st.markdown(f"#### [{data['title']}]({url})")
            st.caption(f"Source URL: `{url}`")
            st.write("**Matching Context Snippets:**")
            for snippet, score in data["snippets"]:
              st.info(f"{snippet}\n\n*(Cosine Score: {score})*")

          # Right: Embedded Media (YouTube video frames and Images)
          with col_right:
            # Video frames
            if data["videos"]:
              st.write("**Attached Videos:**")
              for vid in data["videos"]:
                st.video(vid)

            # Image previews
            if data["images"]:
              st.write("**Extracted Pictures:**")
              img_cols = st.columns(min(len(data["images"]), 2))
              for idx, img_url in enumerate(data["images"]):
                with img_cols[idx % 2]:
                  st.image(img_url, width='stretch')

            if not data["videos"] and not data["images"]:
              st.caption("No media available for this document.")