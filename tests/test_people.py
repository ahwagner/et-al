from etal.people import AliasIndex, author_flags, is_author, normalize_name

def test_normalize_name():
    assert normalize_name("  Wagner,  AH. ") == "wagner, ah"

def test_resolve_through_aliases(data):
    idx = AliasIndex.build(data.people)
    assert idx.resolve("Kuzma, K").name == "Kori Kuzma"
    assert idx.resolve("wagner ah").name == "Alex Wagner"
    assert idx.resolve("Griffith OL") is None

def test_flags_last_author_is_senior(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2025 MAVE mapping"], alex, idx)
    assert (f.first, f.senior_or_corresponding, f.peer_reviewed, f.first_or_corresponding_peer_reviewed) == (False, True, True, True)

def test_flags_first_author_not_corresponding(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2013 Exon-level expression"], alex, idx)
    assert (f.first, f.senior_or_corresponding) == (True, False)

def test_flags_corresponding_and_last(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2024 DGIdb 5.0"], alex, idx)
    assert (f.first, f.senior_or_corresponding) == (False, True)

def test_flags_middle_author(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2016 SAT1"], alex, idx)
    assert (f.first, f.senior_or_corresponding, f.first_or_corresponding_peer_reviewed) == (False, False, False)

def test_flags_preprint_not_peer_reviewed(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2026 Cat-VRS preprint"], alex, idx)
    assert f.senior_or_corresponding and not f.peer_reviewed and not f.first_or_corresponding_peer_reviewed

def test_empty_authors_do_not_raise(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    pub = data.by_name["publications"]["2026 Unresolved import"]
    assert not is_author(pub, alex, idx)
    f = author_flags(pub, alex, idx)
    assert (f.first, f.senior_or_corresponding) == (False, False)

def test_candidates_and_is_person(data):
    idx = AliasIndex.build(data.people)
    alex = idx.resolve("Alex Wagner"); kori = idx.resolve("Kori Kuzma")
    assert idx.candidates("Wagner A") == [alex]
    assert idx.candidates("Nobody N") == []
    assert idx.is_person("  WAGNER AH. ", alex)
    assert not idx.is_person("Wagner AH", kori)

def test_ambiguous_alias_has_two_candidates_and_no_resolution(data):
    alex = data.by_name["people"]["Alex Wagner"]; kori = data.by_name["people"]["Kori Kuzma"]
    kori.aliases = [*kori.aliases, "Wagner A"]
    idx = AliasIndex.build(data.people)
    assert idx.resolve("Wagner A") is None
    assert set(map(id, idx.candidates("Wagner A"))) == {id(alex), id(kori)}
    assert idx.is_person("Wagner A", alex) and idx.is_person("Wagner A", kori)

def test_person_repeating_own_alias_is_not_ambiguous(data):
    alex = data.by_name["people"]["Alex Wagner"]
    alex.aliases = [*alex.aliases, "alex  wagner"]
    idx = AliasIndex.build(data.people)
    assert idx.resolve("Alex Wagner") is alex

def test_explicit_corresponding_and_senior_lists(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    pub = data.by_name["publications"]["2016 SAT1"]
    pub.authors = ["Smith J", "Wagner AH", "Jones B", "Lee C"]
    assert not author_flags(pub, alex, idx).senior_or_corresponding
    pub.corresponding = ["wagner ah"]
    assert author_flags(pub, alex, idx).senior_or_corresponding
    pub.corresponding = []; pub.senior = ["Wagner AH"]
    assert author_flags(pub, alex, idx).senior_or_corresponding
    # an explicit senior list replaces the last-author default
    pub.authors = ["Smith J", "Jones B", "Wagner AH"]; pub.senior = ["Lee C"]
    assert not author_flags(pub, alex, idx).senior_or_corresponding

def test_co_first_counts_as_first(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    pub = data.by_name["publications"]["2016 SAT1"]
    pub.authors = ["Smith J", "Wagner AH", "Jones B"]; pub.co_first = ["Smith J", "Wagner A"]
    assert author_flags(pub, alex, idx).first
