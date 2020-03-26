# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import pytest

from servicelib import config
from servicelib.compat import env_var
from servicelib.config import client as config_client


def test_value_from_env(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_INT", "42"))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_FLOAT", "42.0"))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_TRUE1", "True"))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_TRUE2", "true"))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_FALSE1", "False"))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_FALSE2", "False"))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_LIST", '["one", {"two": 3}]'))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_DICT", '{"two": 3}'))
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR_PEPE", "just a string"))
    assert config.get("foo.bar_int") == 42
    assert config.get("foo.bar_float") == 42.0
    assert config.get("foo.bar_true1")
    assert config.get("foo.bar_true2")
    assert not config.get("foo.bar_false1")
    assert not config.get("foo.bar_false2")
    assert config.get("foo.bar_list") == ["one", {"two": 3}]
    assert config.get("foo.bar_dict") == {"two": 3}
    assert config.get("foo.bar_pepe") == "just a string"


def test_missing_key(servicelib_yaml):
    with pytest.raises(Exception) as exc:
        config.get("foo")
    assert str(exc.value).startswith("No config value for `foo`")


def test_default_value(servicelib_yaml):
    assert config.get("foo", default="42") == "42"


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_FOO_BAR", "42"))
    assert config.get("foo.bar", default="43") == 42


def test_config_file(servicelib_yaml):
    assert config.get("worker.num_processes") == 10
    assert config.get("worker.num_threads") == 1
    assert config.get("inventory.class") == "default"
    assert config.get("registry.url") == "redis://some-host/12"
    assert config.get("registry.cache_ttl") == 5


def test_config_file_overrides_default(servicelib_yaml):
    assert config.get("worker.num_processes", default="42") == 10


def test_env_overrides_config_file(servicelib_yaml, monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_WORKER_NUM_PROCESSES", "42"))
    assert config.get("worker.num_processes") == 42


def test_default_value_with_config_file(servicelib_yaml):
    assert config.get("no.such_key", default="whatever") == "whatever"


def test_delete_entry_from_config_file(servicelib_yaml):
    assert config_client.instance().get("worker.num_processes") == 10
    assert config.get("worker.num_processes") == 10

    with pytest.raises(Exception) as exc:
        config_client.instance().delete("worker.num_processes")

    assert str(exc.value) == "File-based config is read-only"
    assert config_client.instance().get("worker.num_processes") == 10
    assert config.get("worker.num_processes") == 10


def test_set_entry_from_config_file(servicelib_yaml):
    assert config_client.instance().get("worker.num_processes") == 10
    assert config.get("worker.num_processes") == 10

    with pytest.raises(Exception) as exc:
        config_client.instance().set("worker.num_processes", 42)

    assert str(exc.value) == "File-based config is read-only"
    assert config_client.instance().get("worker.num_processes") == 10
    assert config.get("worker.num_processes") == 10


def test_unsupported_source():
    with pytest.raises(ValueError) as exc:
        config_client.instance("ftp://wherever")
    assert str(exc.value).startswith("Unsupported URL scheme")


@pytest.mark.parametrize(
    "instance,expected",
    [
        (
            config_client.instance("file:///some/path"),
            "FileConfigClient(url=file:///some/path)",
        ),
        (
            config_client.instance("http://localhost/blah"),
            "HTTPConfigClient(url=http://localhost/blah)",
        ),
    ],
)
def test_repr(instance, expected):
    assert repr(instance) == expected
