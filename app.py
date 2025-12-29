import streamlit as st
import pandas as pd
import requests
import io

# ===================== PAGE CONFIG ===================== #
st.set_page_config(
    page_title="Europe PMC Search & Download",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Europe PMC Literature Search")
st.caption("Search Europe PMC via RESTful API and download results")

# ===================== SIDEBAR INPUTS ===================== #
with st.sidebar:
    st.header("🔍 Search Query")

    search_terms = st.text_area(
        "Enter search terms",
        "surgical site infection AND antibacterial suture"
    )

    search_field = st.selectbox(
        "Search in",
        ["TITLE_ABSTRACT", "TITLE", "ABSTRACT", "FULL_TEXT"]
    )

    pub_types = st.multiselect(
        "Publication Type",
        ["Journal Article", "Clinical Trial", "Review", "Meta-Analysis"]
    )

    year_from, year_to = st.slider(
        "Publication year range",
        1990, 2025, (2000, 2025)
    )

    country = st.text_input(
        "Affiliation country (optional)",
        ""
    )

    open_access = st.checkbox("Open Access only", False)

    max_results = st.number_input(
        "Maximum results",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )

    run_search = st.button("🔎 Run Europe PMC Search")

# ===================== QUERY BUILDER ===================== #
def build_epmc_query(
    terms, field, pub_types, country, oa, y_from, y_to
):
    field_map = {
        "TITLE": "TITLE:",
        "ABSTRACT": "ABSTRACT:",
        "TITLE_ABSTRACT": "TITLE_ABSTRACT:",
        "FULL_TEXT": ""
    }

    query = terms.strip()

    if field_map[field]:
        query = f"{field_map[field]}({query})"

    if pub_types:
        pt_block = " OR ".join([f'PUB_TYPE:"{pt}"' for pt in pub_types])
        query += f" AND ({pt_block})"

    if country:
        query += f' AND AFFIL:"{country}"'

    if oa:
        query += " AND OPEN_ACCESS:Y"

    query += f" AND FIRST_PDATE:[{y_from}-01-01 TO {y_to}-12-31]"

    return query

# ===================== EUROPE PMC SEARCH ===================== #
def europe_pmc_search(query, page_size):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": page_size,
        "resultType": "core"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

# ===================== RUN SEARCH ===================== #
if run_search:
    epmc_query = build_epmc_query(
        search_terms,
        search_field,
        pub_types,
        country,
        open_access,
        year_from,
        year_to
    )

    st.subheader("🧠 Europe PMC Search Strategy")
    st.code(epmc_query, language="text")

    with st.spinner("Fetching results from Europe PMC..."):
        try:
            data = europe_pmc_search(epmc_query, max_results)
            results = data.get("resultList", {}).get("result", [])

            if not results:
                st.warning("No results found.")
            else:
                df = pd.DataFrame([
                    {
                        "Title": r.get("title"),
                        "Authors": r.get("authorString"),
                        "Journal": r.get("journalTitle"),
                        "Year": r.get("pubYear"),
                        "Publication Type": ", ".join(
                            r.get("pubTypeList", {}).get("pubType", [])
                        ),
                        "Open Access": r.get("isOpenAccess"),
                        "Europe PMC URL": f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
                    }
                    for r in results
                ])

                st.subheader(f"📄 Results ({len(df)})")
                st.dataframe(df, use_container_width=True)

                # ===================== DOWNLOADS ===================== #
                st.subheader("💾 Download Results")

                st.download_button(
                    "⬇️ Download CSV",
                    df.to_csv(index=False),
                    "europe_pmc_results.csv",
                    "text/csv"
                )

                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False)
                excel_buffer.seek(0)

                st.download_button(
                    "⬇️ Download Excel",
                    excel_buffer,
                    "europe_pmc_results.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Europe PMC API error: {e}")

st.divider()
st.info(
    "This app uses the official Europe PMC RESTful API. "
    "Downloaded results are suitable for screening, SR, and PRISMA documentation."
)
