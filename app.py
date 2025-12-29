import streamlit as st
import pandas as pd
import urllib.parse
import io
import requests

# ===================== CONFIG ===================== #
EUROPE_PMC_API_KEY = ""  # Optional

st.set_page_config(
    page_title="Literature Search Builder",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Literature Search String Builder")
st.caption("Build database-specific search strings and run Europe PMC searches directly")

# ===================== SIDEBAR INPUTS ===================== #
with st.sidebar:
    st.header("🔧 Search Concepts")

    term1 = st.text_input("Concept 1 (required)", "surgical site infection")
    synonyms1 = st.text_area("Synonyms (one per line)", "SSI")

    term2 = st.text_input("Concept 2 (optional)", "antibacterial suture")
    synonyms2 = st.text_area("Synonyms (one per line)", "triclosan suture\nPLUS suture")

    term3 = st.text_input("Concept 3 (optional)", "")

    exclude_terms = st.text_area("Exclude terms (NOT)", "review")

    year_from, year_to = st.slider(
        "Publication year range",
        1990, 2025, (2000, 2025)
    )

    st.divider()
    st.header("🌍 Europe PMC Filters")

    epmc_field = st.selectbox(
        "Search in",
        ["TITLE_ABSTRACT", "TITLE", "ABSTRACT", "FULL_TEXT"]
    )

    epmc_pub_type = st.multiselect(
        "Publication Type",
        ["Journal Article", "Clinical Trial", "Review", "Meta-Analysis"]
    )

    epmc_country = st.text_input("Affiliation country (optional)", "")
    epmc_open_access = st.checkbox("Open Access only", False)

    epmc_max_results = st.number_input(
        "Max results",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )

# ===================== HELPER FUNCTIONS ===================== #
def build_or_block(main, synonyms, field=None):
    terms = []
    if main:
        terms.append(main)
    if synonyms:
        terms.extend([s.strip() for s in synonyms.split("\n") if s.strip()])
    if not terms:
        return ""
    if field:
        terms = [f'{t}[{field}]' for t in terms]
    return "(" + " OR ".join(terms) + ")" if len(terms) > 1 else terms[0]

def build_not_block(terms, field=None):
    if not terms:
        return ""
    items = [t.strip() for t in terms.split("\n") if t.strip()]
    if field:
        items = [f'{t}[{field}]' for t in items]
    return " NOT (" + " OR ".join(items) + ")"

def combine_blocks(*blocks):
    return " AND ".join([b for b in blocks if b])

def build_europe_pmc_query(base_query, field, pub_types, country, oa, y_from, y_to):
    field_map = {
        "TITLE": "TITLE:",
        "ABSTRACT": "ABSTRACT:",
        "TITLE_ABSTRACT": "TITLE_ABSTRACT:",
        "FULL_TEXT": ""
    }

    q = base_query
    if field_map[field]:
        q = field_map[field] + "(" + base_query + ")"

    if pub_types:
        q += " AND (" + " OR ".join([f'PUB_TYPE:"{pt}"' for pt in pub_types]) + ")"

    if country:
        q += f' AND AFFIL:"{country}"'

    if oa:
        q += " AND OPEN_ACCESS:Y"

    q += f" AND FIRST_PDATE:[{y_from}-01-01 TO {y_to}-12-31]"
    return q

def search_europe_pmc(query, page_size):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": page_size,
        "resultType": "core"
    }
    headers = {}
    if EUROPE_PMC_API_KEY:
        headers["X-API-Key"] = EUROPE_PMC_API_KEY

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

# ===================== BUILD SEARCH STRINGS ===================== #
block1 = build_or_block(term1, synonyms1, "Title/Abstract")
block2 = build_or_block(term2, synonyms2, "Title/Abstract")
block3 = build_or_block(term3, "", "Title/Abstract")
not_block = build_not_block(exclude_terms, "Publication Type")

pubmed_query = combine_blocks(block1, block2, block3) + not_block
gs_query = combine_blocks(
    build_or_block(term1, synonyms1),
    build_or_block(term2, synonyms2),
    build_or_block(term3, "")
) + build_not_block(exclude_terms)

# ===================== DIRECT SEARCH LINKS ===================== #
pubmed_url = (
    "https://pubmed.ncbi.nlm.nih.gov/?term="
    + urllib.parse.quote(pubmed_query)
    + f"&filter=years.{year_from}-{year_to}"
)

pmc_url = "https://www.ncbi.nlm.nih.gov/pmc/?term=" + urllib.parse.quote(pubmed_query)
europe_pmc_url = "https://europepmc.org/search?query=" + urllib.parse.quote(pubmed_query)
google_scholar_url = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(gs_query)

# ===================== DISPLAY SEARCH STRINGS ===================== #
st.subheader("🧾 Generated Search Strings")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**PubMed / PMC / Europe PMC**")
    st.code(pubmed_query, language="text")
with col2:
    st.markdown("**Google Scholar**")
    st.code(gs_query, language="text")

# ===================== DIRECT LINKS ===================== #
st.subheader("🔗 Direct Database Searches")

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"[🔬 PubMed]({pubmed_url})")
c2.markdown(f"[📄 PMC]({pmc_url})")
c3.markdown(f"[🌍 Europe PMC]({europe_pmc_url})")
c4.markdown(f"[🎓 Google Scholar]({google_scholar_url})")

# ===================== EUROPE PMC LIVE SEARCH ===================== #
st.subheader("🌍 Europe PMC Live Results")

epmc_query = build_europe_pmc_query(
    pubmed_query,
    epmc_field,
    epmc_pub_type,
    epmc_country,
    epmc_open_access,
    year_from,
    year_to
)

st.markdown("**Europe PMC Search Strategy**")
st.code(epmc_query, language="text")

if st.button("🔍 Run Europe PMC Search"):
    with st.spinner("Searching Europe PMC..."):
        try:
            data = search_europe_pmc(epmc_query, epmc_max_results)
            results = data.get("resultList", {}).get("result", [])

            if not results:
                st.warning("No results found.")
            else:
                df = pd.DataFrame([{
                    "Title": r.get("title"),
                    "Authors": r.get("authorString"),
                    "Journal": r.get("journalTitle"),
                    "Year": r.get("pubYear"),
                    "Publication Type": ", ".join(r.get("pubTypeList", {}).get("pubType", [])),
                    "Open Access": r.get("isOpenAccess"),
                    "Europe PMC URL": f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
                } for r in results])

                st.dataframe(df, use_container_width=True)

                # Downloads
                st.download_button(
                    "⬇️ Download CSV",
                    df.to_csv(index=False),
                    "europe_pmc_results.csv",
                    "text/csv"
                )

                excel_buf = io.BytesIO()
                with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False)
                excel_buf.seek(0)

                st.download_button(
                    "⬇️ Download Excel",
                    excel_buf,
                    "europe_pmc_results.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Europe PMC error: {e}")

st.divider()
st.info(
    "Europe PMC results are fetched via API and are suitable for systematic reviews, "
    "screening, and PRISMA documentation."
)
