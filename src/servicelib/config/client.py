# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import copy
import json
import os
import threading
import time

import requests
import yaml

from servicelib import logutils
from servicelib.compat import urlparse

from .types import ConfigDict


__all__ = ["get"]


NO_DEFAULT = object()

LOG = logutils.get_logger(__name__)


DEFAULT_SETTINGS_POLL_INTERVAL = 10


class ConfigClient(object):

    """A caching client for the config source."""

    log = logutils.get_logger(__name__)

    def __init__(
        self, url, group=None, name=None, poll_interval=DEFAULT_SETTINGS_POLL_INTERVAL,
    ):
        """Constructor.

        This client will talk to the config source at `url`.

        Arguments `group` and `name` are used to build the prefix for key
        searches. When a user wants to retrieve the value of setting
        `foo`, the following keys are looked up in his order:

            1. `<group>.<name>.foo`
            2. `<group>.foo`
            3. `foo`

        This client will poll the settings server every `poll_interval`
        seconds, in order to get changes to the values stored in the config
        source.

        """
        self.url = url
        self.group = group
        self.name = name
        self.__values = None
        self.__old_values = None

        self.poll_interval = poll_interval
        self._pid = None
        self._lock = threading.Lock()
        self._poll_thread_active = True

    def lookup(self, key, default=NO_DEFAULT, exact=False, name=None, group=None):
        """Get the value associated with `key`.

        If `exact` is false, the following keys will be looked up:

            1. `<group>.<name>.<key>`
            2. `<group>.<key>`
            3. `<key>`

        Othewise (if `exact` is true), `key` will be looked up.

        If no value is found, and `default` is given, the value of `default` is
        returned. Otherwise `KeyError` is raised.

        """
        self._ensure_poller_thread()

        if exact or group is None:
            keys = [key]
        else:
            if name:
                keys = [".".join([group, name, key]), ".".join([group, key]), key]
            else:
                keys = [".".join([group, key]), key]

        for k in keys:
            env_k = env_var(k)
            try:
                ret = os.environ[env_k].strip()
            except KeyError:
                try:
                    self.log.debug("config(%s): Key %s not in environment", key, env_k)
                except Exception:
                    pass
            else:
                ret_lower = ret.lower()
                if ret_lower == "true":
                    ret = True
                elif ret_lower == "false":
                    ret = False
                elif ret[0] in {"{", "["}:
                    try:
                        ret = json.loads(ret)
                    except Exception:
                        pass
                else:
                    try:
                        ret = int(ret)
                    except ValueError:
                        try:
                            ret = float(ret)
                        except ValueError:
                            pass

                self.log.debug(
                    "config(%s): Returning %s (from environment %s)", key, ret, env_k
                )
                return ret

            exc_fetching_source = None
            try:
                ret = self._values.get(k)
                try:
                    self.log.debug(
                        "config(%s): Returning %s (from config %s)", key, ret, self.url,
                    )
                except Exception:
                    pass
                return ret
            except KeyError:
                pass
            except Exception as exc:
                self.log.warn(
                    "config(%s): Error fetching config key %s from %s: %s",
                    key,
                    k,
                    self.url,
                    exc,
                    exc_info=True,
                )
                exc_fetching_source = exc

        if default is not NO_DEFAULT:
            self.log.debug("config(%s): Returning %s (from default)", key, default)
            return default

        if exc_fetching_source is not None:
            raise exc_fetching_source

        raise Exception(
            "No config value for `{}` (tried {}, exact={}, group={})".format(
                key, keys, exact, group,
            )
        )

    def get(self, key, default=NO_DEFAULT, exact=False):
        return self.lookup(
            key, default=default, exact=exact, name=self.name, group=self.group
        )

    def set(self, key, value):
        """Sets the given setting.

        `key` is expected to have the following form:

            foo.bar.baz

        """
        if key in {"", None}:
            raise ValueError("Invalid key `{}`".format(key))

        self._key_set(key, value)

        # Ensure we get updated values on next read.
        self.clear()

    def dump(self):
        """Returns a dictionary containing all settings.

        The returned value is JSON-serialisable.

        """
        self._ensure_poller_thread()
        return self._values.as_dict()

    def delete(self, key):
        """Removes the given setting.

        `key` is expected to have the following form:

            foo.bar.baz

        Raises `KeyError` if `key` does not exist.

        """
        self._key_deleted(key)

        # Ensure we get updated values on next read.
        self.clear()

    def clear(self):
        """Clears cached settings.

        """
        self.__values = None

    refresh = clear

    def url():
        """Normilized URL of the config source.

        """

        def fget(self):
            return self._url

        def fset(self, url):
            self._url = str(url.rstrip("/"))

        return locals()

    url = property(**url())

    def _ensure_poller_thread(self):
        try:
            with self._lock:
                pid = os.getpid()
                if self._pid != pid:
                    t = threading.Thread(target=self._poll)
                    t.setDaemon(True)
                    t.start()
                    self._pid = pid
                    # Ensure the poller thread has run at least once
                    # before returning from this function (by doing
                    # explicitly what the poller thread does).
                    self._poll(only_once=True)
        except Exception as exc:
            self.log.warn(
                "Call to _ensure_poller_thread() failed: %s", exc, exc_info=True
            )

    def _poll(self, only_once=False):
        while True:
            if self._poll_thread_active:
                self.clear()
            if only_once:
                return
            time.sleep(self.poll_interval)

    @property
    def _values(self):
        """Returns all settings, retrieving them from the settings source if
        necessary.

        """
        v = copy.deepcopy(self.__values)
        if v is None:
            try:
                values = self._read_values()
                self.__old_values = values
            except Exception as exc:
                if self.__old_values is not None:
                    self.log.warn(
                        "Cannot fetch config from %s, reusing previous values: %s",
                        self.url,
                        exc,
                        exc_info=True,
                    )
                    values = self.__old_values
                else:
                    raise

            self.__values = v = ConfigDict(values)

        return v

    def _read_values(self):
        raise NotImplementedError("Implement in subclass!")

    def __repr__(self):
        return "{}(url={})".format(self.__class__.__name__, self.url)


