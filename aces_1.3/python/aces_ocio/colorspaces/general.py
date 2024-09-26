#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Implements support for general colorspaces conversions and transfer functions.
"""

from __future__ import division

import array
import copy
import os

import PyOpenColorIO as ocio

import aces_ocio.generate_lut as genlut
from aces_ocio.colorspaces import aces
from aces_ocio.utilities import ColorSpace, mat44_from_mat33

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
    'create_matrix_colorspace', 'create_transfer_colorspace',
    'create_matrix_plus_transfer_colorspace', 'create_gamma_colorspace',
    'create_matrix_plus_gamma_colorspace', 'linear_to_sRGB', 'sRGB_to_linear',
    'linear_to_Rec709', 'Rec709_to_linear', 'linear_to_Rec2020_10bit',
    'Rec2020_10bit_to_linear', 'linear_to_Rec2020_12bit',
    'Rec2020_12bit_to_linear', 'linear_to_Rec1886', 'Rec1886_to_linear',
    'create_colorspaces', 'create_raw'
]


# -------------------------------------------------------------------------
# *Matrix Transform*
# -------------------------------------------------------------------------
def create_matrix_colorspace(name='matrix',
                             from_reference_values=None,
                             to_reference_values=None,
                             aliases=None):
    """
    Creates a colorspace expressed as a single or multiple *MatrixTransform*.

    Parameters
    ----------
    name : str, optional
        Aliases for this colorspace
    from_reference_values : list of matrices
        List of matrices to convert from the reference colorspace to this
        colorspace.
    to_reference_values : list of matrices
        List of matrices to convert to the reference colorspace from this
        colorspace.
    aliases : list of str, optional
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
         A colorspace expressed as a single or multiple *MatrixTransform*.
    """

    if from_reference_values is None:
        from_reference_values = []

    if to_reference_values is None:
        to_reference_values = []

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables.
    cs.allocation_type = ocio.ALLOCATION_LG2
    cs.allocation_vars = [-8, 5, 0.00390625]

    cs.to_reference_transforms = []
    if to_reference_values:
        for matrix in to_reference_values:
            cs.to_reference_transforms.append({
                'type':
                'matrix',
                'matrix':
                mat44_from_mat33(matrix),
                'direction':
                'forward'
            })

    cs.from_reference_transforms = []
    if from_reference_values:
        for matrix in from_reference_values:
            cs.from_reference_transforms.append({
                'type':
                'matrix',
                'matrix':
                mat44_from_mat33(matrix),
                'direction':
                'forward'
            })

    return cs


# -------------------------------------------------------------------------
# *Transfer Function Transform*
# -------------------------------------------------------------------------
def create_transfer_colorspace(name='transfer',
                               transfer_function_name='transfer_function',
                               transfer_function=lambda x: x,
                               lut_directory='/tmp',
                               lut_resolution_1D=1024,
                               aliases=None):
    """
    Creates a colorspace expressed as a *FileTransform* transformation.

    Parameters
    ----------
    name : str, optional
        Aliases for this colorspace.
    transfer_function_name : str, optional
        The name of the transfer function.
    transfer_function : function, optional
        The transfer function to be evaluated.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    aliases : list of str
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
         A colorspace expressed as a *FileTransform* transformation.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    cs.allocation_type = ocio.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    # Sampling the transfer function.
    data = array.array('f', b'\0' * lut_resolution_1D * 4)
    for c in range(lut_resolution_1D):
        data[c] = transfer_function(c / (lut_resolution_1D - 1))

    # Writing the sampled data to a *LUT*.
    lut = 'linear_to_{0}.spi1d'.format(transfer_function_name)
    genlut.write_SPI_1D(
        os.path.join(lut_directory, lut), 0, 1, data, lut_resolution_1D, 1)

    # Creating the *to_reference* transforms.
    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type': 'lutFile',
        'path': lut,
        'interpolation': 'linear',
        'direction': 'inverse'
    })

    # Creating the *from_reference* transforms.
    cs.from_reference_transforms = []

    return cs


