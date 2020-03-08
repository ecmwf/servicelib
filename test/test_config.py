# Copyright (c) ECMWF 2020.

from __future__ import absolute_import, unicode_literals

import pytest

from servicelib import config
from servicelib.compat import env_var


def test_value_from_env(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR", "42"))
    assert config.get("foo_bar") == "42"


def test_missing_key():
    with pytest.raises(Exception) as exc:
        config.get("foo")
    assert str(exc.value) == "No value for config variable `foo`"


def test_default_value():
    assert config.get("foo", default="42") == "42"


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR", "42"))
    assert config.get("foo_bar", default="43") == "42"


def test_config_file(servicelib_ini):
    assert config.get("worker_num_processes") == "10"
    assert config.get("worker_num_threads") == "1"
    assert config.get("inventory_class") == "default"
    assert config.get("registry_url") == "redis://some-host/12"
    assert config.get("registry_cache_ttl") == "5"


def test_config_file_overrides_default(servicelib_ini):
    assert config.get("worker_num_processes", default="42") == "10"


def test_env_overrides_config_file(servicelib_ini, monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_WORKER_NUM_PROCESSES", "42"))
    assert config.get("worker_num_processes") == "42"


def test_default_value_with_config_file(servicelib_ini):
    assert config.get("no_such_key", default="whatever") == "whatever"
