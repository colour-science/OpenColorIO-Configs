#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Implements support for *Canon* colorspaces conversions and transfer functions.
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

__all__ = ['create_CLog', 'create_colorspaces']


def create_CLog(gamut, transfer_function, lut_directory, lut_resolution_1D,
                aliases):
    """
    Creates a colorspace covering the conversion from *CLog* to *ACES*, with
    various transfer functions and encoding gamuts covered.

    Parameters
    ----------
    gamut : str
        The name of the encoding gamut to use.
    transfer_function : str
        The name of the transfer function to use
    lut_directory : str or unicode 
        The directory to use when generating LUTs
    lut_resolution_1D : int
        The resolution of generated 1D LUTs
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
        name = 'Linear - Canon {0}'.format(gamut)
    if gamut == '':
        name = 'Curve - {0}'.format(transfer_function)

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/Canon'
    cs.is_data = False

    # A linear space needs allocation variables.
    if transfer_function == '':
        cs.allocation_type = ocio.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    def legal_to_full(code_value):
        return (code_value - 64) / (940 - 64)

    def CLog_to_linear(code_value):
        # log = fullToLegal(c1 * log10(c2*linear + 1) + c3)
        # linear = (pow(10, (legalToFul(log) - c3)/c1) - 1)/c2
        c1 = 0.529136
        c2 = 10.1596
        c3 = 0.0730597

        linear = (pow(10, (legal_to_full(code_value) - c3) / c1) - 1) / c2
        linear *= 0.9

        return linear

    def CLog2_to_linear(code_value):
        # log = fullToLegal(c1 * log10(c2*linear + 1) + c3)
        # linear = (pow(10, (legalToFul(log) - c3)/c1) - 1)/c2
        c1 = 0.281863093
        c2 = 87.09937546
        c3 = 0.035388128

        linear = (pow(10, (legal_to_full(code_value) - c3) / c1) - 1) / c2
        linear *= 0.9

        return linear

    def CLog3_to_linear(code_value):
        # if(CLog3_ire < 0.04076162)
        #     out = -( pow( 10, ( 0.07623209 - CLog3_ire ) / 0.42889912 )
        #     - 1 ) / 14.98325;
        # else if(CLog3_ire <= 0.105357102)
        #     out = ( CLog3_ire - 0.073059361 ) / 2.3069815;
        # else
        #     out = ( pow( 10, ( CLog3_ire - 0.069886632 ) / 0.42889912 )
        #     - 1 ) / 14.98325;

        c1 = 0.42889912
        c2 = 14.98325
        c3 = 0.069886632

        c4 = 0.04076162
        c5 = 0.07623209

        c6 = 0.105357102
        c7 = 0.073059361
        c8 = 2.3069815

        CLog3_ire = legal_to_full(code_value)

        if CLog3_ire < c4:
            linear = -(pow(10, (c5 - CLog3_ire) / c1) - 1) / c2
        elif CLog3_ire <= c6:
            linear = (CLog3_ire - c7) / c8
        else:
            linear = (pow(10, (CLog3_ire - c3) / c1) - 1) / c2
        linear *= 0.9

        return linear

    cs.to_reference_transforms = []

    if transfer_function:
        if transfer_function == 'Canon-Log':
            data = array.array('f', b'\0' * lut_resolution_1D * 4)
            for c in range(lut_resolution_1D):
                data[c] = CLog_to_linear(1023 * c / (lut_resolution_1D - 1))
        elif transfer_function == 'Canon-Log2':
            data = array.array('f', b'\0' * lut_resolution_1D * 4)
            for c in range(lut_resolution_1D):
                data[c] = CLog2_to_linear(1023 * c / (lut_resolution_1D - 1))
        elif transfer_function == 'Canon-Log3':
            data = array.array('f', b'\0' * lut_resolution_1D * 4)
            for c in range(lut_resolution_1D):
                data[c] = CLog3_to_linear(1023 * c / (lut_resolution_1D - 1))

        lut = '{0}_to_linear.spi1d'.format(transfer_function)
        genlut.write_SPI_1D(
            os.path.join(lut_directory, lut), 0, 1, data, lut_resolution_1D, 1)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

    if gamut == 'Rec. 709 Daylight':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.561538969, 0.402060105, 0.036400926, 0, 0.092739623,
                0.924121198, -0.016860821, 0, 0.084812961, 0.006373835,
                0.908813204, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'Rec. 709 Tungsten':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.566996399, 0.365079418, 0.067924183, 0, 0.070901044,
                0.880331008, 0.048767948, 0, 0.073013542, -0.066540862,
                0.99352732, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'DCI-P3 Daylight':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.607160575, 0.299507286, 0.093332140, 0, 0.004968120,
                1.050982224, -0.055950343, 0, -0.007839939, 0.000809127,
                1.007030813, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'DCI-P3 Tungsten':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.650279125, 0.253880169, 0.095840706, 0, -0.026137986,
                1.017900530, 0.008237456, 0, 0.007757558, -0.063081669,
                1.055324110, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'Cinema Gamut Daylight':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.763064455, 0.149021161, 0.087914384, 0, 0.003657457,
                1.10696038, -0.110617837, 0, -0.009407794, -0.218383305,
                1.227791099, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'Cinema Gamut Tungsten':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.817416293, 0.090755698, 0.091828009, 0, -0.035361374,
                1.065690585, -0.030329211, 0, 0.010390366, -0.299271107,
                1.288880741, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'Rec. 2020 Daylight':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.678891151, 0.158868422, 0.162240427, 0, 0.045570831,
                0.860712772, 0.093716397, 0, -0.000485710, 0.025060196,
                0.975425515, 0, 0, 0, 0, 1
            ],
            'direction':
            'forward'
        })
    elif gamut == 'Rec. 2020 Tungsten':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix': [
                0.724488568, 0.115140904, 0.160370529, 0, 0.010659276,
                0.839605344, 0.149735380, 0, 0.014560161, -0.028562057,
                1.014001897, 0, 0, 0, 0, 1
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
         A list of colorspaces for Canon cameras and encodings .
    """

    colorspaces = []

    # Full Conversion
    c_log_1 = create_CLog('Rec. 709 Daylight', 'Canon-Log', lut_directory,
                          lut_resolution_1D, ['canonlog_rec709day'])
    colorspaces.append(c_log_1)

    c_log_2 = create_CLog('Rec. 709 Tungsten', 'Canon-Log', lut_directory,
                          lut_resolution_1D, ['canonlog_rec709tung'])
    colorspaces.append(c_log_2)

    c_log_3 = create_CLog('DCI-P3 Daylight', 'Canon-Log', lut_directory,
                          lut_resolution_1D, ['canonlog_dcip3day'])
    colorspaces.append(c_log_3)

    c_log_4 = create_CLog('DCI-P3 Tungsten', 'Canon-Log', lut_directory,
                          lut_resolution_1D, ['canonlog_dcip3tung'])
    colorspaces.append(c_log_4)

    c_log_5 = create_CLog('Cinema Gamut Daylight', 'Canon-Log', lut_directory,
                          lut_resolution_1D, ['canonlog_cgamutday'])
    colorspaces.append(c_log_5)

    c_log_6 = create_CLog('Cinema Gamut Tungsten', 'Canon-Log', lut_directory,
                          lut_resolution_1D, ['canonlog_cgamuttung'])
    colorspaces.append(c_log_6)

    c_log_20 = create_CLog('Rec. 2020 Daylight', 'Canon-Log', lut_directory,
                           lut_resolution_1D, ['canonlog_rec2020day'])
    colorspaces.append(c_log_20)

    c_log_21 = create_CLog('Rec. 2020 Tungsten', 'Canon-Log', lut_directory,
                           lut_resolution_1D, ['canonlog_rec2020tung'])
    colorspaces.append(c_log_21)

    c_log_22 = create_CLog('Rec. 2020 Daylight', 'Canon-Log2', lut_directory,
                           lut_resolution_1D, ['canonlog2_rec2020day'])
    colorspaces.append(c_log_22)

    c_log_23 = create_CLog('Rec. 2020 Tungsten', 'Canon-Log2', lut_directory,
                           lut_resolution_1D, ['canonlog2_rec2020tung'])
    colorspaces.append(c_log_23)

    c_log_24 = create_CLog('Cinema Gamut Daylight', 'Canon-Log2',
                           lut_directory, lut_resolution_1D,
                           ['canonlog2_cgamutday'])
    colorspaces.append(c_log_24)

    c_log_25 = create_CLog('Cinema Gamut Tungsten', 'Canon-Log2',
                           lut_directory, lut_resolution_1D,
                           ['canonlog2_cgamuttung'])
    colorspaces.append(c_log_25)

    c_log_32 = create_CLog('Rec. 2020 Daylight', 'Canon-Log3', lut_directory,
                           lut_resolution_1D, ['canonlog3_rec2020day'])
    colorspaces.append(c_log_32)

    c_log_33 = create_CLog('Rec. 2020 Tungsten', 'Canon-Log3', lut_directory,
                           lut_resolution_1D, ['canonlog3_rec2020tung'])
    colorspaces.append(c_log_33)

    c_log_34 = create_CLog('Cinema Gamut Daylight', 'Canon-Log3',
                           lut_directory, lut_resolution_1D,
                           ['canonlog3_cgamutday'])
    colorspaces.append(c_log_34)

    c_log_35 = create_CLog('Cinema Gamut Tungsten', 'Canon-Log3',
                           lut_directory, lut_resolution_1D,
                           ['canonlog3_cgamuttung'])
    colorspaces.append(c_log_35)

    # Linearization Only
    c_log_7 = create_CLog('', 'Canon-Log', lut_directory, lut_resolution_1D,
                          ['crv_canonlog'])
    colorspaces.append(c_log_7)

    c_log2_7 = create_CLog('', 'Canon-Log2', lut_directory, lut_resolution_1D,
                           ['crv_canonlog2'])
    colorspaces.append(c_log2_7)

    c_log3_7 = create_CLog('', 'Canon-Log3', lut_directory, lut_resolution_1D,
                           ['crv_canonlog3'])
    colorspaces.append(c_log3_7)

    # Primaries Only
    c_log_8 = create_CLog('Rec. 709 Daylight', '', lut_directory,
                          lut_resolution_1D, ['lin_canonrec709day'])
    colorspaces.append(c_log_8)

    c_log_9 = create_CLog('Rec. 709 Tungsten', '', lut_directory,
                          lut_resolution_1D, ['lin_canonrec709tung'])
    colorspaces.append(c_log_9)

    c_log_10 = create_CLog('DCI-P3 Daylight', '', lut_directory,
                           lut_resolution_1D, ['lin_canondcip3day'])
    colorspaces.append(c_log_10)

    c_log_11 = create_CLog('DCI-P3 Tungsten', '', lut_directory,
                           lut_resolution_1D, ['lin_canondcip3tung'])
    colorspaces.append(c_log_11)

    c_log_12 = create_CLog('Cinema Gamut Daylight', '', lut_directory,
                           lut_resolution_1D, ['lin_canoncgamutday'])
    colorspaces.append(c_log_12)

    c_log_13 = create_CLog('Cinema Gamut Tungsten', '', lut_directory,
                           lut_resolution_1D, ['lin_canoncgamuttung'])
    colorspaces.append(c_log_13)

    c_log_14 = create_CLog('Rec. 2020 Daylight', '', lut_directory,
                           lut_resolution_1D, ['lin_canonrec2020day'])
    colorspaces.append(c_log_14)

    c_log_15 = create_CLog('Rec. 2020 Tungsten', '', lut_directory,
                           lut_resolution_1D, ['lin_canonrec2020tung'])
    colorspaces.append(c_log_15)

    return colorspaces
