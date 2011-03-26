"""
Installer for cxm.

Developer cheat sheet
---------------------

Create the installer archive::

  $ python setup.py sdist --formats=zip

Upload release to PyPI::

  $ python setup.py test
  $ python setup.py sdist --formats=zip upload
"""
# Copyright (C) 2011 Thomas Aglassinger
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from setuptools import setup, find_packages

import cxm

setup(
    name="cxm",
    version=cxm.__version__,
    py_modules=["cxm"],
    description=cxm._Description,
    install_requires=[
        "cutplace>=0.6.4",
        "loxun>=1.2",
        "nose>=1.0"
    ],
    entry_points = {
        'console_scripts': [
            'cxm = cxm:main'
        ],
    },
    test_suite = "nose.collector",
    keywords="csv prn xml convert",
    author="Thomas Aglassinger",
    author_email="roskakori@users.sourceforge.net",
    url="http://pypi.python.org/pypi/cxm/",
    license="GNU Library or Lesser General Public License (LGPL)",
    long_description=cxm.__doc__, #@UndefinedVariable
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Text Processing :: Markup :: XML",
    ],
)
