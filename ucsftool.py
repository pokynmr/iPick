# -----------------------------------------------------------------------------
# UCSF tool
#
# -----------------------------------------------------------------------------
#
# Developed by Woonghee Lee
# e-mail: woonghee.lee@ucdenver.edu
# Department of Chemistry, University of Colorado Denver
#
# Last updated: December 26, 2020
#
# This tool is to read, write and transform ucsf files
#
# Developed since July, 2018
#
# Python 3 Ported by Mehdi Rahimi
#
# -----------------------------------------------------------------------------
#
# e.g. Use help() function to see what this does
#   import sys
#   sys.path.append("/home/samic/Desktop/wlee_group/source/rahimi/ucsfTool")
#   import ucsftool
#   ut = ucsftool.ucsfTool()
#   ut.help()
#
# e.g. Simple pseudo-3D split to multiple 2D example
#   import ucsftool
#   ut = ucsftool.ucsfTool()
#   ut.ucsf_open('HNCACB.ucsf')
#   ut.write_planes('relax')
#
# e.g. Make 2D projection
#   import ucsftool
#   ut = ucsftool.ucsfTool()
#   ut.ucsf_open('my3d.ucsf')
#   ut.write_projection('my2d.ucsf',dim=2)

# e.g. Automated peak picking
#   import os, sys, ucsftool
#   in_filename='C105A_2A_CBCACONH.ucsf'
#   pre, ext = os.path.splitext(in_filename)
#   out_filename= pre + '.list'
#   ut = ucsftool.ucsfTool()
#   ut.ucsf_open(in_filename)
#   ut.auto_pick_peaks(out_filename)
#
#
# BSD 2-Clause License
#
# Copyright (c) 2020, Woonghee Lee (woonghee.lee@ucdenver.edu)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function
import os, sys, struct
import itertools
import random
random.seed()
import time, datetime
import multiprocessing
import tempfile

tile_count_buffer = 256 # we will hold tile max 256 in memory (approx. 8mb)
#tile_count_buffer = 4096 # 128mb # we will hold tile max 512 in memory (approx. 16mb)
unpack_float = struct.Struct('>f').unpack
unpack_byte = struct.Struct('>B').unpack
unpack_int = struct.Struct('>I').unpack
pack_float = struct.Struct('>f').pack

OS_WINDOWS = False
if ((sys.platform == 'win32') or (sys.platform == 'cygwin')):
    OS_WINDOWS = True

def print_log(*args):
    msg = ''
    for s in args:
        try:
            msg += str(s)
        except:
            msg += '! Could not convert to String'
    f = open(os.path.join(tempfile.gettempdir(), 'process.log'), 'a')
    f.write(msg + '\n')
    f.close()
    print(*args)

def interpolation(f1, f2, f3):
  a0 = f1
  a1 = -1.5 * f1 + 2.0 * f2 - 0.5 * f3
  a2 = 0.5 * f1 - f2 + 0.5 * f3
  if a2 == 0:
    return 1, f2
  x = -0.5 * a1 / a2
  value = a2 * x * x + a1 * x + a0
  return x, value

def lastabs(elem):
  return abs(elem[-1])

def mean(data):
    """Return the sample arithmetic mean of data."""
    n = len(data)
    if n < 1:
        raise ValueError('mean requires at least one data point')
    return sum(data)/n # in Python 2 use sum(data)/float(n)

def _ss(data):
    """Return sum of square deviations of sequence data."""
    c = mean(data)
    ss = sum((x-c)**2 for x in data)
    return ss

def stddev(data, ddof=0):
    """Calculates the population standard deviation
    by default; specify ddof=1 to compute the sample
    standard deviation."""
    n = len(data)
    if n < 2:
        raise ValueError('variance requires at least two data points')
    ss = _ss(data)
    pvar = ss/(n-ddof)
    return pvar**0.5

