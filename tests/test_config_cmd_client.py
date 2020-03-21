# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import json

import pytest
import yaml

from servicelib.compat import PY2, env_var, open


def test_get(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42, "bar": {"baz": 42.0}}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))

    r = script_runner.run("servicelib-config-client", "get", "foo")
    assert r.success
    assert json.loads(r.stdout) == 42
    assert r.stderr == ""

    r = script_runner.run("servicelib-config-client", "get", "bar")
    assert r.success
    assert json.loads(r.stdout) == {"baz": 42.0}
    assert r.stderr == ""

    r = script_runner.run("servicelib-config-client", "get", "bar.baz")
    assert r.success
    assert json.loads(r.stdout) == 42.0
    assert r.stderr == ""


def test_get_invalid_key(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42, "bar": {"baz": 42.0}}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))

    r = script_runner.run("servicelib-config-client", "get", "no-such-key")
    assert not r.success
    assert r.stdout == ""
    assert r.stderr.startswith("No config value for `no-such-key`")

    r = script_runner.run("servicelib-config-client", "get", "bar.no-such-key")
    assert not r.success
    assert r.stderr.startswith("No config value for `bar.no-such-key`")


def test_dump(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42, "bar": {"baz": 42.0}}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))

    r = script_runner.run("servicelib-config-client", "dump")
    assert r.success
    assert json.loads(r.stdout) == {"foo": 42, "bar": {"baz": 42.0}}
    assert r.stderr == ""


def test_set(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42, "bar": {"baz": 42.0}}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))

    r = script_runner.run("servicelib-config-client", "set", "foo", "43")
    assert r.success
    assert r.stdout == ""
    assert r.stderr == ""
    assert config_server.client.get("foo") == 43

    r = script_runner.run(
        "servicelib-config-client", "set", "moo", '[true, false, {"bzz": 43.0}]'
    )
    assert r.success
    assert r.stdout == ""
    assert r.stderr == ""
    assert config_server.client.get("moo") == [True, False, {"bzz": 43.0}]


def test_set_invalid_values(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))

    r = script_runner.run(
        "servicelib-config-client", "set", "foo", "this-is-not-valid-json"
    )
    assert not r.success
    assert r.stdout == ""
    assert r.stderr == "Invalid JSON: <this-is-not-valid-json>\n"
    assert config_server.client.get("foo") == 42

    r = script_runner.run(
        "servicelib-config-client", "set", "foo", '"this-is-valid-json"'
    )
    assert r.success
    assert r.stdout == ""
    assert r.stderr == ""
    assert config_server.client.get("foo") == "this-is-valid-json"


def test_delete(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42, "bar": {"baz": 42.0}}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))
    assert config_server.client.get("foo") == 42

    r = script_runner.run("servicelib-config-client", "delete", "foo")
    assert r.success
    assert r.stdout == ""
    assert r.stderr == ""
    with pytest.raises(Exception) as exc:
        config_server.client.get("foo")
    assert str(exc.value).startswith("No config value for `foo`")

    r = script_runner.run("servicelib-config-client", "delete", "bar.baz")
    assert r.success
    assert r.stdout == ""
    assert r.stderr == ""
    assert config_server.client.dump() == {"bar": {}}


def test_delete_invalid_key(script_runner, config_server, monkeypatch):
    config_server.initial_config = {"foo": 42}
    config_server.start()
    monkeypatch.setenv(*env_var("SERVICELIB_CONFIG_URL", config_server.client.url))

    r = script_runner.run("servicelib-config-client", "delete", "no-such-key")
    assert not r.success
    assert r.stdout == ""
    assert r.stderr == "no-such-key: Not found\n"


_EXPECTED_DIFF = """
Only in {config_a}: bzzz
--- bar.bazz
+++ bar.bazz
@@ -1,4 +1,4 @@
 [
- true,
- false
+ false,
+ true
 ]

--- bar.boo
+++ bar.boo
@@ -6,6 +6,8 @@
  [
   "one",
   "nested",
-  "list"
+  "list",
+  "but",
+  "longer"
  ]
 ]

Only in {config_b}: bar.moo
--- foo
+++ foo
@@ -1 +1 @@
-24
+42
"""


@pytest.mark.skipif(PY2, reason="output of `diff` not quite the same")
def test_diff(tmp_path, script_runner):
    config_a = tmp_path / "config-a.yaml"
    with open(config_a, "wb") as f:
        yaml.safe_dump(
            {
                "foo": 24,
                "bzzz": 17,
                "bar": {
                    "bazz": [True, False,],
                    "boo": [
                        "some-string",
                        {"a-float": 42.0},
                        ["one", "nested", "list"],
                    ],
                },
                "boo": True,
            },
            f,
            encoding="utf-8",
            allow_unicode=True,
        )

    config_b = tmp_path / "config-b.yaml"
    with open(config_b, "wb") as f:
        yaml.safe_dump(
            {
                "bar": {
                    "bazz": [False, True,],
                    "boo": [
                        "some-string",
                        {"a-float": 42.0},
                        ["one", "nested", "list", "but", "longer"],
                    ],
                    "moo": 24,
                },
                "foo": 42,
                "boo": True,
            },
            f,
            encoding="utf-8",
            allow_unicode=True,
        )

    expected = _EXPECTED_DIFF.format(
        config_a=config_a.as_uri(), config_b=config_b.as_uri()
    ).strip()
    r = script_runner.run(
        "servicelib-config-client", "diff", config_a.as_uri(), config_b.as_uri()
    )
    assert r.success
    assert r.stdout.strip() == expected
    assert r.stderr == ""