# -------------------------------------------------------------------------
# *Transfer Function + Matrix Transform*
# -------------------------------------------------------------------------
def create_matrix_plus_transfer_colorspace(
        name='matrix_plus_transfer',
        transfer_function_name='transfer_function',
        transfer_function=lambda x: x,
        lut_directory='/tmp',
        lut_resolution_1D=1024,
        from_reference_values=None,
        to_reference_values=None,
        aliases=None):
    """
    Creates a colorspace expressed as a single or multiple *MatrixTransform*
    and 1D LUT *FileTransform* transformations.

    Parameters
    ----------
    name : str, optional
        Aliases for this colorspace.
    transfer_function_name : str, optional
        The name of the transfer function.
    transfer_function : function, optional
        The transfer function to be evaluated.
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int
        The resolution of generated 1D LUTs.
    from_reference_values : list of matrices
        List of matrices to convert from the reference colorspace to this
        colorspace.
    to_reference_values : list of matrices
        List of matrices to convert to the reference colorspace from this
        colorspace.
    aliases : list of str
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
         A colorspace expressed as a single or multiple *MatrixTransform* and
         1D LUT *FileTransform* transformations.
    """

    if from_reference_values is None:
        from_reference_values = []

    if to_reference_values is None:
        to_reference_values = []

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables.
    cs.allocation_type = ocio.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    # Sampling the transfer function.
    data = array.array('f', b'\0' * lut_resolution_1D * 4)
    for c in range(lut_resolution_1D):
        data[c] = transfer_function(c / (lut_resolution_1D - 1))

    # Writing the sampled data to a *LUT*.
    lut = 'linear_to_{0}.spi1d'.format(transfer_function_name)
    genlut.write_SPI_1D(
        os.path.join(lut_directory, lut), 0, 1, data, lut_resolution_1D, 1)

    # Creating the *to_reference* transforms.
    cs.to_reference_transforms = []
    if to_reference_values:
        cs.to_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'inverse'
        })

        for matrix in to_reference_values:
            cs.to_reference_transforms.append({
                'type':
                'matrix',
                'matrix':
                mat44_from_mat33(matrix),
                'direction':
                'forward'
            })

    # Creating the *from_reference* transforms.
    cs.from_reference_transforms = []
    if from_reference_values:
        for matrix in from_reference_values:
            cs.from_reference_transforms.append({
                'type':
                'matrix',
                'matrix':
                mat44_from_mat33(matrix),
                'direction':
                'forward'
            })

        cs.from_reference_transforms.append({
            'type': 'lutFile',
            'path': lut,
            'interpolation': 'linear',
            'direction': 'forward'
        })

    return cs


# -------------------------------------------------------------------------
# *Gamma Function Transform*
# -------------------------------------------------------------------------
def create_gamma_colorspace(name='gamma', gamma_value=1.0, aliases=None):
    """
    Creates a colorspace expressed as an *ExponentTransform* transformation.

    Parameters
    ----------
    name : str, optional
        Aliases for this colorspace.
    gamma_value : function, optional
        The gamma value.
    aliases : list of str
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
         A colorspace expressed as an *ExponentTransform* transformation.
    """

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    # A linear space needs allocation variables.
    cs.allocation_type = ocio.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    # Creating the *to_reference* transforms.
    cs.to_reference_transforms = []
    cs.to_reference_transforms.append({
        'type':
        'exponent',
        'value': [gamma_value, gamma_value, gamma_value, 1]
    })

    # Creating the *from_reference* transforms.
    cs.from_reference_transforms = []

    return cs


