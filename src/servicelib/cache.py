# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import hashlib
import time

from functools import wraps

import memcache
import requests

from servicelib import config, logutils
from servicelib.compat import string_types
from servicelib import encoding as json


__all__ = [
    "cache_control",
    "instance",
]


IN_FLIGHT = "in-flight"


class cache_control(object):

    """Decorator that caches the result of service calls as JSON-encoded
    objects in `memcached`.

    """

    def __init__(self, time=0, result_is_url=False):
        self.ttl = time
        self.result_is_url = result_is_url
        self.cache = instance()
        self.cache_check_frequency = float(
            config.get("cache_check_frequency", default="0.1")
        )
        self.inflight_ttl = int(config.get("cache_inflight_ttl", default="60"))

    def __call__(self, f):
        @wraps(f)
        def wrapped_f(context, *args, **kwargs):
            if not context.request.kwargs.get("cache", True):
                self.annotate(context, status="off")
                return f(context, *args, **kwargs)

            with context.timer("cache") as timer:
                if context.name is not None:
                    name = context.name
                else:
                    name = f.func_name
                    assert name

                try:
                    request = (name, args, list(kwargs.items()))
                    request_encoded = json.dumps(request, sort_keys=True).encode(
                        "utf-8"
                    )
                    request_md5 = hashlib.md5(request_encoded).hexdigest()

                    status, response = self.state_loop(
                        context, request_md5, timer, f, args, kwargs
                    )
                except Exception as exc:
                    try:
                        log = context.log
                    except Exception:
                        log = logutils.get_logger(__name__)
                    log.warn(
                        "cache_control: Error handling request: %s", exc, exc_info=True
                    )
                    self.cache.delete(request_md5)
                    raise

                self.annotate(context, status, request_md5)
                return response

        return wrapped_f

    def state_loop(self, context, request_md5, timer, f, args, kwargs):
        state, response, status = self.process_initial(request_md5)

        while True:
            if state == "process_in_flight":
                state, response, status = self.process_in_flight(context, request_md5)

            elif state == "process_hit":
                state, response, status = self.process_hit(
                    context, request_md5, response
                )

            elif state == "process_miss":
                state, response, status = self.process_miss(
                    context, request_md5, timer, f, args, kwargs
                )

            elif state == "done":
                break

        return status, response

    def process_initial(self, request_md5):
        response = self.cache.get(request_md5)
        if response is None:
            return "process_miss", None, None

        if response == IN_FLIGHT:
            return "process_in_flight", None, None

        return "process_hit", response, None

    def process_in_flight(self, context, request_md5):
        # A request with the same hash is being processed right now by
        # some other worker.
        #
        # Wait until either that other request finishes (and return a
        # cache hit), or, if the other request vanishes (because it
        # has failed, for instance), return a cache miss.
        while True:
            time.sleep(self.cache_check_frequency)

            response = self.cache.get(request_md5)

            if response == IN_FLIGHT:
                continue

            if response is None:
                return "process_miss", None, None

            return "process_hit", response, None

    def process_hit(self, context, request_md5, response):
        response = json.loads(response)["result"]
        if valid_url(context, response):
            return "done", response, "hit"

        return "process_miss", None, None

    def process_miss(self, context, request_md5, timer, f, args, kwargs):
        # Let everybody know we're dealing with this request, so that
        # they don't rush to do it as well.
        #
        # Set the TTL of this entry to a reasonably low value, so that
        # others may retry it if we die while we're processing it.
        self.cache.set(request_md5, IN_FLIGHT, ttl=self.inflight_ttl)

        timer.stop()
        try:
            response = f(context, *args, **kwargs)
        finally:
            timer.start()

        response_json = json.dumps(
            {"result": response, "created": int(time.time()), "max_age": self.ttl,}
        )
        self.cache.set(request_md5, response_json, ttl=self.ttl)

        return "done", response, "miss"

    def annotate(self, context, status, request_md5=None):
        context.annotate("cache", status)
        if request_md5 is not None:
            context.annotate("cache_key", request_md5)
            context.annotate("cache_ttl", self.ttl)
        context.log = context.log.bind(cache=status)


class Cache(object):

    log = logutils.get_logger(__name__)

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value, ttl):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError

    def get_response(self, key):
        """Return the cached response object associated with the given key
        from the results cache, or `None` if no such response was found.

        """
        ret = self.get(key)
        if ret is None or ret == IN_FLIGHT:
            self.log.debug(
                "get_response(%s): Got `%s` from cache, retuning `None`", key, ret
            )
            return None

        try:
            ret = json.loads(ret)
        except Exception as exc:
            self.log.error(
                "Cannot decode JSON object <%s> for key '%s': %s",
                ret,
                key,
                exc,
                exc_info=True,
            )

            # There is no point in keeping this cached value if we cannot
            # decode it.
            self.delete(key)

            return

        self.log.debug("get_response(%s): Returning %s", key, ret)
        return ret


class MemcachedCache(Cache):
    def __init__(self):
        super(MemcachedCache, self).__init__
        memcached_addresses = config.get("cache_memcached_addresses").split()
        self.log.debug("Using memcached instances: %s", memcached_addresses)
        self._memcached = memcache.Client(memcached_addresses)

    def get(self, key):
        return self._memcached.get(key)

    def set(self, key, value, ttl):
        self._memcached.set(key, value, time=ttl, noreply=False)

    def delete(self, key):
        self._memcached.delete(key, noreply=False)

    def flush(self):
        self._memcached.flush_all()


class NoOpCache(Cache):

    log = logutils.get_logger(__name__)

    def get(self, key):
        return None

    def set(self, key, value, ttl):
        pass

    def delete(self, key):
        pass

    def flush(self):
        pass


_INSTANCE_MAP = {
    "memcached": MemcachedCache,
    "no-op": NoOpCache,
}


def instance():
    class_name = config.get("cache_class", default="no-op")
    try:
        ret = _INSTANCE_MAP[class_name]
    except KeyError:
        raise Exception("Invalid value for `cache_class`: {}".format(class_name))
    if isinstance(ret, type):
        _INSTANCE_MAP[class_name] = ret = ret()
    return ret


def valid_url(context, data):
    """Check whether all URL fields within `data` point to valid resources.

    """
    if data is None:
        return True

    if isinstance(data, (int, float, string_types)):
        return True

    if isinstance(data, list):
        for d in data:
            if not valid_url(context, d):
                return False
        return True

    # If we're here, we assume `data` is a dict.
    if "location" not in data:
        # Check in the dict values for `{url: xxx}` objects.
        for v in data.values():
            if not valid_url(context, v):
                return False
        return True

    url = None
    try:
        url = data["location"]
        res = requests.head(url)
        res.raise_for_status()
        if "contentLength" in data:
            cached_length = int(data["contentLength"])
            remote_length = int(res.headers["content-length"])
            context.log.debug(
                "valid_url(%s): Checking content length (cached: %s, actual: %s)",
                url,
                cached_length,
                remote_length,
            )
            if cached_length != remote_length:
                raise Exception(
                    "Invalid url {}, size mismatch: cache: {}, actual: {}".format(
                        url, cached_length, remote_length
                    )
                )
    except Exception as exc:
        context.log.warn("valid_url(%s): Error: %s", url, exc, exc_info=True)
        return False

    return True


# def memcached_client():
#     return memcache.Client(default.lookup("memcached_daemons", group="services"))


# def flush():
#     """Clears all cached results.

#     """
#     memcached_client().flush_all()
