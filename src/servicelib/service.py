# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import inspect

import os
import platform
import sys

from servicelib.context.service import ServiceContext
from servicelib.core import Response
from servicelib.errors import Serializable, TaskError


__all__ = [
    "ServiceInstance",
    "service_instances",
    "start_service",
    "start_services",
]


HOST = platform.node().split(".")[0]


_SERVICE_INSTANCES = {}


class ServiceInstance(object):

    name = None

    def __init__(self, name=None, execute=None, home=None):
        if name is not None:
            self.name = name
        if execute is not None:
            self.execute = execute
        if home is None:
            frame = inspect.currentframe().f_back
            try:
                mod = inspect.getmodule(frame.f_code)
            finally:
                del frame
                home = os.path.dirname(mod.__file__)
        self.home = home

    def execute(self, context, *args, **kwargs):
        """User-provided service implementation."""
        raise NotImplementedError()

    def _execute(self, req):
        context = ServiceContext(self.name, self.home, None, req)
        with context.timer("elapsed") as timer:
            context.metadata.start()
            try:
                result = self.execute(context, *req.args)
            except Serializable as exc:
                if exc.service is None:
                    exc.service = self.name
                if exc.origin is None:
                    exc.origin = HOST
                result = exc
            except Exception as exc:
                exc_type, _, exc_tb = sys.exc_info()
                result = TaskError(self.name, exc_type, exc, exc_tb)
                context.log.info(
                    "Error raised: %s", result, exc_info=True, stack_info=True
                )
            finally:
                try:
                    context.cleanup()
                except Exception as exc:
                    context.log.warn(
                        "Error raised in context cleanup: %s",
                        exc,
                        exc_info=True,
                        stack_info=True,
                    )

            context.metadata.stop()

        if self.name not in {"availability"}:
            context.log.info(
                "Service %s called", self.name, elapsed="{:.4f}".format(timer.elapsed)
            )

        res = Response(result, context.metadata)
        try:
            # Force the JSON encoding of this response, so that we may
            # trap serialization errors and return a proper error
            # response.
            res.http_body
        except Exception as exc:
            exc_type, _, exc_tb = sys.exc_info()
            exc = exc_type("Cannot encode <{}> as JSON: {}".format(res, exc))
            res = Response(
                TaskError(self.name, exc_type, exc, exc_tb), context.metadata
            )
        return res


def start_services(*services):
    """Starts a process which runs several services.

    ``services`` is expected to be an iterable containing either:

    * Dictionaries with the following keys:

        ``name``
            The service name. Required

        ``execute``
            A callable object to handle execution requests. Required.

        ``home``
            Path to the service home directory. Optional.

    * ``ServiceInstance`` instances.

    """
    frame = inspect.currentframe().f_back
    try:
        mod = inspect.getmodule(frame.f_code)
    finally:
        del frame

    service_dir = os.path.dirname(mod.__file__)

    for s in services:
        if isinstance(s, dict):
            kwargs = dict(s)
            kwargs.setdefault("home", service_dir)
            s = ServiceInstance(**kwargs)

        name = s.name
        if name in _SERVICE_INSTANCES:
            raise Exception("Service '{}' already defined".format(name))

        _SERVICE_INSTANCES[name] = s


def start_service(name=None):
    """Starts a daemon process which runs a single service.

    """
    frame = inspect.currentframe().f_back
    try:
        mod = inspect.getmodule(frame.f_code)
    finally:
        del frame

    if name is None:
        name, _ = os.path.splitext(os.path.basename(mod.__file__))

    home = os.path.dirname(mod.__file__)
    execute = getattr(mod, "execute")

    start_services(
        {"name": name, "execute": execute, "home": home,}
    )


def service_instances():
    return _SERVICE_INSTANCES
