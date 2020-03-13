# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Service loading facilities."""

from __future__ import absolute_import, unicode_literals

import importlib
import os
import socket

import psutil

from servicelib import config, logutils
from servicelib.compat import scandir
from servicelib.service import service_instances


__all__ = [
    "Inventory",
    "instance",
]


class Inventory(object):

    log = logutils.get_logger(__name__)

    def service_modules(self):
        raise NotImplementedError

    def load_services(self):
        for mod_name in sorted(self.service_modules()):
            self.log.debug("Loading service module: %s", mod_name)
            mod = importlib.import_module(mod_name)
            self.log.debug("Registering services in module: %s", mod_name)
            mod.main()

        ret = service_instances()
        self.log.debug("Services: %s", ", ".join(sorted(ret.keys())))
        return ret


class DefaultInventory(Inventory):
    def service_modules(self):
        ret = []
        for entry in scandir(
            config.get("worker_services_dir", default="/code/services")
        ):
            if not entry.is_dir():
                self.log.debug("Ignoring %s (not a directory)", entry.path)
                continue

            dname = entry.name
            for fname in ("__init__.py", dname + ".py"):
                path = os.path.join(entry.path, fname)
                if not os.access(path, os.F_OK):
                    self.log.debug("Ignoring %s: %s not found", entry.path, path)
                    break
            else:
                ret.append("{dname}.{dname}".format(dname=dname))

        return ret


def service_url(service_name):
    host = config.get("worker_host", default=socket.getfqdn())
    port = config.get("worker_port", "0")
    if port == "0":
        p = psutil.Process()
        for c in p.connections(kind="tcp"):
            if c.status == psutil.CONN_LISTEN:
                port = c.laddr.port
                break
        else:
            raise Exception("Cannot determine listening port")
        os.environ["SERVICELIB_WORKER_PORT"] = str(port)
    else:
        try:
            port = int(port)
        except Exception as exc:
            raise ValueError("Invalid listening port {}: {}".format(port, exc))

    return "http://{}:{}/services/{}".format(host, port, service_name)


class LegacyInventory(Inventory):
    def service_modules(self):
        raise NotImplementedError("Legacy `workers.yaml` loading not implemented")


class MetviewInventory(Inventory):
    def service_modules(self):
        raise NotImplementedError("Metview services loading not implemented")

    def load_services(self):
        services = super(LegacyInventory, self).load_services()

        # TODO: Write to a file in a well-known location the list of services
        # implemented by this worker
        raise NotImplementedError("Metview loading not implemented yet.")

        return services


_INSTANCE_MAP = {
    "default": DefaultInventory,
    "eccharts-legacy": LegacyInventory,
    "metview": MetviewInventory,
}


def instance():
    class_name = config.get("inventory_class", "default")
    try:
        ret = _INSTANCE_MAP[class_name]
    except KeyError:
        raise Exception("Invalid value for `inventory_class`: {}".format(class_name))
    if isinstance(ret, type):
        _INSTANCE_MAP[class_name] = ret = ret()
    return ret
