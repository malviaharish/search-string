# app.py
"""
Literature Search String Builder & PMC/Europe PMC Results Viewer

Databases supported:
- PubMed
- PMC (PubMed Central)
- Europe PMC
- Google Scholar

Features:
- Build Boolean search strings (AND / OR / NOT)
- Field-specific queries
- One-click search links
- Fetch top PMC / Europe PMC results (requires API key)
- Export results to CSV or RIS

Run:
  streamlit run app.py

Requirements:
  pip install streamlit requests pandas
"""

import streamlit as st
import requests
import pandas as pd
import urllib.parse
import time

# -------------------- CONFIG -------------------- #
# Add your PMC API key here
PMC_API_KEY = "YOUR_PMC_API_KEY"
EUROPE_PMC_API_KEY = "YOUR_EUROPE_PMC_API_KEY"

# -------------------- PAGE CONFIG -------------------- #
st.set_page_config(
    page_title="Literature Search Builder",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Literature Search String Builder + PMC Results")
st.caption("Build search strings & fetch PMC / Europe PMC search results")

# -------------------- SIDEBAR INPUT -------------------- #
with st.sidebar:
    st.header("🔧 Search Terms")
    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR-separated, one per line)", "SSI")
    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (OR-separated, one per line)", "triclosan suture\nPLUS suture")
    term3 = st.text_input("Concept 3 (optional)", "")
    exclude_terms = st.text_area("Exclude terms (NOT)", "review")
    year_from, year_to = st.slider("Publication year range", 1990, 2025, (2000, 2025))
    max_results = st.number_input("Maximum results to fetch (PMC / Europe PMC)", 10, 100, 20)

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
    return "(" + " OR ".join(terms) + ")" if len(terms) > 1 else terms[0]

def build_not_block(terms: str, field: str | None = None):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    if field:
        items = [f'{t}[{field}]' for t in items]
    return " NOT (" + " OR ".join(items) + ")" if items else ""

def combine_blocks(*blocks):
    return " AND ".join([b for b in blocks if b])

# -------------------- SEARCH STRING GENERATION -------------------- #
# PubMed / PMC / Europe PMC
block1_pubmed = build_or_block(term1, synonyms1, "Title/Abstract")
block2_pubmed = build_or_block(term2, synonyms2, "Title/Abstract")
block3_pubmed = build_or_block(term3, "", "Title/Abstract")
not_pubmed = build_not_block(exclude_terms, "Publication Type")
pubmed_query = combine_blocks(block1_pubmed, block2_pubmed, block3_pubmed) + not_pubmed

# Google Scholar
block1_gs = build_or_block(term1, synonyms1)
block2_gs = build_or_block(term2, synonyms2)
block3_gs = build_or_block(term3, "")
not_gs = build_not_block(exclude_terms)
gs_query = combine_blocks(block1_gs, block2_gs, block3_gs) + not_gs

# -------------------- URL BUILDERS -------------------- #
pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/?term=" + urllib.parse.quote(pubmed_query)
pmc_url = "https://www.ncbi.nlm.nih.gov/pmc/?term=" + urllib.parse.quote(pubmed_query)
europe_pmc_url = "https://europepmc.org/search?query=" + urllib.parse.quote(pubmed_query)
google_scholar_url = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(gs_query)

# -------------------- PMC / Europe PMC API -------------------- #
def fetch_pmc_results(query, max_count=20):
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pmc",
        "term": query,
        "retmax": max_count,
        "retmode": "json",
        "api_key": PMC_API_KEY
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    ids = r.json()["esearchresult"]["idlist"]
    results = []
    for pmcid in ids:
        url_s = "https://www.ncbi.nlm.nih.gov/pmc/utils/entrez/eutils/esummary.fcgi"
        r2 = requests.get(url_s, params={"db":"pmc","id":pmcid,"retmode":"json","api_key":PMC_API_KEY}, timeout=20)
        r2.raise_for_status()
        doc = r2.json()["result"][pmcid]
        results.append({
            "PMCID": f"PMC{pmcid}",
            "Title": doc.get("title",""),
            "Journal": doc.get("fulljournalname",""),
            "Year": doc.get("pubdate","")[:4],
            "DOI": doc.get("elocationid","").replace("doi:",""),
        })
        time.sleep(0.3)
    return results

def fetch_europe_pmc_results(query, max_count=20):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": query, "format":"json", "pageSize": max_count, "apiKey": EUROPE_PMC_API_KEY}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    hits = r.json().get("resultList", {}).get("result", [])
    results = []
    for h in hits:
        results.append({
            "PMCID": h.get("pmcid",""),
            "Title": h.get("title",""),
            "Journal": h.get("journalTitle",""),
            "Year": h.get("pubYear",""),
            "DOI": h.get("doi","")
        })
    return results

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
    st.markdown(f"🔬 [PubMed]({pubmed_url})")
with link_col2:
    st.markdown(f"📄 [PMC]({pmc_url})")
with link_col3:
    st.markdown(f"🌍 [Europe PMC]({europe_pmc_url})")
with link_col4:
    st.markdown(f"🎓 [Google Scholar]({google_scholar_url})")

st.divider()

# -------------------- FETCH RESULTS -------------------- #
if st.button("📥 Fetch PMC / Europe PMC Results"):
    with st.spinner("Fetching results..."):
        pmc_results = fetch_pmc_results(pubmed_query, max_results)
        europe_results = fetch_europe_pmc_results(pubmed_query, max_results)
        all_results = pmc_results + europe_results
        df = pd.DataFrame(all_results).drop_duplicates(subset=["PMCID"])
        st.success(f"✅ Fetched {len(df)} results")
        st.dataframe(df, use_container_width=True)

        # CSV download
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv_data, "pmc_results.csv", "text/csv")
