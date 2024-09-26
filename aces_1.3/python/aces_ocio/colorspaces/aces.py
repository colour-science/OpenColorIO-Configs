#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Implements support for *ACES* colorspaces conversions and transfer functions.
"""

from __future__ import division

import copy
import math
import numpy as np
import os
import pprint
import shutil

import PyOpenColorIO as ocio

from aces_ocio.generate_lut import (generate_1D_LUT_from_CTL,
                                    generate_3D_LUT_from_CTL, write_SPI_1D)
from aces_ocio.utilities import (ColorSpace, mat44_from_mat33, sanitize,
                                 compact)

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
    'ACES_AP1_TO_AP0', 'ACES_AP0_TO_AP1', 'ACES_AP0_TO_XYZ', 'ACES_XYZ_TO_AP0',
    'create_ACES', 'create_ACEScc', 'create_ACEScct', 'create_ACESproxy',
    'create_ACEScg', 'create_ADX', 'create_generic_log', 'create_DolbyPQ',
    'create_shaper_DolbyPQ', 'create_shapers_log2', 'create_shapers_DolbyPQ',
    'create_shapers', 'create_blue_light_artifact_fix_LMT', 'create_LMT',
    'create_LMTs', 'create_output_transform', 'create_output_transforms',
    'get_transform_info', 'get_transforms_info', 'create_colorspaces'
]

# Matrix converting *ACES AP1* primaries to *ACES AP0*.
ACES_AP1_TO_AP0 = [
    0.6954522414, 0.1406786965, 0.1638690622, 0.0447945634, 0.8596711185,
    0.0955343182, -0.0055258826, 0.0040252103, 1.0015006723
]

# Matrix converting *ACES AP0* primaries to *ACES AP1*.
ACES_AP0_TO_AP1 = [
    1.4514393161, -0.2365107469, -0.2149285693, -0.0765537734, 1.1762296998,
    -0.0996759264, 0.0083161484, -0.0060324498, 0.9977163014
]

# Matrix converting *ACES AP0* primaries to *XYZ*.
ACES_AP0_TO_XYZ = [
    0.9525523959, 0.0000000000, 0.0000936786, 0.3439664498, 0.7281660966,
    -0.0721325464, 0.0000000000, 0.0000000000, 1.0088251844
]

# Matrix converting *ACES AP0* primaries to *XYZ*.
ACES_XYZ_TO_AP0 = [
    1.0498110175, 0.0000000000, -0.0000974845, -0.4959030231, 1.3733130458,
    0.0982400361, 0.0000000000, 0.0000000000, 0.9912520182
]


def create_ACES():
    """
    Creates the *ACES2065-1* reference colorspace.

    Returns
    -------
    ColorSpace
         *ACES2065-1* and all its identifying information.
    """

    # Defining the reference colorspace.
    aces2065_1 = ColorSpace('ACES2065-1')
    aces2065_1.description = (
        'The Academy Color Encoding System reference color space')
    aces2065_1.equality_group = ''
    aces2065_1.aliases = ['lin_ap0', 'aces']
    aces2065_1.family = 'ACES'
    aces2065_1.is_data = False
    aces2065_1.allocation_type = ocio.ALLOCATION_LG2
    aces2065_1.allocation_vars = [-8, 5, 0.00390625]

    return aces2065_1


def create_ACEScc(aces_ctl_directory,
                  lut_directory,
                  lut_resolution_1D,
                  cleanup,
                  name='ACEScc',
                  min_value=0,
                  max_value=1,
                  input_scale=1):
    """
    Creates the *ACEScc* reference colorspace.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    name : str or unicode, optional
        The name of the colorspace.
    min_value : float, optional
        The minimum value to consider for the colorspace.
    max_value : float, optional
        The maximum value to consider for the colorspace.
    input_scale : float, optional
        A scale factor to divide input values.

    Returns
    -------
    ColorSpace
         *ACEScc* and all its identifying information.
    """

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = ['acescc', 'acescc_ap1']
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False
    cs.allocation_type = ocio.ALLOCATION_UNIFORM
    cs.allocation_vars = [min_value, max_value]
    cs.aces_transform_id = 'ACEScsc.Academy.ACEScc_to_ACES'

    ctls = [
        os.path.join(aces_ctl_directory, 'csc', 'ACEScc',
                     'ACEScsc.Academy.ACEScc_to_ACES.ctl'),
        # This transform gets back to the *AP1* primaries.
        # Useful as the 1d LUT is only covering the transfer function.
        # The primaries switch is covered by the matrix below:
        os.path.join(aces_ctl_directory, 'csc', 'ACEScg',
                     'ACEScsc.Academy.ACES_to_ACEScg.ctl')
    ]
    lut = '{0}_to_linear.spi1d'.format(name)

    lut = sanitize(lut)

    generate_1D_LUT_from_CTL(
        os.path.join(lut_directory,
                     lut), ctls, lut_resolution_1D, 'float', input_scale, 1,
        {}, cleanup, aces_ctl_directory, min_value, max_value, 1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    # *AP1* primaries to *AP0* primaries
    cs.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix':
        mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction':
        'forward'
    })

    cs.from_reference_transforms = []
    return cs


def create_ACEScct(aces_ctl_directory,
                   lut_directory,
                   lut_resolution_1D,
                   cleanup,
                   name='ACEScct',
                   min_value=0,
                   max_value=1,
                   input_scale=1):
    """
    Creates the *ACEScct* reference colorspace.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    name : str or unicode, optional
        The name of the colorspace.
    min_value : float, optional
        The minimum value to consider for the colorspace.
    max_value : float, optional
        The maximum value to consider for the colorspace.
    input_scale : float, optional
        A scale factor to divide input values.

    Returns
    -------
    ColorSpace
         *ACEScc* and all its identifying information.
    """

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = ['acescct', 'acescct_ap1']
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False
    cs.allocation_type = ocio.ALLOCATION_UNIFORM
    cs.allocation_vars = [min_value, max_value]
    cs.aces_transform_id = 'ACEScsc.Academy.ACEScct_to_ACES'

    ctls = [
        os.path.join(aces_ctl_directory, 'csc', 'ACEScct',
                     'ACEScsc.Academy.ACEScct_to_ACES.ctl')
    ]

    # Removing the ACES to ACEScg transform for ACEScct only.
    # Including this transform allows us to isolate the ACEScct transfer
    # function from the change of gamut (AP1 to AP0) in the ACEScct to
    # ACES transform. The ACES to ACEScg transform clips values below 0
    # though. Since the ACEScct transfer function maps some values in the
    # normalized 0 to 1 range below 0, the clip in the ACES to ACEScg
    # transform is an issue when concatenated with the ACEScct to ACES
    # transform.
    #
    # # This transform gets back to the *AP1* primaries.
    # # Useful as the 1d LUT is only covering the transfer function.
    # # The primaries switch is covered by the matrix below:
    # os.path.join(aces_ctl_directory,
    #              'csc',
    #              'ACEScg',
    #              'ACEScsc.Academy.ACES_to_ACEScg.ctl')]

    lut = '{0}_to_linear.spi1d'.format(name)

    lut = sanitize(lut)

    generate_1D_LUT_from_CTL(
        os.path.join(lut_directory,
                     lut), ctls, lut_resolution_1D, 'float', input_scale, 1,
        {}, cleanup, aces_ctl_directory, min_value, max_value, 1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    # *AP1* primaries to *AP0* primaries
    cs.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix':
        mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction':
        'forward'
    })

    cs.from_reference_transforms = []
    return cs


def create_ACESproxy(aces_ctl_directory,
                     lut_directory,
                     lut_resolution_1D,
                     cleanup,
                     name='ACESproxy'):
    """
    Creates the *ACESproxy* colorspace.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    name : str or unicode, optional
        The name of the colorspace.

    Returns
    -------
    ColorSpace
         *ACESproxy* and all its identifying information.
    """

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = ['acesproxy', 'acesproxy_ap1']
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False

    cs.aces_transform_id = 'ACEScsc.Academy.ACESproxy10i_to_ACES'

    ctls = [
        os.path.join(aces_ctl_directory, 'csc', 'ACESproxy',
                     'ACEScsc.Academy.ACESproxy10i_to_ACES.ctl'),
        # This transform gets back to the *AP1* primaries.
        # Useful as the 1d LUT is only covering the transfer function.
        # The primaries switch is covered by the matrix below:
        os.path.join(aces_ctl_directory, 'csc', 'ACEScg',
                     'ACEScsc.Academy.ACES_to_ACEScg.ctl')
    ]
    lut = '{0}_to_linear.spi1d'.format(name)

    lut = sanitize(lut)

    generate_1D_LUT_from_CTL(
        os.path.join(lut_directory, lut), ctls, lut_resolution_1D, 'float', 1,
        1, {}, cleanup, aces_ctl_directory, 0, 1, 1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    # *AP1* primaries to *AP0* primaries
    cs.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix':
        mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction':
        'forward'
    })

    cs.from_reference_transforms = []
    return cs


# -------------------------------------------------------------------------
# *ACEScg*
# -------------------------------------------------------------------------
def create_ACEScg():
    """
    Creates the *ACEScg* colorspace.

    Returns
    -------
    ColorSpace
         *ACEScg* and all its identifying information.
    """

    name = 'ACEScg'

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = ['acescg', 'lin_ap1']
    cs.equality_group = ''
    cs.family = 'ACES'
    cs.is_data = False
    cs.allocation_type = ocio.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]

    cs.aces_transform_id = 'ACEScsc.Academy.ACEScg_to_ACES'

    cs.to_reference_transforms = []

    # *AP1* primaries to *AP0* primaries
    cs.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix':
        mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction':
        'forward'
    })

    cs.from_reference_transforms = []

    # Commented out because specifying the inverse matrix causes some
    # of OCIO's checks to see if a set of transforms can be collapsed
    # to fail.

    # *AP1* primaries to *AP0* primaries
    # cs.from_reference_transforms.append({
    #    'type': 'matrix',
    #    'matrix': mat44_from_mat33(ACES_AP0_TO_AP1),
    #    'direction': 'forward'})

    return cs


# -------------------------------------------------------------------------
# *ADX*
# -------------------------------------------------------------------------
def create_ADX(lut_directory, bit_depth=10, name='ADX'):
    """
    Creates the *ADX* colorspace.

    Parameters
    ----------
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    bit_depth : int
        Choose either 10 or 16 bit ADX.
    name : str or unicode, optional
        The name of the colorspace.

    Returns
    -------
    ColorSpace
         *ADX* and all its identifying information.
    """

    name = '{0}{1}'.format(name, bit_depth)
    cs = ColorSpace(name)
    cs.description = '{0} color space - used for film scans'.format(name)
    cs.aliases = ['adx{0}'.format(bit_depth)]
    cs.equality_group = ''
    cs.family = 'Input/ADX'
    cs.is_data = False

    if bit_depth == 10:
        cs.aces_transform_id = 'ACEScsc.Academy.ADX10_to_ACES'

        cs.bit_depth = ocio.BIT_DEPTH_UINT10
        ADX_to_CDD = [
            1023 / 500, 0, 0, 0, 0, 1023 / 500, 0, 0, 0, 0, 1023 / 500, 0, 0,
            0, 0, 1
        ]
        offset = [-95 / 500, -95 / 500, -95 / 500, 0]
    elif bit_depth == 16:
        cs.aces_transform_id = 'ACEScsc.Academy.ADX16_to_ACES'

        cs.bit_depth = ocio.BIT_DEPTH_UINT16
        ADX_to_CDD = [
            65535 / 8000, 0, 0, 0, 0, 65535 / 8000, 0, 0, 0, 0, 65535 / 8000,
            0, 0, 0, 0, 1
        ]
        offset = [-1520 / 8000, -1520 / 8000, -1520 / 8000, 0]

    cs.to_reference_transforms = []

    # Converting from *ADX* to *Channel-Dependent Density*.
    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': ADX_to_CDD,
        'offset': offset,
        'direction': 'forward'
    })

    # Converting from *Channel-Dependent Density* to
    # *Channel-Independent Density*.
    cs.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix': [
            0.75573, 0.22197, 0.02230, 0, 0.05901, 0.96928, -0.02829, 0,
            0.16134, 0.07406, 0.76460, 0, 0, 0, 0, 1
        ],
        'direction':
        'forward'
    })

    # Copied from *Alex Fry*'s *adx_cid_to_rle.py*
    def create_CID_to_RLE_LUT():
        def interpolate_1d(x, xp, fp):
            return np.interp(x, xp, fp)

        LUT_1D_XP = [
            -0.190000000000000, 0.010000000000000, 0.028000000000000,
            0.054000000000000, 0.095000000000000, 0.145000000000000,
            0.220000000000000, 0.300000000000000, 0.400000000000000,
            0.500000000000000, 0.600000000000000
        ]

        LUT_1D_FP = [
            -6.000000000000000, -2.721718645000000, -2.521718645000000,
            -2.321718645000000, -2.121718645000000, -1.921718645000000,
            -1.721718645000000, -1.521718645000000, -1.321718645000000,
            -1.121718645000000, -0.926545676714876
        ]

        REF_PT = ((7120 - 1520) / 8000 * (100 / 55) - math.log(0.18, 10))

        def cid_to_rle(x):
            if x <= 0.6:
                return interpolate_1d(x, LUT_1D_XP, LUT_1D_FP)
            return (100 / 55) * x - REF_PT

        def fit(value, from_min, from_max, to_min, to_max):
            if from_min == from_max:
                raise ValueError('from_min == from_max')
            return (value - from_min) / (from_max - from_min) * (
                to_max - to_min) + to_min

        num_samples = 2**12
        domain = (-0.19, 3)
        data = []
        for i in range(num_samples):
            x = i / (num_samples - 1)
            x = fit(x, 0, 1, domain[0], domain[1])
            data.append(cid_to_rle(x))

        lut = 'ADX_CID_to_RLE.spi1d'
        write_SPI_1D(
            os.path.join(lut_directory, lut), domain[0], domain[1], data,
            num_samples, 1)

        return lut

    # Converting *Channel Independent Density* values to
    # *Relative Log Exposure* values.
    lut = create_CID_to_RLE_LUT()
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    # Converting *Relative Log Exposure* values to
    # *Relative Exposure* values.
    cs.to_reference_transforms.append({
        'type': 'log',
        'base': 10,
        'direction': 'inverse'
    })

    # Convert *Relative Exposure* values to *ACES* values.
    cs.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix': [
            0.72286, 0.12630, 0.15084, 0, 0.11923, 0.76418, 0.11659, 0,
            0.01427, 0.08213, 0.90359, 0, 0, 0, 0, 1
        ],
        'direction':
        'forward'
    })

    cs.from_reference_transforms = []
    return cs


# -------------------------------------------------------------------------
# Generic *Log* Transform
# -------------------------------------------------------------------------
def create_generic_log(aces_ctl_directory,
                       lut_directory,
                       lut_resolution_1D,
                       cleanup,
                       name='log',
                       aliases=None,
                       min_value=0,
                       max_value=1,
                       input_scale=1,
                       middle_grey=0.18,
                       min_exposure=-6.5,
                       max_exposure=6.5):
    """
    Creates the *Generic Log* colorspace.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    name : str or unicode, optional
        The name of the colorspace.
    aliases : list of str or unicode, optional
        The alias names to use for the colorspace.
    min_value : float, optional
        The minimum value to consider for the colorspace.
    max_value : float, optional
        The maximum value to consider for the colorspace.
    input_scale : float, optional
        A scale factor to divide input values.
    middle_grey : float, optional
        The middle of the dynamic range covered by the transfer function.
    min_exposure : float, optional
        The offset from middle grey, in stops, that defines the low end of the
        dynamic range covered by the transfer function.
    max_exposure : float, optional
        The offset from middle grey, in stops, that defines the high end of
        the dynamic range covered by the transfer function.

    Returns
    -------
    ColorSpace
         *Generic Log* colorspace.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    ctls = [
        os.path.join(aces_ctl_directory, 'utilities',
                     'ACESutil.Log2_to_Lin_param.ctl')
    ]
    lut = '{0}_to_linear.spi1d'.format(name)

    lut = sanitize(lut)

    generate_1D_LUT_from_CTL(
        os.path.join(lut_directory, lut), ctls, lut_resolution_1D, 'float',
        input_scale, 1, {
            'middleGrey': middle_grey,
            'minExposure': min_exposure,
            'maxExposure': max_exposure
        }, cleanup, aces_ctl_directory, min_value, max_value, 1)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    cs.from_reference_transforms = []
    return cs


