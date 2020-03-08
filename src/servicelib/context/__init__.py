# Copyright (C) 2009 ECMWF

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
        # XXX Put the ``import`` statement here in order to avoid a circular
        # import
        from servicelib.client import Broker

        return Broker(self)

    @property
    def name(self):
        return self._name

    def timer(self, name):
        return self._metadata.timer(name)

    @property
    def default_uid(self):
        return _DEFAULT_UID
