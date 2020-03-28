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

import yaml

from servicelib import config, logutils
from servicelib.compat import Path, env_var, open, scandir
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
        for entry in scandir(self.services_dir):
            if not entry.is_dir():
                self.log.debug("Ignoring %s (not a directory)", entry.path)
                continue

            dname = entry.name
            if self.active_services and dname not in self.active_services:
                self.log.debug(
                    "Ignoring %s (`%s` not in list of active services)",
                    entry.path,
                    dname,
                )
                continue

            for fname in ("__init__.py", dname + ".py"):
                path = os.path.join(entry.path, fname)
                if not os.access(path, os.F_OK):
                    self.log.debug("Ignoring %s: %s not found", entry.path, path)
                    break
            else:
                ret.append("{dname}.{dname}".format(dname=dname))

        return ret

    @property
    def services_dir(self):
        return config.get("worker.services_dir", default="/code/services")

    @property
    def active_services(self):
        return set()


class LegacyInventory(DefaultInventory):
    def __init__(self):
        super(LegacyInventory, self).__init__()
        self._active_services = None

    def service_modules(self):
        ret = super(LegacyInventory, self).service_modules()
        runtime_config_url = config.get("inventory.runtime_config_url", default=None)
        if runtime_config_url is not None:
            self.log.debug("Switching runtime config URL to %s", runtime_config_url)
            k, v = env_var("SERVICELIB_CONFIG_URL", runtime_config_url)
            os.environ[k] = v
        return ret

    @property
    def active_services(self):
        if self._active_services is None:
            worker_name = config.get("inventory.worker_name")
            workers_yaml = Path(self.services_dir) / "workers.yaml"
            with open(workers_yaml, "rb") as f:
                workers_yaml = yaml.safe_load(f)

            if worker_name == "other":
                ret = set()
                skip = set()
                for w in workers_yaml.values():
                    skip.update(set(w["services"]))

                for entry in scandir(self.services_dir):
                    if not entry.is_dir():
                        continue

                    dname = entry.name
                    if dname in skip:
                        continue

                    ret.add(dname)
            else:
                ret = set(workers_yaml[worker_name]["services"])

            self._active_services = ret
            self.log.debug("active_services(%s): %s", worker_name, ret)

        return self._active_services


class MetviewInventory(Inventory):
    def service_modules(self):
        raise NotImplementedError("Metview services loading not implemented")

    def load_services(self):
        # TODO: Write to a file in a well-known location the list of services
        # implemented by this worker
        raise NotImplementedError("Metview loading not implemented yet.")


_INSTANCE_MAP = {
    "default": DefaultInventory,
    "legacy": LegacyInventory,
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
