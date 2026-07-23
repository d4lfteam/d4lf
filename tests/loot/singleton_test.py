from src.loot.singleton import singleton


def test_singleton_decorator_reuses_instance():
    class Value:
        pass

    factory = singleton(Value)
    assert factory() is factory()
