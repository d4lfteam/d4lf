from src.perception.backend import TTSBackend, load_backend


def test_backend_interface_exposes_contract_and_loader() -> None:
    assert TTSBackend is not None
    assert callable(load_backend)
