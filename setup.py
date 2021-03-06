"""
Installer for cxm.

Developer cheat sheet
---------------------

Install developer build::

  $ sudo python setup.py develop

Create the installer archive::

  $ python setup.py sdist --formats=zip

Upload release to PyPI::

  $ python setup.py test
  $ python setup.py sdist --formats=zip upload

Tag a release::

  $ git tag -a -m 'Tagged version 0.1.x.' v0.1.x
  $ git push --tags
"""
# Copyright (C) 2011-2012 Thomas Aglassinger
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
from __future__ import with_statement

from setuptools import setup

import codecs
import os
import shutil

import xsc


def _readMeText():
    '''The whole text of the README file as single string.'''
    with codecs.open('README.txt', 'rb', 'ascii') as readMeFile:
        result = readMeFile.read()
    return result


# Note: The documentation is stored in README.rst so github shows a formatted
# version when browsing the repository. Python's distutils expect a
# README.txt so we crate a temporary copy during the build process and remove
# it afterwards.

shutil.copy('README.rst', 'README.txt')
try:
    setup(
        name="xsc",
        version=xsc.__version__,
        py_modules=["xsc"],
        description=xsc._Description,
        install_requires=[
            "coverage>=3.2",
            "cutplace>=0.6.8",
            "loxun>=1.2",
            "nose>=1.0"
        ],
        entry_points = {
            'console_scripts': [
                'xsc = xsc:mainWithExit'
            ],
        },
        test_suite = "nose.collector",
        keywords="csv prn xml convert",
        author="Thomas Aglassinger",
        author_email="roskakori@users.sourceforge.net",
        url="http://pypi.python.org/pypi/cxm/",
        license="GNU Library or Lesser General Public License (LGPL)",
        long_description=_readMeText(),
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
finally:
    os.remove('README.txt')