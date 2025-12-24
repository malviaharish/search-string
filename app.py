# app.py
"""
Literature Search String Builder with Direct Search & Metadata Download

Databases:
- PubMed
- PMC (direct search link)
- Europe PMC (metadata + CSV download)
- Google Scholar

Run:
    streamlit run app.py

Requirements:
    pip install streamlit requests pandas
"""

import streamlit as st
import urllib.parse
import requests
import pandas as pd

# -------------------- PAGE CONFIG -------------------- #
st.set_page_config(page_title="Literature Search Builder", page_icon="📚", layout="wide")
st.title("📚 Literature Search String Builder")
st.caption("Build database-specific search strings and launch searches directly")

# -------------------- INPUTS -------------------- #
with st.sidebar:
    st.header("🔧 Search Terms")
    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")
    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")
    term3 = st.text_input("Concept 3 (optional)", "")
    exclude_terms = st.text_area("Exclude terms (NOT)", "review")
    year_from, year_to = st.slider("Publication year range", 1990, 2025, (2000, 2025))
    max_europe_pmc = st.number_input("Max Europe PMC results to fetch", value=100, min_value=10, step=10)

# -------------------- HELPER FUNCTIONS -------------------- #
def build_or_block(main_term: str, synonyms: str, field: str | None = None):
    terms = [main_term] if main_term else []
    if synonyms:
        terms += [s.strip() for s in synonyms.split("\n") if s.strip()]
    if not terms:
        return ""
    if field:
        terms = [f'{t}[{field}]' for t in terms]
    return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"

def build_not_block(terms: str, field: str | None = None):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    if field:
        items = [f'{t}[{field}]' for t in items]
    return " NOT (" + " OR ".join(items) + ")"

def combine_blocks(*blocks):
    return " AND ".join([b for b in blocks if b])

# -------------------- SEARCH STRING -------------------- #
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

# -------------------- URL BUILDERS -------------------- #
pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(pubmed_query)}&filter=years.{year_from}-{year_to}"
pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={urllib.parse.quote(pubmed_query)}"
europe_pmc_api = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
gs_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(gs_query)}"

# -------------------- EUROPE PMC METADATA -------------------- #
def fetch_europe_pmc(query, max_results=100):
    url = europe_pmc_api
    params = {"query": query, "format": "json", "pageSize": max_results}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    hits = r.json().get("resultList", {}).get("result", [])
    data = []
    for h in hits:
        data.append({
            "Title": h.get("title",""),
            "Authors": h.get("authorString",""),
            "Journal": h.get("journalTitle",""),
            "Year": h.get("pubYear",""),
            "DOI": h.get("doi",""),
            "PMID": h.get("pmid",""),
            "PMCID": h.get("pmcid",""),
        })
    return pd.DataFrame(data)

# -------------------- DISPLAY -------------------- #
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
with link_col1:
    st.markdown(f"🔬 **PubMed**  \n[Open Search]({pubmed_url})")
with link_col2:
    st.markdown(f"📄 **PMC (Full Results)**  \n[Open Search]({pmc_url})")
with link_col3:
    st.markdown(f"🌍 **Europe PMC**  \n[Open Search]({europe_pmc_api}?query={urllib.parse.quote(pubmed_query)})")
with link_col4:
    st.markdown(f"🎓 **Google Scholar**  \n[Open Search]({gs_url})")

# -------------------- EUROPE PMC METADATA DOWNLOAD -------------------- #
if st.button("⬇️ Fetch Europe PMC Metadata"):
    try:
        with st.spinner("Fetching Europe PMC metadata..."):
            df = fetch_europe_pmc(pubmed_query, max_results=max_europe_pmc)
        st.success(f"Fetched {len(df)} records")
        st.dataframe(df)
        csv_data = df.to_csv(index=False)
        st.download_button("⬇️ Download Europe PMC Metadata CSV", csv_data, "europe_pmc_metadata.csv", "text/csv")
    except Exception as e:
        st.error(f"Error fetching Europe PMC metadata: {e}")

st.info("PMC API fetch is limited; for full PMC results, use the direct search link.")
