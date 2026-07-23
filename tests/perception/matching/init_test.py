from src.perception.matching import SearchArgs, SearchResult, TemplateMatch, search


def test_matching_interface_exposes_models_and_engine() -> None:
    assert SearchArgs is not None
    assert SearchResult is not None
    assert TemplateMatch is not None
    assert callable(search)
