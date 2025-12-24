# app.py
"""
Literature Search String Builder & PMC Results Downloader
Databases supported:
- PubMed
- PMC (PubMed Central)
- Europe PMC
- Google Scholar

Features:
- Build Boolean search strings (AND / OR / NOT)
- Field-specific queries for PubMed/PMC
- Auto-generate database-specific syntax
- Fetch PMC search results via NCBI API with API key
- Download PMC results as CSV
"""

import streamlit as st
import requests
import pandas as pd
import urllib.parse
import time

# ---------------- CONFIG ---------------- #

NCBI_API_KEY = "YOUR_NCBI_API_KEY"  # <-- Add your NCBI API Key here
MAX_PMC_RESULTS = 100  # max results to fetch

# ---------------- PAGE ---------------- #

st.set_page_config(page_title="Literature Search Builder", layout="wide")
st.title("📚 Literature Search String Builder")
st.caption("Build database-specific search strings and fetch PMC results")

# ---------------- INPUT ---------------- #

with st.sidebar:
    st.header("🔧 Search Terms")
    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")
    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")
    term3 = st.text_input("Concept 3 (optional)", "")
    exclude_terms = st.text_area("Exclude terms (NOT)", "review")
    year_from, year_to = st.slider("Publication year range", 1990, 2025, (2000, 2025))

# ---------------- HELPERS ---------------- #

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

# ---------------- SEARCH STRINGS ---------------- #

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

pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/?term=" + urllib.parse.quote(pubmed_query) + f"&filter=years.{year_from}-{year_to}"
pmc_url = "https://www.ncbi.nlm.nih.gov/pmc/?term=" + urllib.parse.quote(pubmed_query)
europe_pmc_url = "https://europepmc.org/search?query=" + urllib.parse.quote(pubmed_query)
google_scholar_url = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(gs_query)

# ---------------- FETCH PMC RESULTS ---------------- #

def fetch_pmc_results(query: str, max_results: int = 100, api_key: str = None):
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
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        results.extend(ids)
        retstart += len(ids)
        if not ids or len(results) >= max_results:
            break
        time.sleep(0.34)  # avoid throttling
    return results[:max_results]

def fetch_pmc_metadata(pmcids: list[str], api_key: str = None):
    records = []
    for i in range(0, len(pmcids), 50):
        batch = pmcids[i:i+50]
        params = {"db": "pmc", "id": ",".join(batch), "retmode": "json"}
        if api_key:
            params["api_key"] = api_key
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        for pid in batch:
            item = data.get("result", {}).get(pid, {})
            records.append({
                "PMCID": pid,
                "Title": item.get("title", ""),
                "Journal": item.get("fulljournalname", ""),
                "Year": item.get("pubdate", "")[:4],
                "DOI": item.get("elocationid", "").replace("doi:", "")
            })
        time.sleep(0.34)
    return records

# ---------------- DISPLAY ---------------- #

st.subheader("🔗 Direct Search Links")
cols = st.columns(4)
cols[0].markdown(f"🔬 [PubMed]({pubmed_url})")
cols[1].markdown(f"📄 [PMC]({pmc_url})")
cols[2].markdown(f"🌍 [Europe PMC]({europe_pmc_url})")
cols[3].markdown(f"🎓 [Google Scholar]({google_scholar_url})")

st.subheader("🧾 Generated Search Strings")
st.code(pubmed_query, language="text")
st.code(gs_query, language="text")

if st.button("📥 Fetch PMC Results"):
    with st.spinner("Fetching PMC results..."):
        pmc_ids = fetch_pmc_results(pubmed_query, max_results=MAX_PMC_RESULTS, api_key=NCBI_API_KEY)
        st.success(f"Found {len(pmc_ids)} PMC articles")
        metadata = fetch_pmc_metadata(pmc_ids, api_key=NCBI_API_KEY)
        df = pd.DataFrame(metadata)
        st.dataframe(df)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download PMC Results as CSV", csv_bytes, "pmc_results.csv", "text/csv")
