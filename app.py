# app.py
"""
Literature Search Builder + Europe PMC / PMC API + Downloadable Results
"""

import streamlit as st
import requests
import pandas as pd
import urllib.parse
from pathlib import Path

# -------------------- CONFIG -------------------- #

EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PMC_API_KEY = "YOUR_PMC_API_KEY"  # <-- add your PMC API key here
PMC_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# -------------------- PAGE CONFIG -------------------- #

st.set_page_config(
    page_title="Literature Search Builder",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Literature Search Builder & Result Downloader")
st.caption("PubMed • PMC • Europe PMC • Google Scholar")

# -------------------- SIDEBAR INPUT -------------------- #

with st.sidebar:
    st.header("🔧 Search Terms")

    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (OR, one per line)", "SSI")

    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms", "triclosan suture\nPLUS suture")

    term3 = st.text_input("Concept 3 (optional)", "")

    exclude_terms = st.text_area("Exclude terms (NOT)", "review")

    year_from, year_to = st.slider(
        "Publication year range",
        1990, 2025, (2000, 2025)
    )

    max_results = st.slider("Max results per database", 10, 200, 50)

# -------------------- HELPERS -------------------- #

def build_or_block(main, synonyms, field=None):
    terms = []
    if main:
        terms.append(main)
    if synonyms:
        terms.extend([s.strip() for s in synonyms.split("\n") if s.strip()])
    if not terms:
        return ""
    if field:
        terms = [f"{t}[{field}]" for t in terms]
    return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"

def build_not_block(terms, field=None):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    if field:
        items = [f"{t}[{field}]" for t in items]
    return " NOT (" + " OR ".join(items) + ")"

def combine(*blocks):
    return " AND ".join([b for b in blocks if b])

# -------------------- SEARCH STRINGS -------------------- #

block1 = build_or_block(term1, synonyms1, "Title/Abstract")
block2 = build_or_block(term2, synonyms2, "Title/Abstract")
block3 = build_or_block(term3, "", "Title/Abstract")
not_block = build_not_block(exclude_terms, "Publication Type")

pubmed_query = combine(block1, block2, block3) + not_block
gs_query = combine(
    build_or_block(term1, synonyms1),
    build_or_block(term2, synonyms2),
    build_or_block(term3, "")
) + build_not_block(exclude_terms)

# -------------------- URL LINKS -------------------- #

pubmed_url = (
    "https://pubmed.ncbi.nlm.nih.gov/?term="
    + urllib.parse.quote(pubmed_query)
    + f"&filter=years.{year_from}-{year_to}"
)
pmc_url = "https://www.ncbi.nlm.nih.gov/pmc/?term=" + urllib.parse.quote(pubmed_query)
europe_pmc_url = "https://europepmc.org/search?query=" + urllib.parse.quote(pubmed_query)
scholar_url = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(gs_query)

# -------------------- DISPLAY SEARCH STRINGS -------------------- #

st.subheader("🧾 Generated Search Strings")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**PubMed / PMC / Europe PMC**")
    st.code(pubmed_query)

with c2:
    st.markdown("**Google Scholar**")
    st.code(gs_query)

st.subheader("🔗 Direct Search Links")
l1, l2, l3, l4 = st.columns(4)
l1.markdown(f"🔬 **PubMed**  \n[Open]({pubmed_url})")
l2.markdown(f"📄 **PMC**  \n[Open]({pmc_url})")
l3.markdown(f"🌍 **Europe PMC**  \n[Open]({europe_pmc_url})")
l4.markdown(f"🎓 **Scholar**  \n[Open]({scholar_url})")

st.divider()

# -------------------- EUROPE PMC API -------------------- #

def fetch_europe_pmc(query, max_results=50):
    r = requests.get(
        EUROPE_PMC_API,
        params={"query": query, "format": "json", "pageSize": max_results},
        timeout=30
    )
    hits = r.json().get("resultList", {}).get("result", [])
    rows = []
    for h in hits:
        rows.append({
            "Title": h.get("title"),
            "Authors": h.get("authorString"),
            "Journal": h.get("journalTitle"),
            "Year": h.get("pubYear"),
            "DOI": h.get("doi"),
            "PMID": h.get("pmid"),
            "PMCID": h.get("pmcid"),
            "OA": "Yes" if h.get("isOpenAccess") == "Y" else "No",
            "PDF": h.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url")
        })
    return pd.DataFrame(rows)

# -------------------- PMC API -------------------- #

def fetch_pmc(query, max_results=50):
    # Use esearch to get PMIDs / PMCIDs
    esearch_url = PMC_BASE + "esearch.fcgi"
    params = {
        "db": "pmc",
        "term": query,
        "retmax": max_results,
        "api_key": PMC_API_KEY,
        "retmode": "json"
    }
    r = requests.get(esearch_url, params=params, timeout=30)
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    rows = []

    if not ids:
        return pd.DataFrame(rows)

    # Fetch details via efetch
    efetch_url = PMC_BASE + "efetch.fcgi"
    params = {
        "db": "pmc",
        "id": ",".join(ids),
        "retmode": "xml",
        "api_key": PMC_API_KEY
    }
    r = requests.get(efetch_url, params=params, timeout=30)
    from xml.etree import ElementTree as ET
    root = ET.fromstring(r.text)

    for article in root.findall(".//article"):
        title = article.findtext(".//article-title")
        journal = article.findtext(".//journal-title")
        year = article.findtext(".//pub-date/year")
        authors = ", ".join([f"{a.findtext('surname')} {a.findtext('given-names')}" for a in article.findall(".//contrib[@contrib-type='author']")])
        pmcid = article.findtext(".//article-id[@pub-id-type='pmc']")
        doi = article.findtext(".//article-id[@pub-id-type='doi']")
        rows.append({
            "Title": title,
            "Authors": authors,
            "Journal": journal,
            "Year": year,
            "DOI": doi,
            "PMID": "",  # PMC only
            "PMCID": pmcid,
            "OA": "Yes",
            "PDF": ""  # Optional: implement PDF extraction from PMC link
        })
    return pd.DataFrame(rows)

# -------------------- FETCH & DISPLAY RESULTS -------------------- #

st.subheader("📥 Fetch Results")

if st.button("🔍 Fetch Europe PMC + PMC"):

    with st.spinner("Fetching Europe PMC results..."):
        df_epmc = fetch_europe_pmc(pubmed_query, max_results)

    with st.spinner("Fetching PMC results..."):
        df_pmc = fetch_pmc(pubmed_query, max_results)

    # Combine, remove duplicates
    df = pd.concat([df_epmc, df_pmc], ignore_index=True).drop_duplicates(subset=["DOI","PMCID"])

    st.success(f"✅ Retrieved {len(df)} records total")
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")

    # -------------------- EXPORT -------------------- #

    def make_ris(df):
        out = []
        for _, r in df.iterrows():
            out += [
                "TY  - JOUR",
                f"TI  - {r['Title']}",
                f"JO  - {r['Journal']}",
                f"PY  - {r['Year']}",
            ]
            if pd.notna(r["Authors"]):
                for a in r["Authors"].split(","):
                    out.append(f"AU  - {a.strip()}")
            if r["DOI"]:
                out.append(f"DO  - {r['DOI']}")
            if r["PMID"]:
                out.append(f"PM  - {r['PMID']}")
            if r["PMCID"]:
                out.append(f"PMCID - {r['PMCID']}")
            out += ["ER  -", ""]
        return "\n".join(out)

    st.download_button(
        "⬇️ Download CSV",
        edited_df.to_csv(index=False),
        "literature_results.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download RIS",
        make_ris(edited_df),
        "literature_results.ris",
        "application/x-research-info-systems"
    )

st.info(
    "Europe PMC + PMC API fetch allows full metadata download. "
    "PMC API requires a valid API key."
)
