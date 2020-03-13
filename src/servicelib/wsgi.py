# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""WSGI entry point module for servicelib workers."""

from __future__ import absolute_import, unicode_literals

import os

import falcon

from servicelib import config, inventory, logutils
from servicelib.falcon import HealthResource, StatsResource, WorkerResource


__all__ = [
    "application",
]


# On y va!

logutils.configure_logging(
    level=config.get("log_level", default="debug").upper(),
    log_type=config.get("log_type", default="text"),
)

services = inventory.instance().load_services()

application = falcon.API(media_type=falcon.MEDIA_JSON)
application.add_route("/services/{service}", WorkerResource(services))

# Now that routes for services have been set up, we are ready to
# handle requests. Let Kubernetes know (or whoever may be sending
# health check probes) by enabling the health check route.
application.add_route("/health", HealthResource())

application.add_route("/stats", StatsResource())

os.umask(0o22)
