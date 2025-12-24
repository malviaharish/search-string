# app.py
"""
Literature Search String Builder & Individual Database Downloader
Databases: PubMed, PMC, Europe PMC
"""

import streamlit as st
import urllib.parse
import requests
import pandas as pd
import time

# ---------------- CONFIG ---------------- #
NCBI_API_KEY = "YOUR_NCBI_API_KEY"
MAX_RESULTS = 50  # Max results per database

# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(page_title="Literature Search Builder", page_icon="📚", layout="wide")
st.title("📚 Literature Search Builder & Individual Database Downloader")
st.caption("Build search strings, open in browser, and download search results individually")

# ---------------- INPUT SECTION ---------------- #
with st.sidebar:
    st.header("🔧 Search Terms")
    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")
    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")
    term3 = st.text_input("Concept 3 (optional)", "")
    exclude_terms = st.text_area("Exclude terms (NOT)", "review")
    year_from, year_to = st.slider("Publication year range", 1990, 2025, (2000, 2025))

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

block1_epmc = build_or_block(term1, synonyms1)
block2_epmc = build_or_block(term2, synonyms2)
block3_epmc = build_or_block(term3, "")
not_epmc = build_not_block(exclude_terms)
epmc_query = combine_blocks(block1_epmc, block2_epmc, block3_epmc) + not_epmc

# URLs
pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(pubmed_query)}&filter=years.{year_from}-{year_to}"
pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={urllib.parse.quote(pubmed_query)}"
europe_pmc_url = f"https://europepmc.org/search?query={urllib.parse.quote(epmc_query)}"

# ---------------- FETCH FUNCTIONS ---------------- #
def fetch_pubmed_results(query: str, max_results: int = 50, api_key: str = None):
    ids = []
    retstart = 0
    while True:
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": min(100, max_results - len(ids)),
            "retstart": retstart
        }
        if api_key:
            params["api_key"] = api_key
        try:
            r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params, timeout=20)
            r.raise_for_status()
        except requests.RequestException as e:
            st.error(f"Error fetching PubMed results: {e}")
            return []
        data = r.json()
        new_ids = data.get("esearchresult", {}).get("idlist", [])
        if not new_ids:
            break
        ids.extend(new_ids)
        retstart += len(new_ids)
        if len(ids) >= max_results:
            break
        time.sleep(0.34)
    return ids[:max_results]

def fetch_europe_pmc_results(query: str, max_results: int = 50):
    results = []
    try:
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", 
                         params={"query": query, "format": "json", "pageSize": max_results}, timeout=20)
        r.raise_for_status()
        hits = r.json().get("resultList", {}).get("result", [])
        for h in hits:
            results.append({
                "Title": h.get("title", ""),
                "Authors": h.get("authorString", ""),
                "Year": h.get("pubYear", ""),
                "DOI": h.get("doi", ""),
                "PMID": h.get("pmid", ""),
                "PMCID": h.get("pmcid", "")
            })
    except requests.RequestException as e:
        st.error(f"Error fetching Europe PMC results: {e}")
    return results

# ---------------- OUTPUT ---------------- #
st.subheader("🔗 Direct Search Links")
col1, col2, col3 = st.columns(3)
col1.markdown(f"🔬 [PubMed]({pubmed_url})", unsafe_allow_html=True)
col2.markdown(f"📄 [PMC]({pmc_url})", unsafe_allow_html=True)
col3.markdown(f"🌍 [Europe PMC]({europe_pmc_url})", unsafe_allow_html=True)

# ---------------- FETCH & DOWNLOAD INDIVIDUAL ---------------- #
st.subheader("📥 Fetch & Download Individual Database Results")

if st.button("Fetch PubMed Metadata"):
    pubmed_ids = fetch_pubmed_results(pubmed_query, MAX_RESULTS, NCBI_API_KEY)
    st.success(f"Fetched {len(pubmed_ids)} PubMed IDs")
    df_pubmed = pd.DataFrame({"PubMed_ID": pubmed_ids, "Search_String": pubmed_query})
    st.download_button("⬇️ Download PubMed CSV", df_pubmed.to_csv(index=False).encode('utf-8'), "pubmed_results.csv", "text/csv")

if st.button("Fetch Europe PMC Metadata"):
    epmc_results = fetch_europe_pmc_results(epmc_query, MAX_RESULTS)
    st.success(f"Fetched {len(epmc_results)} Europe PMC results")
    df_epmc = pd.DataFrame(epmc_results)
    df_epmc["Search_String"] = epmc_query
    st.download_button("⬇️ Download Europe PMC CSV", df_epmc.to_csv(index=False).encode('utf-8'), "europe_pmc_results.csv", "text/csv")

# PMC direct search (browser only, no API fetch included)
st.info("PMC metadata API fetch is limited, use direct search link for full PMC results")