# -------------------------------------------------------------------------
# Base *Dolby PQ* Transform
# -------------------------------------------------------------------------
def create_DolbyPQ(aces_ctl_directory,
                   lut_directory,
                   lut_resolution_1D,
                   cleanup,
                   name='pq',
                   aliases=None,
                   min_value=0.0,
                   max_value=1.0,
                   input_scale=1.0):
    """
    Creates the generic *Dolby PQ* colorspace.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    name : str or unicode, optional
        The name of the colorspace.
    aliases : list of str or unicode, optional
        The alias names to use for the colorspace.
    min_value : float, optional
        The minimum value to consider for the colorspace.
    max_value : float, optional
        The maximum value to consider for the colorspace.
    input_scale : float, optional
        A scale factor to divide input values.

    Returns
    -------
    ColorSpace
         Generic *Dolby PQ* colorspace.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    ctls = [
        os.path.join(aces_ctl_directory, 'utilities',
                     'ACESutil.DolbyPQ_to_Lin.ctl')
    ]
    lut = '{0}_to_linear.spi1d'.format(name)

    lut = sanitize(lut)

    generate_1D_LUT_from_CTL(
        os.path.join(lut_directory,
                     lut), ctls, lut_resolution_1D, 'float', input_scale, 1.0,
        {}, cleanup, aces_ctl_directory, min_value, max_value)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    cs.from_reference_transforms = []
    return cs


# -------------------------------------------------------------------------
# *Dolby PQ* Transform - Fixed Linear Range
# -------------------------------------------------------------------------
def create_shaper_DolbyPQ(aces_ctl_directory,
                          lut_directory,
                          lut_resolution_1D,
                          cleanup,
                          name='pq',
                          aliases=None,
                          min_value=0.0,
                          max_value=1.0,
                          input_scale=1.0,
                          middle_grey=0.18,
                          min_exposure=-6.5,
                          max_exposure=6.5):
    """
    Creates a *Dolby PQ* colorspace that covers a specific dynamic range.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    name : str or unicode, optional
        The name of the colorspace.
    aliases : list of str or unicode, optional
        The alias names to use for the colorspace.
    min_value : float, optional
        The minimum value to consider for the colorspace.
    max_value : float, optional
        The maximum value to consider for the colorspace.
    input_scale : float, optional
        A scale factor to divide input values.
    middle_grey : float, optional
        The middle of the dynamic range covered by the transfer function.
    min_exposure : float, optional
        The offset from middle grey, in stops, that defines the low end of the
        dynamic range covered by the transfer function.
    max_exposure : float, optional
        The offset from middle grey, in stops, that defines the high end of
        the dynamic range covered by the transfer function.

    Returns
    -------
    ColorSpace
         A *Dolby PQ* colorspace that covers a specific dynamic range.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    ctls = [
        os.path.join(aces_ctl_directory, 'utilities',
                     'ACESutil.OCIOshaper_to_Lin_param.ctl')
    ]
    lut = '{0}_to_linear.spi1d'.format(name)

    lut = sanitize(lut)

    generate_1D_LUT_from_CTL(
        os.path.join(lut_directory, lut), ctls, lut_resolution_1D, 'float',
        input_scale, 1.0, {
            'middleGrey': middle_grey,
            'minExposure': min_exposure,
            'maxExposure': max_exposure
        }, cleanup, aces_ctl_directory, min_value, max_value)

    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'forward'
    })

    cs.from_reference_transforms = []
    return cs


