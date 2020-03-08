# Copyright (c) ECMWF 2020

from __future__ import absolute_import, unicode_literals

import os

import pytest

from servicelib import inventory
from servicelib.compat import env_var
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