class FileConfigClient(ConfigClient):
    def __init__(self, url, *args, **kwargs):
        super(FileConfigClient, self).__init__(url, *args, **kwargs)
        self._fname = urlparse(self.url).path

    def _read_values(self):
        with open(self._fname, "rb") as f:
            return yaml.safe_load(f)

    def _key_set(self, key, value):
        raise Exception("File-based config is read-only")

    def _key_deleted(self, key):
        raise Exception("File-based config is read-only")


class HTTPConfigClient(ConfigClient):
    def __init__(self, url, *args, **kwargs):
        super(HTTPConfigClient, self).__init__(url, *args, **kwargs)

    def _read_values(self):
        r = requests.get(self.url, proxies={"http": None, "https": None})
        r.raise_for_status()
        ret = yaml.safe_load(r.content)
        self.log.debug("_read_values(%s): Returning: %s", self.url, ret)
        return ret

    def _key_set(self, key, value):
        url = self._key_to_url(self.url, key)
        headers = {
            "Content-Type": "application/json",
        }
        r = requests.post(
            url,
            data=json.dumps(value),
            headers=headers,
            proxies={"http": None, "https": None},
        )
        if r.status_code != 200:
            raise Exception(r.json())

    def _key_deleted(self, key):
        url = self._key_to_url(self.url, key)
        r = requests.delete(url, proxies={"http": None, "https": None})

        if r.status_code == 404:
            raise KeyError(key)
        if r.status_code != 200:
            raise Exception(r.json())

    def _key_to_url(self, base_url, key):
        """Returns the URL for a given key.

        ``key`` is expected to be of the form::

            foo.bar.baz

        """
        bits = [base_url]
        bits.extend(b for b in key.split(".") if b)
        return "/".join(bits)


def env_var(key):
    return "SERVICELIB_{}".format(key.replace(".", "_").upper())


_instances = {}


def instance(url=None, group=None, name=None):
    """Factory for config clients.

    Returns a config client reading values from the URL taken from the
    environment variable `SERVICELIB_CONFIG_URL`. If that environment variable
    is not set, the hard-coded value `http://localhost:9999/settings/` will be
    used.

    """

    if url is None:
        url = os.environ.get("SERVICELIB_CONFIG_URL", "http://localhost:9999/settings/")
    try:
        return _instances[url]
    except KeyError:
        scheme = urlparse(url).scheme

        if scheme in {"http", "https"}:
            ret = HTTPConfigClient(url, group=group, name=name)
        elif scheme == "file":
            ret = FileConfigClient(url, group=group, name=name)
        else:
            raise ValueError("Unsupported URL scheme in {}".format(url))
        _instances[url] = ret
        return ret


def get(*args, **kwargs):
    return instance().get(*args, **kwargs)
