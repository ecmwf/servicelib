# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Error handling code for the servicelib framework."""

from __future__ import absolute_import, unicode_literals

import json
import platform
import sys
import traceback

import six

from servicelib import logutils


__all__ = [
    "BadRequest",
    "CommError",
    "RetryLater",
    "ServiceError",
    "TaskError",
    "Timeout",
]


HOSTNAME = platform.node().split(".")[0]


class Serializable(Exception):

    """Class for serializable errors."""

    log = logutils.get_logger(__name__)

    def __init__(self, *args):
        super(Serializable, self).__init__(*args)
        self.service = None
        self.origin = None

    def as_dict(self):
        cls = self.__class__
        return {
            "exc_type": "{}.{}".format(cls.__module__, cls.__name__),
            "exc_args": self.args,
            "exc_service": self.service,
            "exc_origin": self.origin,
        }

    @classmethod
    def from_dict(cls, d):
        bits = d["exc_type"].split(".")
        exc_module, exc_name = ".".join(bits[:-1]), bits[-1]
        try:
            exc_cls = getattr(sys.modules[exc_module], exc_name)
        except KeyError:
            exc_cls = cls
            cls.log.debug(
                "Module '%s' not found for error '%s', deserializing as %s",
                exc_module,
                d["exc_type"],
                exc_cls,
            )
        except AttributeError:
            exc_cls = cls
            cls.log.debug(
                "Error '%s' not found in module '%s', deserializing as %s",
                exc_name,
                exc_module,
                exc_cls,
            )
        else:
            from_dict = getattr(exc_cls, "from_dict", None)
            if callable(from_dict):
                if six.PY2:
                    if getattr(from_dict, "im_self", None) != cls:
                        cls.log.debug("from_dict(%s): Delegating to %s", d, from_dict)
                        return from_dict(d)
                else:
                    if from_dict.__qualname__ != "Serializable.from_dict":
                        cls.log.debug("from_dict(%s): Delegating to %s", d, from_dict)
                        return from_dict(d)

        exc = exc_cls(*d.get("exc_args", []))
        if isinstance(exc, Serializable):
            exc.service = d["exc_service"]
            exc.origin = d["exc_origin"]
        return exc

    @property
    def message(self):
        try:
            return self.args[0]
        except IndexError:
            return None

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__, ", ".join(repr(a) for a in self.args)
        )

    def __str__(self):
        return str(self.message)

    def __eq__(self, other):
        if other.__class__ == self.__class__:
            return self.as_dict() == other.as_dict()
        return False

    def __hash__(self):
        return hash(json.dumps(self.as_dict()))


class ServiceError(Serializable):

    """Models an error raised by the `servicelib` internals."""

    http_response_code = "500 Internal Server Error"

    def __init__(self, *args):
        super(ServiceError, self).__init__(*args)

    @property
    def retry(self):
        return False


class CommError(ServiceError):

    """Signals a communications error.

    Users receiving this kind of error should retry the operation that raised
    it after a while, since the system believes the reason for this error is
    transient.

    """

    http_response_code = "503 Service Unavailable"

    retry = True

    def __init__(self, message):
        super(CommError, self).__init__(message)


class Timeout(ServiceError):

    """Signals a processing timeout.

    The service is processing the call, but it has not sent a reply
    withong the specified timeout.

    """

    http_response_code = "503 Service Unavailable"

    retry = True

    def __init__(self, message):
        super(Timeout, self).__init__(message)


class BadRequest(ServiceError):

    """Error raised due to a malformed request.

    Users receiving this kind of error should *not* retry the operation that
    caused it, since the error was caused by the user's input, and the system
    will raise it again.

    """

    http_response_code = "400 Bad Request"

    def __init__(self, message):
        super(BadRequest, self).__init__(message)


class RetryLater(ServiceError):

    """Error raised on temporary failures.

    Caller should retry after the delay expressed by this error.

    """

    http_response_code = "503 Service Unavailable"

    def __init__(self, message, delay):
        super(RetryLater, self).__init__(message, delay)
        self.delay = int(delay)

    @property
    def retry(self):
        return self.delay


@six.python_2_unicode_compatible
class TaskError(Serializable):

    """Wrapper for errors raised by service implementations.

    Instances of `TaskError` are raised by *client* code calling services. They
    are not meant to be raised explicitly by service implementations (i.e. the
    constructor should be treated as private).

    """

    http_response_code = "500 Internal Server Error"

    log = logutils.get_logger(__name__)

    def __init__(self, service, exc_type, exc_value, exc_tb, origin=None):
        if origin is None:
            origin = HOSTNAME
        super(TaskError, self).__init__(service, exc_type, exc_value, exc_tb, origin)
        self.origin = origin
        self.service = service
        self._exc_type = exc_type
        self._exc_value = exc_value
        try:
            self._exc_tb = traceback.format_tb(exc_tb)
        except Exception:
            self._exc_tb = exc_tb

    def as_dict(self):
        d = super(TaskError, self).as_dict()

        # Arguments to our constructor are not serializable, so ensure we
        # do not send them.
        del d["exc_args"]

        # If the exception args can be serialized, use them
        # unmodified. Otherwise fall back to their string
        # representations.

        exc_args = []
        for arg in self._exc_value.args:
            try:
                json.dumps(arg)
            except TypeError:
                exc_args.append(repr(arg))
            else:
                exc_args.append(arg)

        d.update(
            {
                "wrapped_exc_type": "%s.%s"
                % (self._exc_type.__module__, self._exc_type.__name__),
                "wrapped_exc_args": exc_args,
                "wrapped_exc_tb": self._exc_tb,
            }
        )
        return d

    @classmethod
    def from_dict(cls, d):
        bits = d["wrapped_exc_type"].split(".")
        exc_module, exc_name = ".".join(bits[:-1]), bits[-1]
        try:
            exc_type = getattr(sys.modules[exc_module], exc_name)
        except KeyError:
            cls.log.debug("%s not found, deserializing as 'Exception'", exc_name)
            exc_type = Exception

        try:
            exc_value = exc_type(*d["wrapped_exc_args"])
        except Exception:
            cls.log.debug(
                "Cannot create %s(%s), exc_value will be string",
                exc_name,
                d["wrapped_exc_args"],
            )
            exc_value = Exception(*d["wrapped_exc_args"])

        return TaskError(
            service=d["exc_service"],
            origin=d["exc_origin"],
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=d["wrapped_exc_tb"],
        )

    @property
    def exc_type(self):
        """Class of the original error, if known, or `exceptions.Exception`
        otherwise.

        """
        return self._exc_type

    @property
    def exc_value(self):
        """Instance of the original error, if available, or instance of
        exceptions.Exception` with a message value of the original error
        otherwise.

        """
        return self._exc_value

    @property
    def exc_tb(self):
        """List of strings describing the traceback of the original error.

        """
        return self._exc_tb

    @property
    def retry(self):
        return False

    def __repr__(self):
        return "TaskError(%s)" % (self.as_dict(),)

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.exc_value)
