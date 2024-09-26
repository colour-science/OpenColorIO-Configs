#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Implements support for *ARRI* colorspaces conversions and transfer functions.
"""

from __future__ import division

import array
import math
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.utilities import ColorSpace, mat44_from_mat33, sanitize

__author__ = (
    'Haarm-Pieter Duiker, Thomas Mansencal, Stephen Hill, Kevin Wheatley, '
    'Joseph Goldstone')
__copyright__ = (
    'Copyright (C) 2014-2021 Academy of Motion Picture Arts and Sciences')
__license__ = 'Academy of Motion Picture Arts and Sciences License Terms'
__maintainer__ = 'Academy of Motion Picture Arts and Sciences'
__email__ = 'acessupport@oscars.org'
__status__ = 'Production'

__all__ = ['create_LogC', 'create_colorspaces']


def create_LogC(gamut, transfer_function, exposure_index, lut_directory,
                lut_resolution_1D, aliases):
    """
    Creates a colorspace covering the conversion from *LogC* to *ACES*, with
    various transfer functions and encoding gamuts covered.

    Parameters
    ----------
    gamut : str
        The name of the encoding gamut to use.
    transfer_function : str
        The name of the transfer function to use.
    exposure_index : str
        The exposure index to use.
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

    name = '{0} (EI{1}) - {2}'.format(transfer_function, exposure_index, gamut)
    if transfer_function == '':
        name = 'Linear - ALEXA {0}'.format(gamut)
    if gamut == '':
        name = 'Curve - {0} (EI{1})'.format(transfer_function, exposure_index)

    cs = ColorSpace(name)
    cs.description = name
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Input/ARRI'
    cs.is_data = False

    if gamut and transfer_function:
        cs.aces_transform_id = (
            'IDT.ARRI.Alexa-v3-logC-EI{0}.a1.v1'.format(exposure_index))

    # A linear space needs allocation variables.
    if transfer_function == '':
        cs.allocation_type = ocio.ALLOCATION_LG2
        cs.allocation_vars = [-8, 5, 0.00390625]

    IDT_maker_version = '0.09'

    nominal_exposure_index = 400
    black_signal = 16 / 4095  # 0.003907
    mid_gray_signal = 0.01
    encoding_gain = 500 / 1023 * 0.525  # 0.256598
    encoding_offset = 400 / 1023  # 0.391007

    def gain_for_EI(ei):
        return (math.log(ei / nominal_exposure_index) / math.log(2) *
                (0.89 - 1) / 3 + 1) * encoding_gain

    def hermite_weights(x, x1, x2):
        d = x2 - x1
        s = (x - x1) / d
        s2 = 1 - s
        return [(1 + 2 * s) * s2 * s2, (3 - 2 * s) * s * s, d * s * s2 * s2,
                -d * s * s * s2]

    def normalized_sensor_to_relative_exposure(ns, ei):
        return (ns - black_signal) * (
            0.18 / (mid_gray_signal * nominal_exposure_index / ei))

    def normalized_LogC_to_linear(code_value, exposure_index):
        cut = 1 / 9
        slope = 1 / (cut * math.log(10))
        offset = math.log10(cut) - slope * cut
        gain = exposure_index / nominal_exposure_index
        gray = mid_gray_signal / gain
        # The higher the EI, the lower the gamma.
        enc_gain = (math.log(gain) / math.log(2) *
                    (0.89 - 1) / 3 + 1) * encoding_gain
        enc_offset = encoding_offset
        for i in range(0, 3):
            nz = ((95 / 1023 - enc_offset) / enc_gain - offset) / slope
            enc_offset = encoding_offset - math.log10(1 + nz) * enc_gain
        # see if we need to bring the hermite spline into play
        xm = math.log10((1 - black_signal) / gray + nz) * enc_gain + enc_offset
        if xm > 1.0:
            if code_value > 0.8:
                hw = hermite_weights(code_value, 0.8, 1)
                d = 0.2 / (xm - 0.8)
                v = [0.8, xm, 1.0, 1 / (d * d)]
                # reconstruct code value from spline
                code_value = 0
                for i in range(0, 4):
                    code_value += (hw[i] * v[i])
        code_value = (code_value - enc_offset) / enc_gain
        # compute normalized sensor value
        ns = pow(10, code_value) if (code_value - offset) / slope > cut else (
            code_value - offset) / slope
        ns = (ns - nz) * gray + black_signal
        return normalized_sensor_to_relative_exposure(ns, exposure_index)

    cs.to_reference_transforms = []

    if transfer_function == 'V3 LogC':
        data = array.array('f', b'\0' * lut_resolution_1D * 4)
        for c in range(lut_resolution_1D):
            data[c] = normalized_LogC_to_linear(c / (lut_resolution_1D - 1),
                                                int(exposure_index))

        lut = '{0}_to_linear.spi1d'.format('{0}_{1}'.format(
            transfer_function, exposure_index))

        lut = sanitize(lut)

        genlut.write_SPI_1D(
            os.path.join(lut_directory, lut), 0, 1, data, lut_resolution_1D, 1)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

    if gamut == 'Wide Gamut':
        cs.to_reference_transforms.append({
            'type':
            'matrix',
            'matrix':
            mat44_from_mat33([
                0.680206, 0.236137, 0.083658, 0.085415, 1.017471, -0.102886,
                0.002057, -0.062563, 1.060506
            ]),
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
         A list of colorspaces for ARRI cameras and encodings.
    """

    colorspaces = []

    # Ensure the ARRI 1D LUTs are at minimum 16 bit
    lut_resolution_1D = max(65536, lut_resolution_1D)

    transfer_function = 'V3 LogC'
    gamut = 'Wide Gamut'

    EIs = [
        160, 200, 250, 320, 400, 500, 640, 800, 1000, 1280, 1600, 2000, 2560,
        3200
    ]
    default_EI = 800

    # Full Conversion
    for EI in EIs:
        log_c_EI_full = create_LogC(
            gamut, transfer_function, EI, lut_directory, lut_resolution_1D,
            ['{0}ei{1}_{2}'.format('logc3', str(EI), 'alexawide')])
        colorspaces.append(log_c_EI_full)

    # Linearization Only
    for EI in [800]:
        log_c_EI_linearization = create_LogC(
            '', transfer_function, EI, lut_directory, lut_resolution_1D,
            ['crv_{0}ei{1}'.format('logc3', str(EI))])
        colorspaces.append(log_c_EI_linearization)

    # Primaries Only
    log_c_EI_primaries = create_LogC(gamut, '', default_EI, lut_directory,
                                     lut_resolution_1D,
                                     ['{0}_{1}'.format('lin', 'alexawide')])
    colorspaces.append(log_c_EI_primaries)

    return colorspaces
