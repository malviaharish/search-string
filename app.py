# app.py
"""
Literature Search String Builder & Results Fetcher
Databases: PubMed, PMC, Europe PMC
Features:
- Build Boolean search strings (AND / OR / NOT)
- Fetch top results with metadata
- Europe PMC pagination for >100 results
- Direct search links
- Download CSV/Excel with results

Run:
  streamlit run app.py
"""

import streamlit as st
import requests
import pandas as pd
import urllib.parse
from time import sleep

# -------------------- CONFIG -------------------- #
MAX_EPMC_RESULTS = 1000  # max number of Europe PMC results to fetch

st.set_page_config(page_title="Literature Search Builder", layout="wide")

st.title("📚 Literature Search Builder & Results Fetcher")
st.caption("Build search strings and fetch metadata from PubMed, PMC, Europe PMC")

# -------------------- INPUT SECTION -------------------- #
with st.sidebar:
    st.header("🔧 Search Terms")
    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")
    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")
    term3 = st.text_input("Concept 3 (optional)", "")
    exclude_terms = st.text_area("Exclude terms (NOT)", "review")
    year_from, year_to = st.slider("Publication year range", 1990, 2025, (2000, 2025))
    max_epmc = st.number_input("Max Europe PMC results to fetch", min_value=10, max_value=5000, value=500)

# -------------------- HELPER FUNCTIONS -------------------- #
def build_or_block(main_term: str, synonyms: str):
    terms = []
    if main_term:
        terms.append(main_term)
    if synonyms:
        terms.extend([s.strip() for s in synonyms.split("\n") if s.strip()])
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]
    return "(" + " OR ".join(terms) + ")"

def build_not_block(terms: str):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    return " NOT (" + " OR ".join(items) + ")"

def combine_blocks(*blocks):
    return " AND ".join([b for b in blocks if b])

def fetch_epmc_results(query, max_results=MAX_EPMC_RESULTS):
    """Fetch Europe PMC metadata with pagination."""
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    hits_all = []
    cursor = "*"
    page_size = 100

    while len(hits_all) < max_results:
        params = {"query": query, "format": "json", "pageSize": page_size, "cursorMark": cursor}
        r = requests.get(base_url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        hits = data.get("resultList", {}).get("result", [])
        hits_all.extend(hits)
        cursor = data.get("nextCursorMark")
        if not cursor or not hits:
            break
        sleep(0.3)
    return hits_all[:max_results]

# -------------------- SEARCH STRING GENERATION -------------------- #
block1_pubmed = build_or_block(term1, synonyms1)
block2_pubmed = build_or_block(term2, synonyms2)
block3_pubmed = build_or_block(term3, "")
not_block = build_not_block(exclude_terms)

search_string = combine_blocks(block1_pubmed, block2_pubmed, block3_pubmed) + not_block

# -------------------- URL BUILDERS -------------------- #
pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(search_string)}&filter=years.{year_from}-{year_to}"
pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={urllib.parse.quote(search_string)}"
europe_pmc_url = f"https://europepmc.org/search?query={urllib.parse.quote(search_string)}"
google_scholar_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(search_string)}"

# -------------------- OUTPUT -------------------- #
st.subheader("🧾 Generated Search String")
st.code(search_string, language="text")

st.subheader("🔗 Direct Search Links")
cols = st.columns(4)
cols[0].markdown(f"🔬 [PubMed]({pubmed_url})")
cols[1].markdown(f"📄 [PMC]({pmc_url})")
cols[2].markdown(f"🌍 [Europe PMC]({europe_pmc_url})")
cols[3].markdown(f"🎓 [Google Scholar]({google_scholar_url})")

# -------------------- FETCH EUROPE PMC RESULTS -------------------- #
if st.button("Fetch Europe PMC Metadata"):
    with st.spinner("Fetching Europe PMC metadata..."):
        epmc_hits = fetch_epmc_results(search_string, max_results=max_epmc)
        if not epmc_hits:
            st.warning("No results found in Europe PMC")
        else:
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "Title": h.get("title", ""),
                    "Journal": h.get("journalTitle", ""),
                    "Year": h.get("pubYear", ""),
                    "Authors": h.get("authorString", ""),
                    "DOI": h.get("doi", ""),
                    "PMCID": h.get("pmcid", "")
                } for h in epmc_hits
            ])
            st.success(f"Fetched {len(df)} Europe PMC results")
            st.dataframe(df)
            
            # Download buttons
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv_bytes, "epmc_results.csv", "text/csv")

            excel_bytes = df.to_excel(index=False, engine="openpyxl")
            st.download_button("⬇️ Download Excel", excel_bytes, "epmc_results.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
