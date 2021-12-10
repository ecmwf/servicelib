# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
import threading

import requests

from servicelib import config, core, errors, logutils, registry
from servicelib.compat import string_types
from servicelib.context import Context
from servicelib.context.client import ClientContext
from servicelib.timer import Timer


__all__ = [
    "Broker",
    "Result",
    "check_args",
]


def check_args(a, name=""):
    if a is None:
        pass
    elif isinstance(a, string_types):
        pass
    elif isinstance(a, (int, float)):
        pass
    elif isinstance(a, (list, tuple)):
        for x in a:
            check_args(x, name)
    elif isinstance(a, dict):
        for k, v in a.items():
            check_args(k, name)
            check_args(v, name)
    elif isinstance(a, object):
        raise Exception("object in call %s %s [%s]" % (type(a), a, name))


def check_timeout(t):
    if t is not None:
        try:
            t = float(t)
        except Exception:
            raise ValueError("Invalid timeout: {}".format(t))
    return t


def get_default_timeout():
    return config.get("client.default_timeout", default=None)


class Result(object):

    log = logutils.get_logger(__name__)

    _default_timeout = None

    def __init__(self, http_session, service, args, kwargs, context):
        self.http_session = http_session
        self.timeout = check_timeout(kwargs.pop("timeout", self.default_timeout))
        self.args = args
        self.kwargs = dict(kwargs)
        # local_only = self.kwargs.pop("local_only", False)
        # self.url = registry.instance().service_url(service, local_only=local_only)
        self.url = registry.instance().service_url(service)
        self.id = core.call_id()
        if context is None:
            context = ClientContext(self.id)
        self.context = context
        self.timer = Timer()

        self._response = None
        self._thread = t = threading.Thread(target=self._runner)
        t.setDaemon(True)
        t.start()

    def _runner(self):
        self.timer.start()
        try:
            req = core.Request(*self.args, **self.kwargs)
            self.log.debug(
                "POST %s, headers: %s, body: %s",
                self.url,
                req.http_headers,
                req.http_body,
            )
            # XXX It's not entirely clear that `requests.Session` is thread-safe.
            res = self.http_session.post(
                self.url,
                data=req.http_body,
                headers=req.http_headers,
                timeout=self.timeout,
            )
            res = core.Response.from_http(res.status_code, res.content, res.headers)
            self.log.debug("Response: %r", res)
            self.timer.stop()
            self.context.update_metadata(res.metadata)
        except requests.Timeout as exc:
            self.log.debug("Got timeout error: %s", exc)
            res = errors.Timeout(self.url)
        except Exception as exc:
            self.log.info(
                "%r failed: %s", self, exc, exc_info=True, stack_info=True,
            )
            res = exc

        res.metadata = self.context.metadata
        self._response = res

    def wait(self, timeout=None):
        if self._response is None:
            self._thread.join(timeout=timeout)
            if timeout is not None:
                if self._thread.is_alive():
                    raise errors.Timeout(self.url)

        if isinstance(self._response, Exception):
            raise self._response

        result = self._response.value
        if isinstance(result, Exception):
            raise result

        return result, self._response.metadata

    @property
    def result(self):
        r, _ = self.wait()
        return r

    @property
    def metadata(self):
        _, m = self.wait()
        return m

    def __repr__(self):
        return "Result(%r, %r)" % (self.url, self.args,)

    @property
    def default_timeout(self):
        if self.__class__._default_timeout is None:
            self.__class__._default_timeout = get_default_timeout()
        return self.__class__._default_timeout


class Broker(object):
    def __init__(self, thing=None, **kwargs):
        self.http_session = requests.Session()
        if isinstance(thing, Context):
            self._context = thing
            self._kwargs = None
        else:
            self._context = None
            self._kwargs = kwargs

    @property
    def context(self):
        if self._context is not None:
            return self._context

        name, _ = os.path.splitext(os.path.basename(sys.argv[0]))
        return ClientContext(name, **self._kwargs)

    def execute(self, service_name, *args, **kwargs):
        try:
            context = kwargs["context"]
            if context is None:
                context = self.context
            del kwargs["context"]
        except KeyError:
            context = self.context
        context.pre_execute_hook(self, service_name, args, kwargs)

        check_args(args)
        check_args(kwargs)

        return Result(self.http_session, service_name, args, kwargs, context)

    def close(self):
        self.http_session.close()