class ucsfTool:
  # ---------------------------------------------------------------------------
  # Creator
  #
  def __init__(self):
    self.is_opened = 0
    self.file_size = 0
    self.nproc = 1
    self.file_name = ''
    self.file_object = None
    self.file_header = self.dummy_file_header()
    self.axis_header_list = []
    self.tile_list = []
    self.pixel_size = []
    self.min_heights = None
    self.cache_data = None
  # ---------------------------------------------------------------------------
  # Close file and init class
  #
  def ucsf_close(self):
    if self.file_object != None:
      for i in range(len(self.file_object)):
        self.file_object[i].close()
      self.file_object = None
    self.file_size = 0
    if self.min_heights != None:
      self.min_heights = []
    self.file_name = ''
    self.file_header = self.dummy_file_header()
    self.axis_header_list = []
    self.tile_list = []
    self.pixel_size = []
    self.is_opened = 0
    self.cache_data = None

  # ---------------------------------------------------------------------------
  # Destructor
  #
  def __del__(self):
    self.ucsf_close()

  # ---------------------------------------------------------------------------
  # Help
  #
  def help(self):
    print_log("""
    ucsf_open(optional: filename)
    ucsf_close()
    dummy_file_header()
    dummy_axis_header()
    dummy_tile()
    copy_file_header(template_file_header)
    copy_axis_header(template_axis_header)
    set_filename(filename)
    get_filename()
    read_file_header()
    read_axis_header()
    print_file_info()
    calculate_pixel_size()
    read_tile_data(tile_indices)
    grid_to_tile_and_remain_indices(grid_pt)
    optimize_tile_size(axis_header_list)
    tile_and_remain_indices_to_grid(tile_pt, index_pt)
    remain_indices_to_remain_index(indices)
    shift_to_grid(shift, dim)
    shifts_to_grids(shifts):
    peaks_to_points(peaks):
    grid_to_shift(grid, dim)
    grids_to_shifts(grids):
    points_to_peaks(points):
    get_data(grid_pt)
    get_data_by_shifts(shift_pt)
    get_interpolated_data(grid_pt)
    get_interpolated_data_by_shifts(grid_pt)
    get_interpolated_data_by_peaks(peaks)
    sample_noise(sample_count=30)
    filter_peaks_by_count(grid_peaks, heights, max_count)
    filter_peaks_by_height(grid_peaks, heights, max_height)
    is_local_maxima(grid_pt, grid_buffers, sign=1)
    is_local_maxima_by_shifts(shift_pt, shift_buffers, sign=1)
    find_peaks(noise_level, sign=1, shift_restraint = None)
    find_fit_peaks(grid_pt, grid_buffers, sign=1, mode='gaussian')
    find_fit_peaks_by_shifts(shift_pt, shift_buffers, sign=1, mode='gaussian')
    auto_pick_peaks(out_filename=None, grid_buffers=None, sign=0, max_count=None,
                    noise_filter = 8., shift_restraint = None, write_peaks=True)
    write_sparky_peaks(out_filename, peaks, heights=None)
    write_transform(out_filename, transform_mode, transform_factor,
                    transform_factor2, overwrite=0)
    write_projection(out_filename, proj_dim, proj_mode = 'avg', overwrite=0)
    write_planes(out_prefix, dim=0, reverse=1, init=1, gap=1, overwrite=0)
    write_swapped_axis(out_filename, dimension 1, dimension 2, overwrite=0)
    write_shifted(out_filename, shift dimension, amount,
                  unit='ppm', overwrite=0)
    write_ucsf_file_header(file_object, file_header)
    write_ucsf_axis_header(file_object, axis_header)
    write_concatenated (not yet implemented)
    """)

  # ---------------------------------------------------------------------------
  # Init file header
  #
  def dummy_file_header(self):
    file_header = {'FileType':'None',
                   'DimCount':0,
                   'DataCompCount':0,
                   'FileVersion':'None'}
    return file_header
  # ---------------------------------------------------------------------------
  # Copy file header
  #
  def copy_file_header(self, template_file_header):
    file_header = {'FileType':      template_file_header['FileType'],
                   'DimCount':      template_file_header['DimCount'],
                   'DataCompCount': template_file_header['DataCompCount'],
                   'FileVersion':   template_file_header['FileVersion']}
    return file_header
  # ---------------------------------------------------------------------------
  # Init axis header and return instance
  #
  def dummy_axis_header(self):
    axis_header = {'AtomName':'None',
                   'DataPointCount':0,
                   'FillPointCount':0,
                   'TileSize':0,
                   'TileCount':0,
                   'SpecFreq':0.0,
                   'SpecWidth':0.0,
                   'Center':0.0,
                   'MarginalPoint':0,
                   'MarginalFreq':0.0,
                   'FreqMin':0.0,
                   'FreqMax':0.0}
    return axis_header
  # ---------------------------------------------------------------------------
  # Copy axis header and return instance
  #
  def copy_axis_header(self, template_axis_header):
    axis_header = {'AtomName':          template_axis_header['AtomName'],
                   'DataPointCount':    template_axis_header['DataPointCount'],
                   'FillPointCount':    template_axis_header['FillPointCount'],
                   'TileSize':          template_axis_header['TileSize'],
                   'TileCount':         template_axis_header['TileCount'],
                   'SpecFreq':          template_axis_header['SpecFreq'],
                   'SpecWidth':         template_axis_header['SpecWidth'],
                   'Center':            template_axis_header['Center'],
                   'MarginalPoint':     template_axis_header['MarginalPoint'],
                   'MarginalFreq':      template_axis_header['MarginalFreq'],
                   'FreqMin':           template_axis_header['FreqMin'],
                   'FreqMax':           template_axis_header['FreqMax'],}
    return axis_header

  # ---------------------------------------------------------------------------
  # Init tile data and return instance
  #
  def dummy_tile(self):
    tile_data = {'TilePos': (),
                 'Values': ()}
    return tile_data

  # ---------------------------------------------------------------------------
  # Set ucsf file name to access
  #
  def set_filename(self, file_name):
    if self.is_opened == 1:
      print_log('Error in ucsfTool:set_filename()- file name is already assigned')
      return 0
    self.file_name = file_name
    return 1

  # ---------------------------------------------------------------------------
  # Get ucsf file name set previously
  #
  def get_filename(self):
    return self.file_name

  # ---------------------------------------------------------------------------
  # open ucsf instances and read header and check validity
  #
  def ucsf_open(self, in_filename=None, nproc=1, cache_mode=True):
    if self.is_opened == 1:
      print_log('Error in ucsfTool:ucsf_open()- file is already opened')
      return 0

    if in_filename != None:
      self.set_filename(in_filename)

    if not os.path.exists(self.file_name):
      print_log('Error in ucsfTool:ucsf_open()- file(%s) does not exist' \
            % (self.file_name))
      return 0

    if OS_WINDOWS:
        self.file_object = map(lambda x: open(self.file_name, 'rb'), range(nproc))
    else:
        self.file_object = map(lambda x: open(self.file_name, 'rb', os.O_NONBLOCK), range(nproc))

    self.file_object[0].seek(0, 2) # seek_end
    self.file_size = self.file_object[0].tell()
    if self.file_size < 180 + 128*2: # 180: file header, 128: axis header
      print_log('Error in ucsfTool:ucsf_open()- file size too small (%d)' \
            % (self.file_size))
      self.ucsf_close()
      return 0
    self.min_heights = map(lambda x: 10**10, range(nproc))
    self.is_opened = 1
    if self.read_file_header() == 0:
      self.ucsf_close()
      return 0

    self.fd_divider = None
    self.nproc = nproc
    if self.read_axis_header() == 0:
      self.ucsf_close()
      return 0

    self.ndim = len(self.axis_header_list)
    self.calculate_pixel_size()
    self.init_pos = 180 + 128 * self.ndim
    self.tile_list = map(lambda x: [], range(nproc))

    self.cube_size = 1 # cube, tile, or 4D cube whatever the size is...
    for i in range(self.ndim):
      self.cube_size *= self.axis_header_list[i]['TileSize']
    self.cube_float_size = self.cube_size * 4 # cube size in float point size
    self.unpack_cube_float = struct.Struct('>%df' % (self.cube_size)).unpack

    # If memory is enough, load all the data first.
    # This will be significantly fast when multiprocessing is activated
    try:
      free_mem = int(os.popen('free -tb').readlines()[1].split()[3])
      if self.file_size * 3 < free_mem and cache_mode:
        self.file_object[0].seek(0, 0)
        self.cache_data = bytes(self.file_object[0].read())
    except:
      pass

  # ---------------------------------------------------------------------------
  # Read file header
  #
  def read_file_header(self):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:read_file_header()- file is not opened')
      return 0

    self.file_object[0].seek(0)
    temp = self.file_object[0].read(16)
    if temp[0:8] != 'UCSF NMR':
      print_log('Error in ucsfTool:read_file_header()- UCSF NMR tag not found')
      return 0

    self.file_header['FileType'] = temp[0:8]

    try:
      self.file_header['DimCount'] = unpack_byte(temp[10])[0]
    except:
      print_log('Error in ucsfTool:read_file_header()- dimension is incorrect')
      return 0

    try:
      self.file_header['DataCompCount'] = unpack_byte(temp[11])[0]
    except:
      print_log('Error in ucsfTool:read_file_header()- data component is incorrect')
      return 0

    try:
      self.file_header['FileVersion'] = unpack_byte(temp[13])[0]
    except:
      print_log('Error in ucsfTool:read_file_header()- file version is incorrect')
      return 0

    return 1
  # ---------------------------------------------------------------------------
  # Read axis header
  #
  def read_axis_header(self):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:read_axis_header()- file is not opened')
      return 0

    try:
      self.axis_header_list = []
      self.file_object[0].seek(180)
      for i in range(self.file_header['DimCount']):
        dah = self.dummy_axis_header()
        temp = self.file_object[0].read(128)

        nuc = struct.unpack('6s',temp[0:6])[0]
        dah['AtomName'] = nuc.replace('\x00', '')
        dah['DataPointCount'] = unpack_int(temp[8:12])[0]
        dah['TileSize'] = unpack_int(temp[16:20])[0]
        dah['TileCount'] = dah['DataPointCount'] / dah['TileSize']
        if dah['DataPointCount'] % dah['TileSize'] != 0:
          dah['TileCount'] = dah['TileCount'] + 1
        dah['FillPointCount'] = dah['TileSize'] * dah['TileCount']
        dah['SpecFreq'] = unpack_float(temp[20:24])[0]
        dah['SpecWidth'] = unpack_float(temp[24:28])[0]
        dah['Center'] = unpack_float(temp[28:32])[0]
        dah['MarginalPoint'] = dah['TileSize'] * dah['TileCount'] \
                                - dah['DataPointCount']
        dah['MarginalFreq'] = float(dah['MarginalPoint']) \
                                / float(dah['DataPointCount']) \
                                * dah['SpecWidth'] / dah['SpecFreq']
        dah['FreqMin'] = dah['Center'] - dah['SpecWidth'] \
                          / dah['SpecFreq'] / 2.0
        dah['FreqMax'] = dah['Center'] + dah['SpecWidth'] \
                          / dah['SpecFreq'] / 2.0
        self.axis_header_list.append(dah)
      # convert to tuple for performance
      self.axis_header_list = tuple(self.axis_header_list)
      #self.fd_divider = int(float(self.axis_header_list[0]['DataPointCount']) / \
      #                    float(self.nproc))+1
      self.fd_divider = float(self.axis_header_list[0]['DataPointCount']) / \
                          float(self.nproc)
      if self.nproc != 1:
        print_log('X axis data points: %d' % \
                  (self.axis_header_list[0]['DataPointCount']))
        #print 'fd_divider set to: %d' % (self.fd_divider)
        print_log('fd_divider set to: %f' % (self.fd_divider))
    except:
      msg = 'Error in ucsfTool:read_axis_header()- processing dimension '
      msg = msg + '%d failed' % (i+1)
      print_log(msg)
      return 0

    # make tuples for performance
    self.tile_count = ()
    self.data_point_count = ()
    self.tile_size = ()
    self.fill_point_count = ()
    for i in range(self.file_header['DimCount']):
      self.data_point_count += (self.axis_header_list[i]['DataPointCount'],)
      self.tile_size += (self.axis_header_list[i]['TileSize'],)
      self.tile_count += (self.axis_header_list[i]['TileCount'],)
      self.fill_point_count += (self.axis_header_list[i]['FillPointCount'],)
    return 1
  # ---------------------------------------------------------------------------
  # Print file information
  #
  def print_file_info(self):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:read_axis_header()- file is not opened')
      return 0
    ahl = self.axis_header_list

    line = '%-20s' % ('axis')
    for i in range(self.ndim):
      ah = ahl[i]
      line = line + '%11s%d' % ('w',i+1)
    print_log(line)

    line = '%-20s' % ('nucleus')
    for ah in ahl:
      line = line + '%12s' % (ah['AtomName'])
    print_log(line)

    for col, head in [['matrix size', 'DataPointCount'],
                      ['block size', 'TileSize']]:
      line = '%-20s' % (col)
      for ah in ahl:
        line = line + '%12d' % (ah[head])
      print_log(line)

    for col, head in [['upfield ppm', 'FreqMin'],
                      ['downfield ppm', 'FreqMax'],
                      ['spectrum frequency','SpecFreq'],
                      ['spectrum width', 'SpecWidth']]:
      line = '%-20s' % (col)
      for ah in ahl:
        line = line + '%12.3f' % (ah[head])
      print_log(line)


  # ---------------------------------------------------------------------------
  # show the raw header data
  #
  def get_raw_header(self):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:read_axis_header()- file is not opened')
      return 0
    print_log(self.axis_header_list)


  # ---------------------------------------------------------------------------
  # dump all data points
  #
  def dump_data_2d(self):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:read_axis_header()- file is not opened')
      return 0
    ahl = self.axis_header_list
    x = ahl[0]['DataPointCount']
    y = ahl[1]['DataPointCount']
    for i in range(x):
      for j in range(y - 1):
        #print_log('{},'.format(self.get_data([i, j])), end='')
        print_log('{},'.format(self.get_data([i, j]))),
      print_log(self.get_data([i, j + 1]))


  # ---------------------------------------------------------------------------
  # Calculate pixel size for a grid
  def calculate_pixel_size(self):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:calculate_pixel_size()- file is not opened')
      return None

    self.pixel_size = ()
    for i in range(self.ndim):
      self.pixel_size += (self.axis_header_list[i]['SpecWidth'] \
                        / self.axis_header_list[i]['DataPointCount'] \
                        / self.axis_header_list[i]['SpecFreq'], )
  # ---------------------------------------------------------------------------
  # Get Tile Block
  #
  def read_tile_data(self, tile_indices, fd=0):
    # browse tile list if already read in the memory
    for i in range(len(self.tile_list[fd])):
      if self.tile_list[fd][i]['TilePos'] == tile_indices:
        # move this tile to the top priority
        if i != 0:
          self.tile_list[fd].insert(0, self.tile_list[fd].pop(i))
        return self.tile_list[fd][0]

    # start finding block position for the tile_indices
    sum_size = 0
    for i in range(self.ndim):
      mult_size = tile_indices[i]
      for j in range(i+1, self.ndim):
        mult_size *= self.tile_count[j]
      sum_size += mult_size
    tile_pos = self.init_pos + self.cube_float_size * sum_size

    # read by tile
    # could not find. read from file
    dt = self.dummy_tile()
    dt['TilePos'] = tile_indices
    dt['Values'] = [0] * self.cube_size
    # not outlier
    if tile_pos + self.cube_float_size < self.file_size+1 and tile_pos > 0:
      if self.cache_data == None:
        self.file_object[fd].seek(tile_pos, 0)
        temp = self.file_object[fd].read(self.cube_float_size)
      else:
        temp = self.cache_data[tile_pos:tile_pos+self.cube_float_size]
      dt['Values'] = self.unpack_cube_float(temp)
      dt['Values'] = tuple(dt['Values'])
      #dt['Values'] = tuple(self.unpack_cube_float(temp))

    # make this tile top priority
    self.tile_list[fd].insert(0, dt)

    # if buffer overflowing, remove last one.
    if len(self.tile_list[fd]) > tile_count_buffer:
      self.tile_list[fd].pop(tile_count_buffer)
    return dt

  # ---------------------------------------------------------------------------
  # Grid to Tile and Index
  #
  def grid_to_tile_and_remain_indices(self, grid_pt):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:grid_to_tile_and_indices()- file is not opened')
      return None
    tile_pt = ()
    remain_pt = ()
    for i in range(self.ndim):
      tile_pt += (grid_pt[i] / self.axis_header_list[i]['TileSize'],)
      remain_pt += (grid_pt[i] % self.axis_header_list[i]['TileSize'],)

    return (tile_pt, remain_pt)

  # ---------------------------------------------------------------------------
  # Optimize tile size
  #
  def optimize_tile_size(self, axis_header_list):
    for i in range(self.ndim):
      axis_header_list[i]['TileSize'] = axis_header_list[i]['DataPointCount'] \
                                         / 2 # initial starting size
    # estimate new tile size
    while True:
      # current size?
      temp_size = 4
      max_dim = 0
      max_tilesize = 0
      for i in range(self.ndim):
        ts = axis_header_list[i]['TileSize']
        if ts > max_tilesize:
          ts = max_tilesize
          max_dim = i
        temp_size = temp_size * ts
      # check if temp_size <= 32kb
      if temp_size < 32*1024: break
      # reduce the largest dimension
      axis_header_list[max_dim]['TileSize'] \
                                    = axis_header_list[max_dim]['TileSize'] / 2

    # readjust TileCount, FillPointCount, and write axis header
    for i in range(self.ndim):
      ts = axis_header_list[i]['TileSize']
      axis_header_list[i]['TileCount'] \
                                    = axis_header_list[i]['DataPointCount'] / ts
      if axis_header_list[i]['DataPointCount'] % ts != 0:
        axis_header_list[i]['TileCount'] = axis_header_list[i]['TileCount'] + 1
      axis_header_list[i]['FillPointCount'] = ts \
                                              * axis_header_list[i]['TileCount']

  # ---------------------------------------------------------------------------
  # Tile and Index to Grid
  #
  def tile_and_remain_indices_to_grid(self, tile_pt, index_pt):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:tile_and_indices_to_grid()- file is not opened')
      return None
    grid_pt = []
    for i in range(self.ndim):
      grid_pt.append(tile_pt[i] * self.axis_header_list[i]['TileSize'] \
                      + index_pt[i])
    return grid_pt
  # ---------------------------------------------------------------------------
  # Remain indices to remain index
  #
  def remain_indices_to_remain_index(self, indices):
    if self.is_opened == 0:
      msg = 'Error in ucsfTool:remain_indices_to_remain_index()- '
      msg = msg + 'file is not opened'
      print_log(msg)
      return None
    sum_size = 0
    for i in range(self.ndim):
      mult_size = indices[i]
      for j in range(i+1, self.ndim):
        mult_size *= self.axis_header_list[j]['TileSize']
      sum_size += mult_size
    return sum_size
  # ---------------------------------------------------------------------------
  # Shift to grid
  #
  def shift_to_grid(self, shift, dim):
    ah = self.axis_header_list[dim-1]
    temp = ah['SpecWidth'] / float(ah['DataPointCount']) / ah['SpecFreq']
    temp2 = ah['Center'] + (ah['SpecWidth'] / ah['SpecFreq'] / 2.0)
    return int((temp2 - shift) / temp + 0.5)
  # all dimension
  def shifts_to_grids(self, shifts):
    grid_list = []
    for i in range(self.ndim):
      grid_list.append(self.shift_to_grid(shifts[i], i+1))
    return grid_list
  # multiple peaks
  def peaks_to_points(self, peaks):
    point_list = []
    for i in range(len(peaks)):
      point_list.append(self.shifts_to_grids(peaks[i]))
    return point_list
  # ---------------------------------------------------------------------------
  # Grid to shift
  #
  def grid_to_shift(self, grid, dim):
    ah = self.axis_header_list[dim-1]
    temp = ah['SpecWidth'] / float(ah['DataPointCount']) / ah['SpecFreq']
    temp2 = ah['Center'] + (ah['SpecWidth'] / ah['SpecFreq'] / 2.0)
    return temp2 - temp * float(grid)
  def grids_to_shifts(self, grids):
    shift_list = ()
    for i in range(self.ndim):
      shift_list += (self.grid_to_shift(grids[i], i+1), )
    return shift_list
  def points_to_peaks(self, points):
    peak_list = ()
    for i in range(len(points)):
      peak_list += (self.grids_to_shifts(points[i]),)
    return peak_list
  # ---------------------------------------------------------------------------
  # Get Data Value by Grid Points
  #
  def get_data(self, grid_pt):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:get_data()- file is not opened')
      return None
    tile_indices, remain_pt = self.grid_to_tile_and_remain_indices(grid_pt)
    fdidx = min(int(float(grid_pt[0]) / self.fd_divider), self.nproc-1)
    remain_index = self.remain_indices_to_remain_index(remain_pt)
    #if self.cache_data == None:
    tile_data = self.read_tile_data(tile_indices, fd=fdidx)
    hts = tile_data['Values'][remain_index]

    #else:
    #  return self.get_point_data(tile_indices, remain_index)
    return hts
  # ---------------------------------------------------------------------------
  def get_point_data(self, tile_indices, remain_index):
    sum_size = 0
    for i in range(self.ndim):
      mult_size = tile_indices[i]
      for j in range(i+1, self.ndim):
        mult_size *= self.tile_count[j]
      sum_size += mult_size
    tile_pos = self.init_pos + self.cube_float_size * sum_size
    grid_pos = tile_pos + remain_index * 4
    try:
      temp = float(self.cache_data[grid_pos:grid_pos + 4])
      temp = unpack_float(self.cache_data[grid_pos:grid_pos + 4])[0]
    except:
      return 0
    return temp
  # ---------------------------------------------------------------------------
  # Get Data Value by Shifts
  #
  def get_data_by_shifts(self, shift_pt):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:get_data_shifts()- file is not opened')
      return None

    # shifts to grids
    grid_pt = ()
    for i in range(len(shift_pt)):
      grid_pt += (self.shift_to_grid(shift_pt[i], i+1), )
    return self.get_data(grid_pt)

  # ---------------------------------------------------------------------------
  # Get Interpolated Shift Position and Data Value by Grid Points
  #
  def get_interpolated_data(self, grid_pt):
    if self.is_opened == 0:
      print_log('Error in ucsfTool:get_interpolated_data()- file is not opened')
      return None

    shifts = [0.0] * len(grid_pt)
    for i in range(len(grid_pt)):
      prev_grid_pt = list(grid_pt)
      next_grid_pt = list(grid_pt)
      prev_grid_pt[i] = grid_pt[i]-1
      next_grid_pt[i] = grid_pt[i]+1
      d1 = self.get_data(prev_grid_pt)
      d2 = self.get_data(grid_pt)
      d3 = self.get_data(next_grid_pt)
      pos, value = interpolation(d1, d2, d3)
      if pos < 0 or pos > 2: # extrapolated- use just middle
        pos = 1
        value = d2
      shifts[i] = self.grid_to_shift(grid_pt[i]+pos-1.0, i+1)
    return shifts, value

  # ---------------------------------------------------------------------------
  # Get Interpolated Shift Position and Data Value by Shifts
  #
  def get_interpolated_data_by_shifts(self, shift_pt):
    if self.is_opened == 0:
      msg = 'Error in ucsfTool:get_interpolated_data_by_shifts()- '
      msg = msg + 'file is not opened'
      print_log(msg)
      return None

    # shifts to grids
    grid_pt = []
    for i in range(len(shift_pt)):
      grid_pt.append(self.shift_to_grid(shift_pt[i], i+1))
    return self.get_interpolated_data(grid_pt)
  # ---------------------------------------------------------------------------
  # Interpolation for peaks
  def get_interpolated_data_by_peaks(self, peaks):
    adj_peaks, adj_hts = [], []
    for i in range(len(peaks)):
      interpolated = self.get_interpolated_data_by_shifts(peaks[i])
      adj_peaks.append(interpolated[0])
      adj_hts.append(interpolated[1])
    return adj_peaks, adj_hts
  # ---------------------------------------------------------------------------
  # Take the median value of randomly sampled data absolute values.
  #
  def sample_noise(self, sample_count=30):
    ahl = self.axis_header_list
    ht_list = []
    for i in range(sample_count):
      grid_pt = []
      for j in range(len(ahl)):
        grid_pt.append(random.randrange(0, ahl[j]['DataPointCount']))
      ht_list.append(abs(self.get_data(grid_pt)))
    sorted_ht_list = sorted(ht_list)
    return sorted_ht_list[sample_count/2]
  # ---------------------------------------------------------------------------
  # Check if this grid is the maximum
  #
  def is_local_maxima(self, grid_pt, grid_buffers, sign = 1, ref_ht = None):
    if ref_ht == None:  std_ht = self.get_data(grid_pt)
    else: std_ht = ref_ht
    if std_ht * sign < 0:
      return False, std_ht 

    if len(grid_pt) == 2:
      it = itertools.product(range(grid_pt[0]-grid_buffers[0],
                                   grid_pt[0]+grid_buffers[0]+1),
                             range(grid_pt[1]-grid_buffers[1],
                                   grid_pt[1]+grid_buffers[1]+1))
    elif len(grid_pt) == 3:
      it = itertools.product(range(grid_pt[0]-grid_buffers[0],
                                   grid_pt[0]+grid_buffers[0]+1),
                             range(grid_pt[1]-grid_buffers[1],
                                   grid_pt[1]+grid_buffers[1]+1),
                             range(grid_pt[2]-grid_buffers[2],
                                   grid_pt[2]+grid_buffers[2]+1))
    elif len(grid_pt) == 4:
      it = itertools.product(range(grid_pt[0]-grid_buffers[0],
                                   grid_pt[0]+grid_buffers[0]+1),
                             range(grid_pt[1]-grid_buffers[1],
                                   grid_pt[1]+grid_buffers[1]+1),
                             range(grid_pt[2]-grid_buffers[2],
                                   grid_pt[2]+grid_buffers[2]+1),
                             range(grid_pt[3]-grid_buffers[3],
                                   grid_pt[3]+grid_buffers[3]+1))
    pt_list = tuple(it)
    astd_ht = abs(std_ht)
    for pt in pt_list:
      if grid_pt == pt: continue
      temp_ht = self.get_data(pt)
      if (temp_ht < std_ht * 0.2 and sign == 1) or \
          (temp_ht > std_ht * 0.2 and sign == -1) or \
          (abs(temp_ht) < astd_ht * 0.2 and sign == 0):
        return False, std_ht
      if (temp_ht > std_ht and sign == 1) or (temp_ht < std_ht and sign == -1) \
          or (abs(temp_ht) > astd_ht and sign == 0):
        return False, std_ht
    return True, std_ht

  # ---------------------------------------------------------------------------
  # Check if this shift is the maximum
  #
  def is_local_maxima_by_shifts(self, shift_pt, shift_buffers, sign = 1,
                                      ref_ht = None):
    grid_pt = []
    grid_buffers = []
    for i in range(len(shift_buffers)):
      grid_buffers.append(shift_buffers[i] / self.pixel_size[i] + 1)
      grid_pt.append(self.shift_to_grid(shift_pt[i], i+1))
    return self.is_local_maxima(grid_pt, grid_buffers, sign, ref_ht)
  # ---------------------------------------------------------------------------
  #
  # Use slope to cut the value
  def filter_peaks_by_slope(self, grid_peaks, heights, min_slope):
    pass
  def filter_peaks_by_sign_ratio(self, grid_peaks, heights, min_ratio):
    pass
  def filter_peaks_by_height(self, grid_peaks, heights, max_height):
    peaks2, heights2 = [], []
    for i in range(len(grid_peaks)):
      hts = heights[i]
      if abs(hts) >= abs(max_height):
        peaks2.append(grid_peaks[i])
        heights2.append(hts)
    return peaks2, heights2

  def filter_peaks_by_count(self, grid_peaks, heights, max_count):
    temp_list = []
    for i in range(len(grid_peaks)):
      temp_list.append([grid_peaks[i], heights[i]])
    temp_list.sort(key=lastabs, reverse = True)
    grid_peaks2, heights2 = [], []
    for i in range(min(max_count, len(temp_list))):
      peak = temp_list[i][0]
      hts = temp_list[i][1]
      grid_peaks2.append(peak)
      heights2.append(hts)
    return grid_peaks2, heights2
  # ---------------------------------------------------------------------------
  # change user shift restraint to grid restraint
  # [[125.6,130.4,..],[7.4,7.8,...],[]]
  def shift_restraint_to_grid_restraint(self, shift_restraint, shift_grid_buffers):
    if shift_restraint == None: return None
    ahl = self.axis_header_list
    grid_restraint = []
    for i in range(len(ahl)):
        grid_restraint.append(list(map(lambda x: x,
                                        range(ahl[i]['DataPointCount']))))
    if shift_restraint == None:
      return grid_restraint
    for i in range(len(ahl)):
      if i >= len(shift_restraint): break
      shift_list = shift_restraint[i]
      if len(shift_list) == 0: continue
      grid_restraint[i] = []
      for shift in shift_list:
        idx = self.shift_to_grid(shift, i+1)
        for j in range(idx-shift_grid_buffers[i], idx+shift_grid_buffers[i]+1):
          grid_restraint[i].append(j)
      grid_restraint[i] = list(set(grid_restraint[i]))
    return grid_restraint
  # ---------------------------------------------------------------------------
  # Find peaks in entire spectrum
  def find_peaks(self, noise_level, grid_buffers, sign=1,
                  shift_restraint=None, shift_grid_buffers=None,
                  max_count=None, verbose=True):
    ahl = self.axis_header_list

    if shift_grid_buffers == None: shift_grid_buffers = grid_buffers
    grid_restraint = self.shift_restraint_to_grid_restraint(shift_restraint,
                                                          shift_grid_buffers)
    range_list = []
    if grid_restraint != None:
      for i in range(grid_restraint):
        if len(grid_restraint[i]) != 0:
          range_list.append(grid_restraint[i])
        else:
          range_list.append(range(ahl[i]['DataPointCount']))
    else:
      for i in range(len(ahl)):
          range_list.append(range(ahl[i]['DataPointCount']))

    if verbose and self.nproc != 1:
      print_log(datetime.datetime.now())
      print_log('Creating multiprocesses')
    # divide for parallelization: dim 1
    x_range = map(lambda x: [], range(self.nproc))
    for i in range(len(range_list[0])):
      xidx = min(int(float(range_list[0][i]) / self.fd_divider), self.nproc-1)
      x_range[xidx].append(range_list[0][i])

    it_list = []
    for i in range(self.nproc):
      if len(ahl) == 2:
        it = itertools.product(x_range[i], range_list[1])
      elif len(ahl) == 3:
        it = itertools.product(x_range[i], range_list[1], range_list[2])
      elif len(ahl) == 4:
        it = itertools.product(x_range[i], range_list[1], range_list[2], \
                                range_list[3])
      it_list.append(it)

    grid_peaks, heights = [], []
    process_list = []
    q = multiprocessing.Queue()
    if max_count == None:
      self.max_count = 1000 # maximum peak in a chunk
    else:
      self.max_count = max_count

    for i in range(len(it_list)):
      it = it_list[i]
      permute_count = len(x_range[i])
      for j in range(1, len(ahl)):
        permute_count *= len(range_list[j])
      if verbose:
        print_log('Process %d: %d permutes' % (i+1, permute_count))

      # the multiprocessing is not working properly in Windows
      if OS_WINDOWS:
        grid_peaks, heights = self.process_find_peaks_windows(it, permute_count, 
            noise_level, grid_buffers, sign, i, grid_restraint, q, verbose)

      else:
        t = multiprocessing.Process(target=self.process_find_peaks,
                                    args=[it, permute_count, noise_level, grid_buffers,
                                    sign, i, grid_restraint, q, verbose])

        t.start()
        process_list.append(t)
    if not OS_WINDOWS:        
      for t in process_list:
        pks, hts = q.get()
        grid_peaks += pks
        heights += hts
      for t in process_list:
        t.join()
