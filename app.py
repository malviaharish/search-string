# app.py
"""
📚 Literature OA Downloader with PMC + Europe PMC + Crossref + Unpaywall

Features:
- Fetch all PMC results (batched)
- Europe PMC search with API key
- Unpaywall OA detection and PDF download
- Scholar, PubMed, PMC pill buttons
- Editable table & export CSV/RIS/ZIP
"""

import streamlit as st
import pandas as pd
import requests
import zipfile
from pathlib import Path
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import time
from xml.etree import ElementTree as ET

# ================= CONFIG ================= #
UNPAYWALL_EMAIL = "your_email@institute.edu"
PMC_API_KEY = "YOUR_PMC_API_KEY"
EUROPE_PMC_API_KEY = "YOUR_EUROPE_PMC_API_KEY"

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/pdf,text/html"
}

PMC_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# ================= UI ================= #
st.set_page_config("Literature OA Downloader", layout="wide")
st.title("📚 Literature OA Downloader")
st.caption("PMC + Europe PMC + Crossref + Unpaywall | 100% Legal OA")

input_text = st.text_area(
    "Paste DOI / PMID / PMCID / Reference (one per line)", height=220
)

st.markdown("""
<style>
table { width:100%; border-collapse:collapse; }
th, td { text-align:center; padding:8px; vertical-align:middle; }
th { background:#f1f5f9; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ================= HELPERS ================= #

def make_btn(url, label, color="#2563eb"):
    if not url:
        return ""
    return f"""
    <a href="{url}" target="_blank"
    style="background:{color};color:white;padding:5px 10px;
    border-radius:999px;text-decoration:none;font-weight:600;margin:2px;">
    {label}</a>
    """

def europe_pmc(query, max_results=50):
    r = requests.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": query,
            "format": "json",
            "pageSize": max_results,
            "apiKey": EUROPE_PMC_API_KEY
        },
        timeout=20
    )
    hits = r.json().get("resultList", {}).get("result", [])
    rows = []
    for h in hits:
        rows.append({
            "Title": h.get("title",""),
            "Authors": h.get("authorString",""),
            "Journal": h.get("journalTitle",""),
            "Year": h.get("pubYear",""),
            "DOI": h.get("doi",""),
            "PMID": h.get("pmid",""),
            "PMCID": h.get("pmcid",""),
            "OA": "Yes" if h.get("isOpenAccess") else "No",
            "PDF": "",
        })
    return rows

def id_crosswalk(val):
    r = requests.get(
        PMC_BASE + "idconv.fcgi",
        params={"ids": val, "format": "json", "api_key": PMC_API_KEY},
        timeout=15
    )
    recs = r.json().get("records", [])
    if not recs:
        return {}
    r0 = recs[0]
    return {"PMID": r0.get("pmid",""), "PMCID": r0.get("pmcid",""), "DOI": r0.get("doi","")}

def crossref(doi):
    r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=15)
    if r.status_code != 200:
        return {}
    m = r.json()["message"]
    return {
        "Title": m.get("title",[""])[0],
        "Journal": m.get("container-title",[""])[0],
        "Year": str(m.get("issued",{}).get("date-parts",[[None]])[0][0]),
        "Authors": ", ".join(f"{a.get('family','')} {a.get('given','')}" for a in m.get("author",[]))
    }

def unpaywall(doi):
    r = requests.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": UNPAYWALL_EMAIL}, timeout=15)
    return r.json() if r.status_code == 200 else {}

def extract_pdf(page):
    r = requests.get(page, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "lxml")
    m = soup.find("meta", attrs={"name":"citation_pdf_url"})
    if m: return m["content"]
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            return urljoin(page, a["href"])
    return None

def download_pdf(url, fname):
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 200 and "pdf" in r.headers.get("Content-Type",""):
        (DOWNLOAD_DIR / fname).write_bytes(r.content)
        return "Downloaded"
    return "Failed"

def make_ris(df):
    out = []
    for _, r in df.iterrows():
        out += [
            "TY  - JOUR",
            f"TI  - {r['Title']}" if r["Title"] else "",
            f"JO  - {r['Journal']}" if r["Journal"] else "",
            f"PY  - {r['Year']}" if r["Year"] else "",
        ]
        for a in r["Authors"].split(","):
            if a.strip():
                out.append(f"AU  - {a.strip()}")
        if r["DOI"]: out.append(f"DO  - {r['DOI']}")
        if r["PMID"]: out.append(f"PM  - {r['PMID']}")
        out += ["ER  -", ""]
    return "\n".join(out)

def fetch_pmc(query, max_results=50, batch_size=50):
    esearch_url = PMC_BASE + "esearch.fcgi"
    params = {"db":"pmc","term":query,"retmax":max_results,"retmode":"json","api_key":PMC_API_KEY}
    r = requests.get(esearch_url, params=params, timeout=30)
    ids = r.json().get("esearchresult",{}).get("idlist",[])
    rows=[]
    if not ids: return pd.DataFrame(rows)

    for i in range(0,len(ids),batch_size):
        batch_ids = ids[i:i+batch_size]
        efetch_url = PMC_BASE + "efetch.fcgi"
        params = {"db":"pmc","id":",".join(batch_ids),"retmode":"xml","api_key":PMC_API_KEY}
        r = requests.get(efetch_url, params=params, timeout=30)
        root = ET.fromstring(r.text)
        for article in root.findall(".//article"):
            title = article.findtext(".//article-title")
            journal = article.findtext(".//journal-title")
            year = article.findtext(".//pub-date/year")
            authors = ", ".join([f"{a.findtext('surname')} {a.findtext('given-names')}" 
                                 for a in article.findall(".//contrib[@contrib-type='author']")])
            pmcid = article.findtext(".//article-id[@pub-id-type='pmc']")
            doi = article.findtext(".//article-id[@pub-id-type='doi']")
            rows.append({
                "Title": title,"Authors": authors,"Journal": journal,"Year": year,
                "DOI": doi,"PMID":"","PMCID":pmcid,"OA":"Yes","PDF":""
            })
    return pd.DataFrame(rows)

# ================= MAIN ================= #

if st.button("🔍 Process"):

    rows=[]
    lines=[l.strip() for l in input_text.splitlines() if l.strip()]
    prog = st.progress(0.0)

    for i,x in enumerate(lines):

        rec={"Input":x,"Title":"","Journal":"","Year":"","Authors":"","DOI":"","PMID":"","PMCID":"",
             "OA":"No","PDF":"","Status":"",
             "Scholar":make_btn(f"https://scholar.google.com/scholar?q={quote(x)}","🎓 Scholar","#6d28d9"),
             "PubMed":make_btn(f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(x)}","🔬 PubMed","#065f46"),
             "PMC":make_btn(f"https://www.ncbi.nlm.nih.gov/pmc/?term={quote(x)}","📄 PMC","#7c3aed")}

        # Europe PMC
        rows += europe_pmc(x, max_results=50)

        # PMC API
        pmc_df = fetch_pmc(x, max_results=50)
        rows += pmc_df.to_dict("records")

        rows.append(rec)
        prog.progress((i+1)/len(lines))
        time.sleep(0.2)

    df = pd.DataFrame(rows)
    st.success("✅ Completed")

    st.data_editor(df, use_container_width=True)

    # ================= EXPORT ================= #
    csv_path = Path("results.csv")
    ris_path = Path("references.ris")

    df.to_csv(csv_path, index=False)
    ris_path.write_text(make_ris(df), encoding="utf-8")

    final_zip = Path("literature_results.zip")
    with zipfile.ZipFile(final_zip,"w") as z:
        z.write(csv_path,"results.csv")
        z.write(ris_path,"references.ris")
        for f in DOWNLOAD_DIR.glob("*.pdf"):
            z.write(f,f"oa_pdfs/{f.name}")

    with open(final_zip,"rb") as f:
        st.download_button("📦 Download ALL (CSV + RIS + PDFs)", f, "literature_results.zip","application/zip")
