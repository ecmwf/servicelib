# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Factories for result objects."""

from __future__ import absolute_import, unicode_literals

import mimetypes
import os
import random
import socket
import tempfile
import uuid

from servicelib import config, logutils
from servicelib.compat import PY2, Path, open, urlparse


__all__ = [
    "Result",
    "Results",
    "instance",
]


class Result(object):
    def __init__(self, content_type):
        self.content_type = content_type
        self._is_open = False
        self._length = 0
        self._metadata = {}

    def as_dict(self):
        if self._is_open:
            raise Exception("{!r}: Still open".format(self))

        ret = {
            "location": self.location,
            "contentLength": self.length,
            "contentType": self.content_type,
        }
        ret.update(self._metadata)

        # TODO: Add `bytes` field, so that we may specify byte ranges.

        return ret

    def __setitem__(self, k, v):
        """Annotates this file with a ``(k, v)`` pair, which will be
        included in its JSON serialized form.

        """
        if k in {"location", "contentType", "contentLength", "metadata"}:
            raise KeyError("Invalid key '{}'".format(k))
        self._metadata[k] = v

    def __enter__(self):
        self._open()
        self._is_open = True
        return self

    def __exit__(self, *exc_info):
        close_exc = None
        try:
            self._close()
        except Exception as exc:
            self.log.warn("Error closing %r: %s", self, exc, exc_info=True)
            close_exc = exc
        self._is_open = False

        if exc_info is None and close_exc:
            raise close_exc

    def write(self, b):
        if not self._is_open:
            raise Exception("{!r}: Not open".format(self))
        n = self._write(b)
        if n is None:
            return None
        self._length += n
        return n

    @property
    def length(self):
        return self._length

    @property
    def location(self):
        raise NotImplementedError

    @property
    def path(self):
        raise NotImplementedError

    def _open(self):
        raise NotImplementedError

    def _close(self):
        raise NotImplementedError

    def _write(self, b):
        raise NotImplementedError

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.as_dict())


class Results(object):
    def create(self, content_type):
        raise NotImplementedError

    def as_local_file(self, result):
        raise NotImplementedError


class LocalFileResult(Result):
    def __init__(self, path, content_type):
        super(LocalFileResult, self).__init__(content_type)
        self._path = path
        self._file_obj = None
        self._path_accessed = False

    @property
    def location(self):
        return self._path.as_uri()

    @property
    def path(self):
        self._path_accessed = True
        return self._path

    @property
    def length(self):
        if not self._path_accessed:
            return super(LocalFileResult, self).length
        return self.path.stat().st_size

    def _open(self):
        self._file_obj = open(self._path, "wb", buffering=0)

    def _close(self):
        self._file_obj.close()

    def _write(self, b):
        n = self._file_obj.write(b)
        if n is None and PY2:
            # Assume we wrote everything, since we opened this file with
            # buffering disabled.
            n = len(b)
        return n


def extension_for(content_type):
    if content_type == "application/postscript":
        return ".ps"

    if content_type == "application/x-netcdf":
        return ".nc"

    if content_type == "text/plain":
        return ".txt"

    ret = mimetypes.guess_extension(content_type)
    if ret is None:
        ret = ""
    return ret


mimetypes.add_type("application/binary", ".bin")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("application/x-bufr", ".bufr")
mimetypes.add_type("application/x-grib", ".grib")
mimetypes.add_type("application/x-odb", ".odb")
mimetypes.add_type("image/gif", ".gif")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/png", ".png")


class LocalFileResults(Results):

    log = logutils.get_logger(__name__)

    def __init__(self):
        pass

    def create(self, content_type):
        return LocalFileResult(self.result_filename(content_type), content_type)

    def as_local_file(self, result):
        ret = Path(urlparse(result["location"]).path)
        for d in self.result_dirs:
            try:
                d = Path(d)
                ret.relative_to(d)
                st_size = ret.stat().st_size
                if st_size == result["contentLength"]:
                    return ret
                self.log.debug(
                    "as_local_file(%s): size %s does not match contentLength",
                    result,
                    st_size,
                )
            except Exception as exc:
                self.log.info("as_local_file(%s): Not in %s: %s", result, d, exc)

    def result_filename(self, content_type):
        dname = (
            Path(random.choice(self.result_dirs))
            / "{:02x}".format(random.randint(0, 0xFF))
            / "{:02x}".format(random.randint(0, 0xFF))
        )
        dname.mkdir(parents=True, exist_ok=True)

        fd, ret = tempfile.mkstemp(
            dir=str(dname),
            prefix="{}-".format(uuid.uuid4().hex),
            suffix=extension_for(content_type),
        )
        os.close(fd)
        return Path(ret)

    @property
    def result_dirs(self):
        return config.get("results_dirs").split(":")


class HttpFileResult(LocalFileResult):
    def __init__(self, netloc, path, content_type):
        super(HttpFileResult, self).__init__(path, content_type)
        self._netloc = netloc

    @property
    def location(self):
        return "http://{}{}".format(self._netloc, self._path)


class HttpFileResults(LocalFileResults):
    def __init__(self):
        super(HttpFileResults, self).__init__()
        host = config.get("results_http_hostname", default=socket.getfqdn())
        try:
            k = "results_http_port"
            port = config.get(k)
            port = int(port)
        except KeyError as exc:
            raise Exception("Missing config variable: {}".format(exc.args[0]))
        except ValueError as exc:
            raise Exception("Invalid config variable {}={}: {}".format(k, port, exc))
        self.netloc = "{}:{}".format(host, port)

    def create(self, content_type):
        return HttpFileResult(
            self.netloc, self.result_filename(content_type), content_type
        )


_INSTANCE_MAP = {
    "local-files": LocalFileResults,
    "http-files": HttpFileResults,
}


def instance():
    class_name = config.get("results_class", default="http-files")
    try:
        ret = _INSTANCE_MAP[class_name]
    except KeyError:
        raise Exception("Invalid value for `results_class`: {}".format(class_name))
    if isinstance(ret, type):
        _INSTANCE_MAP[class_name] = ret = ret()
    return ret
