#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Implements support for *GoPro* colorspaces conversions and transfer functions.
"""

from __future__ import division

import array
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.utilities import ColorSpace, sanitize

__author__ = (
    'Haarm-Pieter Duiker, Thomas Mansencal, Stephen Hill, Kevin Wheatley, '
    'Joseph Goldstone')
__copyright__ = (
    'Copyright (C) 2014-2021 Academy of Motion Picture Arts and Sciences')
__license__ = 'Academy of Motion Picture Arts and Sciences License Terms'
__maintainer__ = 'Academy of Motion Picture Arts and Sciences'
__email__ = 'acessupport@oscars.org'
__status__ = 'Production'

__all__ = ['create_Protune', 'create_colorspaces']


def create_Protune(gamut, transfer_function, lut_directory, lut_resolution_1D,
                   aliases):
    """
    Creates colorspace covering the conversion from *ProTune* to *ACES*, with
    various transfer functions and encoding gamuts covered.

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

    # The gamut should be marked as experimental until  matrices are fully
    # verified.
    name = '{0} - {1} - Experimental'.format(transfer_function, gamut)
    if transfer_function == '':
        name = 'Linear - {0} - Experimental'.format(gamut)
    if gamut == '':
        name = 'Curve - {0}'.format(transfer_function)

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/GoPro'
    cs.is_data = False

    # A linear space needs allocation variables.
    if transfer_function == '':
        cs.allocation_type = ocio.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    def Protune_to_linear(normalized_code_value):
        c1 = 113.0
        c2 = 1.0
        c3 = 112.0
        linear = ((pow(c1, normalized_code_value) - c2) / c3)

        return linear

    cs.to_reference_transforms = []

    if transfer_function == 'Protune Flat':
        data = array.array('f', b'\0' * lut_resolution_1D * 4)
        for c in range(lut_resolution_1D):
            data[c] = Protune_to_linear(float(c) / (lut_resolution_1D - 1))

        lut = '{0}_to_linear.spi1d'.format(transfer_function)
        lut = sanitize(lut)
        genlut.write_SPI_1D(
            os.path.join(lut_directory, lut), 0, 1, data, lut_resolution_1D, 1)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

    if gamut == 'Protune Native':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.533448429, 0.32413911, 0.142412421, 0, -0.050729924,
                1.07572006, -0.024990416, 0, 0.071419661, -0.290521962,
                1.219102381, 0, 0, 0, 0, 1
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
         A list of colorspaces for GoPro cameras and encodings.
    """

    colorspaces = []

    # Full conversion
    protune_1 = create_Protune('Protune Native', 'Protune Flat', lut_directory,
                               lut_resolution_1D,
                               ['protuneflat_protunegamutexp'])
    colorspaces.append(protune_1)

    # Linearization Only
    protune_2 = create_Protune('', 'Protune Flat', lut_directory,
                               lut_resolution_1D, ['crv_protuneflat'])
    colorspaces.append(protune_2)

    # Primaries Only
    protune_3 = create_Protune('Protune Native', '', lut_directory,
                               lut_resolution_1D, ['lin_protunegamutexp'])
    colorspaces.append(protune_3)

    return colorspaces
