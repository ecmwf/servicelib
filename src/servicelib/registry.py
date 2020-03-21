# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Services registry."""

from __future__ import absolute_import, unicode_literals

import socket
import threading

# import time

import redis

from servicelib import config, logutils

# from servicelib.compat import urlparse


__all__ = [
    "Registry",
    "instance",
]


class Registry(object):
    def register(self, services):
        raise NotImplementedError

    def unregister(self, services):
        raise NotImplementedError

    # def service_url(self, name, local_only=False):
    #     raise NotImplementedError

    def service_url(self, name):
        raise NotImplementedError


class NoOpRegistry(Registry):
    def register(self, services):
        pass

    def unregister(self, services):
        pass


class RedisPool(object):

    log = logutils.get_logger(__name__)

    def __init__(self):
        self._pool = None
        self._lock = threading.RLock()

    @property
    def pool(self):
        with self._lock:
            if self._pool is None:
                url = config.get("registry.url")
                self._pool = redis.ConnectionPool.from_url(url)
                self.log.debug("Initialized Redis connection pool for URL %s", url)
        return self._pool

    def connection(self):
        return redis.Redis(connection_pool=self.pool)


HOSTNAME = socket.getfqdn()


class RedisRegistry(Registry):

    _redis_key_prefix = "servicelib.url.".encode("utf-8")

    log = logutils.get_logger(__name__)

    def __init__(self):
        super(RedisRegistry, self).__init__()
        self._pool = RedisPool()

    def register(self, services):
        p = self._pool.connection().pipeline()
        for (name, url) in services:
            k = self.redis_key(name)
            self.log.info("Registering service %s at %s", name, url)
            p.sadd(k, url.encode("utf-8"))
        p.execute()

    def unregister(self, services):
        p = self._pool.connection().pipeline()
        for (name, url) in services:
            k = self.redis_key(name)
            self.log.info("Unregistering service %s at %s", name, url)
            p.srem(k, url)
        p.execute()

    # def service_url(self, name, local_only=False):
    def service_url(self, name):
        # TODO: Cache results.
        c = self._pool.connection()
        k = self.redis_key(name)

        # url = None
        # if local_only:
        #     for parsed, unparsed in [(urlparse(u), u) for u in c.smembers(k)]:
        #         if parsed.netloc.split(":")[0] == HOSTNAME:
        #             url = unparsed
        #             break
        # else:
        #     url = c.srandmember(k)
        url = c.srandmember(k)

        if url is None:
            # raise Exception(
            #     "No URL for service {} (local-only: {})".format(name, local_only)
            # )
            raise Exception("No URL for service {}".format(name))

        return url.decode("utf-8")

    def services_by_name(self):
        ret = {}
        c = self._pool.connection()
        cur = 0
        while True:
            cur, keys = c.scan(cur)
            self.log.debug("services_by_name(): keys: %s", keys)
            for k in keys:
                self.log.debug("services_by_name(): %s ?", k)
                if k.startswith(self._redis_key_prefix):
                    self.log.debug("services_by_name(): Yep: %s", k)
                    ret.setdefault(
                        k[len(self._redis_key_prefix) :].decode("utf-8"), set()
                    )
            if cur == 0:
                break
        self.log.debug("services_by_name(): ret: %s", ret)
        for k, urls in ret.items():
            for url in c.smembers(self.redis_key(k)):
                urls.add(url.decode("utf-8"))
        return ret

    def redis_key(self, service_name):
        return self._redis_key_prefix + service_name.encode("utf-8")


_INSTANCE_MAP = {
    "no-op": NoOpRegistry,
    "redis": RedisRegistry,
}


def instance():
    class_name = config.get("registry.class", default="no-op")
    try:
        ret = _INSTANCE_MAP[class_name]
    except KeyError:
        raise Exception("Invalid value for `registry.class`: {}".format(class_name))
    if isinstance(ret, type):
        _INSTANCE_MAP[class_name] = ret = ret()
    return ret


LOG = logutils.get_logger(__name__)


# class Cache(object):
#     def __init__(self, ttl):
#         self.ttl = ttl
#         self._data = {}

#     def get(self, k):
#         v, expires = self._data[k]
#         now = time.time()
#         if now > expires:
#             try:
#                 del self._data[k]
#             except KeyError:
#                 pass
#             raise KeyError(k)
#         return v

#     def put(self, k, v):
#         self._data[k] = (v, time.time() + self.ttl)


# _CACHE = Cache(int(config.get("registry.cache_ttl", default=5)))


# def services_by_netloc():
#     ret = {}
#     for service, urls in services_by_name().items():
#         for url in urls:
#             ret.setdefault(urlparse(url).netloc, set()).add(service)
#     return ret