# -------------------------------------------------------------------------
# *Gamma Function + Matrix Transform*
# -------------------------------------------------------------------------
def create_matrix_plus_gamma_colorspace(name='matrix_plus_gamma',
                                        gamma_value=1.0,
                                        from_reference_values=None,
                                        to_reference_values=None,
                                        aliases=None):
    """
    Creates a colorspace expressed as a single or multiple *MatrixTransform*
    and an *ExponentTransform* transformations.

    Parameters
    ----------
    name : str, optional
        Aliases for this colorspace.
    gamma_value : function, optional
        The gamma value.
    from_reference_values : list of matrices
        List of matrices to convert from the reference colorspace to this
        colorspace.
    to_reference_values : list of matrices
        List of matrices to convert to the reference colorspace from this
        colorspace.
    aliases : list of str
        Aliases for this colorspace.

    Returns
    -------
    ColorSpace
        A colorspace expressed as a single or multiple *MatrixTransform* and an
        *ExponentTransform* transformations.
    """

    if from_reference_values is None:
        from_reference_values = []

    if to_reference_values is None:
        to_reference_values = []

    if aliases is None:
        aliases = []

    cs = ColorSpace(name)
    cs.description = 'The {0} color space'.format(name)
    cs.aliases = aliases
    cs.equality_group = name
    cs.family = 'Utility'
    cs.is_data = False

    cs.allocation_type = ocio.ALLOCATION_UNIFORM
    cs.allocation_vars = [0, 1]

    # Creating the *to_reference* transforms.
    cs.to_reference_transforms = []
    if to_reference_values:
        cs.to_reference_transforms.append({
            'type':
            'exponent',
            'value': [gamma_value, gamma_value, gamma_value, 1]
        })

        for matrix in to_reference_values:
            cs.to_reference_transforms.append({
                'type':
                'matrix',
                'matrix':
                mat44_from_mat33(matrix),
                'direction':
                'forward'
            })

    # Creating the *from_reference* transforms.
    cs.from_reference_transforms = []
    if from_reference_values:
        for matrix in from_reference_values:
            cs.from_reference_transforms.append({
                'type':
                'matrix',
                'matrix':
                mat44_from_mat33(matrix),
                'direction':
                'forward'
            })

        cs.from_reference_transforms.append({
            'type':
            'exponent',
            'value':
            [1.0 / gamma_value, 1.0 / gamma_value, 1.0 / gamma_value, 1]
        })

    return cs


# Transfer functions for standard colorspaces.
def linear_to_sRGB(L):
    """
    The *sRGB (IEC 61966-2-1)* encoding transfer function.

    Parameters
    ----------
    L : float
        *Luminance* :math:`L` of the image.

    Returns
    -------
    float
        A converted value.
    """

    if L <= 0.0031308:
        return L * 12.92
    else:
        return 1.055 * pow(L, 1.0 / 2.4) - 0.055


def sRGB_to_linear(V):
    """
    The *sRGB (IEC 61966-2-1)* decoding transfer function.

    Parameters
    ----------
    V : float
         Electrical signal :math:`V`.

    Returns
    -------
    float
        A converted value.
    """

    if V < linear_to_sRGB(0.0031308):
        return V / 12.92
    else:
        return pow((V + 0.055) / 1.055, 2.4)


def linear_to_Rec709(L):
    """
    The *Rec.709* encoding transfer function.

    Parameters
    ----------
    L : float
        *Luminance* :math:`L` of the image.

    Returns
    -------
    float
        A converted value.
    """

    if L < 0.018:
        return L * 4.5
    else:
        return 1.099 * pow(L, 0.45) - 0.099


def Rec709_to_linear(E):
    """
    The *Rec.709* decoding transfer function.

    Parameters
    ----------
    E : float
        Electrical signal :math:`E`.

    Returns
    -------
    float
        A converted value.
    """

    if E < linear_to_Rec709(0.018):
        return E / 4.5
    else:
        return pow((E + 0.099) / 1.099, 1.0 / 0.45)


def linear_to_Rec2020_10bit(E):
    """
    The *Rec.2020* 10-bit encoding transfer function.

    Parameters
    ----------
    E : float
        Voltage :math:`E` normalised by the reference white level and
        proportional to the implicit light intensity that would be detected
        with a reference camera colour channel R, G, B.

    Returns
    -------
    float
        A converted value.
    """

    if E < 0.018:
        return E * 4.5
    else:
        return 1.099 * pow(E, 0.45) - (1.099 - 1)


