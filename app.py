# app.py
"""
Literature Search String Builder & Direct Search Launcher with PMC API
"""

import streamlit as st
import urllib.parse
import requests
import time
import pandas as pd

# ---------------- CONFIG ---------------- #
NCBI_API_KEY = "YOUR_VALID_NCBI_API_KEY"
MAX_PMC_RESULTS = 50  # Maximum PMC results to fetch per query

# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(
    page_title="Literature Search Builder",
    page_icon="📚",
    layout="wide",
)
st.title("📚 Literature Search String Builder")
st.caption("Build database-specific search strings and launch searches directly")

# ---------------- INPUT SECTION ---------------- #
with st.sidebar:
    st.header("🔧 Search Terms")
    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")
    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")
    term3 = st.text_input("Concept 3 (optional)", "")
    exclude_terms = st.text_area("Exclude terms (NOT)", "review")
    year_from, year_to = st.slider(
        "Publication year range", 1990, 2025, (2000, 2025)
    )

# ---------------- HELPER FUNCTIONS ---------------- #
def build_or_block(main_term: str, synonyms: str, field: str | None = None):
    terms = [main_term] if main_term else []
    if synonyms:
        terms.extend([s.strip() for s in synonyms.split("\n") if s.strip()])
    if not terms:
        return ""
    if field:
        terms = [f"{t}[{field}]" for t in terms]
    return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"

def build_not_block(terms: str, field: str | None = None):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    if field:
        items = [f"{t}[{field}]" for t in items]
    return " NOT (" + " OR ".join(items) + ")"

def combine_blocks(*blocks):
    return " AND ".join([b for b in blocks if b])

# ---------------- SEARCH STRING ---------------- #
block1_pubmed = build_or_block(term1, synonyms1, "Title/Abstract")
block2_pubmed = build_or_block(term2, synonyms2, "Title/Abstract")
block3_pubmed = build_or_block(term3, "", "Title/Abstract")
not_pubmed = build_not_block(exclude_terms, "Publication Type")
pubmed_query = combine_blocks(block1_pubmed, block2_pubmed, block3_pubmed) + not_pubmed

block1_gs = build_or_block(term1, synonyms1)
block2_gs = build_or_block(term2, synonyms2)
block3_gs = build_or_block(term3, "")
not_gs = build_not_block(exclude_terms)
gs_query = combine_blocks(block1_gs, block2_gs, block3_gs) + not_gs

# ---------------- URL BUILDERS ---------------- #
pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(pubmed_query)}&filter=years.{year_from}-{year_to}"
pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={urllib.parse.quote(pubmed_query)}"
europe_pmc_url = f"https://europepmc.org/search?query={urllib.parse.quote(pubmed_query)}"
google_scholar_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(gs_query)}"

# ---------------- FETCH PMC RESULTS ---------------- #
def fetch_pmc_results(query: str, max_results: int = 50, api_key: str = None):
    results = []
    retstart = 0
    while True:
        params = {
            "db": "pmc",
            "term": query,
            "retmode": "json",
            "retmax": min(100, max_results - len(results)),
            "retstart": retstart
        }
        if api_key:
            params["api_key"] = api_key
        try:
            r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params, timeout=20)
            r.raise_for_status()
        except requests.HTTPError as e:
            st.error(f"HTTP error while fetching PMC results: {e}")
            return results
        except requests.RequestException as e:
            st.error(f"Request error: {e}")
            return results

        data = r.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        results.extend(ids)
        retstart += len(ids)
        if not ids or len(results) >= max_results:
            break
        time.sleep(0.34)
    return results[:max_results]

# ---------------- OUTPUT ---------------- #
st.subheader("🧾 Generated Search Strings")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**PubMed / PMC / Europe PMC**")
    st.code(pubmed_query, language="text")
with col2:
    st.markdown("**Google Scholar**")
    st.code(gs_query, language="text")

st.subheader("🔗 Direct Search Links")
link_col1, link_col2, link_col3, link_col4 = st.columns(4)
link_col1.markdown(f"🔬 [PubMed]({pubmed_url})", unsafe_allow_html=True)
link_col2.markdown(f"📄 [PMC]({pmc_url})", unsafe_allow_html=True)
link_col3.markdown(f"🌍 [Europe PMC]({europe_pmc_url})", unsafe_allow_html=True)
link_col4.markdown(f"🎓 [Google Scholar]({google_scholar_url})", unsafe_allow_html=True)

# ---------------- FETCH PMC IDs ---------------- #
if st.button("Fetch PMC IDs"):
    st.info("Fetching PMC IDs...")
    pmc_ids = fetch_pmc_results(pubmed_query, max_results=MAX_PMC_RESULTS, api_key=NCBI_API_KEY)
    st.success(f"Fetched {len(pmc_ids)} PMC IDs")
    if pmc_ids:
        st.download_button("⬇️ Download PMC IDs as CSV", pd.DataFrame({"PMC_ID": pmc_ids}).to_csv(index=False), "pmc_ids.csv", "text/csv")
