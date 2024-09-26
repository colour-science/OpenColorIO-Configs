#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Defines unit tests for *ACES* configuration.
"""

from __future__ import division

import hashlib
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from aces_ocio.utilities import files_walker
from aces_ocio.generate_config import (ACES_OCIO_CTL_DIRECTORY_ENVIRON,
                                       generate_config)

__author__ = (
    'Haarm-Pieter Duiker, Thomas Mansencal, Stephen Hill, Kevin Wheatley, '
    'Joseph Goldstone')
__copyright__ = (
    'Copyright (C) 2014-2021 Academy of Motion Picture Arts and Sciences')
__license__ = 'Academy of Motion Picture Arts and Sciences License Terms'
__maintainer__ = 'Academy of Motion Picture Arts and Sciences'
__email__ = 'acessupport@oscars.org'
__status__ = 'Production'

__all__ = [
    'REFERENCE_CONFIG_ROOT_DIRECTORY', 'HASH_TEST_PATTERNS',
    'UNHASHABLE_TEST_PATTERNS', 'TestACESConfig'
]

# TODO: Investigate how the current config has been generated to use it for
# tests.
REFERENCE_CONFIG_ROOT_DIRECTORY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..'))

HASH_TEST_PATTERNS = ('\.3dl', '\.lut', '\.csp')
UNHASHABLE_TEST_PATTERNS = ('\.icc', '\.ocio')


class TestACESConfig(unittest.TestCase):
    """
    Performs tests on the *ACES* configuration.
    """

    def setUp(self):
        """
        Initialises common tests attributes.
        """

        self.__aces_ocio_ctl_directory = os.environ.get(
            ACES_OCIO_CTL_DIRECTORY_ENVIRON, None)

        assert self.__aces_ocio_ctl_directory is not None, (
            'Undefined "{0}" environment variable!'.format(
                ACES_OCIO_CTL_DIRECTORY_ENVIRON))

        assert os.path.exists(self.__aces_ocio_ctl_directory) is True, (
            '"{0}" directory does not exists!'.format(
                self.__aces_ocio_ctl_directory))

        self.maxDiff = None
        self.__temporary_directory = tempfile.mkdtemp()

    def tearDown(self):
        """
        Post tests actions.
        """

        shutil.rmtree(self.__temporary_directory)

    @staticmethod
    def directory_hashes(directory, filters_in=None, filters_out=None,
                         flags=0):
        """
        Recursively computes the hashes from the file within given directory.

        Parameters
        ----------
        directory : str or unicode
            Directory to compute the file hashes.
        filters_in : array_like
            Included patterns.
        filters_out : array_like
            Excluded patterns.
        flags : int
            Regex flags.

        Returns
        -------
        dict
             Directory file hashes.
        """

        hashes = {}
        for path in files_walker(
                directory,
                filters_in=filters_in,
                filters_out=filters_out,
                flags=flags):
            with open(path) as file:
                digest = hashlib.md5(re.sub('\s', '', file.read())).hexdigest()
            hashes[path.replace(directory, '')] = digest
        return hashes

    def test_ACES_config(self):
        """
        Performs tests on the *ACES* configuration by computing hashes on the
        generated configuration and comparing them to the existing one.
        """

        self.assertTrue(
            generate_config(self.__aces_ocio_ctl_directory,
                            self.__temporary_directory))

        reference_hashes = self.directory_hashes(
            REFERENCE_CONFIG_ROOT_DIRECTORY, HASH_TEST_PATTERNS)
        test_hashes = self.directory_hashes(self.__temporary_directory,
                                            HASH_TEST_PATTERNS)

        self.assertDictEqual(reference_hashes, test_hashes)

        # Checking that unashable files ('.icc', '.ocio') are generated.
        unashable = lambda x: (
            sorted([file.replace(x, '') for file in
                    files_walker(x, UNHASHABLE_TEST_PATTERNS)]))

        self.assertListEqual(
            unashable(REFERENCE_CONFIG_ROOT_DIRECTORY),
            unashable(self.__temporary_directory))


if __name__ == '__main__':
    unittest.main()
