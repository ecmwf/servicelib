# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import os
import socket
import tempfile
import time

from contextlib import closing

import requests

from servicelib.compat import PY2, raise_from, urlparse


__all__ = [
    "available_port",
    "download",
    "wait_for_url",
]


def available_port():
    """Returns a free IPv4 TCP port number, found using ``listen(0)``.

    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.listen(0)
        return s.getsockname()[1]


# Some random number (https://eklitzke.org/efficient-file-copying-on-linux)
XFER_BLOCK_SIZE = 128 * 1024


def download(result, path):
    url = result["location"]
    p = urlparse(url)
    if p.scheme not in {"http", "https"}:
        raise Exception("{}: Unsupported URL scheme '{}'".format(url, p.scheme))

    if PY2:
        path = str(path)

    fd, tmp_fname = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with closing(requests.get(url, stream=True, timeout=20)) as res:
            res.raise_for_status()
            for chunk in res.iter_content(XFER_BLOCK_SIZE):
                os.write(fd, chunk)
    except Exception as exc:
        try:
            os.unlink(tmp_fname)
        except Exception:
            pass
        raise_from(exc, exc)
    finally:
        os.close(fd)

    # TODO: Verify number of bytes downloaded matches `result["contentLength"]`

    os.rename(tmp_fname, path)


def wait_for_url(url, timeout=5.0):
    """Blocks until the given URL is accessible.

    """
    start = time.time()
    while True:
        try:
            res = requests.get(url)
            res.raise_for_status()
        except Exception as exc:
            elapsed = time.time() - start
            if elapsed > timeout:
                raise Exception(
                    "URL {} not ready after {} s: {}".format(url, timeout, exc)
                )
        else:
            return
        time.sleep(0.1)
