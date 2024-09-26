#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AMPAS
# Copyright Academy of Motion Picture Arts and Sciences
"""
Generates images comparing the *ACES* Output Transforms from *CTL* and *OCIO*.
"""

from __future__ import division

import optparse
import os
import sys

from aces_ocio.colorspaces import aces
from aces_ocio.generate_config import (
    ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON, ACES_OCIO_CTL_DIRECTORY_ENVIRON)
from aces_ocio.process import Process

from aces_ocio.generate_lut import (apply_CTL_to_image)

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
    'apply_ocio_to_image'
    'idiff_images'
    'generate_comparison_images'
    'main'
]


def apply_ocio_to_image(input_image, input_colorspace, output_image,
                        output_colorspace, ocio_config):
    """
    Applies an *OCIO* colorspace transform to an input image and writes a new
    image.

    Relies on the *OCIO* *ocioconvert* command.

    Parameters
    ----------
    input_image : str or unicode
        The path to the image to transform using the CTL files.
    input_colorspace : str or unicode
        The colorspace of the input image.
    output_image : str or unicode
        The path to write the result of the transforms.
    output_colorspace : str or unicode
        The colorspace for the output image.
    ocio_config : str or unicode, optional
        The path to the *OCIO* config.
    """

    ocioenv = os.environ
    ocioenv['OCIO'] = ocio_config

    args = []
    args += [input_image, input_colorspace]
    args += [output_image, output_colorspace]

    ociop = Process(
        description='an ocioconvert process',
        cmd='ocioconvert',
        args=args,
        env=ocioenv)

    ociop.execute()


def idiff_images(image_1, image_2, difference_image):
    """
    Generates an image encoding the difference between two images.

    Relies on the *OIIO* *idiff* command.

    Parameters
    ----------
    image_1 : str or unicode
        The path to the first image.
    image_2 : str or unicode
        The path to the second image.
    difference_image : str or unicode
        The path to write the result of the difference.
    """

    args = []
    args += [image_1, image_2]
    args += ["-abs", "-o", difference_image]

    idiffp = Process(description='an idiff process', cmd='idiff', args=args)

    idiffp.execute()


def generate_comparison_images(aces_ctl_directory,
                               config_directory,
                               source_image,
                               destination_directory,
                               specific_odts=None):
    """
    Generates a set of images from *CTL* and from *OCIO* for all Output
    Transforms.

    Parameters
    ----------
    aces_ctl_directory : str or unicode
        The path to *ACES* *CTL* *transforms/ctl/utilities* directory.
    config_directory : str or unicode
        The directory containing the *OCIO* config.
    source_image : str or unicode
        The path to the source image to transform.
    destination_directory : str or unicode
        The directory to use when writing images.

    Returns
    -------
    bool
         Success or failure of the image generation process.
    """

    use_ocio = config_directory is not None

    odt_info = aces.get_ODTs_info(aces_ctl_directory)

    if use_ocio:
        config_path = os.path.join(config_directory, 'config.ocio')

    source_image_name = os.path.split(source_image)[-1]
    image_base = os.path.splitext(source_image_name)[0]
    image_format = os.path.splitext(source_image_name)[-1].split('.')[-1]

    # RRT Only - Not compared, but helpful for reference
    dest_image = '{0}.RRT'.format(image_base)

    dest_image_ctl = os.path.join(destination_directory,
                                  '.'.join([dest_image, 'ctl', image_format]))

    ctls = [os.path.join(aces_ctl_directory, 'rrt', 'RRT.ctl')]

    input_scale = 1.0
    output_scale = 1.0
    global_params = None

    apply_CTL_to_image(source_image, dest_image_ctl, ctls, input_scale,
                       output_scale, global_params, aces_ctl_directory)

    # Output Transforms
    for odt_ctl_name, odt_values in odt_info.items():
        odt_name = odt_values['transformUserName']

        if specific_odts and odt_name not in specific_odts:
            continue

        print('\n')
        print('Output Transform - {0}'.format(odt_name))
        print('\n')

        # Forward Output Transform
        # Generate difference images for the forward Output Transform
        # Two result images per Output Transform:
        #   1. The *CTL* transforms applied to the original image
        #   2. The *OCIO* transforms applied to the original image
        # One difference images per Output Transform:
        #   1. The difference between the the *OCIO* and *CTL* results
        if 'transformCTL' in odt_values:
            output_transform_image = '{0}.RRT.{1}'.format(image_base, odt_name)

            # *CTL* render
            output_transform_image_ctl = os.path.join(
                destination_directory,
                '.'.join([output_transform_image, 'ctl', image_format]))

            ctls = [
                os.path.join(aces_ctl_directory, 'rrt', 'RRT.ctl'),
                os.path.join(aces_ctl_directory, 'odt',
                             odt_values['transformCTL'])
            ]

            input_scale = 1.0
            output_scale = 1.0
            global_params = None

            apply_CTL_to_image(source_image, output_transform_image_ctl, ctls,
                               input_scale, output_scale, global_params,
                               aces_ctl_directory)

            if use_ocio:
                # *OCIO* render
                output_transform_image_ocio = os.path.join(
                    destination_directory,
                    '.'.join([output_transform_image, 'ocio', image_format]))

                ocio_input_colorspace = 'ACES - ACES2065-1'
                ocio_output_colorspace = 'Output - {0}'.format(odt_name)

                apply_ocio_to_image(source_image, ocio_input_colorspace,
                                    output_transform_image_ocio,
                                    ocio_output_colorspace, config_path)

                # Difference image
                output_transform_image_diff = os.path.join(
                    destination_directory,
                    '.'.join([output_transform_image, 'diff', image_format]))

                idiff_images(output_transform_image_ctl,
                             output_transform_image_ocio,
                             output_transform_image_diff)

            # Inverse Output Transform
            # Generate difference images for the Inverse Output Transform
            # Two result images per Inverse Output Transform:
            #   1. The *CTL* inverse transforms applied to the forwarded
            #   transformed image.
            #   2. The *OCIO* inverse transforms applied to the forwarded
            #   transformed image.
            # Three difference images per output transform:
            #   1. The difference between the the *OCIO* and *CTL* results.
            #   2. The difference between the *CTL* result and the original
            #   image.
            #   3. The difference between the *OCIO* result and the
            #   original image.
            if 'transformCTLInverse' in odt_values:
                inverse_output_transform_image = (
                    '{0}.Inverse{1}.InvRRT'.format(image_base, odt_name))

                # *CTL Render*
                inverse_output_transform_image_ctl = os.path.join(
                    destination_directory, '.'.join(
                        [inverse_output_transform_image, 'ctl', image_format]))

                ctls = [
                    os.path.join(aces_ctl_directory, 'odt',
                                 odt_values['transformCTLInverse']),
                    os.path.join(aces_ctl_directory, 'rrt', 'InvRRT.ctl')
                ]

                input_scale = 1.0
                output_scale = 1.0
                global_params = None

                apply_CTL_to_image(output_transform_image_ctl,
                                   inverse_output_transform_image_ctl, ctls,
                                   input_scale, output_scale, global_params,
                                   aces_ctl_directory)

                if use_ocio:
                    # *OCIO* render
                    inverse_output_transform_image_ocio = os.path.join(
                        destination_directory, '.'.join([
                            inverse_output_transform_image, 'ocio',
                            image_format
                        ]))

                    ocio_input_colorspace = 'Output - {0}'.format(odt_name)
                    ocio_output_colorspace = 'ACES - ACES2065-1'

                    apply_ocio_to_image(output_transform_image_ocio,
                                        ocio_input_colorspace,
                                        inverse_output_transform_image_ocio,
                                        ocio_output_colorspace, config_path)

                    # Difference Image - CTL and OCIO
                    inverse_output_transform_image_diff1 = os.path.join(
                        destination_directory, '.'.join([
                            inverse_output_transform_image, 'diff_ocio_ctl',
                            image_format
                        ]))

                    idiff_images(inverse_output_transform_image_ctl,
                                 inverse_output_transform_image_ocio,
                                 inverse_output_transform_image_diff1)

                    # Difference image - OCIO original
                    inverse_output_transform_image_diff3 = os.path.join(
                        destination_directory, '.'.join([
                            inverse_output_transform_image,
                            'diff_ocio_original', image_format
                        ]))

                    idiff_images(inverse_output_transform_image_ocio,
                                 source_image,
                                 inverse_output_transform_image_diff3)

                # Difference image - CTL and original
                inverse_output_transform_image_diff2 = os.path.join(
                    destination_directory, '.'.join([
                        inverse_output_transform_image, 'diff_ctl_original',
                        image_format
                    ]))

                idiff_images(inverse_output_transform_image_ctl, source_image,
                             inverse_output_transform_image_diff2)

    return True