#      t = multiprocessing.Process(target=self.process_find_peaks,
#                          args=[it, permute_count, noise_level, grid_buffers,
#                          sign, i, grid_restraint, q, verbose])
#      t.start()
#      process_list.append(t)
#    for t in process_list:
#      pks, hts = q.get()
#      grid_peaks += pks
#      heights += hts
#    for t in process_list:
#      t.join()
      
    if verbose and self.nproc != 1:
      print_log(datetime.datetime.now())
      print_log('Find peaks: %d peaks' % (len(grid_peaks)))
    return grid_peaks, heights
  
  def process_find_peaks_windows(self, it, permute_count, noise_level, grid_buffers,
                                 sign, pnum, grid_restraint, q, verbose):

    chunk_size = 100000
    chunk_count = int(permute_count / chunk_size) + 1
    cur_percent = -1
    peaks, heights = [], []
    for i in range(chunk_count):
      if verbose and self.nproc == 1:
        tmp_percent = int(float(i+1) / float(chunk_count) * 10.0)
        if tmp_percent > cur_percent:
          cur_percent = tmp_percent
          print_log(datetime.datetime.now())
          print_log('Find peaks: %d / %d (%3d %%)' % (i+1, chunk_count, cur_percent*10))
      pts = tuple(itertools.islice(it, chunk_size))
      pks, hts = self.find_peaks_per_node(pts, noise_level, grid_buffers, sign,
                                pnum, grid_restraint)
      peaks += pks
      heights += hts
    return peaks, heights

  def process_find_peaks(self, it, permute_count, noise_level, grid_buffers,
                        sign, pnum, grid_restraint, q, verbose):

    chunk_size = 100000
    chunk_count = int(permute_count / chunk_size) + 1
    cur_percent = -1
    peaks, heights = [], []
    for i in range(chunk_count):
      if verbose and self.nproc == 1:
        tmp_percent = int(float(i+1) / float(chunk_count) * 10.0)
        if tmp_percent > cur_percent:
          cur_percent = tmp_percent
          print_log(datetime.datetime.now())
          print_log('Find peaks: %d / %d (%3d %%)' % (i+1, chunk_count, cur_percent*10))
      pts = tuple(itertools.islice(it, chunk_size))
      pks, hts = self.find_peaks_per_node(pts, noise_level, grid_buffers, sign,
                                pnum, grid_restraint)
      peaks += pks
      heights += hts
    q.put([peaks, heights])
    return
  # ---------------------------------------------------------------------------
  # Find peaks in entire spectrum
  """  def find_peaks(self, noise_level, grid_buffers, sign=1,
                shift_restraint=None, shift_grid_buffers=None, verbose=False):
    ahl = self.axis_header_list

    if shift_grid_buffers == None: shift_grid_buffers = grid_buffers
    grid_restraint = self.shift_restraint_to_grid_restraint(shift_restraint,
                                                          shift_grid_buffers)
    range_list = []
    if grid_restraint != None:
      for i in range(grid_restraint):
        if len(grid_restraint[i]) != 0:
          range_list.append(grid_restraint[i])
        else:
          range_list.append(range(ahl[i]['DataPointCount']))
    else:
      for i in range(len(ahl)):
          range_list.append(range(ahl[i]['DataPointCount']))

    if len(ahl) == 2:
      it = itertools.product(range_list[0], range_list[1])
    elif len(ahl) == 3:
      it = itertools.product(range_list[1], range_list[1], range_list[2])
    elif len(ahl) == 4:
      it = itertools.product(range_list[2], range_list[1], range_list[2], \
                              range_list[3])

    grid_peaks, heights = [], []
    chunk_size = 100000
    permute_count = 1
    for i in range(0, len(ahl)):
      permute_count *= len(range_list[i])

    chunk_count = int(permute_count / chunk_size) + 1

    cur_percent = -1
    for i in range(chunk_count):
      if verbose:
        tmp_percent = int(float(i+1) / float(chunk_count) * 10.0)
        if tmp_percent > cur_percent:
          cur_percent = tmp_percent
          print datetime.datetime.now()
          print 'Find peaks: %d / %d (%3d %%)' % (i+1, chunk_count, cur_percent*10)

      pts = tuple(itertools.islice(it, chunk_size))
      temp_peaks, temp_heights = self.find_peaks_per_node(pts, noise_level,
              grid_buffers, sign, grid_restraint)
      grid_peaks += temp_peaks
      heights += temp_heights
    return grid_peaks, heights"""

  def find_peaks_per_node(self, pts, noise_level, grid_buffers, sign, pnum,
                  grid_restraint=None):
    grid_peaks, heights = [], []
    npt = len(pts)
    prev_grid_pt = list(map(lambda x: -2, range(len(pts))))
    sgb = sum(grid_buffers)
    hts = noise_level
    ahts = abs(hts)
    tf = False
    ndim = len(grid_buffers)
    zl = [[0, 0, 0], [0,0], [0], [],]
    for i in range(npt):
      grid_pt = pts[i]
      
      # if neighbor is maximum. No need to evaluate
      if tf:
        diff = 0
        for j in range(ndim):
          diff += abs(prev_grid_pt[j]-grid_pt[j])
        if diff < sgb: continue 
      
      temp_hts = self.get_data(grid_pt)
      atemp_hts = abs(temp_hts)
      if atemp_hts < ahts: continue
      if len(grid_peaks) > self.max_count and atemp_hts < self.min_heights[pnum]:
        continue

      if (temp_hts < noise_level and sign == 1) or \
         (temp_hts > noise_level and sign == -1) or \
         (temp_hts * sign < 0):
        continue

      # check if it is local maxima in 1D->2D->3D->4D
      for j in range(ndim):
        tf, hts = self.is_local_maxima(grid_pt,
                    grid_buffers[0:1+j] + zl[4-ndim+j],
                    sign, ref_ht = temp_hts)
        if not tf:
          break

      if tf:
        grid_peaks.append(grid_pt)
        heights.append(hts)
        prev_grid_pt = grid_pt
        self.min_heights[pnum] = min(self.min_heights[pnum], ahts)
    return grid_peaks, heights

    # EXAMPLE
    #noise = ut.sample_noise()
    #pks, hts = ut.find_peaks(noise*8., [2, 2])
    #peaks = ut.points_to_peaks(pks)
    #adj_peaks, adj_hts= ut.get_interpolated_data_by_peaks(peaks)
    #ut.write_sparky_peaks('test.list', adj_peaks, adj_hts)

  # ---------------------------------------------------------------------------
  # Find peaks around given grid points by peak simulation and fitting
  # mode: gaussian, lorentzian, pseudovoigt_50 (50 is 50% gaussian-mix)
  def find_fit_peaks(self, grid_pt, grid_buffers, sign=1, mode='gaussian'):
     pass
  # ---------------------------------------------------------------------------
  # Find peaks around given shifts by peak simulation and fitting
  #
  def find_fit_peaks_by_shifts(self, shift_pt, shift_buffers, sign=1,
                                mode='gaussian'):
    grid_pt = []
    grid_buffers = []
    for i in range(len(shift_buffers)):
      grid_buffers.append(shift_buffers[i] / self.pixel_size[i] + 1)
      grid_pt.append(self.shift_to_grid(shift_pt[i], i+1))
    return self.find_fit_peaks(grid_pt, grid_buffers, sign, mode)
  # ---------------------------------------------------------------------------
  # Automate noise estimation, peak picking, interpolation and saving
  def auto_pick_peaks(self, out_filename=None, grid_buffers=None, sign=0,
                    max_count=None, threshold=None, noise_filter = 8.,
                    shift_restraint = None, shift_grid_buffers=None,
                    write_peaks=True, verbose=False):
    noise = self.sample_noise(sample_count=100)
    if threshold == None:
      thresh = int(noise*noise_filter)
    else:
      thresh = threshold
    if verbose:
      print_log('Noise level: %d' % (thresh))
    if grid_buffers == None:
      g_buffers = list(map(lambda x: 2, range(len(self.axis_header_list))))
    else:
      g_buffers = grid_buffers
    pks, hts = self.find_peaks(thresh, g_buffers, sign, \
                    shift_restraint, shift_grid_buffers, max_count, verbose)
    if max_count != None:
      pks2, hts2 = self.filter_peaks_by_count(pks, hts, max_count)
      if verbose:
        print_log('Filtered by peak count: %d ---> %d' % (len(pks), len(pks2)))
      peaks = self.points_to_peaks(pks2)
    else:
      peaks = self.points_to_peaks(pks)
    adj_peaks, adj_hts = self.get_interpolated_data_by_peaks(peaks)
    if write_peaks and out_filename != None:
      self.write_sparky_peaks(out_filename, adj_peaks, adj_hts)
    return adj_peaks, adj_hts
  # ---------------------------------------------------------------------------
  # Refine sparky peaks
  def refine_sparky_peaks(self, in_filename, out_filename, grid_buffers=None,
           sign=0, max_count=None, noise_filter = 8.):
    noise = self.sample_noise(sample_count=60)
    noise_level = noise*noise_filter
    if grid_buffers == None:
      g_buffers = list(map(lambda x: 2, range(self.ndim)))
    else:
      g_buffers = grid_buffers
    spts = self.read_sparky_peaks(in_filename, g_buffers)
    pks, hts = self.find_peaks_per_node(spts, noise_level, g_buffers, sign)
    peaks = self.points_to_peaks(pks)
    adj_peaks, adj_hts = self.get_interpolated_data_by_peaks(peaks)
    self.write_sparky_peaks(out_filename, adj_peaks, adj_hts)
  # ---------------------------------------------------------------------------
  # Read SPARKY peak list file and convert to grid points
  def read_sparky_peaks(self, in_filename, grid_buffers):
    f = open(in_filename, 'r')
    lines = f.readlines()
    f.close()
    spts = []
    ahl = self.axis_header_list

    for line in lines:
      try:
        sp = line.strip().split()
        spt = []
        for i in range(1, len(ahl)+1):
          idx = self.shift_to_grid(float(sp[i]), i)
          spt.append(idx)

        if len(spt) == 2:
          it = itertools.product(range(spt[0]-grid_buffers[0],
                                       spt[0]+grid_buffers[0]+1),
                                 range(spt[1]-grid_buffers[1],
                                       spt[1]+grid_buffers[1]+1))
        elif len(spt) == 3:
          it = itertools.product(range(spt[0]-grid_buffers[0],
                                       spt[0]+grid_buffers[0]+1),
                                 range(spt[1]-grid_buffers[1],
                                       spt[1]+grid_buffers[1]+1),
                                 range(spt[2]-grid_buffers[2],
                                       spt[2]+grid_buffers[2]+1))
        elif len(spt) == 4:
          it = itertools.product(range(spt[0]-grid_buffers[0],
                                       spt[0]+grid_buffers[0]+1),
                                 range(spt[1]-grid_buffers[1],
                                       spt[1]+grid_buffers[1]+1),
                                 range(spt[2]-grid_buffers[2],
                                       spt[2]+grid_buffers[2]+1),
                                 range(spt[3]-grid_buffers[3],
                                       spt[3]+grid_buffers[3]+1))
        spts.append(list(it))
      except:
        continue

    print_log('%d sparky peaks made' % (len(spts)))
    return sum(spts, [])
  # ---------------------------------------------------------------------------
  # Write SPARKY peak list file
  def write_sparky_peaks(self, out_filename, peaks, heights=None):
    # write column headers
    ahl = self.axis_header_list
    columns = ['Assignment']
    for i in range(self.ndim):
      columns.append('w%d' % (i+1))
    if heights != None:
      columns.append('Data Height')
    lines = ''
    for clm in columns:
      lines = lines + '%-13s' % (clm)
    lines = lines + '\n\n'
    for i in range(len(peaks)):
      if len(ahl) == 2: lines = lines + '%10s   ' % ('?-?')
      elif len(ahl) == 3: lines = lines + '%10s   ' % ('?-?-?')
      elif len(ahl) == 4: lines = lines + '%10s   ' % ('?-?-?-?')
      peak = peaks[i]
      for clm in peak:
        lines = lines + '%-13.3f' % (clm)
      if heights != None:
        lines = lines + '%13d' % (int(heights[i]))
      lines = lines + '\n'
    f = open(out_filename, 'w')
    f.write(lines)
    f.close()

  # ---------------------------------------------------------------------------
  # Write a copy of transformed data
  # mode: exponential, multiply, combine, subtract
  def write_transform(self, out_filename, transform_mode, \
                      transform_factor, transform_factor2, overwrite=0):
    use_logo = """
      ucsfTool.write_transform('file_to_write.ucsf',
                          'transform_mode',   # mult, comb, subt, pow, abs
                          transform_factor,   # e.g.
                                              # pow(transform_factor,
                                              #     transform_factor2)
                          transform_factor2,  # ignored if not power.
                                              # e.g. 'pow', 2, NC_proc value
                          overwrite)          # overwrite 0 or 1
    """
    if self.is_opened == 0:
      print_log('Error in ucsfTool:write_transform()- file is not opened')
      return None

    if overwrite == 0 and os.path.exists(out_filename):
      print_log('Error in ucsfTool:write_transform()- output file already exists')
      print_log(use_logo)
      return 0

    try:
      trans_mode = ['mult','comb','subt','pow','abs'].index(transform_mode)
    except:
      print_log('Error in ucsfTool:write_transform()- incorrect transform mode')
      print_log(use_logo)
      return 0

    f = open(out_filename, 'wb')
    # write header
    self.write_ucsf_file_header(f, self.file_header)
    # write axis header
    for i in range(self.ndim):
      self.write_ucsf_axis_header(f, self.ndim)
    # write data
    data_count = (self.file_size - (180+128*self.ndim) ) / 4
    self.file_object[0].seek(180+128*self.ndim)
    for i in range(data_count):
      temp = self.file_object[0].read(4)
      temp2 = struct.unpack('>f', temp)[0]
      # modify
      if trans_mode == 0: # mult
        temp3 = temp2 * transform_factor
      elif trans_mode == 1: # comb
        temp3 = temp2 + transform_factor
      elif trans_mode == 2: # subt
        temp3 = temp2 - transform_factor
      elif trans_mode == 3: # pow
        temp3 = temp2*(transform_factor**transform_factor2)
      elif trans_mode == 4: # abs
        temp3 = abs(temp2)
      #f.write(struct.pack('>f', temp3))
      f.write(pack_float(temp3))
    f.close()
  # ---------------------------------------------------------------------------
  # Write projection
  # proj_mode : 'avg', 'sum', 'min', max', 'pos_avg', 'neg_avg', .....
  def write_projection(self, out_filename, proj_dim, proj_mode = 'avg', overwrite=0):
    use_logo = """
      ucsfTool.write_projection('file_to_write.ucsf',
                          dimension,          # dimension number to project
                          proj_mode='avg',    # 'avg', 'sum', 'min', 'max'
                                              # 'pos_avg', 'neg_avg'....
                                              # (e.g. 1,2, or 3)
                          overwrite=0)        # overwrite 0 or 1
    """
    if self.is_opened == 0:
      print_log('Error in ucsfTool:write_projection()- file is not opened')
      return None

    if overwrite == 0 and os.path.exists(out_filename):
      print_log('Error in ucsfTool:write_projection()- output file already exists')
      print_log(use_logo)
      return 0

    try:
      p_mode = ['avg','sum','min','max',
                'pos_avg','pos_sum','pos_min','pos_max',
                'neg_avg','neg_sum','neg_min','neg_max',].index(proj_mode)
      sign_mode = p_mode / 4  # 0: all, 1: pos, 2: neg
      p_mode = p_mode % 4
    except:
      if proj_mode == 'abs' or proj_mode == 'absolute':
        p_mode = -1
        sign_mode = 1
      else:
        print_log('Error in ucsfTool:write_projection()- incorrect projection mode')
        print_log(use_logo)
        return 0

    # write header
    file_header = self.copy_file_header(self.file_header)
    if file_header['DimCount'] < 3:
      msg = 'Error in ucsfTool:write_projection()- current ucsf dimension '
      msg = msg + 'must be 3 or 4'
      print_log(msg)
      print_log(use_logo)
      return 0
    if proj_dim < 1 or proj_dim > file_header['DimCount']:
      msg = 'Error in ucsfTool:write_projection()- incorrect projection '
      msg = msg + 'dimension'
      print_log(msg)
      print_log(use_logo)
      return 0

    f = open(out_filename, 'wb')
    file_header['DimCount'] = file_header['DimCount'] - 1
    self.write_ucsf_file_header(f, file_header)

    # fill axis header
    axis_header_list = [] # this is new axis list excluding proj dim
    proj_axis_header = self.axis_header_list[proj_dim-1]
    for i in range(self.ndim):
      if i == proj_dim-1: continue
      ah = self.copy_axis_header(self.axis_header_list[i])
      axis_header_list.append(ah)

    # estimate new tile size
    self.optimize_tile_size(axis_header_list)

    # and write axis header
    cube_count = 1
    cube_size = 1
    for i in range(self.ndim):
      self.write_ucsf_axis_header(f, axis_header_list[i])
      cube_count = cube_count * axis_header_list[i]['TileCount']
      cube_size = cube_size * axis_header_list[i]['TileSize']

    # write data
    for i in range(cube_count):
      cube_grid_pt = [0] * self.ndim
      pos = i
      for j in range(self.ndim):
        dim_idx = self.ndim-j-1
        cube_grid_pt[dim_idx] = pos % axis_header_list[dim_idx]['TileCount']
        pos = pos / axis_header_list[dim_idx]['TileCount']
      for j in range(cube_size):
        # absolute grid point
        grid_pt = [0] * self.ndim # this is absolute position
        part_grid_pt = [0] * self.ndim
        pos = j
        for k in range(self.ndim):
          dim_idx = self.ndim-k-1
          part_grid_pt[dim_idx] = pos % axis_header_list[dim_idx]['TileSize']
          pos = pos / axis_header_list[dim_idx]['TileSize']
        # combine cube pos + part pos
        for k in range(self.ndim):
          grid_pt[k] = cube_grid_pt[k] * axis_header_list[k]['TileSize'] \
                      + part_grid_pt[k]
        #print grid_pt
        grid_pt.insert(proj_dim-1,0)
        # add increment through project dimension
        value_list = []
        for k in range(proj_axis_header['DataPointCount']):
          grid_pt[proj_dim-1] = k
          val = self.get_data(grid_pt)
          if p_mode == -1:
            val = abs(val)
          if sign_mode == 1 and val <= 0: continue
          elif sign_mode == 2 and val >= 0: continue
          value_list.append(val)
        # process and write
        if len(value_list) == 0:
          value_list.append(0)
        if p_mode == 0:  # avg
            val = sum(value_list) / float(len(value_list))
        elif p_mode == 1: val = sum(value_list)                 # sum
        elif p_mode == 2: val = min(value_list)                 # min
        elif p_mode == 3 or p_mode == -1: val = max(value_list)     # max
        #f.write(struct.pack('>f', val))
        f.write(pack_float(val))
    f.close()

  # ---------------------------------------------------------------------------
  # Write 2d planes from 3d cube
  #
  def write_planes(self, out_prefix, dim=0, reverse=1, init=1, gap = 1, \
                    overwrite=0):
    use_logo = """
      ucsfTool.write_planes('prefix',         # prefix_0.ucsf, prefix_1.ucsf ....
                          dim=0,              # dimension number to pick
                                              # (e.g. 1,2, or 3, and 0 is auto)
                          reverse=1,          # reverse mode for the dimension
                                              # (e.g. 0: no reverse, 1: reverse)
                          init=1,             # starting index
                          gap=1,              # gap between index
                          overwrite=0)        # overwrite 0 or 1
    """
    if self.is_opened == 0:
      print_log('Error in ucsfTool:write_planes()- file is not opened')
      return None

    if dim < 0 or dim > self.ndim:
      print_log('Error in ucsfTool:write_planes()- incorrect dimension')
      print_log(use_logo)
      return 0

    # set header
    # file header
    file_header = self.copy_file_header(self.file_header)
    if file_header['DimCount'] < 3:
      msg = 'Error in ucsfTool:write_planes()- current ucsf dimension '
      msg = msg + 'must be 3 or 4'
      print_log(msg)
      print_log(use_logo)
      return 0
    file_header['DimCount'] = file_header['DimCount'] - 1

    # dimension process
    split_dim = dim
    # Non general atom name
    if split_dim == 0:
      for i in range(self.ndim):
        atm = self.axis_header_list[i]['AtomName']
        if atm != '1H' and atm != '15N' and atm != '13C':
          split_dim = i+1
          break
    # Or, the smallest number
    if split_dim == 0:
      size = 99999
      for i in range(self.ndim):
        size2 = self.axis_header_list[i]['DataPointCount']
        if size2 < size:
          size = size2
          split_dim = i+1

    # fill axis header
    axis_header_list = [] # this is new axis list excluding proj dim
    split_axis_header = self.axis_header_list[split_dim-1]
    for i in range(self.ndim):
      if i == split_dim-1: continue
      ah = self.copy_axis_header(self.axis_header_list[i])
      axis_header_list.append(ah)

    # estimate new tile size
    self.optimize_tile_size(axis_header_list)

    cube_count = 1
    cube_size = 1
    for i in range(self.ndim):
      cube_count = cube_count * axis_header_list[i]['TileCount']
      cube_size = cube_size * axis_header_list[i]['TileSize']

    # prepare file names
    # check if user input is decimal
    try:
      temp = int(init)
      temp = int(gap)
      int_mode = 1
    except:
      int_type = 0
    out_files = []
    max_num = gap * self.axis_header_list[split_dim-1]['DataPointCount'] + init
    for i in range(self.axis_header_list[split_dim-1]['DataPointCount']):
      if int_mode == 1:
        tp = gap*i + init
        if max_num < 10 or max_num >= 100000:
          out_files.append('%s_%d.ucsf' % (out_prefix, tp))
        elif max_num < 100:
          out_files.append('%s_%02d.ucsf' % (out_prefix, tp))
        elif max_num < 1000:
          out_files.append('%s_%03d.ucsf' % (out_prefix, tp))
        elif max_num < 10000:
          out_files.append('%s_%04d.ucsf' % (out_prefix, tp))
        elif max_num < 100000:
          out_files.append('%s_%05d.ucsf' % (out_prefix, tp))
      else:
        tp = gap(float(i)) + init
        if max_num < 10:
          out_files.append('%s_%05.3f.ucsf' % (out_prefix, tp))
        elif max_num < 100:
          out_files.append('%s_%06.3f.ucsf' % (out_prefix, tp))
        elif max_num < 1000:
          out_files.append('%s_%07.3f.ucsf' % (out_prefix, tp))
        elif max_num < 10000:
          out_files.append('%s_%08.3f.ucsf' % (out_prefix, tp))
        elif max_num < 100000:
          out_files.append('%s_%09.3f.ucsf' % (out_prefix, tp))
        else:
          out_files.append('%s_%.3f.ucsf' % (out_prefix, tp))
      if overwrite == 0 and os.path.exists(out_files[-1]):
        print_log('Error in ucsfTool:write_planes()- output file already exists')
        print_log(use_logo)
        return 0

    for i in range(len(out_files)):
      out_filename = out_files[i]

      f = open(out_filename, 'wb')

      # write header
      self.write_ucsf_file_header(f, file_header)

      # and write axis header
      for j in range(len(axis_header_list)):
        self.write_ucsf_axis_header(f, axis_header_list[j])

      # write data
      for j in range(cube_count):
        cube_grid_pt = [0] * len(axis_header_list)
        pos = j
        for k in range(len(axis_header_list)):
          dim_idx = len(axis_header_list)-k-1
          cube_grid_pt[dim_idx] = pos % axis_header_list[dim_idx]['TileCount']
          pos = pos / axis_header_list[dim_idx]['TileCount']
        for k in range(cube_size):
          # absolute grid point
          grid_pt = [0] * len(axis_header_list) # this is absolute position
          part_grid_pt = [0] * len(axis_header_list)
          pos = k
          for l in range(len(axis_header_list)):
            dim_idx = len(axis_header_list)-l-1
            part_grid_pt[dim_idx] = pos % axis_header_list[dim_idx]['TileSize']
            pos = pos / axis_header_list[dim_idx]['TileSize']
          # combine cube pos + part pos
          for l in range(len(axis_header_list)):
            grid_pt[l] = cube_grid_pt[l] * axis_header_list[l]['TileSize'] \
                        + part_grid_pt[l]
          #print grid_pt
          grid_pt.insert(split_dim-1,0)
          # add increment through project dimension
          if reverse == 1:  grid_pt[split_dim-1] = i
          else:             grid_pt[split_dim-1] = \
                                    split_axis_header['DataPointCount'] - i - 1
          val = self.get_data(grid_pt)
          f.write(struct.pack('>f', val))
      f.close()

  # ---------------------------------------------------------------------------
  # Write axis swapped
  #
  def write_swapped_axis(self, out_filename, dim1, dim2, overwrite = 0):
    use_logo = """
      ucsfTool.write_swapped_axis('filename.ucsf', # output
                          dim1, dim2,         # dimension to swap (1, 2)
                          overwrite=0)        # overwrite 0 or 1
    """

    if self.is_opened == 0:
      print_log('Error in ucsfTool:write_swapped_axis()- file is not opened')
      return None

    if dim1 < 1 or dim1 > len(self.axis_header_list) or dim2 < 1 \
                          or dim2 > len(self.axis_header_list) or dim1 == dim2:
      print_log('Error in ucsfTool:write_swapped_axis()- incorrect dimension')
      print_log(use_logo)
      return 0

    if overwrite == 0 and os.path.exists(out_filename):
      print_log('Error in ucsfTool:write_swapped_axis()- output file already exists')
      print_log(use_logo)
      return 0

    # set header
    # file header
    file_header = self.copy_file_header(self.file_header)

    # fill axis header
    axis_header_list = []
    for i in range(len(self.axis_header_list)):
      if i != dim1-1 and i != dim2-1:
        axis_header_list.append(self.copy_axis_header(self.axis_header_list[i]))
      elif i == dim1-1:
        axis_header_list.append(
                          self.copy_axis_header(self.axis_header_list[dim2-1]))
      else:
        axis_header_list.append(
                          self.copy_axis_header(self.axis_header_list[dim1-1]))

    cube_count = 1
    cube_size = 1
    for i in range(len(axis_header_list)):
      cube_count = cube_count * axis_header_list[i]['TileCount']
      cube_size = cube_size * axis_header_list[i]['TileSize']

    f = open(out_filename, 'wb')

    # write header
    self.write_ucsf_file_header(f, file_header)

    # and write axis header
    for i in range(len(axis_header_list)):
      self.write_ucsf_axis_header(f, axis_header_list[i])

    # write data
    for i in range(cube_count):
      cube_grid_pt = [0] * len(axis_header_list)
      pos = i
      for j in range(len(axis_header_list)):
        dim_idx = len(axis_header_list)-j-1
        cube_grid_pt[dim_idx] = pos % axis_header_list[dim_idx]['TileCount']
        pos = pos / axis_header_list[dim_idx]['TileCount']

      for j in range(cube_size):
        # absolute grid point
        grid_pt = [0] * len(axis_header_list) # this is absolute position
        part_grid_pt = [0] * len(axis_header_list)
        pos = j
        for k in range(len(axis_header_list)):
          dim_idx = len(axis_header_list)-k-1
          part_grid_pt[dim_idx] = pos % axis_header_list[dim_idx]['TileSize']
          pos = pos / axis_header_list[dim_idx]['TileSize']
        # combine cube pos + part pos, and swap grid
        for k in range(len(axis_header_list)):
          grid_pt[k] = cube_grid_pt[k] * axis_header_list[k]['TileSize'] \
                      + part_grid_pt[k]
        swap_grid_pt = list(grid_pt)
        swap_grid_pt[dim1-1] = grid_pt[dim2-1]
        swap_grid_pt[dim2-1] = grid_pt[dim1-1]
        val = self.get_data(swap_grid_pt)
        f.write(struct.pack('>f', val))

    f.close()

  # ---------------------------------------------------------------------------
  # Write shifted
  #
  def write_shifted(self, out_filename, shift_dim, amount, unit='ppm', \
                    overwrite=0):
    use_logo = """
      ucsfTool.write_shifted('filename.ucsf', # output
                          shift_dim,          # dimension to shift
                                              # (e.g 1, 2, or 3)
                          amount,             # value to shift. By summation
                          unit='ppm',         # "ppm", "hz", or "pt"
                          overwrite=0)        # overwrite 0 or 1
    """

    if self.is_opened == 0:
      print_log('Error in ucsfTool:write_shifted()- file is not opened')
      return None

    if shift_dim < 1 or shift_dim > len(self.axis_header_list):
      print_log('Error in ucsfTool:write_shifted()- incorrect dimension')
      print_log(use_logo)
      return 0

    if overwrite == 0 and os.path.exists(out_filename):
      print_log('Error in ucsfTool:write_shifted()- output file already exists')
      print_log(use_logo)
      return 0

    if unit.lower() != 'ppm' and unit.lower() != 'hz' and unit.lower() != 'pt':
      print_log('Error in ucsfTool:write_shifted()- incorrect unit')
      print_log(use_logo)
      return 0

    # set header
    f = open(out_filename, 'wb')

    # write header
    self.write_ucsf_file_header(f, self.file_header)

    # and write axis header
    for i in range(len(self.axis_header_list)):
      ah = self.copy_axis_header(self.axis_header_list[i])

      # do modification- Center (ppm)
      if i == shift_dim-1:
        if unit.lower() == 'ppm':
          ah['Center'] = ah['Center'] + amount
        elif unit.lower() == 'hz':
          ah['Center'] = ah['Center'] + amount / ah['SpecFreq']
        elif unit.lower() == 'pt':
          ah['Center'] = ah['Center'] + float(amount) * ah['SpecWidth'] \
                        / float(ah['DataPointCount']-1)
      self.write_ucsf_axis_header(f, ah)

    # write data
    data_count = (self.file_size - (180+128*len(self.axis_header_list)) ) / 4
    self.file_object[0].seek(180+128*len(self.axis_header_list))
    for i in range(data_count):
      temp = self.file_object[0].read(4)
      f.write(temp)
    f.close()

  # ---------------------------------------------------------------------------
  # Write concatenated
  #
  #def write_concatenated(self, ref_file_name):
  #

  # ---------------------------------------------------------------------------
  # Write header
  #
  def write_ucsf_file_header(self, file_object, file_header):
    f = file_object
    f.seek(0)
    f.write(struct.pack('10s', 'UCSF NMR'))
    f.write(struct.pack('B',  file_header['DimCount']))
    f.write(struct.pack('2B', file_header['DataCompCount'], 0))
    f.write(struct.pack('B',  file_header['FileVersion']))      # 14 bytes
    # 180 byte: header + 166 bytes
    import datetime
    dstr = datetime.datetime.now().strftime('%Y-%m-%d')
    f.write(struct.pack('30s', "Woonghee's ucsftool %s" % (dstr)))
    for i in range(2): # 136 bytes
      f.write(struct.pack('8d',0,0,0,0,0,0,0,0))
    f.write(struct.pack('d',0)) # cap 180 bytes

  # ---------------------------------------------------------------------------
  # Write axis header
  #
  def write_ucsf_axis_header(self, file_object, axis_header):
    f = file_object
    f.write(struct.pack('6s', axis_header['AtomName']))
    f.write(struct.pack('2B', 0,0))
    f.write(struct.pack('>I', axis_header['DataPointCount']))
    f.write(struct.pack('4B', 0,0,0,0))
    f.write(struct.pack('>I', axis_header['TileSize']))
    f.write(struct.pack('>f', axis_header['SpecFreq']))
    f.write(struct.pack('>f', axis_header['SpecWidth']))
    f.write(struct.pack('>f', axis_header['Center']))
    f.write(struct.pack('12d', 0,0,0,0,0,0,0,0,0,0,0,0)) # cap 128 bytes