def create_shapers_log2(aces_ctl_directory, lut_directory, lut_resolution_1D,
                        cleanup, shaper_name, middle_grey, min_exposure,
                        max_exposure):
    """
    Creates two *Log base 2* colorspaces, that cover a specific dynamic range.
    One has no gamut conversion. The other with has conversion from *ACES*
    *AP0* to *AP1*.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    shaper_name : str or unicode, optional
        The name of the colorspace.
    middle_grey : float
        The middle of the dynamic range covered by the transfer function.
    min_exposure : float
        The offset from middle grey, in stops, that defines the low end of the
        dynamic range covered by the transfer function.
    max_exposure : float
        The offset from middle grey, in stops, that defines the high end of
        the dynamic range covered by the transfer function.

    Returns
    -------
    ColorSpace
         A *Log base 2* colorspace that covers a specific dynamic range.
    """

    colorspaces = []
    shaper_data = {}

    # Defining the *Log 2* shaper for *ODTs covering 48 nit output*.
    log2_shaper_name = shaper_name
    log2_shaper_name_aliases = ['crv_{0}'.format(compact(log2_shaper_name))]
    log2_params = {
        'middleGrey': middle_grey,
        'minExposure': min_exposure,
        'maxExposure': max_exposure
    }

    log2_shaper_colorspace = create_generic_log(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1D,
        cleanup,
        name=log2_shaper_name,
        middle_grey=log2_params['middleGrey'],
        min_exposure=log2_params['minExposure'],
        max_exposure=log2_params['maxExposure'],
        aliases=log2_shaper_name_aliases)
    colorspaces.append(log2_shaper_colorspace)

    shaper_input_scale_generic_log2 = 1

    # *Log 2* shaper name and *CTL* transforms bundled up.
    log2_shaper_data = [
        log2_shaper_name,
        os.path.join('{0}', 'utilities', 'ACESutil.Log2_to_Lin_param.ctl'),
        os.path.join('{0}', 'utilities', 'ACESutil.Lin_to_Log2_param.ctl'),
        shaper_input_scale_generic_log2, log2_params
    ]

    shaper_data[log2_shaper_name] = log2_shaper_data

    # Defining the *Log2 shaper that includes the AP1* primaries.
    log2_shaper_api1_name = '{0} - AP1'.format(log2_shaper_name)
    log2_shaper_api1_colorspace = copy.deepcopy(log2_shaper_colorspace)

    log2_shaper_api1_colorspace.name = log2_shaper_api1_name
    log2_shaper_api1_colorspace.description = (
        'The {0} color space'.format(log2_shaper_api1_name))
    log2_shaper_api1_colorspace.aliases = [
        '{0}_ap1'.format(compact(log2_shaper_name))
    ]
    log2_shaper_api1_colorspace.equality_group = log2_shaper_api1_name

    # *AP1* primaries to *AP0* primaries
    log2_shaper_api1_colorspace.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix':
        mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction':
        'forward'
    })
    colorspaces.append(log2_shaper_api1_colorspace)

    return shaper_data, colorspaces


