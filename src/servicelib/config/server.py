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

import falcon
import yaml

from servicelib import logutils
from servicelib.config import types


__all__ = ["ConfigServer"]


class ConfigServer(object):

    log = logutils.get_logger(__name__)

    def __init__(self, fname):
        self.fname = fname
        self.config = types.ConfigDict()

        with open(fname, "rb") as f:
            self.config.reset(yaml.safe_load(f))

        self.read_only = os.environ.get("SERVICELIB_CONFIG_SERVER_READ_ONLY") == "true"
        self.lock = threading.Lock()

    def on_get(self, req, resp, key):
        """Returns the whole configuration encoded in JSON.

        """
        resp.data = json.dumps(self.config.as_dict()).encode("utf-8")
        resp.status = falcon.HTTP_200
        return

    def on_post(self, req, resp, key):
        """Updates the value for the setting specified in the HTTP request
        path.

        """
        if self.read_only:
            resp.status = falcon.HTTP_403
            resp.data = json.dumps("Config server in read-only mode").encode("utf-8")
            return

        resp.status = falcon.HTTP_200

        self.log.debug("on_post(req.path=%s, key=%s): Entering", req.path, key)
        if req.content_length:
            value = json.load(req.stream)
            self.log.debug("Setting '%s' to: %s", key, value)
            old_config = copy.deepcopy(self.config)
            self.config.set(key, value)
            try:
                self.save_config()
            except Exception as exc:
                msg = "Cannot save config: {}".format(exc)
                self.log.error(msg, exc_info=True, stack_info=True)
                self.config = old_config
                resp.status = falcon.HTTP_500
                resp.data = json.dumps(msg).encode("utf-8")

    def on_delete(self, req, resp, key=None):
        """Removes the setting specified in the HTTP request path.

        Returns an HTTP 200 response on success, or an HTTP 404 response if
        the setting was not found.

        """
        if self.read_only:
            resp.status = falcon.HTTP_403
            resp.data = json.dumps("Config server in read-only mode").encode("utf-8")
            return

        old_config = copy.deepcopy(self.config)
        try:
            self.config.delete(key)
        except KeyError:
            resp.status = falcon.HTTP_404
            return

        resp.status = falcon.HTTP_200
        try:
            self.save_config()
        except Exception as exc:
            msg = "Cannot save config: {}".format(exc)
            self.log.error(msg, exc_info=True, stack_info=True)
            self.config = old_config
            resp.status = falcon.HTTP_500
            resp.data = json.dumps(msg).encode("utf-8")

    def save_config(self):
        fname_new = "{}.new".format(self.fname)

        config = json.dumps(self.config.as_dict())
        with self.lock:
            with open(fname_new, "wb") as f:
                yaml.safe_dump(config, f, encoding="utf-8", allow_unicode=True)
                f.flush()
                os.fsync(f.fileno())

            os.rename(fname_new, self.fname)
