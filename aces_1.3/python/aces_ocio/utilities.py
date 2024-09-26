#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Defines various package utilities objects.
"""

from __future__ import division

import itertools
import os
import re
from collections import OrderedDict

import PyOpenColorIO as ocio

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
    'ColorSpace', 'mat44_from_mat33', 'filter_words', 'files_walker',
    'replace', 'sanitize', 'compact', 'colorspace_prefixed_name',
    'unpack_default', 'cmp'
]


class ColorSpace(object):
    """
    A container for data needed to define an *OCIO* *ColorSpace*.
    """

    def __init__(self,
                 name,
                 aliases=None,
                 description=None,
                 bit_depth=ocio.BIT_DEPTH_F32,
                 equality_group='',
                 family=None,
                 is_data=False,
                 to_reference_transforms=None,
                 from_reference_transforms=None,
                 allocation_type=ocio.ALLOCATION_UNIFORM,
                 allocation_vars=None,
                 aces_transform_id=None):
        """
        Constructor for ColorSpace container class.

        Parameters
        ----------
        name : str or unicode
            Name of the colorspace.
        All other arguments are optional
        """

        if aliases is None:
            aliases = []

        if to_reference_transforms is None:
            to_reference_transforms = []

        if from_reference_transforms is None:
            from_reference_transforms = []

        if allocation_vars is None:
            allocation_vars = [0, 1]

        self.name = name
        self.aliases = aliases
        self.bit_depth = bit_depth
        self.description = description
        self.equality_group = equality_group
        self.family = family
        self.is_data = is_data
        self.to_reference_transforms = to_reference_transforms
        self.from_reference_transforms = from_reference_transforms
        self.allocation_type = allocation_type
        self.allocation_vars = allocation_vars
        self.aces_transform_id = aces_transform_id


def mat44_from_mat33(mat33):
    """
    Creates a 4x4 matrix from given 3x3 matrix.

    Parameters
    ----------
    mat33 : array of float
        A 3x3 matrix

    Returns
    -------
    array of float
         A 4x4 matrix
    """

    return [
        mat33[0], mat33[1], mat33[2], 0, mat33[3], mat33[4], mat33[5], 0,
        mat33[6], mat33[7], mat33[8], 0, 0, 0, 0, 1
    ]


def filter_words(words, filters_in=None, filters_out=None, flags=0):
    """
    A function to filter strings in an array.

    Parameters
    ----------
    words : array of str or unicode
        Array of strings
    filters_in : array of str or unicode, optional
        Words to match
    filters_out : array of str or unicode, optional
        Words to NOT match
    flags : int, optional
        Flags for re.search

    Returns
    -------
    array of str or unicode
         An array of matched or unmatched strings
    """

    filtered_words = []
    for word in words:
        if filters_in:
            filter_matched = False
            for filter in filters_in:
                if re.search(filter, word, flags):
                    filter_matched = True
                    break
            if not filter_matched:
                continue

        if filters_out:
            filter_matched = False
            for filter in filters_out:
                if re.search(filter, word, flags):
                    filter_matched = True
                    break
            if filter_matched:
                continue
        filtered_words.append(word)
    return filtered_words


def files_walker(directory, filters_in=None, filters_out=None, flags=0):
    """
    A function to walk a directory hierarchy, only returning items that do or
    do not match the specified filters

    Parameters
    ----------
    directory : str or unicode
        The starting point for directory walking
    filters_in : array of str or unicode, optional
        File or directory names to match
    filters_out : array of str or unicode, optional
        File or directory names to NOT match
    flags : int, optional
        Flags for re.search

    Returns
    -------
    iterable
         The next matching file or directory name
    """

    for parent_directory, directories, files in os.walk(
            directory, topdown=False, followlinks=True):
        for file in files:
            path = os.path.join(parent_directory, file)
            if os.path.isfile(path):
                if not filter_words((path, ), filters_in, filters_out, flags):
                    continue

                yield path


def replace(string, data):
    """
    Replaces the data occurrences in the string.

    Parameters
    ----------
    string : str or unicode
        String to manipulate.
    data : dict
        Replacement occurrences.

    Returns
    -------
    unicode
        Manipulated string.

    Examples
    --------
    >>> patterns = {'John' : 'Luke',
    ...             'Jane' : 'Anakin',
    ...             'Doe' : 'Skywalker',
    ...             'Z6PO' : 'R2D2'}
    >>> data = 'Users are: John Doe, Jane Doe, Z6PO.'
    >>> replace(data,patterns )
    u'Users are: Luke Skywalker, Anakin Skywalker, R2D2.'
    """

    for old, new in data.items():
        string = string.replace(old, new)
    return string


def sanitize(path):
    """
    Replaces occurrences of ' ', '(', or ')' in the string with an underscore.

    Parameters
    ----------
    path : str or unicode
        Path string to manipulate.

    Returns
    -------
    unicode
        Manipulated string.
    """

    return replace(path, {' ': '_', ')': '_', '(': '_'})


def compact(string):
    """
    Removes blanks, underscores, dashes and parentheses.

    Parameters
    ----------
    string : str or unicode
        String to compact.

    Returns
    -------
    str or unicode
         A compact version of that string.
    """

    return replace(
        string.lower(),
        OrderedDict(((' ', '_'), ('(', '_'), (')', '_'), ('.', '_'),
                     ('-', '_'), ('___', '_'), ('__', '_'), ('_', ''))))


def colorspace_prefixed_name(colorspace):
    """
    Returns given *OCIO* colorspace prefixed name with its family name.

    Parameters
    ----------
    colorspace : ColorSpace
        ColorSpace to prefix.

    Returns
    -------
    str or unicode
         Family prefixed *OCIO* colorspace name.
    """
    prefix = colorspace.family.replace('/', ' - ')

    return '{0} - {1}'.format(prefix, colorspace.name)


def unpack_default(iterable, length=3, default=None):
    """
    Unpacks given iterable maintaining given length and filling missing
    entries with given default.

    Parameters
    ----------
    iterable : object
        Iterable.
    length : int
        Iterable length.
    default : object
        Filling default object.

    Returns
    -------
    iterable
    """

    return itertools.islice(
        itertools.chain(iter(iterable), itertools.repeat(default)), length)


def cmp(x, y):
    """
    Comparison function compatible with Python 2.

    Parameters
    ----------
    x : object
        Object to compare.
    y : object
        Object to compare.

    Returns
    -------
    int
        Comparison result.
    """

    return (x > y) - (x < y)
