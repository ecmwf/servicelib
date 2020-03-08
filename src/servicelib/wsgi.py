# Copyright (c) ECMWF 2019.

"""WSGI entry point module for servicelib workers."""

from __future__ import absolute_import, unicode_literals

import falcon

from servicelib import config, inventory, logutils
from servicelib.falcon import HealthResource, StatsResource, WorkerResource


__all__ = [
    "application",
]


# On y va!

logutils.configure_logging(
    level=config.get("log_level").upper(), log_type=config.get("log_type"),
)

services = inventory.instance().load_services()

application = falcon.API(media_type=falcon.MEDIA_JSON)
application.add_route("/services/{service}", WorkerResource(services))

# Now that routes for services have been set up, we are ready to
# handle requests. Let Kubernetes know (or whoever may be sending
# health check probes) by enabling the health check route.
application.add_route("/health", HealthResource())

application.add_route("/stats", StatsResource())
