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
import os
import random
import tempfile
import uuid

from servicelib import config, logutils
from servicelib.compat import Path
from servicelib.utils import download


__all__ = [
    "Scratch",
    "instance",
]


class Scratch(object):
    def create_temp_file(self):
        raise NotImplementedError

    def as_local_file(self, result):
        raise NotImplementedError


class DefaultScratch(Scratch):

    log = logutils.get_logger(__name__)

    def __init__(self, strategy):
        self.strategy = strategy

    def create_temp_file(self):
        dname = (
            Path(self.strategy.download_dir(self.scratch_dirs))
            / "{:02x}".format(random.randint(0, 0xFF))
            / "{:02x}".format(random.randint(0, 0xFF))
        )
        dname.mkdir(parents=True, exist_ok=True)

        fd, ret = tempfile.mkstemp(
            dir=str(dname), prefix="{}-".format(uuid.uuid4().hex)
        )
        os.close(fd)
        return ret

    def as_local_file(self, result):
        h = hashlib.sha256()
        h.update(result["location"].encode("utf-8"))
        # TODO: Update hash object with byte range fields, too, once they are
        # implemented.
        fname = h.hexdigest()

        for dname in self.scratch_dirs:
            path = os.path.join(dname, fname[0:2], fname[2:4], fname)
            if os.access(path, os.F_OK):
                self.log.debug("%s already downloaded, returning", path)
                return Path(path)

        dname = Path(random.choice(self.scratch_dirs)) / fname[0:2] / fname[2:4]
        dname.mkdir(parents=True, exist_ok=True)
        path = dname / fname

        self.log.debug("Downloading %s into %s", result, path)
        download(result, path)
        return path

    @property
    def scratch_dirs(self):
        return config.get("scratch.dirs")


class ScratchStrategy(object):
    def download_dir(self, dirs):
        raise NotImplementedError


class Random(ScratchStrategy):
    def download_dir(self, dirs):
        return random.choice(dirs)


_INSTANCE_MAP = {
    "random": Random,
}


def instance():
    class_name = config.get("scratch.strategy", default="random")
    try:
        ret = _INSTANCE_MAP[class_name]
    except KeyError:
        raise Exception("Invalid value for `scratch.strategy`: {}".format(class_name))
    if isinstance(ret, type):
        _INSTANCE_MAP[class_name] = ret = DefaultScratch(ret())
    return ret
