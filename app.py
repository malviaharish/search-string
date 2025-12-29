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

st.title("🌍 Europe PMC Search (Paste Search String)")
st.caption("Paste a complete Europe PMC search string and download results")

# ===================== SIDEBAR ===================== #
with st.sidebar:
    st.header("🔎 Search Settings")

    max_results = st.number_input(
        "Maximum results",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )

    run_search = st.button("🔍 Run Europe PMC Search")

# ===================== MAIN INPUT ===================== #
search_string = st.text_area(
    "Paste Europe PMC search string",
    height=160,
    placeholder=(
        'Example:\n'
        'TITLE_ABSTRACT:("surgical site infection" OR SSI) '
        'AND ("antibacterial suture" OR triclosan) '
        'AND PUB_TYPE:"Journal Article" '
        'AND FIRST_PDATE:[2015-01-01 TO 2024-12-31]'
    )
)

# ===================== EUROPE PMC API ===================== #
def europe_pmc_search(query, page_size):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": page_size,
        "resultType": "core"
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# ===================== RUN SEARCH ===================== #
if run_search:
    if not search_string.strip():
        st.warning("Please paste a search string before running the search.")
    else:
        st.subheader("🧠 Europe PMC Search Strategy")
        st.code(search_string, language="text")

        with st.spinner("Fetching results from Europe PMC..."):
            try:
                data = europe_pmc_search(search_string, max_results)
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

                    # ===================== DOWNLOAD ===================== #
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
    "Paste a valid Europe PMC query exactly as you would use on europepmc.org. "
    "All filters must be included inside the search string."
)