def Rec2020_10bit_to_linear(E_p):
    """
    The *Rec.2020* 10-bit decoding transfer function.

    Parameters
    ----------
    E_p : float
        Non-linear signal :math:`E'`.

    Returns
    -------
    float
        A converted value.
    """

    if E_p < linear_to_Rec2020_10bit(0.018):
        return E_p / 4.5
    else:
        return pow((E_p + 0.099) / 1.099, 1.0 / 0.45)


def linear_to_Rec2020_12bit(E):
    """
    The *Rec.2020* 12-bit encoding transfer function.

    Parameters
    ----------
    E : float
        Voltage :math:`E` normalised by the reference white level and
        proportional to the implicit light intensity that would be detected
        with a reference camera colour channel R, G, B.

    Returns
    -------
    float
        A converted value.
    """

    if E < 0.0181:
        return E * 4.5
    else:
        return 1.0993 * pow(E, 0.45) - (1.0993 - 1)


def Rec2020_12bit_to_linear(E_p):
    """
    The *Rec.2020* 12-bit decoding transfer function.

    Parameters
    ----------
    E_p : float
        Non-linear signal :math:`E'`.

    Returns
    -------
    float
        A converted value.
    """

    if E_p < linear_to_Rec2020_10bit(0.0181):
        return E_p / 4.5
    else:
        return pow((E_p + 0.0993) / 1.0993, 1.0 / 0.45)


def linear_to_Rec1886(L, L_B=0, L_W=1):
    """
    The *Rec.1886* encoding transfer function.

    Parameters
    ----------
    L : numeric or array_like
        Screen luminance in :math:`cd/m^2`.
    L_B : numeric, optional
        Screen luminance for black.
    L_W : numeric, optional
        Screen luminance for white.

    Returns
    -------
    float
        A converted value.
    """

    gamma = 2.40
    gamma_d = 1.0 / gamma

    n = L_W**gamma_d - L_B**gamma_d
    a = n**gamma
    b = L_B**gamma_d / n

    V = (L / a)**gamma_d - b

    return V


def Rec1886_to_linear(V, L_B=0, L_W=1):
    """
    The *Rec.1886* decoding transfer function.

    Parameters
    ----------
    V : numeric or array_like
        Input video signal level (normalised, black at :math:`V = 0`, to white
        at :math:`V = 1`. For content mastered per
        *Recommendation ITU-R BT.709*, 10-bit digital code values :math:`D` map
        into values of :math:`V` per the following equation:
        :math:`V = (D-64)/876`
    L_B : numeric, optional
        Screen luminance for black.
    L_W : numeric, optional
        Screen luminance for white.

    Returns
    -------
    float
        A converted value.
    """

    gamma = 2.40
    gamma_d = 1.0 / gamma

    n = L_W**gamma_d - L_B**gamma_d
    a = n**gamma
    b = L_B**gamma_d / n
    L = a * max(V + b, 0)**gamma

    return L


