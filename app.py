# app.py
"""
Literature Search String Builder & Direct Search Launcher

Databases supported:
- PubMed
- PMC (PubMed Central)
- Europe PMC

Features:
- Build Boolean search strings (AND / OR / NOT)
- Field-specific queries where applicable
- Auto-generate database-specific syntax
- One-click search links (open in new tab)
- Download search results metadata as CSV or Excel

Run:
  streamlit run app.py

Requirements:
  pip install streamlit pandas openpyxl
"""

import streamlit as st
import pandas as pd
import urllib.parse
import io

# -------------------- PAGE CONFIG -------------------- #
st.set_page_config(
    page_title="Literature Search Builder",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Literature Search String Builder")
st.caption("Build database-specific search strings and launch searches directly")

# -------------------- INPUT SECTION -------------------- #
with st.sidebar:
    st.header("🔧 Search Terms")

    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")

    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")

    term3 = st.text_input("Concept 3 (optional)", "")

    exclude_terms = st.text_area("Exclude terms (NOT)", "review")

    year_from, year_to = st.slider(
        "Publication year range",
        1990, 2025, (2000, 2025)
    )

# -------------------- HELPER FUNCTIONS -------------------- #
def build_or_block(main_term: str, synonyms: str, field: str | None = None):
    terms = []
    if main_term:
        terms.append(main_term)
    if synonyms:
        terms.extend([s.strip() for s in synonyms.split("\n") if s.strip()])
    if not terms:
        return ""
    if field:
        terms = [f'{t}[{field}]' for t in terms]
    if len(terms) == 1:
        return terms[0]
    return "(" + " OR ".join(terms) + ")"

def build_not_block(terms: str, field: str | None = None):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    if field:
        items = [f'{t}[{field}]' for t in items]
    return " NOT (" + " OR ".join(items) + ")"

def combine_blocks(*blocks):
    return " AND ".join([b for b in blocks if b])

# -------------------- BUILD SEARCH STRINGS -------------------- #
# PubMed / PMC / Europe PMC
block1_pubmed = build_or_block(term1, synonyms1, "Title/Abstract")
block2_pubmed = build_or_block(term2, synonyms2, "Title/Abstract")
block3_pubmed = build_or_block(term3, "", "Title/Abstract")
not_pubmed = build_not_block(exclude_terms, "Publication Type")
pubmed_query = combine_blocks(block1_pubmed, block2_pubmed, block3_pubmed) + not_pubmed

# Google Scholar (no field tags)
block1_gs = build_or_block(term1, synonyms1)
block2_gs = build_or_block(term2, synonyms2)
block3_gs = build_or_block(term3, "")
not_gs = build_not_block(exclude_terms)
gs_query = combine_blocks(block1_gs, block2_gs, block3_gs) + not_gs

# -------------------- DATABASE SEARCH LINKS -------------------- #
pubmed_url = (
    "https://pubmed.ncbi.nlm.nih.gov/?term="
    + urllib.parse.quote(pubmed_query)
    + f"&filter=years.{year_from}-{year_to}"
)
pmc_url = "https://www.ncbi.nlm.nih.gov/pmc/?term=" + urllib.parse.quote(pubmed_query)
europe_pmc_url = "https://europepmc.org/search?query=" + urllib.parse.quote(pubmed_query)
google_scholar_url = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(gs_query)

# -------------------- DISPLAY SEARCH STRINGS -------------------- #
st.subheader("🧾 Generated Search Strings")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**PubMed / PMC / Europe PMC**")
    st.code(pubmed_query, language="text")
with col2:
    st.markdown("**Google Scholar**")
    st.code(gs_query, language="text")

# -------------------- DIRECT SEARCH LINKS -------------------- #
st.subheader("🔗 Direct Search Links")
link_col1, link_col2, link_col3, link_col4 = st.columns(4)
with link_col1:
    st.markdown(f"🔬 **PubMed**  \n[Open Search]({pubmed_url})")
with link_col2:
    st.markdown(f"📄 **PMC (Full Text)**  \n[Open Search]({pmc_url})")
with link_col3:
    st.markdown(f"🌍 **Europe PMC**  \n[Open Search]({europe_pmc_url})")
with link_col4:
    st.markdown(f"🎓 **Google Scholar**  \n[Open Search]({google_scholar_url})")

# -------------------- DOWNLOAD LINKS -------------------- #
st.subheader("💾 Download Search Results Metadata")

# Create a simple dataframe of search metadata
data = {
    "Database": ["PubMed", "PMC (Direct Link)", "Europe PMC", "Google Scholar"],
    "Search String": [pubmed_query, pubmed_query, pubmed_query, gs_query],
    "Search URL": [pubmed_url, pmc_url, europe_pmc_url, google_scholar_url]
}
df = pd.DataFrame(data)

# CSV download
csv_buffer = io.StringIO()
df.to_csv(csv_buffer, index=False)
st.download_button(
    "⬇️ Download CSV",
    data=csv_buffer.getvalue(),
    file_name="search_results.csv",
    mime="text/csv"
)

# Excel download
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="SearchResults")
excel_buffer.seek(0)
st.download_button(
    "⬇️ Download Excel",
    data=excel_buffer,
    file_name="search_results.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()
st.info(
    "This app builds search strings for multiple databases. "
    "For PMC, the API has limits, so full results should be accessed via the direct search link."
)
