# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

"""Unit tests for cache support."""

import time

import pytest

from servicelib.cache import instance
from servicelib.compat import env_var


def cache_key(meta):
    try:
        k = meta.as_dict()["kids"][-1]
        return k["cache_key"]
    except (IndexError, KeyError):
        pass


def cache_status(meta):
    try:
        k = meta.as_dict()["kids"][-1]
        return k["cache"]
    except (IndexError, KeyError):
        pass


def cache_ttl(meta):
    try:
        k = meta.as_dict()["kids"][-1]
        return k["cache_ttl"]
    except (IndexError, KeyError):
        pass


@pytest.fixture(scope="function")
def req():
    return {
        "name": "mslp",
        "base_time": "1975-01-14 00:00",
    }


@pytest.fixture(scope="function")
def cache(request, monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_CACHE_CLASS", "memcached"))
    monkeypatch.setenv(
        *env_var("SERVICELIB_CACHE_MEMCACHED_ADDRESSES", "localhost:11211")
    )
    c = instance()
    c.flush()
    try:
        yield c
    finally:
        c.flush()


def test_cache(broker, cache, req):
    """Request caching works.

    """
    res, meta = broker.execute("mock_preload", req, cache=True).wait()
    assert cache_status(meta) == "miss"

    new_res, meta = broker.execute("mock_preload", req, cache=True).wait()
    assert cache_status(meta) == "hit"
    assert new_res == res

    req["another_field"] = 42
    meta = broker.execute("mock_preload", req, cache=True).metadata
    assert cache_status(meta) == "miss"


def test_ttl(broker, cache, req):
    """Cached requests expire.

    """
    meta = broker.execute("mock_preload", req, cache=True).metadata
    assert cache_status(meta) == "miss"

    meta = broker.execute("mock_preload", req, cache=True).metadata
    assert cache_status(meta) == "hit"

    ttl = cache_ttl(meta)
    assert ttl > 0

    time.sleep(ttl + 0.1)
    meta = broker.execute("mock_preload", req, cache=True).metadata
    assert cache_status(meta) == "miss"


def test_inflight_requests(broker, cache, req):
    """Not all simultaneous requests to a cached service are executed.

    """
    req = dict(req)
    req["delay"] = 2
    results = []
    for _ in range(10):
        results.append(broker.execute("mock_preload_long_ttl", req, cache=True))

    status = [cache_status(r.metadata) for r in results]
    hits = [s for s in status if s == "hit"]
    misses = [s for s in status if s == "miss"]
    assert len(hits) > len(misses)


def test_bypass_cache(broker, cache, req):
    """Cache might be bypassed.

    """
    meta = broker.execute("mock_preload", req, cache=False).metadata
    assert cache_status(meta) == "off"
    assert cache_key(meta) is None

    meta = broker.execute("mock_preload", req, cache=True).metadata
    assert cache_status(meta) in ("hit", "miss")


def test_get_response(broker, cache, req):
    meta = broker.execute("mock_preload", req, cache=True).metadata
    assert cache_status(meta) == "miss"

    key = cache_key(meta)
    assert key is not None, meta.as_dict()
    res = cache.get_response(key)
    assert res is not None

    cache.flush()
    res = cache.get_response(key)
    assert res is None


# def test_memcache_ttl(cache):
#     """The ttl parameter for Memcached stored values is honoured.

#     """
#     cache.flush()

#     c = cache.memcached_client()
#     ttl = 1.0
#     k = "foo"
#     v = "42"

#     c.set(k, v, time=ttl)
#     assert c.get(k) == v

#     time.sleep(ttl + 0.1)
#     assert c.get(k) is None


# from newrelic.common.object_names import callable_name


# @cache_control(time=42, result_is_url=True)
# def sample_service():
#     """A sample service."""


# def test_cache_decorator_preserves_wrapped_info():
#     """Decorator `cache_control` preserves basic metadata of wrapped
#     service.

#     """
#     assert callable_name(sample_service) == "services.lib.test_cache:sample_service"


def test_invalid_cache_factory(monkeypatch):
    monkeypatch.setenv(*env_var("SERVICELIB_CACHE_CLASS", "no-such-impl"))
    with pytest.raises(Exception) as exc:
        instance()
    assert str(exc.value) == "Invalid value for `cache_class`: no-such-impl"
