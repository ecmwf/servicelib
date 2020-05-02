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

import atexit

import falcon

from servicelib import config, inventory, logutils, registry
from servicelib.falcon import HealthResource, StatsResource, WorkerResource


__all__ = [
    "application",
]


# On y va!

logutils.configure_logging(
    level=config.get("log.level", default="debug").upper(),
    log_type=config.get("log.type", default="text"),
)

services = inventory.instance().load_services()

application = falcon.API(media_type=falcon.MEDIA_JSON)
application.add_route("/services/{service}", WorkerResource(services))

# Now that routes for services have been set up, we may add the services we
# host here to the service registry.
worker_hostname = config.get("worker.hostname")
worker_port = config.get("worker.port")
service_urls = [
    (name, "http://{}:{}/services/{}".format(worker_hostname, worker_port, name,),)
    for name in services
]
registry.instance().register(service_urls)

# Now that routes for services have been set up, we are ready to
# handle requests. Let Kubernetes know (or whoever may be sending
# health check probes) by enabling the health check route.
application.add_route("/health", HealthResource())


# When we die, try reporting it to the registry.
@atexit.register
def unregister():
    registry.instance().unregister(service_urls)


application.add_route("/stats", StatsResource())
