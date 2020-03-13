# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

from servicelib import core, logutils
from servicelib.context import Context


__all__ = [
    "ClientContext",
]


class ClientContext(Context):
    def __init__(self, name, metadata=None, uid=None, **kwargs):
        super(ClientContext, self).__init__(name, metadata)

        if uid is None:
            uid = self.default_uid

        self._uid = uid
        for k, v in kwargs.items():
            self.annotate(k, v)

        self.tracker = kwargs.get("tracker", core.tracker())
        bind = {"uid": self._uid, "tracker": self.tracker}

        log_name = kwargs.get("log_name")
        if log_name is not None:
            self.log = logutils.get_logger(log_name)
        self.log = self.log.bind(**bind)

    def pre_execute_hook(self, broker, service, args, kwargs):
        tracker = kwargs.get("tracker", self.tracker)
        kwargs.setdefault("tracker", tracker)
        kwargs.setdefault("uid", self.uid)

    @property
    def uid(self):
        return self._uid
