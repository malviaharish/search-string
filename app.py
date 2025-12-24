# app.py
"""
Literature Search Builder + Europe PMC / PMC Result Downloader

Features:
- Boolean search builder
- PubMed / PMC / Europe PMC / Google Scholar syntax
- Europe PMC API search
- PMC full-text detection
- Result table
- CSV + RIS export

Run:
streamlit run app.py
"""

import streamlit as st
import requests
import pandas as pd
import urllib.parse
from pathlib import Path

# -------------------- CONFIG -------------------- #

EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

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

    max_results = st.slider("Max results (Europe PMC)", 10, 200, 50)

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

# -------------------- LINKS -------------------- #

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

st.subheader("🔗 Direct Search")

l1, l2, l3, l4 = st.columns(4)
l1.markdown(f"🔬 **PubMed**  \n[Open]({pubmed_url})")
l2.markdown(f"📄 **PMC**  \n[Open]({pmc_url})")
l3.markdown(f"🌍 **Europe PMC**  \n[Open]({europe_pmc_url})")
l4.markdown(f"🎓 **Scholar**  \n[Open]({scholar_url})")

st.divider()

# -------------------- EUROPE PMC SEARCH -------------------- #

st.subheader("📥 Europe PMC Results")

if st.button("🔍 Fetch Results from Europe PMC"):

    with st.spinner("Querying Europe PMC API..."):

        r = requests.get(
            EUROPE_PMC_API,
            params={
                "query": pubmed_query,
                "format": "json",
                "pageSize": max_results
            },
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

        df = pd.DataFrame(rows)

        st.success(f"✅ Retrieved {len(df)} records")

        # Editable table
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic"
        )

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
                out += ["ER  -", ""]
            return "\n".join(out)

        st.download_button(
            "⬇️ Download CSV",
            edited_df.to_csv(index=False),
            "europe_pmc_results.csv",
            "text/csv"
        )

        st.download_button(
            "⬇️ Download RIS",
            make_ris(edited_df),
            "europe_pmc_results.ris",
            "application/x-research-info-systems"
        )

st.info(
    "Europe PMC API is officially supported and includes PubMed + PMC records. "
    "PMC full-text availability is derived from Europe PMC enrichment."
)
