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

from servicelib.compat import env_var
from servicelib import registry


@pytest.fixture
def redis_registry(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_REGISTRY_URL", "redis://localhost/0"))
    r = registry.RedisRegistry()
    try:
        yield r
    finally:
        services_by_name = r.services_by_name()
        service_urls = []
        for name, urls in services_by_name.items():
            service_urls.extend((name, url) for url in urls)
        r.unregister(service_urls)


def test_register(redis_registry):
    redis_registry.register(
        [
            ("foo", "http://somewhere/services/foo"),
            ("foo", "http://somewhere-else/services/foo"),
            ("bar", "http://somewhere/services/bar"),
        ]
    )

    assert redis_registry.service_url("foo") in {
        "http://somewhere/services/foo",
        "http://somewhere-else/services/foo",
    }
    assert redis_registry.service_url("bar") == "http://somewhere/services/bar"


def test_url_for_unknown_service(redis_registry):
    with pytest.raises(Exception) as exc:
        redis_registry.service_url("no-such-service")
    assert str(exc.value) == "No URL for service no-such-service"


def test_invalid_registry_factory(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_REGISTRY_CLASS", "no-such-impl"))
    with pytest.raises(Exception) as exc:
        registry.instance()
    assert str(exc.value) == "Invalid value for `registry.class`: no-such-impl"
