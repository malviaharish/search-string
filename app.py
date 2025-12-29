import streamlit as st
import requests
import pandas as pd
import io
import time

# ===================== PAGE CONFIG ===================== #
st.set_page_config(
    page_title="Literature Search Downloader",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Literature Search (PubMed | Europe PMC)")
st.caption("Paste search strings directly and fetch all results (unlimited)")

# ===================== REQUIRED CONFIG ===================== #
NCBI_EMAIL = "malviaharish@gmail.com"  # Your email required by NCBI
TOOL_NAME = "Harish_LitSearch_App"    # Short descriptive name for the app

# ===================== INPUT ===================== #
db_choice = st.radio(
    "Select Database",
    ["Europe PMC", "PubMed"],
    horizontal=True
)

search_string = st.text_area(
    "Paste search string",
    height=180,
    placeholder=(
        "Examples:\n\n"
        "Europe PMC:\n"
        'TITLE_ABSTRACT:("surgical site infection" OR SSI)\n\n'
        "PubMed:\n"
        '"surgical site infection"[Title/Abstract] NOT review[Publication Type]'
    )
)

run_search = st.button("🔍 Run Search")

# ===================== EUROPE PMC ===================== #
def fetch_all_epmc(query):
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    cursor = "*"
    page_size = 1000
    all_results = []

    while True:
        params = {
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "cursorMark": cursor,
            "resultType": "core"
        }
        r = requests.get(base_url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()

        results = data.get("resultList", {}).get("result", [])
        if not results:
            break

        all_results.extend(results)
        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor
        time.sleep(0.2)

    return pd.DataFrame([{
        "Title": r.get("title"),
        "Authors": r.get("authorString"),
        "Journal": r.get("journalTitle"),
        "Year": r.get("pubYear"),
        "DOI": r.get("doi"),
        "Open Access": r.get("isOpenAccess"),
        "URL": f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
    } for r in all_results])

# ===================== NCBI (PubMed) ===================== #
import xml.etree.ElementTree as ET

def ncbi_esearch(db, query):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": db,
        "term": query,
        "retmax": 100000,
        "usehistory": "y",
        "email": NCBI_EMAIL,
        "tool": TOOL_NAME
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return (
        int(root.findtext("Count")),
        root.findtext("WebEnv"),
        root.findtext("QueryKey")
    )

def ncbi_efetch(db, webenv, query_key, total):
    records = []
    batch_size = 200

    for start in range(0, total, batch_size):
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": db,
            "query_key": query_key,
            "WebEnv": webenv,
            "retstart": start,
            "retmax": batch_size,
            "retmode": "xml",
            "email": NCBI_EMAIL,
            "tool": TOOL_NAME
        }

        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        root = ET.fromstring(r.text)

        for art in root.findall(".//PubmedArticle"):
            title = art.findtext(".//ArticleTitle")
            year = art.findtext(".//PubDate/Year")
            journal = art.findtext(".//Journal/Title")
            abstract = " ".join([a.text for a in art.findall(".//AbstractText") if a.text])

            pmid = art.findtext(".//PMID")
            doi = art.findtext(".//ArticleId[@IdType='doi']")

            url_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            records.append({
                "Title": title,
                "Journal": journal,
                "Year": year,
                "PMID": pmid,
                "DOI": doi,
                "Abstract": abstract,
                "URL": url_link
            })

        time.sleep(0.2)

    return pd.DataFrame(records)

# ===================== RUN SEARCH ===================== #
if run_search:
    if not search_string.strip():
        st.warning("Please paste a search string.")
    else:
        st.subheader("🧠 Search Strategy Used")
        st.code(search_string, language="text")

        with st.spinner("Fetching ALL results (no limit)..."):
            try:
                if db_choice == "Europe PMC":
                    df = fetch_all_epmc(search_string)
                else:  # PubMed
                    total, webenv, qk = ncbi_esearch("pubmed", search_string)
                    df = ncbi_efetch("pubmed", webenv, qk, total)

                if df.empty:
                    st.warning("No results found.")
                else:
                    st.subheader(f"📄 Results Retrieved: {len(df)}")
                    st.dataframe(df, use_container_width=True)

                    # ===================== DOWNLOAD ===================== #
                    st.subheader("💾 Download Results")
                    st.download_button(
                        "⬇️ Download CSV",
                        df.to_csv(index=False),
                        f"{db_choice.replace(' ', '_').lower()}_results.csv",
                        "text/csv"
                    )

                    excel_buf = io.BytesIO()
                    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False)
                    excel_buf.seek(0)

                    st.download_button(
                        "⬇️ Download Excel",
                        excel_buf,
                        f"{db_choice.replace(' ', '_').lower()}_results.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"API error: {e}")

st.divider()
st.info(
    "Europe PMC uses RESTful API (cursor-based pagination). "
    "PubMed uses official NCBI Entrez E-utilities. "
    "All results are retrieved without artificial limits."
)
