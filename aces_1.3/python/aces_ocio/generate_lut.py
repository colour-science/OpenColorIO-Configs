#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Defines objects to generate various kind of 1D and 3D LUTs in various file
formats.
"""

from __future__ import division

import array
import numpy as np
import os
import re

import OpenImageIO as oiio

from aces_ocio.process import Process

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
    'remove_nans_from_file', 'generate_1D_LUT_image', 'write_SPI_1D',
    'write_CSP_1D', 'write_CTL_1D', 'write_1D', 'generate_1D_LUT_from_image',
    'generate_3D_LUT_image', 'generate_3D_LUT_from_image',
    'apply_CTL_to_image', 'convert_bit_depth', 'generate_1D_LUT_from_CTL',
    'correct_LUT_image', 'generate_3D_LUT_from_CTL', 'main'
]


def remove_nans_from_file(filename):
    """
    Removes NaNs from given file.

    Parameters
    ----------
    filename : str or unicode
        File to remove the NaNs from.
    """

    with open(filename, 'r') as reader:
        content = re.sub('-?nan', '0', reader.read(), flags=re.IGNORECASE)

    with open(filename, 'w') as writer:
        writer.write(content)


def generate_1D_LUT_image(ramp_1d_path,
                          resolution=1024,
                          min_value=0,
                          max_value=1):
    """
    Generates a 1D LUT image, i.e. a simple ramp, going from the min_value to 
    the max_value.

    Parameters
    ----------
    ramp_1d_path : str or unicode
        The path of the 1D ramp image to be written.
    resolution : int, optional
        The resolution of the 1D ramp image to be written.
    min_value : float, optional
        The lowest value in the 1D ramp.
    max_value : float, optional
        The highest value in the 1D ramp.
    """

    ramp = oiio.ImageOutput.create(ramp_1d_path)

    spec = oiio.ImageSpec()
    spec.set_format(oiio.FLOAT)
    # spec.format.basetype = oiio.FLOAT
    spec.width = resolution
    spec.height = 1
    spec.nchannels = 3

    ramp.open(ramp_1d_path, spec)

    data = array.array('f',
                       b'\0' * spec.width * spec.height * spec.nchannels * 4)
    for i in range(resolution):
        value = float(i) / (resolution - 1) * (
            max_value - min_value) + min_value
        data[i * spec.nchannels + 0] = value
        data[i * spec.nchannels + 1] = value
        data[i * spec.nchannels + 2] = value

    ramp.write_image(data)
    ramp.close()


def write_SPI_1D(filename,
                 from_min,
                 from_max,
                 data,
                 entries,
                 channels,
                 components=3):
    """
    Writes a 1D LUT in the *Sony Pictures Imageworks* .spi1d format.

    Credit to *Alex Fry* for the original single channel version of the spi1d
    writer.

    Parameters
    ----------
    filename : str or unicode
        The path of the 1D LUT to be written.
    from_min : float
        The lowest value in the 1D ramp.
    from_max : float
        The highest value in the 1D ramp.
    data : array of floats
        The entries in the LUT.
    entries : int
        The resolution of the LUT, i.e. number of entries in the data set.
    channels : int
        The number of channels in the data.
    components : int, optional
        The number of channels in the data to actually write.
    """

    data = np.squeeze(data)
    if data.ndim == 1:
        data = data[..., np.newaxis]

    # May want to use fewer components than there are channels in the data
    # Most commonly used for single channel LUTs
    components = min(3, components, channels)

    with open(filename, 'w') as fp:
        fp.write('Version 1\n')
        fp.write('From {0} {1}\n'.format(from_min, from_max))
        fp.write('Length {0}\n'.format(entries))
        fp.write('Components {0}\n'.format(components))
        fp.write('{\n')
        for i in range(0, entries):
            entry = ''
            for j in range(0, components):
                entry = '{0} {1:.10e}'.format(entry, data[i, j])
            fp.write('{0}\n'.format(entry))
        fp.write('}\n')


def write_CSP_1D(filename,
                 from_min,
                 from_max,
                 data,
                 entries,
                 channels,
                 components=3):
    """
    Writes a 1D LUT in the *Rising Sun Research Cinespace* .csp format.

    Parameters
    ----------
    filename : str or unicode
        The path of the 1D LUT to be written.
    from_min : float
        The lowest value in the 1D ramp.
    from_max : float
        The highest value in the 1D ramp.
    data : array of floats
        The entries in the LUT.
    entries : int
        The resolution of the LUT, i.e. number of entries in the data set.
    channels : int
        The number of channels in the data.
    components : int, optional
        The number of channels in the data to actually write.
    """

    data = np.squeeze(data)
    if data.ndim == 1:
        data = data[..., np.newaxis]

    # May want to use fewer components than there are channels in the data
    # Most commonly used for single channel LUTs
    components = min(3, components, channels)

    with open(filename, 'w') as fp:
        fp.write('CSPLUTV100\n')
        fp.write('1D\n')
        fp.write('\n')
        fp.write('BEGIN METADATA\n')
        fp.write('END METADATA\n')

        fp.write('\n')

        fp.write('2\n')
        fp.write('{0} {1}\n'.format(from_min, from_max))
        fp.write('0.0 1.0\n')
        fp.write('2\n')
        fp.write('{0} {1}\n'.format(from_min, from_max))
        fp.write('0.0 1.0\n')
        fp.write('2\n')
        fp.write('{0} {1}\n'.format(from_min, from_max))
        fp.write('0.0 1.0\n')

        fp.write('\n')

        fp.write('{0}\n'.format(entries))
        if components == 1:
            for i in range(0, entries):
                entry = ''
                for j in range(3):
                    entry = '{0} {1:.10e}'.format(entry, data[i * channels])
                fp.write('{0}\n'.format(entry))
        else:
            for i in range(entries):
                entry = ''
                for j in range(components):
                    entry = '{0} {1:.10e}'.format(entry,
                                                  data[i * channels + j])
                fp.write('{0}\n'.format(entry))
        fp.write('\n')


def write_CTL_1D(filename,
                 from_min,
                 from_max,
                 data,
                 entries,
                 channels,
                 components=3):
    """
    Writes a 1D LUT in the *Academy Color Transformation Language* .ctl format.

    Parameters
    ----------
    filename : str or unicode
        The path of the 1D LUT to be written.
    from_min : float
        The lowest value in the 1D ramp.
    from_max : float
        The highest value in the 1D ramp.
    data : array of floats
        The entries in the LUT.
    entries : int
        The resolution of the LUT, i.e. number of entries in the data set.
    channels : int
        The number of channels in the data.
    components : int, optional
        The number of channels in the data to actually write.
    """

    data = np.squeeze(data)
    if data.ndim == 1:
        data = data[..., np.newaxis]

    # May want to use fewer components than there are channels in the data
    # Most commonly used for single channel LUTs
    components = min(3, components, channels)

    with open(filename, 'w') as fp:
        fp.write('// {0} x {1} LUT generated by "generate_lut"\n'.format(
            entries, components))
        fp.write('\n')
        fp.write('const float min1d = {0};\n'.format(from_min))
        fp.write('const float max1d = {0};\n'.format(from_max))
        fp.write('\n')

        # Write LUT
        if components == 1:
            fp.write('const float lut[] = {\n')
            for i in range(0, entries):
                fp.write('{0}'.format(data)[i * channels])
                if i != (entries - 1):
                    fp.write(',')
                fp.write('\n')
            fp.write('};\n')
            fp.write('\n')
        else:
            for j in range(components):
                fp.write('const float lut{0}[] = {\n'.format(j))
                for i in range(0, entries):
                    fp.write('{0}'.format(data)[i * channels])
                    if i != (entries - 1):
                        fp.write(',')
                    fp.write('\n')
                fp.write('};\n')
                fp.write('\n')

        fp.write('void main\n')
        fp.write('(\n')
        fp.write('  input varying float rIn,\n')
        fp.write('  input varying float gIn,\n')
        fp.write('  input varying float bIn,\n')
        fp.write('  input varying float aIn,\n')
        fp.write('  output varying float rOut,\n')
        fp.write('  output varying float gOut,\n')
        fp.write('  output varying float bOut,\n')
        fp.write('  output varying float aOut\n')
        fp.write(')\n')
        fp.write('{\n')
        fp.write('  float r = rIn;\n')
        fp.write('  float g = gIn;\n')
        fp.write('  float b = bIn;\n')
        fp.write('\n')
        fp.write('  // Apply LUT\n')
        if components == 1:
            fp.write('  r = lookup1D(lut, min1d, max1d, r);\n')
            fp.write('  g = lookup1D(lut, min1d, max1d, g);\n')
            fp.write('  b = lookup1D(lut, min1d, max1d, b);\n')
        elif components == 3:
            fp.write('  r = lookup1D(lut0, min1d, max1d, r);\n')
            fp.write('  g = lookup1D(lut1, min1d, max1d, g);\n')
            fp.write('  b = lookup1D(lut2, min1d, max1d, b);\n')
        fp.write('\n')
        fp.write('  rOut = r;\n')
        fp.write('  gOut = g;\n')
        fp.write('  bOut = b;\n')
        fp.write('  aOut = aIn;\n')
        fp.write('}\n')


def write_1D(filename,
             from_min,
             from_max,
             data,
             data_entries,
             data_channels,
             lut_components=3,
             format='spi1d'):
    """
    Writes a 1D LUT in the specified format.

    Parameters
    ----------
    filename : str or unicode
        The path of the 1D LUT to be written.
    from_min : float
        The lowest value in the 1D ramp.
    from_max : float
        The highest value in the 1D ramp.
    data : array of floats
        The entries in the LUT.
    data_entries : int
        The resolution of the LUT, i.e. number of entries in the data set.
    data_channels : int
        The number of channels in the data.
    lut_components : int, optional
        The number of channels in the data to actually use when writing.
    format : str or unicode, optional
        The format of the the 1D LUT that will be written.
    """

    ocio_formats_to_extensions = {
        'cinespace': 'csp',
        'flame': '3dl',
        'icc': 'icc',
        'houdini': 'lut',
        'lustre': '3dl',
        'ctl': 'ctl'
    }

    if format in ocio_formats_to_extensions:
        if ocio_formats_to_extensions[format] == 'csp':
            write_CSP_1D(filename, from_min, from_max, data, data_entries,
                         data_channels, lut_components)
        elif ocio_formats_to_extensions[format] == 'ctl':
            write_CTL_1D(filename, from_min, from_max, data, data_entries,
                         data_channels, lut_components)
    else:
        write_SPI_1D(filename, from_min, from_max, data, data_entries,
                     data_channels, lut_components)


def generate_1D_LUT_from_image(ramp_1d_path,
                               output_path=None,
                               min_value=0,
                               max_value=1,
                               channels=3,
                               format='spi1d'):
    """
    Reads a 1D LUT image and writes a 1D LUT in the specified format.

    Parameters
    ----------
    ramp_1d_path : str or unicode
        The path of the 1D ramp image to be read.
    output_path : str or unicode, optional
        The path of the 1D LUT to be written.
    min_value : float, optional
        The lowest value in the 1D ramp.
    max_value : float, optional
        The highest value in the 1D ramp.
    channels : int, optional
        The number of channels in the data.
    format : str or unicode, optional
        The format of the the 1D LUT that will be written.
    """

    if output_path is None:
        output_path = '{0}.{1}'.format(ramp_1d_path, 'spi1d')

    ramp = oiio.ImageInput.open(ramp_1d_path)

    ramp_spec = ramp.spec()
    ramp_width = ramp_spec.width
    ramp_channels = ramp_spec.nchannels

    # Forcibly read data as float, the Python API doesn't handle half-float
    # well yet.
    type = oiio.FLOAT
    ramp_data = ramp.read_image(type)

    write_1D(output_path, min_value, max_value, ramp_data, ramp_width,
             ramp_channels, channels, format)

    remove_nans_from_file(output_path)


def generate_3D_LUT_image(ramp_3d_path, resolution=32):
    """
    Generates a 3D LUT image covering the specified resolution

    Relies on *OCIO* *ociolutimage* command.

    Parameters
    ----------
    ramp_3d_path : str or unicode
        The path of the 3D ramp image to be written.
    resolution : int, optional
        The resolution of the 3D ramp image to be written.
    """

    args = [
        '--generate', '--cubesize',
        str(resolution), '--maxwidth',
        str(resolution * resolution), '--output', ramp_3d_path
    ]
    lut_extract = Process(
        description='generate a 3d LUT image', cmd='ociolutimage', args=args)
    lut_extract.execute()


def generate_3D_LUT_from_image(ramp_3d_path,
                               output_path=None,
                               resolution=32,
                               format='spi3d'):
    """
    Reads a 3D LUT image and writes a 3D LUT in the specified format.

    Relies on *OCIO* *ociolutimage* command.

    Parameters
    ----------
    ramp_3d_path : str or unicode
        The path of the 3D ramp image to be read.
    output_path : str or unicode, optional
        The path of the 1D LUT to be written.
    resolution : int, optional
        The resolution of the 3D LUT represented in the image.
    format : str or unicode, optional
        The format of the the 3D LUT that will be written.
    """

    if output_path is None:
        output_path = '{0}.{1}'.format(ramp_3d_path, 'spi3d')

    ocio_formats_to_extensions = {
        'cinespace': 'csp',
        'flame': '3dl',
        'icc': 'icc',
        'houdini': 'lut',
        'lustre': '3dl'
    }

    if format == 'spi3d' or not (format in ocio_formats_to_extensions):
        # Extract a spi3d LUT
        args = [
            '--extract', '--cubesize',
            str(resolution), '--maxwidth',
            str(resolution * resolution), '--input', ramp_3d_path, '--output',
            output_path
        ]
        lut_extract = Process(
            description='extract a 3d LUT', cmd='ociolutimage', args=args)
        lut_extract.execute()

    else:
        output_path_spi3d = '{0}.{1}'.format(output_path, 'spi3d')

        # Extract a spi3d LUT
        args = [
            '--extract', '--cubesize',
            str(resolution), '--maxwidth',
            str(resolution * resolution), '--input', ramp_3d_path, '--output',
            output_path_spi3d
        ]
        lut_extract = Process(
            description='extract a 3d LUT', cmd='ociolutimage', args=args)
        lut_extract.execute()

        # Convert to a different format
        args = ['--lut', output_path_spi3d, '--format', format, output_path]
        lut_convert = Process(
            description='convert a 3d LUT', cmd='ociobakelut', args=args)
        lut_convert.execute()

    remove_nans_from_file(output_path)


def apply_CTL_to_image(input_image,
                       output_image,
                       ctl_paths=None,
                       input_scale=1,
                       output_scale=1,
                       global_params=None,
                       aces_ctl_directory=None):
    """
    Applies a set of Academy Color Transformation Language .ctl files to an
    input image and writes a new image.

    Relies on the *ACES* *ctlrender* command.

    Parameters
    ----------
    input_image : str or unicode
        The path to the image to transform using the CTL files.
    output_image : str or unicode
        The path to write the result of the transforms.
    ctl_paths : array of str or unicode, optional
        The path to write the result of the transforms.
    input_scale : float, optional
        The argument to the *ctlrender* *-input_scale* parameter.
        For images with integer bit depths, this divides image code values 
        before they are sent to the CTL commands.
        For images with float or half bit depths, this multiplies image code 
        values before they are sent to the CTL commands.
    output_scale : float, optional
        The argument to the *ctlrender* *-output_scale* parameter.
        For images with integer bit depths, this multiplies image code values 
        before they are written to a file.
        For images with float or half bit depths, this divides image code
        values before they are sent to the CTL commands.
    global_params : dict of key value pairs, optional
        The set of parameter names and values to pass to the *ctlrender*
        *-global_param1* parameter.
    aces_ctl_directory : str or unicode, optional
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    """

    if ctl_paths is None:
        ctl_paths = []
    if global_params is None:
        global_params = {}

    if len(ctl_paths) > 0:
        ctlenv = os.environ

        if "/usr/local/bin" not in ctlenv['PATH'].split(':'):
            ctlenv['PATH'] = '{0}:/usr/local/bin'.format(ctlenv['PATH'])

        if aces_ctl_directory is not None:
            if os.path.split(aces_ctl_directory)[1] != 'utilities':
                ctl_module_path = '{0}:{1}'.format(
                    os.path.join(aces_ctl_directory, 'utilities'),
                    os.path.join(aces_ctl_directory, 'lib'))
            else:
                ctl_module_path = aces_ctl_directory
            ctlenv['CTL_MODULE_PATH'] = ctl_module_path

        args = []
        for ctl in ctl_paths:
            args += ['-ctl', ctl]
        args += ['-force']
        args += ['-input_scale', str(input_scale)]
        args += ['-output_scale', str(output_scale)]
        args += ['-global_param1', 'aIn', '1.0']
        for key, value in global_params.items():
            args += ['-global_param1', key, str(value)]
        args += [input_image]
        args += [output_image]

        ctlp = Process(
            description='a ctlrender process',
            cmd='ctlrender',
            args=args,
            env=ctlenv)

        ctlp.execute()


def convert_bit_depth(input_image, output_image, depth):
    """
    Convert the input image to the specified bit depth and write a new image.

    Relies on the OIIO oiiotool command.

    Parameters
    ----------
    input_image : str or unicode
        The path to the image to transform using the CTL files.
    output_image : str or unicode
        The path to write the result of the transforms.
    depth : str or unicode
        The bit depth of the output image.
        Data types include: uint8, sint8, uint10, uint12, uint16, sint16,
        half, float, double.
    """

    args = [input_image, '-d', depth, '-o', output_image]
    convert = Process(
        description='convert image bit depth', cmd='oiiotool', args=args)
    convert.execute()


def generate_1D_LUT_from_CTL(lut_path,
                             ctl_paths,
                             lut_resolution=1024,
                             identity_lut_bit_depth='half',
                             input_scale=1,
                             output_scale=1,
                             global_params=None,
                             cleanup=True,
                             aces_ctl_directory=None,
                             min_value=0,
                             max_value=1,
                             channels=3,
                             format='spi1d'):
    """
    Creates a 1D LUT from the specified CTL files by creating a 1D LUT image,
    applying the CTL files and then extracting and writing a LUT based on the
    resulting image.

    Parameters
    ----------
    lut_path : str or unicode
        The path to write the 1D LUT.
    ctl_paths : array of str or unicode
        The CTL files to apply.
    lut_resolution : int, optional
        The resolution of the 1D LUT to generate.
    identity_lut_bit_depth : string, optional
        The bit depth to use for the intermediate 1D LUT image.
    input_scale : float, optional
        The argument to the *ctlrender* *-input_scale* parameter.
        For images with integer bit depths, this divides image code values 
        before they are sent to the CTL commands.
        For images with float or half bit depths, this multiplies image code 
        values before they are sent to the CTL commands.
    output_scale : float, optional
        The argument to the *ctlrender* *-output_scale* parameter.
        For images with integer bit depths, this multiplies image code values 
        before they are written to a file.
        For images with float or half bit depths, this divides image code
        values before they are sent to the CTL commands.
    global_params : dict of key, value pairs, optional
        The set of parameter names and values to pass to the *ctlrender*
        *-global_param1* parameter.
    cleanup : bool, optional
        Whether or not to clean up the intermediate images.
    aces_ctl_directory : str or unicode, optional
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    min_value : float, optional
        The minimum value to consider as input to the LUT.
    max_value : float, optional
        The maximum value to consider as input to the LUT.
    channels : int, optional
        The number of channels to use for the LUT. 1 or 3 are valid.
    format : str or unicode, optional
        The format to use when writing the LUT.
    """

    if global_params is None:
        global_params = {}

    lut_path_base = os.path.splitext(lut_path)[0]

    identity_lut_image_float = '{0}.{1}.{2}'.format(lut_path_base, 'float',
                                                    'tiff')
    generate_1D_LUT_image(identity_lut_image_float, lut_resolution, min_value,
                          max_value)

    if identity_lut_bit_depth not in ['half', 'float']:
        identity_lut_image = '{0}.{1}.{2}'.format(lut_path_base, 'uint16',
                                                  'tiff')
        convert_bit_depth(identity_lut_image_float, identity_lut_image,
                          identity_lut_bit_depth)
    else:
        identity_lut_image = identity_lut_image_float

    transformed_lut_image = '{0}.{1}.{2}'.format(lut_path_base, 'transformed',
                                                 'exr')
    apply_CTL_to_image(identity_lut_image, transformed_lut_image, ctl_paths,
                       input_scale, output_scale, global_params,
                       aces_ctl_directory)

    generate_1D_LUT_from_image(transformed_lut_image, lut_path, min_value,
                               max_value, channels, format)

    if cleanup:
        os.remove(identity_lut_image)
        if identity_lut_image != identity_lut_image_float:
            os.remove(identity_lut_image_float)
        os.remove(transformed_lut_image)


def correct_LUT_image(transformed_lut_image, corrected_lut_image,
                      lut_resolution):
    """
    For some combinations of resolution and bit depth, *ctlrender* would
    generate images with the right number of pixels but with the values for
    width and height transposed. This function generating a new, corrected
    image based on the original. The function acts as a pass through if the
    problem is not detected.

    Parameters
    ----------
    transformed_lut_image : str or unicode
        The path to an image generated by *cltrender*.
    corrected_lut_image : str or unicode
        The path to a 'corrected' image to be generated.
    lut_resolution : int
        The resolution of the 3D LUT that should be contained in 
        transformed_lut_image

    Returns
    -------
    str or unicode
        The path to the corrected image, or the original, if no correction was
        needed.
    """

    transformed = oiio.ImageInput.open(transformed_lut_image)

    transformed_spec = transformed.spec()
    width = transformed_spec.width
    height = transformed_spec.height
    channels = transformed_spec.nchannels

    if width != lut_resolution * lut_resolution or height != lut_resolution:
        print(('Correcting image as resolution is off. '
               'Found {0} x {1}. Expected {2} x {3}').format(
                   width, height, lut_resolution * lut_resolution,
                   lut_resolution))
        print('Generating {0}'.format(corrected_lut_image))

        # Forcibly read data as float, the Python API doesn't handle half-float
        # well yet.
        type = oiio.FLOAT
        source_data = transformed.read_image(type)

        correct = oiio.ImageOutput.create(corrected_lut_image)

        correct_spec = oiio.ImageSpec()
        correct_spec.set_format(oiio.FLOAT)
        correct_spec.width = height
        correct_spec.height = width
        correct_spec.nchannels = channels

        correct.open(corrected_lut_image, correct_spec, oiio.Create)

        dest_data = array.array(
            'f', (b'\0' * correct_spec.width * correct_spec.height *
                  correct_spec.nchannels * 4))
        for j in range(0, correct_spec.height):
            for i in range(0, correct_spec.width):
                for c in range(0, correct_spec.nchannels):
                    dest_data[(
                        correct_spec.nchannels * correct_spec.width * j +
                        correct_spec.nchannels * i + c)] = (source_data[
                            correct_spec.nchannels * correct_spec.width * j +
                            correct_spec.nchannels * i + c])

        correct.write_image(correct_spec.format, dest_data)
        correct.close()
    else:
        # shutil.copy(transformedLUTImage, correctedLUTImage)
        corrected_lut_image = transformed_lut_image

    transformed.close()

    return corrected_lut_image


def generate_3D_LUT_from_CTL(lut_path,
                             ctl_paths,
                             lut_resolution=64,
                             identity_lut_bit_depth='half',
                             input_scale=1,
                             output_scale=1,
                             global_params=None,
                             cleanup=True,
                             aces_ctl_directory=None,
                             format='spi3d'):
    """
    Creates a 3D LUT from the specified CTL files by creating a 3D LUT image,
    applying the CTL files and then extracting and writing a LUT based on the
    resulting image.

    Parameters
    ----------
    lut_path : str or unicode
        The path to write the 1D LUT.
    ctl_paths : array of str or unicode
        The CTL files to apply
    lut_resolution : int, optional.
        The resolution of the 1D LUT to generate.
    identity_lut_bit_depth : string, optional
        The bit depth to use for the intermediate 1D LUT image.
    input_scale : float, optional
        The argument to the *ctlrender* *-input_scale* parameter.
        For images with integer bit depths, this divides image code values 
        before they are sent to the CTL commands.
        For images with float or half bit depths, this multiplies image code 
        values before they are sent to the CTL commands.
    output_scale : float, optional
        The argument to the *ctlrender* *-output_scale* parameter.
        For images with integer bit depths, this multiplies image code values 
        before they are written to a file.
        For images with float or half bit depths, this divides image code
        values before they are sent to the CTL commands.
    global_params : dict of key, value pairs, optional
        The set of parameter names and values to pass to the *ctlrender*
        *-global_param1* parameter.
    cleanup : bool, optional
        Whether or not to clean up the intermediate images .
    aces_ctl_directory : str or unicode, optional
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    format : str or unicode, optional
        The format to use when writing the LUT.
    """

    if global_params is None:
        global_params = {}

    lut_path_base = os.path.splitext(lut_path)[0]

    identity_lut_image_float = '{0}.{1}.{2}'.format(lut_path_base, 'float',
                                                    'tiff')
    generate_3D_LUT_image(identity_lut_image_float, lut_resolution)

    if identity_lut_bit_depth not in ['half', 'float']:
        identity_lut_image = '{0}.{1}.{2}'.format(
            lut_path_base, identity_lut_bit_depth, 'tiff')
        convert_bit_depth(identity_lut_image_float, identity_lut_image,
                          identity_lut_bit_depth)
    else:
        identity_lut_image = identity_lut_image_float

    transformed_lut_image = '{0}.{1}.{2}'.format(lut_path_base, 'transformed',
                                                 'exr')
    apply_CTL_to_image(identity_lut_image, transformed_lut_image, ctl_paths,
                       input_scale, output_scale, global_params,
                       aces_ctl_directory)

    corrected_lut_image = '{0}.{1}.{2}'.format(lut_path_base, 'correct', 'exr')
    corrected_lut_image = correct_LUT_image(
        transformed_lut_image, corrected_lut_image, lut_resolution)

    generate_3D_LUT_from_image(corrected_lut_image, lut_path, lut_resolution,
                               format)

    if cleanup:
        os.remove(identity_lut_image)
        if identity_lut_image != identity_lut_image_float:
            os.remove(identity_lut_image_float)
        os.remove(transformed_lut_image)
        if corrected_lut_image != transformed_lut_image:
            os.remove(corrected_lut_image)
        if format != 'spi3d':
            lut_path_spi3d = '{0}.{1}'.format(lut_path, 'spi3d')
            os.remove(lut_path_spi3d)


def main():
    """
    A simple main that allows the user to exercise the various functions
    defined in this file.
    """

    import optparse

    p = optparse.OptionParser(
        description='A utility to generate LUTs from CTL',
        prog='generateLUT',
        version='0.01',
        usage='.format(prog) [options]')

    p.add_option('--lut', '-l', type='string', default='')
    p.add_option('--format', '-f', type='string', default='')
    p.add_option('--ctl', '-c', type='string', action='append')
    p.add_option('--lutResolution1d', '', type='int', default=4096)
    p.add_option('--lutResolution3d', '', type='int', default=65)
    p.add_option('--ctlReleasePath', '-r', type='string', default='')
    p.add_option('--bitDepth', '-b', type='string', default='float')
    p.add_option('--keepTempImages', '', action='store_true')
    p.add_option('--minValue', '', type='float', default=0)
    p.add_option('--maxValue', '', type='float', default=1)
    p.add_option('--inputScale', '', type='float', default=1)
    p.add_option('--outputScale', '', type='float', default=1)
    p.add_option(
        '--ctlRenderParam', '-p', type='string', nargs=2, action='append')

    p.add_option('--generate1d', '', action='store_true')
    p.add_option('--generate3d', '', action='store_true')

    options, arguments = p.parse_args()

    lut = options.lut
    format = options.format
    ctls = options.ctl
    lut_resolution_1D = options.lutResolution1d
    lut_resolution_3D = options.lutResolution3d
    min_value = options.minValue
    max_value = options.maxValue
    input_scale = options.inputScale
    output_scale = options.outputScale
    ctl_release_path = options.ctlReleasePath
    generate_1d = options.generate1d is True
    generate_3d = options.generate3d is True
    bit_depth = options.bitDepth
    cleanup = not options.keepTempImages

    params = {}
    if options.ctlRenderParam is not None:
        for param in options.ctlRenderParam:
            params[param[0]] = float(param[1])

    if generate_1d:
        print('1D LUT generation options')
    else:
        print('3D LUT generation options')

    print('LUT                 : {0}'.format(lut))
    print('Format              : {0}'.format(format))
    print('CTLs                : {0}'.format(ctls))
    print('LUT Res 1d          : {0}'.format(lut_resolution_1D))
    print('LUT Res 3d          : {0}'.format(lut_resolution_3D))
    print('Min Value           : {0}'.format(min_value))
    print('Max Value           : {0}'.format(max_value))
    print('Input Scale         : {0}'.format(input_scale))
    print('Output Scale        : {0}'.format(output_scale))
    print('CTL Render Params   : {0}'.format(params))
    print('CTL Release Path    : {0}'.format(ctl_release_path))
    print('Input Bit Depth     : {0}'.format(bit_depth))
    print('Cleanup Temp Images : {0}'.format(cleanup))

    if generate_1d:
        generate_1D_LUT_from_CTL(
            lut,
            ctls,
            lut_resolution_1D,
            bit_depth,
            input_scale,
            output_scale,
            params,
            cleanup,
            ctl_release_path,
            min_value,
            max_value,
            format=format)

    elif generate_3d:
        generate_3D_LUT_from_CTL(
            lut,
            ctls,
            lut_resolution_3D,
            bit_depth,
            input_scale,
            output_scale,
            params,
            cleanup,
            ctl_release_path,
            format=format)
    else:
        print(('\n\nNo LUT generated! '
               'You must choose either 1D or 3D LUT generation\n\n'))


if __name__ == '__main__':
    main()
