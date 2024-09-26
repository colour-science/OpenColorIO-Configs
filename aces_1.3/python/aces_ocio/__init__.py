#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
ACES OCIO
=========

Usage
-----

Python
******

>>> from aces_ocio.generate_config import generate_config
>>> aces_ctl_directory = '/path/to/github/checkout/releases/v1.0.1/transforms/ctl'
>>> config_directory = '/path/to/configuration/dir'
>>> generate_config(aces_ctl_directory, config_directory, 4096, 65, True)

Command Line
************

Using the *create_aces_config* binary:

$ create_aces_config -a '/path/to/github/checkout/releases/v1.0.1/transforms/ctl' -c '/path/to/config/dir' --lutResolution1d 4096 --lutResolution3d 65 --keepTempImages

It is possible to set the following environment variables to avoid passing
the paths to the binary:

- *ACES_OCIO_CTL_DIRECTORY*
- *ACES_OCIO_CONFIGURATION_DIRECTORY*

The above command line call would be done as follows:

$ create_aces_config --lutResolution1d 4096 --lutResolution3d 65 --keepTempImages

Testing the generated configuration is needs the
*ACES_OCIO_CTL_DIRECTORY* environment variable to be set and is done as
follows:

$ tests_aces_config

Build
-----

Mac OS X - Required packages
****************************

OpenColorIO
___________

$ brew install -vd opencolorio --with-python

OpenImageIO
___________

$ brew tap homebrew/science

Optional Dependencies
_____________________

$ brew install -vd libRaw
$ brew install -vd OpenCV
$ brew install -vd openimageio --with-python

CTL
___

$ brew install -vd CTL

OpenColorIO
___________

*ociolutimage* will build with *openimageio* installed.

$ brew uninstall -vd opencolorio
$ brew install -vd opencolorio --with-python
"""

__author__ = (
    'Haarm-Pieter Duiker, Thomas Mansencal, Stephen Hill, Kevin Wheatley, '
    'Joseph Goldstone')
__copyright__ = (
    'Copyright (C) 2014-2021 Academy of Motion Picture Arts and Sciences')
__license__ = 'Academy of Motion Picture Arts and Sciences License Terms'
__maintainer__ = 'Academy of Motion Picture Arts and Sciences'
__email__ = 'acessupport@oscars.org'
__status__ = 'Production'

__major_version__ = '1'
__minor_version__ = '0'
__change_version__ = '3'
__version__ = '.'.join((__major_version__, __minor_version__,
                        __change_version__))
