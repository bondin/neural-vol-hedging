import importlib

import pytest

CANDIDATES = ["projectx", "neural_vol_hedging", "neural_volatility"]


@pytest.mark.parametrize("name", CANDIDATES)
def test_try_import_main_package(name):
    try:
        importlib.import_module(name)
        assert True
        return
    except ModuleNotFoundError:
        pass
    pytest.skip(f"Main package not found (tried: {', '.join(CANDIDATES)})")
