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
        workers_to_load = set(config.get("worker.load_workers", default=[]))
        ret = []
        for entry in scandir(
            config.get("worker.services_dir", default="/code/services")
        ):
            if not entry.is_dir():
                self.log.debug("Ignoring %s (not a directory)", entry.path)
                continue

            dname = entry.name
            if workers_to_load and dname not in workers_to_load:
                self.log.debug("Ignoring %s (not in %s)", dname, workers_to_load)
                continue

            for fname in ("__init__.py", dname + ".py"):
                path = os.path.join(entry.path, fname)
                if not os.access(path, os.F_OK):
                    self.log.debug("Ignoring %s: %s not found", entry.path, path)
                    break
            else:
                ret.append("{dname}.{dname}".format(dname=dname))

        return ret


class MetviewInventory(Inventory):
    def service_modules(self):
        raise NotImplementedError("Metview services loading not implemented")

    def load_services(self):
        # TODO: Write to a file in a well-known location the list of services
        # implemented by this worker
        raise NotImplementedError("Metview loading not implemented yet.")


_INSTANCE_MAP = {
    "default": DefaultInventory,
    "metview": MetviewInventory,
}


def instance():
    class_name = config.get("inventory.class", "default")
    try:
        ret = _INSTANCE_MAP[class_name]
    except KeyError:
        raise Exception("Invalid value for `inventory.class`: {}".format(class_name))
    if isinstance(ret, type):
        _INSTANCE_MAP[class_name] = ret = ret()
    return ret