def main():
    """
    A simple main that allows the user to exercise the various functions
    defined in this file

    Returns
    -------
    bool
    """

    usage = '.format(prog) [options]\n'
    usage += '\n'
    usage += ('A script to compare results between OCIO and CTL '
              'for an ACES release.\n')
    usage += '\n'
    usage += 'The source image should be an EXR or floating point TIFF '
    usage += 'in the ACES 2065-1 colorspace. '
    usage += '\n'
    usage += 'If the OCIO configDir is not specified, the CTL transforms will '
    usage += 'be run.'
    usage += '\n'
    usage += 'Use the -o option to specify a specific set of ODTs to compare.'
    usage += '\n'
    usage += 'Ex. -o sRGB -o P3-DCI'
    usage += '\n'

    p = optparse.OptionParser(
        description='',
        prog='generate_comparison_images',
        version='generate_comparison_images 1.0',
        usage=usage)

    p.add_option(
        '--acesCTLDir',
        '-a',
        default=os.environ.get(ACES_OCIO_CTL_DIRECTORY_ENVIRON, None))
    p.add_option(
        '--configDir',
        '-c',
        default=os.environ.get(ACES_OCIO_CONFIGURATION_DIRECTORY_ENVIRON,
                               None))
    p.add_option('--sourceImage', '-s', type='string', default='')
    p.add_option('--destinationDir', '-d', type='string', default='')
    p.add_option('--odt', '-o', type='string', default=None, action='append')

    options, arguments = p.parse_args()

    aces_ctl_directory = options.acesCTLDir
    config_directory = options.configDir
    source_image = options.sourceImage
    destination_directory = options.destinationDir
    specific_odts = options.odt

    print('command line : \n{0}\n'.format(' '.join(sys.argv)))

    assert aces_ctl_directory is not None, (
        'process: No "{0}" environment variable defined or no "ACES CTL" '
        'directory specified'.format(ACES_OCIO_CTL_DIRECTORY_ENVIRON))

    return generate_comparison_images(
        aces_ctl_directory,
        config_directory,
        source_image,
        destination_directory,
        specific_odts=specific_odts)


if __name__ == '__main__':
    main()