# -------------------------------------------------------------------------
# *Dolby PQ-based Shapers*
# -------------------------------------------------------------------------
def create_shapers_DolbyPQ(aces_ctl_directory, lut_directory,
                           lut_resolution_1D, cleanup, shaper_name,
                           middle_grey, min_exposure, max_exposure):
    """
    Creates two *Dolby PQ* colorspaces, that cover a specific dynamic range.
    One has no gamut conversion. The other with has conversion from *ACES*
    *AP0* to *AP1*.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    shaper_name : str or unicode, optional
        The name of the colorspace.
    middle_grey : float
        The middle of the dynamic range covered by the transfer function.
    min_exposure : float
        The offset from middle grey, in stops, that defines the low end of the
        dynamic range covered by the transfer function.
    max_exposure : float
        The offset from middle grey, in stops, that defines the high end of
        the dynamic range covered by the transfer function.

    Returns
    -------
    dict
        Values defining a Shaper.
    list of ColorSpaces
         A list of *Dolby PQ* colorspaces that covers a specific dynamic range.
    """

    colorspaces = []
    shaper_data = {}

    # Define the *Dolby PQ Shaper that considers a fixed linear range*
    dolby_pq_shaper_name = shaper_name
    dolby_pq_shaper_name_aliases = [
        'crv_{0}'.format(compact(dolby_pq_shaper_name))
    ]

    dolby_pq_params = {
        'middleGrey': middle_grey,
        'minExposure': min_exposure,
        'maxExposure': max_exposure
    }

    dolby_pq_shaper_colorspace = create_shaper_DolbyPQ(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1D,
        cleanup,
        name=dolby_pq_shaper_name,
        aliases=dolby_pq_shaper_name_aliases,
        middle_grey=dolby_pq_params['middleGrey'],
        min_exposure=dolby_pq_params['minExposure'],
        max_exposure=dolby_pq_params['maxExposure'])
    colorspaces.append(dolby_pq_shaper_colorspace)

    # *Dolby PQ* shaper name and *CTL* transforms bundled up.
    dolby_pq_shaper_data = [
        dolby_pq_shaper_name,
        os.path.join('{0}', 'utilities',
                     'ACESutil.OCIOshaper_to_Lin_param.ctl'),
        os.path.join('{0}', 'utilities',
                     'ACESutil.Lin_to_OCIOshaper_param.ctl'), 1.0,
        dolby_pq_params
    ]

    shaper_data[dolby_pq_shaper_name] = dolby_pq_shaper_data

    # Defining the *Dolby PQ shaper that includes the AP1* primaries.
    dolby_pq_shaper_api1_name = '{0} - AP1'.format(dolby_pq_shaper_name)
    dolby_pq_shaper_api1_colorspace = copy.deepcopy(dolby_pq_shaper_colorspace)

    dolby_pq_shaper_api1_colorspace.name = dolby_pq_shaper_api1_name
    dolby_pq_shaper_api1_colorspace.description = (
        'The {0} color space'.format(dolby_pq_shaper_api1_name))
    dolby_pq_shaper_api1_colorspace.aliases = [
        '{0}_ap1'.format(compact(dolby_pq_shaper_name))
    ]
    dolby_pq_shaper_api1_colorspace.equality_group = dolby_pq_shaper_api1_name

    # *AP1* primaries to *AP0* primaries
    dolby_pq_shaper_api1_colorspace.to_reference_transforms.append({
        'type':
        'matrix',
        'matrix':
        mat44_from_mat33(ACES_AP1_TO_AP0),
        'direction':
        'forward'
    })
    colorspaces.append(dolby_pq_shaper_api1_colorspace)

    return shaper_data, colorspaces


