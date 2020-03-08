# Copyright (c) ECMWF 2020

"""Services registry."""

from __future__ import absolute_import, unicode_literals

import socket
import threading
import time

import redis

from servicelib import config, logutils
from servicelib.compat import urlparse


__all__ = [
    "register_services",
    "service_url",
    "services_by_name",
    "services_by_netloc",
    "unregister_services",
]


class RedisPool(object):

    log = logutils.get_logger(__name__)

    def __init__(self):
        self._pool = None
        self._lock = threading.RLock()

    @property
    def pool(self):
        with self._lock:
            if self._pool is None:
                url = config.get("registry_url")
                self._pool = redis.ConnectionPool.from_url(url)
                self.log.debug("Initialized Redis connection pool for URL %s", url)
        return self._pool

    def connection(self):
        return redis.Redis(connection_pool=self.pool)


_redis_pool = RedisPool()

_redis_key_prefix = "servicelib.url."


def redis_key(service_name):
    return "{}{}".format(_redis_key_prefix, service_name)


LOG = logutils.get_logger(__name__)


def register_services(services):
    p = _redis_pool.connection().pipeline()
    for (name, url) in services:
        k = redis_key(name)
        LOG.info("Registering service %s at %s", name, url)
        p.sadd(k, url)
    p.execute()


def unregister_services(services):
    p = _redis_pool.connection().pipeline()
    for (name, url) in services:
        k = redis_key(name)
        LOG.info("Unregistering service %s at %s", name, url)
        p.srem(k, url)
    p.execute()


HOSTNAME = socket.getfqdn()


class Cache(object):
    def __init__(self, ttl):
        self.ttl = ttl
        self._data = {}

    def get(self, k):
        v, expires = self._data[k]
        now = time.time()
        if now > expires:
            try:
                del self._data[k]
            except KeyError:
                pass
            raise KeyError(k)
        return v

    def put(self, k, v):
        self._data[k] = (v, time.time() + self.ttl)


_CACHE = Cache(int(config.get("registry_cache_ttl", default=5)))


def service_url(name, local_only=False):
    # TODO: Cache results.
    c = _redis_pool.connection()
    k = redis_key(name)

    url = None
    if local_only:
        for parsed, unparsed in [(urlparse(u), u) for u in c.smembers(k)]:
            if parsed.netloc.split(":")[0] == HOSTNAME:
                url = unparsed
                break
    else:
        url = c.srandmember(k)

    if url is None:
        raise Exception(
            "No URL for service {} (local-only: {})".format(name, local_only)
        )
    return url


def services_by_name():
    ret = {}
    c = _redis_pool.connection()
    cur = 0
    while True:
        cur, keys = c.scan(cur)
        if cur == 0:
            break
        for k in keys:
            if k.startswith(_redis_key_prefix):
                ret.setdefault(k[len(_redis_key_prefix) :], set())
    for k, urls in ret.items():
        for url in c.smembers(redis_key(k)):
            urls.add(url)
    return ret


def services_by_netloc():
    ret = {}
    for service, urls in services_by_name().items():
        for url in urls:
            ret.setdefault(urlparse(url).netloc, set()).add(service)
    return ret
