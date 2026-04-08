"""Tests for environment variable resolution in town YAML config loader."""
import os
import pytest

from app.config import resolve_env_vars


def test_simple_string_substitution(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "abc123")
    assert resolve_env_vars("${TOMTOM_API_KEY}") == "abc123"


def test_no_vars_passthrough():
    assert resolve_env_vars("no-vars-here") == "no-vars-here"


def test_dict_recursive_resolution(monkeypatch):
    monkeypatch.setenv("VAR", "resolved")
    result = resolve_env_vars({"key": "${VAR}"})
    assert result == {"key": "resolved"}


def test_list_recursive_resolution(monkeypatch):
    monkeypatch.setenv("VAR", "value")
    result = resolve_env_vars(["${VAR}", "plain"])
    assert result == ["value", "plain"]


def test_non_string_passthrough():
    assert resolve_env_vars(42) == 42
    assert resolve_env_vars(3.14) == 3.14
    assert resolve_env_vars(True) is True
    assert resolve_env_vars(None) is None


def test_mid_string_substitution(monkeypatch):
    monkeypatch.setenv("VAR", "middle")
    assert resolve_env_vars("prefix-${VAR}-suffix") == "prefix-middle-suffix"


def test_missing_env_var_raises_key_error():
    # Ensure the variable is not set
    os.environ.pop("DEFINITELY_NOT_SET_XYZ", None)
    with pytest.raises(KeyError) as exc_info:
        resolve_env_vars("${DEFINITELY_NOT_SET_XYZ}")
    assert "DEFINITELY_NOT_SET_XYZ" in str(exc_info.value)
