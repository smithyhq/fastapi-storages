import pytest

from fastapi_storages.utils import lookup_env


def test_lookup_env_string_default_missing(monkeypatch):
    monkeypatch.delenv("SOME_VAR", raising=False)
    assert lookup_env("SOME_VAR") == ""


def test_lookup_env_string_set(monkeypatch):
    monkeypatch.setenv("SOME_VAR", "hello")
    assert lookup_env("SOME_VAR") == "hello"


def test_lookup_env_bool_default_true_missing(monkeypatch):
    monkeypatch.delenv("SOME_BOOL", raising=False)
    assert lookup_env("SOME_BOOL", True) is True


def test_lookup_env_bool_default_false_missing(monkeypatch):
    monkeypatch.delenv("SOME_BOOL", raising=False)
    assert lookup_env("SOME_BOOL", False) is False


@pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "Yes", "YES"])
def test_lookup_env_bool_truthy(monkeypatch, value):
    monkeypatch.setenv("SOME_BOOL", value)
    assert lookup_env("SOME_BOOL", False) is True


@pytest.mark.parametrize("value", ["false", "False", "0", "no", ""])
def test_lookup_env_bool_falsy(monkeypatch, value):
    monkeypatch.setenv("SOME_BOOL", value)
    assert lookup_env("SOME_BOOL", True) is False
