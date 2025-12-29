import streamlit as st
import pandas as pd
import requests
import io
import time

# ===================== PAGE CONFIG ===================== #
st.set_page_config(
    page_title="Europe PMC Search & Download",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Europe PMC Search")
st.caption("Paste a Europe PMC search string and retrieve ALL results (no limit)")

# ===================== INPUT ===================== #
search_string = st.text_area(
    "Paste Europe PMC search string",
    height=180,
    placeholder=(
        'Example:\n'
        'TITLE_ABSTRACT:("surgical site infection" OR SSI)\n'
        'AND ("antibacterial suture" OR triclosan)\n'
        'AND PUB_TYPE:"Journal Article"\n'
        'AND FIRST_PDATE:[2015-01-01 TO 2024-12-31]'
    )
)

run_search = st.button("🔍 Run Europe PMC Search")

# ===================== EUROPE PMC API ===================== #
def fetch_all_epmc_results(query):
    """
    Fetch ALL results from Europe PMC using cursor-based pagination
    """
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    page_size = 1000  # Europe PMC max
    cursor = "*"
    all_results = []

    while True:
        params = {
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "cursorMark": cursor,
            "resultType": "core"
        }

        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        results = data.get("resultList", {}).get("result", [])
        if not results:
            break

        all_results.extend(results)

        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor
        time.sleep(0.2)  # polite delay

    return all_results

# ===================== RUN SEARCH ===================== #
if run_search:
    if not search_string.strip():
        st.warning("Please paste a Europe PMC search string.")
    else:
        st.subheader("🧠 Search Strategy Used")
        st.code(search_string, language="text")

        with st.spinner("Fetching ALL results from Europe PMC (this may take time)..."):
            try:
                records = fetch_all_epmc_results(search_string)

                if not records:
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
                            "DOI": r.get("doi"),
                            "Europe PMC URL": f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
                        }
                        for r in records
                    ])

                    st.subheader(f"📄 Results Retrieved: {len(df)}")
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
    "This app uses cursor-based pagination from the official Europe PMC REST API "
    "to retrieve ALL matching records without an artificial limit."
)
