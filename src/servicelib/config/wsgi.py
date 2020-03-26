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

import falcon

from servicelib import logutils
from servicelib.config.server import ConfigServer
from servicelib.falcon import HealthResource


__all__ = [
    "application",
]


logutils.configure_logging(
    level=os.environ.get("SERVICELIB_LOG_LEVEL", "DEBUG").upper(),
    log_type=os.environ.get("SERVICELIB_LOG_TYPE", "text"),
)


class ConfigServerMiddleware(object):

    log = logutils.get_logger("config-server")

    def __init__(self, prefix):
        self.prefix = prefix

    def process_request(self, req, resp):
        """'Translate the key in the HTTP path, so that slashes get
        transformed in dots.

        This is a workaround for a Falcon limitation:

            https://github.com/falconry/falcon/issues/648

        This should be done in the `ConfigServer` object.

        """
        if req.path.startswith(self.prefix):
            key = req.path[len(self.prefix) + 1 :].replace("/", ".")
            req.path = "{}/{}".format(self.prefix, key)


settings = ConfigServer(os.environ["SERVICELIB_CONFIG_FILE"])

prefix = "/settings"
application = falcon.API(
    media_type=falcon.MEDIA_JSON, middleware=[ConfigServerMiddleware(prefix)]
)
application.add_route(prefix, settings)
application.add_route(prefix + "/{key}", settings)

application.add_route("/health", HealthResource())
