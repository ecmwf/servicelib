# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import sys

from setuptools import find_packages, setup


install_requires = [
    "falcon",
    "psutil",
    "python-json-logger",
    "python-memcached",
    "pyyaml",
    "redis",
    "requests",
    "six",
    "structlog",
    "uwsgi",
]

if sys.version_info.major == 2:
    install_requires.extend(
        ["pathlib2", "scandir",]
    )

setup(
    name="servicelib",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    entry_points={
        "console_scripts": [
            "servicelib-client=servicelib.cmd.client:main",
            "servicelib-config-client=servicelib.cmd.config_client:main",
            "servicelib-config-server=servicelib.cmd.config_server:main",
            "servicelib-worker=servicelib.cmd.worker:main",
        ],
    },
    extras_require={
        "docs": ["sphinx"],
        "tests": [
            "coverage[toml]<5.0",
            "pyflakes",
            "pytest",
            "pytest-console-scripts",
            "pytest-cov",
            "pytest-lazy-fixture",
            "pytest-rerunfailures",
        ],
    },
    include_package_data=True,
    install_requires=install_requires,
    license="Apache Software License",
    package_dir={"": "src",},
    packages=find_packages(where="src"),
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, !=3.6.*",
    version="0.1.0",
    zip_safe=False,
)
