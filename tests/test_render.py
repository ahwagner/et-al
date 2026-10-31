from etal.render import markdown_table, csv_text, nlm_citation, presentation_line

def test_nlm_citation_full(data):
    pub = data.by_name["publications"]["2026 Druggable genome LLM"]
    assert nlm_citation(pub) == ("Schimmelpfennig L, Cannon M, Cody Q, McMichael J, Coffman AC, Kiwala S, Krysiak K, Wagner AH, Griffith M, Griffith OL. "
        "Searching the druggable genome using large language models. Bioinformatics. 2026;42(9):btag632. "
        "https://doi.org/10.1093/bioinformatics/btag632. PMID: 42631692; PMCID: PMC13544961.")

def test_nlm_citation_minimal(data):
    pub = data.by_name["publications"]["2026 Cat-VRS preprint"]
    assert nlm_citation(pub) == "Puthawala D, Reardon B, Wagner AH. " + pub.title + ". bioRxiv. 2026."

def test_presentation_line_with_people_and_override(data):
    p = data.by_name["presentations"]["2026-08-05 FUSOR poster"]
    assert presentation_line(p) == "Poster, in person | Daniel Puthawala. Standardizing fusion calls in a computable format with FUSOR. CGC Annual Meeting 2026, Satellite venue, Houston, TX. National."

def test_presentation_line_month_only_and_plain_presenter(data):
    p = data.by_name["presentations"]["2026-07 AnyVar research in review"]
    assert presentation_line(p) == "Lightning talk, virtual | Jennifer Bowser. AnyVar and AnyVLM. IGM Research in Review, Virtual. Institutional. Day not recorded."

def test_tables():
    assert markdown_table(["a", "b"], [["1", "x|y"]]) == "| a | b |\n| --- | --- |\n| 1 | x\\|y |\n"
    assert csv_text(["a", "b"], [["1", 'x,"y']]) == 'a,b\n1,"x,""y"\n'

def test_presentation_line_omits_missing_parts(data):
    p = data.by_name["presentations"]["2026-08-05 FUSOR poster"]
    p.location_own = None
    p.event.location = None
    p.audience_own = None
    p.event.audience = None
    assert presentation_line(p) == "Poster, in person | Daniel Puthawala. Standardizing fusion calls in a computable format with FUSOR. CGC Annual Meeting 2026."

def test_presentation_line_blank_title(data):
    p = data.by_name["presentations"]["2026-08-05 FUSOR poster"]
    p.title = None
    assert presentation_line(p).startswith("Poster, in person | Daniel Puthawala. CGC Annual Meeting 2026,")


def test_title_ending_in_punctuation_gets_no_extra_period(data):
    pub = data.by_name["publications"]["2026 Cat-VRS preprint"]
    pub.title = "Is Cat-VRS ready?"
    assert nlm_citation(pub) == "Puthawala D, Reardon B, Wagner AH. Is Cat-VRS ready? bioRxiv. 2026."
    pub.title = "Cat-VRS works!"
    assert "Cat-VRS works! bioRxiv." in nlm_citation(pub)
    pub.title = "Cat-VRS, et al."
    assert "Cat-VRS, et al. bioRxiv." in nlm_citation(pub)
    p = data.by_name["presentations"]["2026-08-05 FUSOR poster"]
    p.title = "Can FUSOR standardize fusions?"
    assert "Daniel Puthawala. Can FUSOR standardize fusions? CGC Annual Meeting 2026," in presentation_line(p)
