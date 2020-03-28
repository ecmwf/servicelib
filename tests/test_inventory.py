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
import os

import pytest
import yaml

from servicelib import inventory
from servicelib.compat import env_var, open
from servicelib.service import ServiceInstance


@pytest.fixture
def default_inventory(monkeypatch):
    samples_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "samples")
    )
    monkeypatch.setenv(*env_var("SERVICELIB_INVENTORY_CLASS", "default"))
    monkeypatch.setenv(*env_var("SERVICELIB_WORKER_SERVICES_DIR", samples_dir))
    monkeypatch.syspath_prepend(samples_dir)
    return inventory.instance()


def test_service_modules(default_inventory):
    mods = default_inventory.service_modules()
    assert mods


def test_load_services(default_inventory):
    services = default_inventory.load_services()
    assert services
    assert all(isinstance(i, ServiceInstance) for i in services.values())


def test_invalid_inventory_factory(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_INVENTORY_CLASS", "no-such-impl"))
    with pytest.raises(Exception) as exc:
        inventory.instance()
    assert str(exc.value) == "Invalid value for `inventory.class`: no-such-impl"


def test_legacy_inventory(legacy_workers):
    w = legacy_workers.start("simple")
    res = w.http_post(
        "/services/dump_request",
        data=json.dumps(["foo", 42]),
        headers={"content-type": "application/json"},
    )
    assert res["args"] == ["foo", 42]

    with pytest.raises(Exception) as exc:
        w.http_post(
            "/services/proxy",
            data=json.dumps(["dump_request", "foo", 42]),
            headers={"content-type": "application/json"},
        )
    assert "404" in str(exc.value)

    w = legacy_workers.start("proxy")
    res = w.http_post(
        "/services/proxy",
        data=json.dumps(["dump_request", "foo", 42]),
        headers={"content-type": "application/json"},
    )
    assert res["args"] == ["foo", 42]

    with pytest.raises(Exception) as exc:
        w.http_post(
            "/services/hello",
            data=json.dumps(["world"]),
            headers={"content-type": "application/json"},
        )
    assert "404" in str(exc.value)
    w = legacy_workers.start("other")
    res = w.http_post(
        "/services/hello",
        data=json.dumps(["world"]),
        headers={"content-type": "application/json"},
    )
    assert res == "Hello, world!"


def test_change_runtime_config_in_legacy_inventory(
    legacy_workers, monkeypatch, tmp_path
):
    w = legacy_workers.start("other")
    res = w.http_post(
        "/services/dump_config",
        data=json.dumps([]),
        headers={"content-type": "application/json"},
    )
    assert "foo" not in res
    legacy_workers.stop("other")

    runtime_config = {"foo": 42}
    servicelib_yaml = tmp_path / "new-servicelib.yaml"
    with open(servicelib_yaml, "wb") as f:
        yaml.safe_dump(runtime_config, f, encoding="utf-8", allow_unicode=True)
    monkeypatch.setenv(
        *env_var("SERVICELIB_INVENTORY_RUNTIME_CONFIG_URL", servicelib_yaml.as_uri())
    )

    w = legacy_workers.start("other")
    res = w.http_post(
        "/services/dump_config",
        data=json.dumps([]),
        headers={"content-type": "application/json"},
    )
    assert res == {"foo": 42}
