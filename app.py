"""
# -------------------- SEARCH STRING GENERATION -------------------- #


# PubMed / PMC / Europe PMC
block1_pubmed = build_or_block(term1, synonyms1, "Title/Abstract")
block2_pubmed = build_or_block(term2, synonyms2, "Title/Abstract")
block3_pubmed = build_or_block(term3, "", "Title/Abstract")
not_pubmed = build_not_block(exclude_terms, "Publication Type")


def combine_blocks(*blocks):
return " AND ".join([b for b in blocks if b])


pubmed_query = combine_blocks(block1_pubmed, block2_pubmed, block3_pubmed) + not_pubmed


# Google Scholar (no field tags)
block1_gs = build_or_block(term1, synonyms1)
block2_gs = build_or_block(term2, synonyms2)
block3_gs = build_or_block(term3, "")
not_gs = build_not_block(exclude_terms)


gs_query = combine_blocks(block1_gs, block2_gs, block3_gs) + not_gs


# -------------------- URL BUILDERS -------------------- #


pubmed_url = (
"https://pubmed.ncbi.nlm.nih.gov/?term="
+ urllib.parse.quote(pubmed_query)
+ f"&filter=years.{year_from}-{year_to}"
)


pmc_url = (
"https://www.ncbi.nlm.nih.gov/pmc/?term="
+ urllib.parse.quote(pubmed_query)
)


europe_pmc_url = (
"https://europepmc.org/search?query="
+ urllib.parse.quote(pubmed_query)
)


google_scholar_url = (
"https://scholar.google.com/scholar?q="
+ urllib.parse.quote(gs_query)
)


# -------------------- OUTPUT -------------------- #


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
st.markdown(f"🔬 **PubMed** \n[Open Search]({pubmed_url})")


with link_col2:
st.markdown(f"📄 **PMC (Full Text)** \n[Open Search]({pmc_url})")


with link_col3:
st.markdown(f"🌍 **Europe PMC** \n[Open Search]({europe_pmc_url})")


with link_col4:
st.markdown(f"🎓 **Google Scholar** \n[Open Search]({google_scholar_url})")


st.divider()


st.info(
"This app automatically adapts search syntax to each database. "
"PubMed/PMC use field tags, while Google Scholar uses free-text Boolean logic."
)