def create_colorspaces(lut_directory, lut_resolution_1D=1024):
    """
    Generates the colorspace conversions.

    Parameters
    ----------
    lut_directory : str or unicode 
        The directory to use when generating LUTs.
    lut_resolution_1D : int, optional
        The resolution of generated 1D LUTs.

    Returns
    -------
    list
         A list of colorspaces for general colorspaces and encodings.
    """

    colorspaces = []

    # -------------------------------------------------------------------------
    # XYZ
    # -------------------------------------------------------------------------
    cs = create_matrix_colorspace(
        'XYZ - D60',
        to_reference_values=[aces.ACES_XYZ_TO_AP0],
        from_reference_values=[aces.ACES_AP0_TO_XYZ],
        aliases=['lin_xyz_d60'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # P3-D60
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *P3D60* primaries
    XYZ_to_P3D60 = [
        2.4027414142, -0.8974841639, -0.3880533700, -0.8325796487,
        1.7692317536, 0.0237127115, 0.0388233815, -0.0824996856, 1.0363685997
    ]

    cs = create_matrix_colorspace(
        'Linear - P3-D60',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3D60],
        aliases=['lin_p3d60'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # P3-D65
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *P3D65* primaries
    XYZ_to_P3D65 = [
        2.46741247, -0.94626093, -0.40077353, -0.83221072, 1.77089071,
        0.02171988, 0.03890671, -0.08141143, 1.03521109
    ]

    cs = create_matrix_colorspace(
        'Linear - P3-D65',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3D65],
        aliases=['lin_p3d65'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # P3-DCI
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *P3DCI* primaries, using Bradford chromatic
    # adaptation
    XYZ_to_P3DCI = [
        2.66286135, -1.11031783, -0.42271635, -0.82282376, 1.75861704,
        0.02502194, 0.03932561, -0.08383448, 1.0372175
    ]

    cs = create_matrix_colorspace(
        'Linear - P3-DCI',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_P3DCI],
        aliases=['lin_p3dci'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # sRGB
    # -------------------------------------------------------------------------
    # *sRGB* and *Rec 709* use the same gamut.

    # *ACES* to *Linear*, *Rec. 709* primaries, D65 white point, using
    # Bradford chromatic adaptation
    XYZ_to_Rec709 = [
        3.20959735, -1.55742955, -0.49580497, -0.97098887, 1.88517118,
        0.03948941, 0.05971934, -0.21010444, 1.14312482
    ]

    cs = create_matrix_colorspace(
        'Linear - sRGB',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['lin_srgb'])
    colorspaces.append(cs)

    # *Linear* to *sRGB* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - sRGB',
        'sRGB',
        linear_to_sRGB,
        lut_directory,
        lut_resolution_1D,
        aliases=['crv_srgb'])
    colorspaces.append(cs)

    # *ACES* to *sRGB* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'sRGB - Texture',
        'sRGB',
        linear_to_sRGB,
        lut_directory,
        lut_resolution_1D,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['srgb_texture'])
    colorspaces.append(cs)

    # Keep a reference to this space
    cs_srgb = copy.deepcopy(cs)
    cs_srgb.name = "sRGB - Texture"
    cs_srgb.family = "Input/Generic"
    cs_srgb.aliases = []

    # -------------------------------------------------------------------------
    # Rec 709
    # -------------------------------------------------------------------------
    # *sRGB* and *Rec. 709* use the same primaries.
    cs = create_matrix_colorspace(
        'Linear - Rec.709',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['lin_rec709'])
    colorspaces.append(cs)

    # *Linear* to *Rec. 709* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - Rec.709',
        'rec709',
        linear_to_Rec709,
        lut_directory,
        lut_resolution_1D,
        aliases=['crv_rec709'])
    colorspaces.append(cs)

    # *ACES* to *Rec. 709* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.709 - Camera',
        'rec709',
        linear_to_Rec709,
        lut_directory,
        lut_resolution_1D,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['rec709_camera'])
    colorspaces.append(cs)

    # *ACES* to *Rec.709* Primaries + Gamma 2.2*
    cs = create_matrix_plus_gamma_colorspace(
        'Gamma 2.2 - Rec.709 - Texture',
        2.2,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['g22_rec709'])
    cs.description = (
        'The Gamma 2.2 - Rec.709 color space for importing certain textures.')
    colorspaces.append(cs)

    # *ACES* to *Rec.709* Primaries + Gamma 1.8*
    cs = create_matrix_plus_gamma_colorspace(
        'Gamma 1.8 - Rec.709 - Texture',
        1.8,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['g18_rec709'])
    cs.description = (
        'The Gamma 1.8 - Rec.709 color space for importing certain textures.')
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Rec 2020
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Rec. 2020* primaries, D65 white point, using
    # Bradford chromatic adaptation
    XYZ_to_Rec2020 = [
        1.69662619, -0.36551982, -0.24857099, -0.67039877, 1.62348187,
        0.01503821, 0.02063163, -0.04775634, 1.01910818
    ]

    cs = create_matrix_colorspace(
        'Linear - Rec.2020',
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=['lin_rec2020'])
    colorspaces.append(cs)

    # *Linear* to *Rec. 2020 10 bit* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - Rec.2020',
        'rec2020',
        linear_to_Rec2020_10bit,
        lut_directory,
        lut_resolution_1D,
        aliases=['crv_rec2020'])
    colorspaces.append(cs)

    # *ACES* to *Rec. 2020 10 bit* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.2020 - Camera',
        'rec2020',
        linear_to_Rec2020_10bit,
        lut_directory,
        lut_resolution_1D,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=['rec2020_camera'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Rec 1886
    # -------------------------------------------------------------------------
    # *Linear* to *Rec.1886* Transfer Function*
    cs = create_transfer_colorspace(
        'Curve - Rec.1886',
        'rec1886',
        linear_to_Rec1886,
        lut_directory,
        lut_resolution_1D,
        aliases=['crv_rec1886'])
    colorspaces.append(cs)

    # *ACES* to *Rec. 709* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.709 - Display',
        'rec1886',
        linear_to_Rec1886,
        lut_directory,
        lut_resolution_1D,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec709],
        aliases=['rec709_display'])
    colorspaces.append(cs)

    # *ACES* to *Rec. 2020* Primaries + Transfer Function*
    cs = create_matrix_plus_transfer_colorspace(
        'Rec.2020 - Display',
        'rec1886',
        linear_to_Rec1886,
        lut_directory,
        lut_resolution_1D,
        from_reference_values=[aces.ACES_AP0_TO_XYZ, XYZ_to_Rec2020],
        aliases=['rec2020_display'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # ProPhoto
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Pro Photo* primaries, D50 white point, using
    # Bradford chromatic adaptation
    AP0_to_RIMM = [
        1.2412367771, -0.1685692287, -0.0726675484, 0.0061203066, 1.083151174,
        -0.0892714806, -0.0032853314, 0.0099796402, 0.9933056912
    ]

    cs = create_matrix_colorspace(
        'Linear - RIMM ROMM (ProPhoto)',
        from_reference_values=[AP0_to_RIMM],
        aliases=['lin_prophoto', 'lin_rimm'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Adobe RGB
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Adobe RGB* primaries, D65 white point, using
    # Bradford chromatic adaptation
    AP0_to_ADOBERGB = [
        1.7245603168, -0.4199935942, -0.3045667227, -0.2764799142,
        1.3727190877, -0.0962391734, -0.0261255258, -0.0901747807, 1.1163003065
    ]

    cs = create_matrix_colorspace(
        'Linear - Adobe RGB',
        from_reference_values=[AP0_to_ADOBERGB],
        aliases=['lin_adobergb'])
    colorspaces.append(cs)

    # -------------------------------------------------------------------------
    # Adobe Wide Gamut RGB
    # -------------------------------------------------------------------------
    # *ACES* to *Linear*, *Adobe Wide Gamut RGB* primaries, D50 white point,
    # using Bradford chromatic adaptation
    AP0_to_ADOBEWIDEGAMUT = [
        1.3809814778, -0.1158594573, -0.2651220205, 0.0057015535, 1.0402949043,
        -0.0459964578, -0.0038908746, -0.0597091815, 1.0636000561
    ]

    cs = create_matrix_colorspace(
        'Linear - Adobe Wide Gamut RGB',
        from_reference_values=[AP0_to_ADOBEWIDEGAMUT],
        aliases=['lin_adobewidegamutrgb'])
    colorspaces.append(cs)

    # Alphabetize the color spaces, based on name
    colorspaces = sorted(colorspaces, key=lambda e: e.name)

    # -------------------------------------------------------------------------
    # sRGB - Input Colorspace
    # -------------------------------------------------------------------------
    # A copy of the sRGB - Texture space that is part of the Input family

    # Make this the first colorspace. in the list
    colorspaces.insert(0, cs_srgb)

    # -------------------------------------------------------------------------
    # Role assignments
    # -------------------------------------------------------------------------
    role_overrides = {'matte_paint': cs_srgb.name}

    return colorspaces, role_overrides


def create_raw():
    """
    Creates the *raw* colorspace.

    Returns
    -------
    ColorSpace
         *raw* and all its identifying information.
    """

    # *Raw* utility space
    name = 'Raw'
    raw = ColorSpace(name)
    raw.description = 'The {0} color space'.format(name)
    raw.aliases = ['raw']
    raw.equality_group = name
    raw.family = 'Utility'
    raw.is_data = True

    return raw
