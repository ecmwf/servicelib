# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

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


def test_invalid_iventory_factory(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_INVENTORY_CLASS", "no-such-impl"))
    with pytest.raises(Exception) as exc:
        inventory.instance()
    assert str(exc.value) == "Invalid value for `inventory_class`: no-such-impl"
