"""C3: the Enricher's directory (D-6)."""


def test_lookup_exact_alias_fuzzy_placeholder_and_miss(directory):
    c, how = directory.lookup("Sample Co")
    assert c.name == "Sample Co" and how == "exact"
    c, how = directory.lookup("SampleCo")
    assert c.name == "Sample Co" and how == "alias"
    c, how = directory.lookup("Sample Co Inc.")
    assert c.name == "Sample Co" and how in ("exact", "alias", "fuzzy")
    c, how = directory.lookup("Placeholdr Inc")
    assert c.name == "Placeholder Inc" and how == "fuzzy"
    for p in ("self", "", None, "N/A", "me"):
        assert directory.lookup(p) == (None, "placeholder")
    assert directory.lookup("Acme Rockets") == (None, "not_found")


def test_kinds_tell_vendors_and_schools_apart(directory):
    assert directory.lookup("Example State University")[0].kind == "education"
    assert directory.lookup("Mock AI Consulting")[0].kind == "vendor"
    assert directory.lookup("Dummy Dynamics")[0].kind == "company"
