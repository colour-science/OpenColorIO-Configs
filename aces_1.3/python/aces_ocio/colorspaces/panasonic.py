#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Implements support for *Panasonic* colorspaces conversions and transfer
functions.
"""

from __future__ import division

import array
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.utilities import ColorSpace

__author__ = (
    'Haarm-Pieter Duiker, Thomas Mansencal, Stephen Hill, Kevin Wheatley, '
    'Joseph Goldstone')
__copyright__ = (
    'Copyright (C) 2014-2021 Academy of Motion Picture Arts and Sciences')
__license__ = 'Academy of Motion Picture Arts and Sciences License Terms'
__maintainer__ = 'Academy of Motion Picture Arts and Sciences'
__email__ = 'acessupport@oscars.org'
__status__ = 'Production'

__all__ = ['create_VLog', 'create_colorspaces']


def create_VLog(gamut, transfer_function, lut_directory, lut_resolution_1D,
                aliases):
    """
    Creates colorspace covering the conversion from *VLog* to *ACES*, with various
    transfer functions and encoding gamuts covered.

    Parameters
    ----------
    gamut : str
        The name of the encoding gamut to use.
    transfer_function : str
        The name of the transfer function to use.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    aliases : list of str
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
         A ColorSpace container class referencing the LUTs, matrices and
         identifying information for the requested colorspace.
    """

    name = '{0} - {1}'.format(transfer_function, gamut)
    if transfer_function == '':
        name = 'Linear - {0}'.format(gamut)
    if gamut == '':
        name = 'Curve - {0}'.format(transfer_function)

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/Panasonic'
    cs.is_data = False

    # A linear space needs allocation variables
    if transfer_function == '':
        cs.allocation_type = ocio.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    def VLog_to_linear(x):
        cut_inv = 0.181
        b = 0.00873
        c = 0.241514
        d = 0.598206

        if x <= cut_inv:
            return (x - 0.125) / 5.6
        else:
            return pow(10, (x - d) / c) - b

    cs.to_reference_transforms = []

    if transfer_function == 'V-Log':
        data = array.array('f', b'\0' * lut_resolution_1D * 4)
        for c in range(lut_resolution_1D):
            data[c] = VLog_to_linear(float(c) / (lut_resolution_1D - 1))

        lut = '{0}_to_linear.spi1d'.format(transfer_function)
        genlut.write_SPI_1D(
            os.path.join(lut_directory, lut), 0.0, 1.0, data,
            lut_resolution_1D, 1)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

    if gamut == 'V-Gamut':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.724382758, 0.166748484, 0.108497411, 0.0, 0.021354009,
                0.985138372, -0.006319092, 0.0, -0.009234278, -0.00104295,
                1.010272625, 0.0, 0, 0, 0, 1.0
            ],
            'direction':
            'forward'
        })

    cs.from_reference_transforms = []
    return cs


def create_colorspaces(lut_directory, lut_resolution_1D):
    """
    Generates the colorspace conversions.

    Parameters
    ----------
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.

    Returns
    -------
    list
         A list of colorspaces for Panasonic cameras and encodings .
    """

    colorspaces = []

    # Full conversion
    v_log_1 = create_VLog('V-Gamut', 'V-Log', lut_directory, lut_resolution_1D,
                          ['vlog_vgamut'])
    colorspaces.append(v_log_1)

    # Linearization Only
    v_log_2 = create_VLog('', 'V-Log', lut_directory, lut_resolution_1D,
                          ['crv_vlog'])
    colorspaces.append(v_log_2)

    # Primaries Only
    v_log_3 = create_VLog('V-Gamut', '', lut_directory, lut_resolution_1D,
                          ['lin_vgamut'])
    colorspaces.append(v_log_3)

    return colorspaces
