# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import configparser
import os

from servicelib import logutils


__all__ = ["get"]


NO_DEFAULT = object()

LOG = logutils.get_logger(__name__)

_from_config_file = {}


def get(key, default=NO_DEFAULT):
    try:
        env_var = "SERVICELIB_{}".format(key).upper()
        ret = os.environ[env_var]
        try:
            LOG.debug(
                "config(%s): Returning %s (from environment %s)", key, ret, env_var
            )
        except Exception:
            pass
        return ret
    except KeyError as exc:
        try:
            LOG.debug("config(%s): Environment variable %s not found", key, exc.args[0])
        except Exception:
            pass

    try:
        ret = _from_config_file[key]
        try:
            LOG.debug("config(%s): Returning %s (from config file, cached)", key, ret)
        except Exception:
            pass
        return ret
    except KeyError:
        pass

    config_file = os.environ.get("SERVICELIB_CONFIG_FILE", "/etc/servicelib.ini")
    p = configparser.ConfigParser()
    try:
        with open(config_file, "rt") as f:
            p.read_file(f, config_file)
        try:
            LOG.debug("Loaded config file from %s", config_file)
        except Exception:
            pass
    except Exception as exc:
        try:
            LOG.warn(
                "Error reading config file %s: %s", config_file, exc, exc_info=True
            )
        except Exception:
            pass
    else:
        for s in p.sections():
            for opt in p.options(s):
                k = "{}_{}".format(s, opt)
                _from_config_file[k] = v = p.get(s, opt)
                if k == key:
                    try:
                        LOG.debug(
                            "config(%s): Returning %s (from config file, not cached)",
                            key,
                            v,
                        )
                    except Exception:
                        pass
                    return v

    if default is not NO_DEFAULT:
        try:
            LOG.debug("config(%s): Returning %s (from default)", key, default)
        except Exception:
            pass
        return default

    raise Exception("No value for config variable `{}`".format(key))