def auto_picking(in_filename, out_filename=None, grid_buffers=None, \
                    noise_filter=8, sign=0, max_count=None, \
                    threshold=None, nproc = 2, verbose=False):
  print_log("""
  Automated Peak Picking by ucsfTool
  by Woonghee Lee (whlee@nmrfam.wisc.edu)

  """)
  import datetime
  print_log(datetime.datetime.now())
  # Make 2D projections
  ut = ucsfTool()
  if out_filename == None:
    pre, ext = os.path.splitext(in_filename)
    out_filename= pre + '.list'
  print_log('Picking peaks: ' + out_filename)
  ut.ucsf_open(in_filename, nproc=nproc)
  peaks, heights = ut.auto_pick_peaks(out_filename, \
              grid_buffers=grid_buffers, noise_filter = noise_filter, \
              sign=sign, max_count=max_count, threshold=threshold, verbose=verbose)
  ut.ucsf_close()
  print_log('\t%d peaks picked.' % (len(peaks)))
  print_log(datetime.datetime.now())


def auto_picking_3D_proj_method(in_filename, out_filename=None, \
            noise_filter = 8, sign=0, max_count=None, threshold=None, \
            nproc = 1, verbose=False):
  print_log(datetime.datetime.now())
  # Set 2D projections
  proj_files = ['xy.ucsf', 'yz.ucsf', 'xz.ucsf']
  proj_dims = [3, 2, 1]
  peak_dims = [[0,1],[0,2],[1,2]]
  restraints = [[],[],[]]

  # Make 2D projections
  ut = ucsfTool()
  ut.ucsf_open(in_filename)
  for i in range(3):
      print_log('Making projections: ' + proj_files[i])
      ut.write_projection(proj_files[0], proj_dims[i], \
                          proj_mode = 'abs', overwrite=1)
  ut.ucsf_close()

  # Pick peaks from 2D projections
  for i in range(3):
      ut.ucsf_open(proj_files[i], nproc=nproc)
      print_log('Picking peaks: ' + proj_files[i])
      peaks, heights = ut.auto_pick_peaks(sign=1, write_peaks=False)
      print_log('\t%d peaks found.' % (len(peaks)))
      for peak in peaks:
          restraints[peak_dims[i][0]].append(peak[0])
          restraints[peak_dims[i][1]].append(peak[1])
      ut.ucsf_close()

  if out_filename == None:
    pre, ext = os.path.splitext(in_filename)
    out_filename= pre + '.list'
  print_log('Picking peaks: ' + out_filename)
  ut.ucsf_open(in_filename, nproc=nproc)
  peaks, heights = ut.auto_pick_peaks(out_filename,
                                    shift_restraint=restraints,
                                    shift_grid_buffers=[4, 4, 4],
                                    max_count=max_count,
                                    threshold=threshold,
                                    sign = sign)
  print_log('\t%d peaks picked.' % (len(peaks)))
  ut.ucsf_close()
  print_log(datetime.datetime.now())

grid_peaks = []
if __name__=="__main__":
  if func != 'find_peaks':
    print_log('List of available functions:')
    ut=ucsfTool()
    ut.help()
  else:
    multiprocessing.freeze_support()
    grid_peaks, _ = ut.find_peaks(noiselevel, grid_buffers=res, sign=sign, 
                              verbose=verbose)

#      def find_peaks(self, noise_level, grid_buffers, sign=1,
#                  shift_restraint=None, shift_grid_buffers=None,
#                  max_count=None, verbose=True):