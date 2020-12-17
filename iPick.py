#!/usr/bin/python

"""
Integrated UCSF Peak Picker v0.1.

by Woonghee Lee (whlee@nmrfam.wisc.edu)


BSD 2-Clause License

Copyright (c) 2020, LeeGroup
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from __future__ import print_function
import os
import sys
import argparse
import time
import tempfile

if sys.version_info[0] == 2:
    import ucsftool
else:
    import ucsftool3 as ucsftool

ut = ucsftool.ucsfTool()

DESC = '\nIntegrated UCSF Peak Picker v0.1\n\t\
    by Woonghee Lee (whlee@nmrfam.wisc.edu)\n'

NMRGLUE_PATH = 'nmrglue-0.7'
UCSFTOOL_PATH = '.'
LOG_FILE = os.path.join(tempfile.gettempdir(), 'process.log')

def print_log(*args):
    msg = ''
    for s in args:
        try:
            msg += str(s)
        except:
            msg += '! Could not convert to String'
    f = open(LOG_FILE, 'a')
    f.write(msg + '\n')
    f.close()
    print(*args)


def parse_args():
    """Parse input options"""
    parg = argparse.ArgumentParser(
        description=DESC,
        formatter_class=argparse.RawTextHelpFormatter)
    parg.add_argument(
        '-i', '--input', type=str,
        help='RAW UCSF spectra to pick peaks.',
        default=''
    )
    parg.add_argument(
        '-o', '--output', type=str,
        help='SPARKY peak list to generate.',
        default='[user_input].list'
    )
    parg.add_argument(
        '-w', '--overwrite',
        help='Overwrite if the output file exists.',
        action='store_true'
    )
    parg.add_argument(
        '-t', '--threshold', type=float,
        help='Intensity threshold to consider as a peak.',
    )
    parg.add_argument(
        '-m', '--multthresh', type=float,
        help='Intensity threshold by multiplier \n\
            to detected median noise level.',
        default=8.5
    )
    parg.add_argument(
        '-n', '--number', type=int,
        help='Choose designed number of peaks \nbased on intensity criteria.',
    )
    parg.add_argument(
        '-r', '--res', type=int,
        help='Resolution. Choose between 1 and 5. \nLower the more sensitive.',
        default=1
    )
    parg.add_argument(
        '-R', '--ress', type=tuple,
        help='Resolutions for all dimensions. e.g. 22',
    )
    parg.add_argument(
        '-g', '--nmrglue', type=str,
        help='NMRGLUE PATH.',
        default=NMRGLUE_PATH
    )
    parg.add_argument(
        '-u', '--ucsftool', type=str,
        help='UCSFTOOL PATH.',
        default=UCSFTOOL_PATH
    )
    parg.add_argument(
        '-c', '--nproc', type=int,
        help='Number of processors.',
        default=1
    )
    parg.add_argument(
        '-s', '--software', type=str,
        help='Peak picking software {e.g. ucsftool or nmrglue}',
        default='ucsftool'
    )
    parg.add_argument(
        '-S', '--sign', type=int,
        help='Peak sign. Choose between 1, 0, and -1. \n0 means both positive and negative peaks.',
        default=0
    )
    parg.add_argument(
        '-p', '--print_info',
        help='Print UCSF information.',
        action='store_true'
    )
    args = parg.parse_args()
    return args


def get_noise_level(in_filename):
    ut.ucsf_open(in_filename, nproc=1, cache_mode=False)
    noise = ut.sample_noise(100)
    multthresh = 8.5
    noiselevel = abs(noise * multthresh)
    return noiselevel


def main():
    args = parse_args()
    print_log(DESC)
    if not args.input:
        print_log('Input file not specified. "iPick.py -h" to show options.')
        return
    in_filename = args.input

    if args.output != '[user_input].list':
        out_filename = args.output
    else:
        pre, _ = os.path.splitext(in_filename)
        out_filename = pre + '.list'

    if args.nmrglue:
        sys.path.append(args.nmrglue)
    if args.ucsftool:
        sys.path.append(args.ucsftool)


    if args.software == 'ucsftool':
        ut.ucsf_open(in_filename, nproc=args.nproc)
    else:
        ut.ucsf_open(in_filename, nproc=args.nproc, cache_mode=False)

    if args.print_info:
        ut.print_file_info()
        if args.output == '[user_input].list':
            return

    if os.path.exists(out_filename) and not args.overwrite:
        print_log('Output file %s already exists.' % (out_filename))
        return

    ndim = len(ut.axis_header_list)
    print_log('Using UCSFTOOL to sample noise level.')

    noise = ut.sample_noise(100)

    if args.threshold:
        noiselevel = abs(args.threshold)
    else:
        noiselevel = abs(noise * args.multthresh)


    print_log('Noise level: ' + str(noiselevel))
    if args.number:
        peak_count = args.number
        print_log('Peak count: ' + str(peak_count))

    if args.software == 'ucsftool':
        print_log('Using UCSFTOOL to detect local maxima.')
        if args.ress:
            res = list(map(lambda x: int(args.ress[x]), range(len(args.ress))))
        else:
            res = [args.res] * ndim
        print_log('Resolution setting: ', res[0])
        peak_sign = int(args.sign)
        grid_peaks, _ = ut.find_peaks(noiselevel, res, sign=peak_sign, verbose=True)
    else:
        print_log('Using NMRGLUE to detect local maxima.')

        grid_peaks = []
        try:
            import nmrglue as ng
            _, data = ng.sparky.read(in_filename)
            grid_peaks = ng.analysis.peakpick.pick(data, noiselevel, nthres=-1*noiselevel)
        except ImportError:
            print_log('Importing NMRGLUE failed. Using UCSFtool instead.')

    if args.number:
        peak_count = min(peak_count, len(grid_peaks))
    else:
        peak_count = len(grid_peaks)
    print_log('Detected peak count: ' + str(len(grid_peaks)))

    # interpolation and get adjusted data heights
    print_log('Using UCSFTOOL to interpolate and obtain adjusted heights.')
    peak_list, hts_list = [], []
    for grid_peak in grid_peaks:
        grid_pt = ()
        for i in range(ndim):
            grid_pt += (int(grid_peak[i]),)
        shifts, value = ut.get_interpolated_data(grid_pt)
        peak_list.append(shifts)
        hts_list.append(value)

    # sort by adjusted heights
    print_log('Using UCSFTOOL to sort and filter peaks.')
    sort_peaks, sort_hts = ut.filter_peaks_by_count(peak_list,
                                                    hts_list,
                                                    peak_count)

    if len(sort_peaks) == 0:
        print_log('No peak detected.')
        return

    print_log('Using UCSFTOOL to write a SPARKY peak list.')
    ut.write_sparky_peaks(out_filename, sort_peaks, sort_hts)
    print_log('%d peaks written in %s' % (peak_count, out_filename))
    ut.ucsf_close()

    # this is to be checked by other modules that this program is done
    time.sleep(0.5)
    IPICK_PATH = os.path.abspath(os.path.dirname(__file__))
    done_file = open(os.path.join(IPICK_PATH, 'done'), 'w')
    done_file.close()


if __name__ == '__main__':
    main()
