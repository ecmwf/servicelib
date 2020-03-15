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
import pwd

from servicelib import compat, logutils
from servicelib.metadata import Metadata

try:
    _DEFAULT_UID = pwd.getpwuid(os.geteuid()).pw_name
except Exception:
    _DEFAULT_UID = os.environ.get("USER", "unknown")


class Context(object):

    log = logutils.get_logger(__name__)

    def __init__(self, name, metadata=None):
        assert isinstance(name, compat.string_types)
        self._name = name
        self._broker = None

        if metadata is None:
            self._metadata = Metadata(name)
        else:
            assert isinstance(metadata, Metadata)
            self._metadata = metadata

    def update_metadata(self, other):
        self._metadata.update_metadata(other)

    def annotate(self, *args, **kwargs):
        return self._metadata.annotate(*args, **kwargs)

    @property
    def metadata(self):
        return self._metadata

    @property
    def broker(self):
        # XXX Put the `import` statement here in order to avoid a circular
        # import
        from servicelib.client import Broker

        if self._broker is None:
            self._broker = Broker(self)
        return self._broker

    @property
    def name(self):
        return self._name

    def timer(self, name):
        return self._metadata.timer(name)

    @property
    def default_uid(self):
        return _DEFAULT_UID