# -------------------------------------------------------------------------
# *Shapers*
# -------------------------------------------------------------------------
def create_shapers(aces_ctl_directory, lut_directory, lut_resolution_1D,
                   cleanup):
    """
    Creates sets of shaper colorspaces covering the *Log 2* and *Dolby PQ*
    transfer functions and dynamic ranges suitable for use with the 48 nit,
    1000 nit, 2000 nit and 4000 nit *ACES Output Transforms*.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.

    Returns
    -------
    list of dicts
        Values defining a set of Shapers.
    list of ColorSpaces
         A list of Shaper colorspaces that covers a varying dynamic ranges and
         transfer functions.
    """

    colorspaces = []
    shaper_data = {}

    # Define the base *Log2 48 nits shaper*
    # The original domain [-6.5, 6.5] has been extended to reduce artefacts
    # induced by over-exposure of highly saturated colours:
    # https://acescentral.com/t/aces-1-1-discussion-tell-us-what-you-think/1421/11
    # The new domain [-7.246068811667588, 10.273931188332412] makes the shaper
    # fit to *ACEScc* and was computed with *Colour*:
    # >>> np.log2(log_decoding_ACEScc([0, 1]) / 0.18)
    # array([-7.246068811667588, 10.273931188332412])
    (log2_48nits_shaper_data, log2_48nits_colorspaces) = create_shapers_log2(
        aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
        'Log2 48 nits Shaper', 0.18, -7.246068811667588, 10.273931188332412)
    colorspaces.extend(log2_48nits_colorspaces)
    shaper_data.update(log2_48nits_shaper_data)

    # Define the base *Log2 108 nits shaper*
    #
    (log2_108nits_shaper_data, log2_108nits_colorspaces) = create_shapers_log2(
        aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
        'Log2 108 nits Shaper', 0.18, -12.0, 8)
    colorspaces.extend(log2_108nits_colorspaces)
    shaper_data.update(log2_108nits_shaper_data)

    # Define the base *Log2 1000 nits shaper*
    #
    (log2_1000nits_shaper_data,
     log2_1000nits_colorspaces) = create_shapers_log2(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Log2 1000 nits Shaper', 0.18, -12.0, 10.0)
    colorspaces.extend(log2_1000nits_colorspaces)
    shaper_data.update(log2_1000nits_shaper_data)

    # Define the base *Log2 2000 nits shaper*
    #
    (log2_2000nits_shaper_data,
     log2_2000nits_colorspaces) = create_shapers_log2(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Log2 2000 nits Shaper', 0.18, -12.0, 11.0)
    colorspaces.extend(log2_2000nits_colorspaces)
    shaper_data.update(log2_2000nits_shaper_data)

    # Define the base *Log2 4000 nits shaper*
    #
    (log2_4000nits_shaper_data,
     log2_4000nits_colorspaces) = create_shapers_log2(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Log2 4000 nits Shaper', 0.18, -12.0, 12.0)
    colorspaces.extend(log2_4000nits_colorspaces)
    shaper_data.update(log2_4000nits_shaper_data)

    # Define the base *Dolby PQ transfer function*
    #
    dolby_pq_shaper_name = 'Dolby PQ 10000'
    dolby_pq_shaper_name_aliases = ['crv_{0}'.format('dolbypq_10000')]

    dolby_pq_shaper_colorspace = create_DolbyPQ(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1D,
        cleanup,
        name=dolby_pq_shaper_name,
        aliases=dolby_pq_shaper_name_aliases)
    colorspaces.append(dolby_pq_shaper_colorspace)

    # *Dolby PQ* shaper name and *CTL* transforms bundled up.
    dolby_pq_shaper_data = [
        dolby_pq_shaper_name,
        os.path.join('{0}', 'utilities', 'ACESutil.DolbyPQ_to_Lin.ctl'),
        os.path.join('{0}', 'utilities', 'ACESutil.Lin_to_DolbyPQ.ctl'), 1.0,
        {}
    ]

    shaper_data[dolby_pq_shaper_name] = dolby_pq_shaper_data

    # Define the *Dolby PQ 48 nits shaper*
    #
    (dolbypq_48nits_shaper_data,
     dolbypq_48nits_colorspaces) = create_shapers_DolbyPQ(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Dolby PQ 48 nits Shaper', 0.18, -6.5, 6.5)
    colorspaces.extend(dolbypq_48nits_colorspaces)
    shaper_data.update(dolbypq_48nits_shaper_data)

    # Define the *Dolby PQ 108 nits shaper*
    #
    (dolbypq_108nits_shaper_data,
     dolbypq_108nits_colorspaces) = create_shapers_DolbyPQ(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Dolby PQ 108 nits Shaper', 0.18, -12, 8)
    colorspaces.extend(dolbypq_108nits_colorspaces)
    shaper_data.update(dolbypq_108nits_shaper_data)

    # Define the *Dolby PQ 1000 nits shaper*
    #
    (dolbypq_1000nits_shaper_data,
     dolbypq_1000nits_colorspaces) = create_shapers_DolbyPQ(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Dolby PQ 1000 nits Shaper', 0.18, -12.0, 10.0)
    colorspaces.extend(dolbypq_1000nits_colorspaces)
    shaper_data.update(dolbypq_1000nits_shaper_data)

    # Define the *Dolby PQ 2000 nits shaper*
    #
    (dolbypq_2000nits_shaper_data,
     dolbypq_2000nits_colorspaces) = create_shapers_DolbyPQ(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Dolby PQ 2000 nits Shaper', 0.18, -12.0, 11.0)
    colorspaces.extend(dolbypq_2000nits_colorspaces)
    shaper_data.update(dolbypq_2000nits_shaper_data)

    # Define the *Dolby PQ 4000 nits shaper*
    #
    (dolbypq_4000nits_shaper_data,
     dolbypq_4000nits_colorspaces) = create_shapers_DolbyPQ(
         aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup,
         'Dolby PQ 4000 nits Shaper', 0.18, -12.0, 12.0)
    colorspaces.extend(dolbypq_4000nits_colorspaces)
    shaper_data.update(dolbypq_4000nits_shaper_data)

    return shaper_data, colorspaces


# -------------------------------------------------------------------------
# Individual *LMT*
# -------------------------------------------------------------------------
def create_blue_light_artifact_fix_LMT(lmt_name, lmt_values, aliases=None):
    """
    Creates the *Blue Light Artifact Fix* *ACES Look Transform (LMT)*
    colorspace.

    Parameters
    ----------
    lmt_name : str or unicode
        The name of the Look Transform (LMT).
    lmt_values : dict
        A collection of values that define the Look Transform's attributes and
        behavior.
    aliases : list of str or unicode, optional
        The alias names to use for the colorspace.

    Returns
    -------
    ColorSpace
         The *Blue Light Artifact Fix* *ACES LMT* colorspace.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace('{0}'.format(lmt_name))
    cs.description = 'The ACES Look Transform: {0}'.format(lmt_name)
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Utility/Look'
    cs.is_data = False
    cs.allocation_type = ocio.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]
    cs.aces_transform_id = lmt_values['transformID']

    pprint.pprint(lmt_values)

    # The matrix *M* is the *lmt/LMT.Academy.BlueLightArtifactFix.ctl* matrix
    # transposed.
    M = [
        0.9404372683, -0.0183068787, 0.0778696104, 0.0083786969, 0.8286599939,
        0.1629613092, 0.0005471261, -0.0008833746, 1.0003362486
    ]
    cs.to_reference_transforms = []

    cs.to_reference_transforms.append({
        'type': 'matrix',
        'matrix': mat44_from_mat33(M),
        'direction': 'inverse'
    })

    cs.from_reference_transforms = []

    return cs


def create_LMT(lmt_name,
               lmt_values,
               shaper_info,
               aces_ctl_directory,
               lut_directory,
               lut_resolution_3D=64,
               cleanup=True,
               aliases=None):
    """
    Creates an *ACES Look Transform (LMT)* colorspace.

    Parameters
    ----------
    lmt_name : str or unicode
        The name of the Look Transform (LMT).
    lmt_values : dict
        A collection of values that define the Look Transform's attributes and
        behavior.
    shaper_info : dict
        A collection of values that define the Shaper to use when generating
        LUTs to represent the Look Transform.
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_3D : int, optional
        The resolution of generated 3D LUTs.
    cleanup : bool, optional
        Whether or not to clean up the intermediate images.
    aliases : list of str or unicode, optional
        The alias names to use for the colorspace.

    Returns
    -------
    ColorSpace
         An *ACES LMT* colorspace.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace('{0}'.format(lmt_name))
    cs.description = 'The ACES Look Transform: {0}'.format(lmt_name)
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Utility/Look'
    cs.is_data = False
    cs.allocation_type = ocio.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]
    cs.aces_transform_id = lmt_values['transformID']

    pprint.pprint(lmt_values)

    # Generating the *shaper* transform.
    (shaper_name, shaper_to_aces_ctl, shaper_from_aces_ctl, shaper_input_scale,
     shaper_params) = shaper_info

    shaper_lut = '{0}_to_linear.spi1d'.format(shaper_name)
    shaper_lut = sanitize(shaper_lut)

    shaper_ocio_transform = {
        'type': 'lutFile',
        'path': shaper_lut,
        'interpolation': 'linear',
        'direction': 'inverse'
    }

    # Generating the forward transform.
    cs.from_reference_transforms = []

    if 'transformCTL' in lmt_values:
        ctls = [
            shaper_to_aces_ctl.format(aces_ctl_directory),
            os.path.join(aces_ctl_directory, lmt_values['transformCTL'])
        ]
        lut = '{0}.{1}.spi3d'.format(shaper_name, lmt_name)

        lut = sanitize(lut)

        generate_3D_LUT_from_CTL(
            os.path.join(lut_directory, lut), ctls, lut_resolution_3D, 'float',
            1 / shaper_input_scale, 1, shaper_params, cleanup,
            aces_ctl_directory)

        cs.from_reference_transforms.append(shaper_ocio_transform)
        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'
        })

    # Generating the inverse transform.
    cs.to_reference_transforms = []

    if 'transformCTLInverse' in lmt_values:
        ctls = [
            os.path.join(aces_ctl_directory,
                         lmt_values['transformCTLInverse']),
            shaper_from_aces_ctl.format(aces_ctl_directory)
        ]
        lut = 'Inverse.{0}.{1}.spi3d'.format(lmt_name, shaper_name)

        lut = sanitize(lut)

        generate_3D_LUT_from_CTL(
            os.path.join(lut_directory,
                         lut), ctls, lut_resolution_3D, 'half', 1,
            shaper_input_scale, shaper_params, cleanup, aces_ctl_directory, 0)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'
        })

        shaper_inverse = shaper_ocio_transform.copy()
        shaper_inverse['direction'] = 'forward'
        cs.to_reference_transforms.append(shaper_inverse)

    return cs


# -------------------------------------------------------------------------
# *LMTs*
# -------------------------------------------------------------------------
def create_LMTs(aces_ctl_directory, lut_directory, lut_resolution_1D,
                lut_resolution_3D, lmt_info, cleanup):
    """
    Create ColorSpaces representing the *ACES Look Transforms*.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    lut_resolution_3D : int
        The resolution of generated 3D LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    lmt_info : dict
        A collection of values that define the Look Transforms that need to be 
        generated.

    Returns
    -------
    list of ColorSpaces
         ColorSpaces representing the *ACES Look Transforms*.
    """

    colorspaces = []

    # -------------------------------------------------------------------------
    # *LMT Shaper*
    # -------------------------------------------------------------------------
    lmt_lut_resolution_1D = max(4096, lut_resolution_1D)
    lmt_lut_resolution_3D = max(65, lut_resolution_3D)

    # Defining the *Log 2* shaper.
    lmt_shaper_name = 'LMT Shaper'
    lmt_shaper_name_aliases = ['crv_lmtshaper']
    lmt_params = {'middleGrey': 0.18, 'minExposure': -10, 'maxExposure': 6.5}

    lmt_shaper = create_generic_log(
        aces_ctl_directory,
        lut_directory,
        lmt_lut_resolution_1D,
        cleanup,
        name=lmt_shaper_name,
        middle_grey=lmt_params['middleGrey'],
        min_exposure=lmt_params['minExposure'],
        max_exposure=lmt_params['maxExposure'],
        aliases=lmt_shaper_name_aliases)
    colorspaces.append(lmt_shaper)

    shaper_input_scale_generic_log2 = 1

    # *Log 2* shaper name and *CTL* transforms bundled up.
    lmt_shaper_data = [
        lmt_shaper_name,
        os.path.join('{0}', 'utilities', 'ACESutil.Log2_to_Lin_param.ctl'),
        os.path.join('{0}', 'utilities', 'ACESutil.Lin_to_Log2_param.ctl'),
        shaper_input_scale_generic_log2, lmt_params
    ]

    sorted_lmts = sorted(lmt_info.items(), key=lambda x: tuple(x[1].items()))
    print(sorted_lmts)
    for lmt in sorted_lmts:
        lmt_name, lmt_values = lmt
        lmt_aliases = [
            'look_{0}'.format(compact(lmt_values['transformUserName']))
        ]
        if lmt_values['transformUserName'] == 'Blue Light Artifact Fix':
            # Pragmatic special case for
            # *lmt/LMT.Academy.BlueLightArtifactFix.ctl* so that it is handled
            # as a *MatrixTransform* directly instead of a *LUT*.
            cs = create_blue_light_artifact_fix_LMT(
                lmt_values['transformUserName'], lmt_values, lmt_aliases)
        else:
            cs = create_LMT(lmt_values['transformUserName'], lmt_values,
                            lmt_shaper_data, aces_ctl_directory, lut_directory,
                            lmt_lut_resolution_3D, cleanup, lmt_aliases)
        colorspaces.append(cs)

    return colorspaces


# -------------------------------------------------------------------------
# *ACES Output Transform*.
# -------------------------------------------------------------------------
def create_output_transform(output_transform_name,
                            output_transform_values,
                            is_SSTS_based,
                            shaper_info,
                            aces_ctl_directory,
                            lut_directory,
                            lut_resolution_3D=64,
                            cleanup=True,
                            aliases=None):
    """
    Creates an *ACES Output Transform* colorspace.

    Parameters
    ----------
    output_transform_name : str or unicode
        The name of the *ACES Output Transform*.
    output_transform_values : dict
        A collection of values that define the *ACES Output Transform*'s
        attributes and behavior.
    is_SSTS_based : bool
        Whether the *ACES Output Transform* is an *ACES SSTS* or
        *ACES RRT + ODT*.
    shaper_info : dict
        A collection of values that define the Shaper to use when generating
        LUTs to represent the*ACES Output Transform*.
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_3D : int, optional
        The resolution of generated 3D LUTs.
    cleanup : bool, optional
        Whether or not to clean up the intermediate images.
    aliases : list of str or unicode, optional
        The alias names to use for the colorspace.

    Returns
    -------
    ColorSpace
         An *ACES Output Transform* colorspace.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace('{0}'.format(output_transform_name))
    cs.description = '{0} - {1} Output Transform'.format(
        output_transform_values['transformUserNamePrefix'],
        output_transform_name)
    cs.aliases = aliases
    cs.equality_group = ''
    cs.family = 'Output'
    cs.is_data = False

    cs.aces_transform_id = output_transform_values['transformID']

    pprint.pprint(output_transform_values)

    # Generating the *shaper* transform.
    (shaper_name, shaper_to_aces_ctl, shaper_from_aces_ctl, shaper_input_scale,
     shaper_params) = shaper_info

    if 'legalRange' in output_transform_values:
        shaper_params['legalRange'] = output_transform_values['legalRange']
    else:
        shaper_params['legalRange'] = 0

    shaper_lut = '{0}_to_linear.spi1d'.format(shaper_name)
    shaper_lut = sanitize(shaper_lut)

    shaper_ocio_transform = {
        'type': 'lutFile',
        'path': shaper_lut,
        'interpolation': 'linear',
        'direction': 'inverse'
    }

    # Generating the *forward* transform.
    cs.from_reference_transforms = []

    if 'transformLUT' in output_transform_values:
        transform_lut_file_name = os.path.basename(
            output_transform_values['transformLUT'])
        lut = os.path.join(lut_directory, transform_lut_file_name)
        shutil.copy(output_transform_values['transformLUT'], lut)

        cs.from_reference_transforms.append(shaper_ocio_transform)
        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': transform_lut_file_name,
            'interpolation': 'tetrahedral',
            'direction': 'forward'
        })
    elif 'transformCTL' in output_transform_values:
        if is_SSTS_based:
            ctls = [
                shaper_to_aces_ctl.format(aces_ctl_directory),
                os.path.join(aces_ctl_directory,
                             output_transform_values['transformCTL'])
            ]
            lut = '{0}.RRTODT.{1}.spi3d'.format(shaper_name,
                                                output_transform_name)
        else:
            ctls = [
                shaper_to_aces_ctl.format(aces_ctl_directory),
                os.path.join(aces_ctl_directory, 'rrt', 'RRT.ctl'),
                os.path.join(aces_ctl_directory, 'odt',
                             output_transform_values['transformCTL'])
            ]
            lut = '{0}.RRT.{1}.spi3d'.format(shaper_name,
                                             output_transform_name)

        lut = sanitize(lut)

        generate_3D_LUT_from_CTL(
            os.path.join(lut_directory, lut), ctls, lut_resolution_3D, 'float',
            1 / shaper_input_scale, 1, shaper_params, cleanup,
            aces_ctl_directory)

        cs.from_reference_transforms.append(shaper_ocio_transform)
        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'
        })

    # Generating the *inverse* transform.
    cs.to_reference_transforms = []

    if 'transformLUTInverse' in output_transform_values:
        transform_lut_inverse_file_name = os.path.basename(
            output_transform_values['transformLUTInverse'])
        lut = os.path.join(lut_directory, transform_lut_inverse_file_name)
        shutil.copy(output_transform_values['transformLUTInverse'], lut)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': transform_lut_inverse_file_name,
            'interpolation': 'tetrahedral',
            'direction': 'forward'
        })

        shaper_inverse = shaper_ocio_transform.copy()
        shaper_inverse['direction'] = 'forward'
        cs.to_reference_transforms.append(shaper_inverse)
    elif 'transformCTLInverse' in output_transform_values:
        if is_SSTS_based:
            ctls = [
                os.path.join(aces_ctl_directory,
                             output_transform_values['transformCTLInverse']),
                shaper_from_aces_ctl.format(aces_ctl_directory)
            ]
            lut = 'InvRRTODT.{0}.{1}.spi3d'.format(output_transform_name,
                                                   shaper_name)
        else:
            ctls = [
                os.path.join(aces_ctl_directory, 'odt',
                             output_transform_values['transformCTLInverse']),
                os.path.join(aces_ctl_directory, 'rrt', 'InvRRT.ctl'),
                shaper_from_aces_ctl.format(aces_ctl_directory)
            ]
            lut = 'InvRRT.{0}.{1}.spi3d'.format(output_transform_name,
                                                shaper_name)

        lut = sanitize(lut)

        generate_3D_LUT_from_CTL(
            os.path.join(lut_directory, lut), ctls, lut_resolution_3D, 'half',
            1, shaper_input_scale, shaper_params, cleanup, aces_ctl_directory)

        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'tetrahedral',
            'direction': 'forward'
        })

        shaper_inverse = shaper_ocio_transform.copy()
        shaper_inverse['direction'] = 'forward'
        cs.to_reference_transforms.append(shaper_inverse)

    return cs


# -------------------------------------------------------------------------
# *ACES Output Transforms*
# -------------------------------------------------------------------------
def create_output_transforms(aces_ctl_directory, lut_directory,
                             lut_resolution_1D, lut_resolution_3D,
                             output_transform_info, shaper_name, cleanup,
                             linear_display_space, log_display_space):
    """
    Create ColorSpaces representing the *ACES Output Transforms*.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    lut_resolution_3D : int
        The resolution of generated 3D LUTs.
    output_transform_info : dict
        A collection of values that define the Output Transforms that need to
        be generated.
    shaper_name : str or unicode, optional
        The name of Shaper colorspace to use when generating LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.
    linear_display_space : str or unicode
        The name of the colorspace to use for the raw or linear View.
    log_display_space : str or unicode
        The name of the colorspace to use for the log View.

    Returns
    -------
    list of ColorSpaces
         ColorSpaces representing the *ACES Output Transforms*.
    list of dicts
        Collections of names and ColorSpaces corresponding to the Displays and
        Views.
    """

    colorspaces = []
    displays = {}

    # -------------------------------------------------------------------------
    # *RRT / ODTs* and *SSTS OTs* Shaper Options
    # -------------------------------------------------------------------------
    shaper_data, shaper_colorspaces = create_shapers(
        aces_ctl_directory, lut_directory, lut_resolution_1D, cleanup)

    colorspaces.extend(shaper_colorspaces)

    # Assumes shaper has variants covering the range expected by the
    # 48, 108, 1000, 2000 and 4000 nits Output Transforms
    shaper_48nits = shaper_data[shaper_name]

    # Override 108, 1000, 2000 and 4000 nits to always use the PQ shapers
    pq_shaper_name = ('{0} {1}'.format('Dolby PQ', ' '.join(
        shaper_name.split(' ')[-3:])))
    shaper_108nits = shaper_data[pq_shaper_name.replace('48 nits', '108 nits')]
    shaper_1000nits = shaper_data[pq_shaper_name.replace(
        '48 nits', '1000 nits')]
    shaper_2000nits = shaper_data[pq_shaper_name.replace(
        '48 nits', '2000 nits')]
    shaper_4000nits = shaper_data[pq_shaper_name.replace(
        '48 nits', '4000 nits')]

    sorted_output_transforms = sorted(
        iter(output_transform_info.items()), key=lambda x: tuple(x[1].items()))

    for output_transform in sorted_output_transforms:
        output_transform_name, output_transform_values = output_transform

        output_transform_name_legal = output_transform_values[
            'transformUserName']
        output_transform_legal = output_transform_values.copy()
        output_transform_aliases = [
            'out_{0}'.format(compact(output_transform_name_legal))
        ]

        if output_transform_values['transformHasFullLegalSwitch']:
            output_transform_legal['legalRange'] = 0

        output_transform_is_ssts_based = output_transform_values[
            'transformIsSSTSBased']

        if '108 nits' in output_transform_name_legal:
            shaper = shaper_108nits
        elif '1000 nits' in output_transform_name_legal:
            shaper = shaper_1000nits
        elif '2000 nits' in output_transform_name_legal:
            shaper = shaper_2000nits
        elif '4000 nits' in output_transform_name_legal:
            shaper = shaper_4000nits
        else:
            shaper = shaper_48nits

        cs = create_output_transform(
            output_transform_name_legal, output_transform_legal,
            output_transform_is_ssts_based, shaper, aces_ctl_directory,
            lut_directory, lut_resolution_3D, cleanup,
            output_transform_aliases)
        colorspaces.append(cs)

        displays[output_transform_name_legal] = {
            'Raw': linear_display_space,
            'Log': log_display_space,
            'Output Transform': cs
        }

    return colorspaces, displays


def get_transform_info(ctl_transform):
    """
    Returns the information stored in first couple of lines of an official
    *ACES Transform* CTL file.

    Parameters
    ----------
    ctl_transform : str or unicode
        The path to the CTL file to be scraped.

    Returns
    -------
    tuple
         Combination of Transform ID, User Name, User Name Prefix,
         Full / Legal switch and whether it is *SSTS* based.
    """

    with open(ctl_transform, 'r') as fp:
        lines = fp.readlines()

    # Retrieving the *transform ID* and *User Name*.
    transform_id = None
    transform_user_name = None
    transform_user_name_prefix = None

    for line in lines:
        if transform_id is None and '</ACEStransformID>' in line:
            transform_id = line[3:].split('<')[1].split('>')[1].strip()

        if transform_user_name is None and '</ACESuserName>' in line:
            transform_user_name = '-'.join(
                line[3:].split('<')[1].split('>')[1].split('-')[1:]).strip()
            transform_user_name_prefix = (
                line[3:].split('<')[1].split('>')[1].split('-')[0].strip())

        if transform_id and transform_user_name:
            break

    # Figuring out if this transform has options for processing *full* and
    # *legal* ranges and whether in the case of an output transform it is
    # *SSTS* based.
    transform_full_legal_switch = False
    transform_is_SSTS_based = False
    for line in lines:
        line = line.strip()
        if 'input uniform bool legalRange = true' in line:
            transform_full_legal_switch = True
        elif 'outputTransform(' in line or 'invOutputTransform(' in line:
            transform_is_SSTS_based = True

    return (transform_id, transform_user_name, transform_user_name_prefix,
            transform_full_legal_switch, transform_is_SSTS_based)


def get_transforms_info(aces_ctl_directory, ctl_sub_directory,
                        has_sub_directories, transform_type):
    """
    Returns the information describing the names and CTL files associated with
    the *ACES Transforms* in a given *ACES* release.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to the base *ACES* transforms CTL directory, e.g.
        *aces-dev/transforms/ctl*.
    ctl_sub_directory : str or unicode
        The path to the *ACES* transforms CTL sub-directory, e.g. *odt*.
    has_sub_directories : bool
        Whether the *ACES* transforms CTL sub-directory has sub-directories.
    transform_type : str or unicode
        The *ACES* transforms CTL type, e.g. *ODT*.

    Returns
    -------
    dict of dicts
         Dict of dicts, one describing each *ACES Look Transform*.
    """

    # Credit to Alex Fry for the original approach here
    transform_dir = os.path.join(aces_ctl_directory, ctl_sub_directory)
    all_transforms = []
    for dir_name, subdir_list, file_list in os.walk(transform_dir):
        for fname in file_list:
            all_transforms.append((os.path.join(dir_name, fname)))

    transform_ctls = [
        x for x in all_transforms
        if ('Inv{0}'.format(transform_type) not in x) and (
            'README' not in x) and (os.path.split(x)[-1][0] != '.')
    ]

    transforms = {}

    for transform_ctl in transform_ctls:
        transform_tokens = os.path.split(transform_ctl)

        # Handling nested directories.
        transform_path_tokens = os.path.split(transform_tokens[-2])
        transform_dir = transform_path_tokens[-1]
        while transform_path_tokens[-2][-3:] != (
                ctl_sub_directory if has_sub_directories else 'ctl'):
            transform_path_tokens = os.path.split(transform_path_tokens[-2])
            transform_dir = os.path.join(transform_path_tokens[-1],
                                         transform_dir)

        # Building full name.
        transform_ctl = transform_tokens[-1]
        transform_name = '.'.join(transform_ctl.split('.')[1:-1])

        # Finding id, user name and user name prefix.
        transform_ctl_path = (os.path.join(
            aces_ctl_directory, ctl_sub_directory, transform_dir,
            transform_ctl) if has_sub_directories else os.path.join(
                aces_ctl_directory, transform_dir, transform_ctl))
        (transform_id, transform_user_name, transform_user_name_prefix,
         transform_full_legal_switch,
         transform_is_SSTS_based) = get_transform_info(transform_ctl_path)

        # Finding inverse.
        transform_ctl_inverse = 'Inv{0}.{1}.ctl'.format(
            transform_type, transform_name)
        if not os.path.exists(
                os.path.join(transform_tokens[-2], transform_ctl_inverse)):
            transform_ctl_inverse = None

        transforms[transform_name] = {}
        transforms[transform_name]['transformCTL'] = os.path.join(
            transform_dir, transform_ctl)
        if transform_ctl_inverse is not None:
            transforms[transform_name]['transformCTLInverse'] = os.path.join(
                transform_dir, transform_ctl_inverse)

        transforms[transform_name]['transformID'] = transform_id
        transforms[transform_name][
            'transformUserNamePrefix'] = transform_user_name_prefix
        transforms[transform_name]['transformUserName'] = transform_user_name
        transforms[transform_name][
            'transformHasFullLegalSwitch'] = transform_full_legal_switch
        transforms[transform_name][
            'transformIsSSTSBased'] = transform_is_SSTS_based

        forward_ctl = transforms[transform_name]['transformCTL']

        print('{0} : {1}'.format(transform_type, transform_name))
        print('\tTransform ID               : {0}'.format(transform_id))
        print('\tTransform User Name Prefix : {0}'.format(
            transform_user_name_prefix))
        print('\tTransform User Name        : {0}'.format(transform_user_name))
        print('\tHas Full / Legal Switch    : {0}'.format(
            transform_full_legal_switch))
        print('\tSSTS Based                 : {0}'.format(
            transform_is_SSTS_based))
        print('\tForward ctl                : {0}'.format(forward_ctl))
        if 'transformCTLInverse' in transforms[transform_name]:
            inverse_ctl = transforms[transform_name]['transformCTLInverse']
            print('\tInverse ctl                : {0}'.format(inverse_ctl))
        else:
            print('\tInverse ctl                : {0}'.format(None))

    print('\n')

    return transforms


def create_colorspaces(aces_ctl_directory, lut_directory, lut_resolution_1D,
                       lut_resolution_3D, lmts_info, odts_info, ssts_ots_info,
                       shaper_name, cleanup):
    """
    Generates the *ACES* colorspaces, displays and views.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    lut_resolution_3D : int
        The resolution of generated 3D LUTs.
    lmts_info : dict
        A collection of values that define the Look Transforms that need to be 
        generated.
    odts_info : dict
        A collection of values that define the Output Device Transforms that
        need to be generated.
    ssts_ots_info : dict
        A collection of values that define the Output Transforms that need to
        be generated.
    shaper_name : str or unicode, optional
        The name of Shaper colorspace to use when generating LUTs.
    cleanup : bool
        Whether or not to clean up the intermediate images.

    Returns
    -------
    tuple
         A collection of values defining:
            - the reference colorspace: ACES
            - a list of the colorspaces created
            - a list of the displays created
            - a list of the general log colorspace
            - a list of the role assignments
            - the name of the default display
    """

    colorspaces = []

    ACES = create_ACES()

    ACEScc = create_ACEScc(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1D,
        cleanup,
        min_value=-0.35840,
        max_value=1.468)
    colorspaces.append(ACEScc)

    ACEScct = create_ACEScct(
        aces_ctl_directory,
        lut_directory,
        lut_resolution_1D,
        cleanup,
        min_value=-0.24913611,
        max_value=1.468)
    colorspaces.append(ACEScct)

    ACESproxy = create_ACESproxy(aces_ctl_directory, lut_directory,
                                 lut_resolution_1D, cleanup)
    colorspaces.append(ACESproxy)

    ACEScg = create_ACEScg()
    colorspaces.append(ACEScg)

    ADX10 = create_ADX(lut_directory, bit_depth=10)
    colorspaces.append(ADX10)

    ADX16 = create_ADX(lut_directory, bit_depth=16)
    colorspaces.append(ADX16)

    lmts = create_LMTs(aces_ctl_directory, lut_directory, lut_resolution_1D,
                       lut_resolution_3D, lmts_info, cleanup)
    colorspaces.extend(lmts)

    odts, odt_displays = create_output_transforms(
        aces_ctl_directory, lut_directory, lut_resolution_1D,
        lut_resolution_3D, odts_info, shaper_name, cleanup, ACES, ACEScc)
    colorspaces.extend(odts)

    ssts_ots, ssts_ots_displays = create_output_transforms(
        aces_ctl_directory, lut_directory, lut_resolution_1D,
        lut_resolution_3D, ssts_ots_info, shaper_name, cleanup, ACES, ACEScc)
    colorspaces.extend(ssts_ots)

    displays = odt_displays
    displays.update(ssts_ots_displays)

    # TODO: Investigate if there is a way to retrieve these values from *CTL*.
    default_display = 'sRGB'
    color_picking = 'sRGB'

    roles = {
        'color_picking': color_picking,
        'color_timing': ACEScc.name,
        'compositing_log': ADX10.name,
        'data': '',
        'default': ACES.name,
        'matte_paint': ACEScc.name,
        'reference': '',
        'scene_linear': ACEScg.name,
        'texture_paint': ACEScc.name,
        'compositing_linear': ACEScg.name,
        'rendering': ACEScg.name
    }

    return ACES, colorspaces, displays, ACEScc, roles, default_display
