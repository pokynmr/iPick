# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
New Peak List Dialog for iPick and Cross-Validation Modules

@author: Mehdi Rahimi
"""

import sys

if sys.version_info[0] == 2:
  import Tkinter as tk
  import tkMessageBox
  import tkFont
else:
  import tkinter as tk
  import tkinter.messagebox as tkMessageBox
  import tkinter.font as tkFont

try:
  import sparky
  from sparky import sputil, tkutil, pyutil
except:
  import poky
  from poky import sputil, tkutil, pyutil
  
  
class peak_list_dialog(tkutil.Dialog, tkutil.Stoppable):

  def __init__(self, session):

    self.session = session
    self.title = 'Peak List'
    self.spectrum = None
    self.peaks = ()
    self.settings = peak_list_settings()

    tkutil.Dialog.__init__(self, session.tk, self.title)


    spectra_list_frame = tk.Frame(self.top)
    spectra_list_frame.pack(anchor='w', padx=8, pady=(8,5))

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    spectra_list_names = []
    for spec in self.spec_list:
        spectra_list_names.append(spec.name)
         
    self.spectrum_selection = tk.StringVar()
    self.spectrum_selection.set(spectra_list_names[0])

    spectra_list_label = tk.Label(spectra_list_frame, text="Showing the peak list for: ")
    spectra_list_label.pack(side='left', anchor='w')

    spectra_list_menu = tk.OptionMenu(spectra_list_frame, self.spectrum_selection, *spectra_list_names, command=self.change_spectrum)
    spectra_list_menu.pack(side='left', anchor='w')
    
    
    peak_list_frame = tk.Frame(self.top)
    peak_list_frame.pack(side='top', expand=1, fill="both")
    
    self.pl = sputil.peak_listbox(peak_list_frame)
    self.pl.frame.pack(side='top', fill='both', expand=1)
    self.pl.listbox['selectmode'] = 'extended'
    self.pl.listbox.bind('<ButtonRelease-1>', self.peak_selected)
    self.pl.listbox.bind('<ButtonRelease-2>', self.pl.goto_peak_cb)
    self.pl.listbox.bind('<Double-ButtonRelease-1>', self.pl.goto_peak_cb)
    self.peak_list = self.pl
    
#    xscroll = tk.Scrollbar(peak_list_frame, orient='horizontal', command=self.pl.listbox.xview)
#    xscroll.pack(side='top', expand=0, fill="x")
#    self.pl.listbox['xscrollcommand'] = xscroll.set
      
      
#    # fix the fonts
#    suggested_fonts = ['Arial', 'NotoSans', 'Ubuntu', 'SegoeUI', 'Helvetica',
#                       'Calibri', 'Verdana', 'DejaVuSans', 'FreeSans']
#    for fnt in suggested_fonts:
#      if fnt in tkFont.families():
#        self.peak_list.listbox['font'] = (fnt, 10)
#        self.peak_list.heading['font'] = (fnt, 11)
#        break

    progress_label = tk.Label(self.top, anchor='nw')
    progress_label.pack(side='top', anchor='w')

    br = tkutil.button_row(self.top,
               ('Update', self.update_cb),
               ('Setup...', self.setup_cb),
               ('Sort by height', self.sort_cb),
               ('Sort by Reliability Score', self.sort_rs),
               ('Sort by Total Corresponding Peaks', self.sort_total_corr),
               )
    br.frame.pack(side='top', anchor='w')

    rs_frame = tk.Frame(self.top)
    rs_frame.pack(anchor='w')

#    br2 = tkutil.button_row(rs_frame,
#               ('Sort by height', self.sort_cb),
#               #('Remove peaks with Reliability Score of 0', self.remove_rs0),
#               )
#    br2.frame.pack(side='left', anchor='w')

    self.remove_rs0_thresh = tkutil.entry_field(rs_frame, 'Reliability Score threshold for removing peaks:',
                                                width=12, initial='100.0')
    self.remove_rs0_thresh.frame.pack(side='left', padx=(5,5))
    tkutil.create_hint(self.remove_rs0_thresh.frame,
                       'Remove peaks with "ABSOLUTE Reliability Score" at and below this threshold')

    remove_rs0_button = tk.Button(rs_frame, text='Remove', command=self.remove_rs0)
    remove_rs0_button.pack(side='left')
    tkutil.create_hint(remove_rs0_button,
                       'Remove peaks with "ABSOLUTE Reliability Score" below this threshold')

    cv_frame = tk.Frame(self.top)
    cv_frame.pack(anchor='w')

    cv = tkutil.button_row(cv_frame,
               ('Remove Lone Peaks', self.remove_peaks),
               ('Save...', self.peak_list.save_cb),
               ('Stop', self.stop_cb),
               ('Close', self.close_cb),
               ('Help', sputil.help_cb(session, 'PeakListPython')),
               )
    cv.frame.pack(side='left', anchor='w')

    tkutil.create_hint(cv.buttons[0], 'Remove peaks that have no corresponding peaks (Total:0, xcheck:0)')
    tkutil.create_hint(cv.buttons[1], 'Save the Peak List data as being shown')

    keypress_cb = pyutil.precompose(sputil.command_keypress_cb, session)
    self.pl.listbox.bind('<KeyPress>', keypress_cb)

    tkutil.Stoppable.__init__(self, progress_label, cv.buttons[2])
    self.change_spectrum()
    

  # ---------------------------------------------------------------------------
  #
  def change_spectrum(self, *args):
    for spec in self.spec_list:
        if spec.name == self.spectrum_selection.get():
            self.spectrum = spec
            break
    self.show_spectrum_peaks(self.spectrum)


  # ---------------------------------------------------------------------------
  #
  def remove_peaks(self, *args):

    confirmation = tkMessageBox.askokcancel(title='Remove peaks?',
             message='Do you want to remove peaks that have no corresponding peaks (determined by cross validation)?')

    if confirmation == True:
        for peak in self.spectrum.peak_list():
            try:
                if peak.is_assigned == 1:
                # we won't delete a peak that the user has assigned
                    continue

                if peak.note.find('xcheck:0') == 0:
                # index of 0 means this also won't delete a peak that the user has put notes on
                    peak.selected = 1
                    self.session.command_characters("")
            except:
                continue
        #tkMessageBox.showinfo(title='Done!', message='Peaks with zero corresponding peaks have been deleted')
        self.update_cb()

  # ---------------------------------------------------------------------------
  #
  def peak_selected(self, *args):
    self.pl.select_peak_cb(*args)

    peaks = self.session.selected_peaks()
    RS = reliability_score(peaks[-1])
    self.remove_rs0_thresh.variable.set('%7.2f' % RS)

  # ---------------------------------------------------------------------------
  #
  def show_peaks(self, peaks, title):

    self.title = title
    self.top.title(self.title)
    self.spectrum = None
    self.peaks = peaks
    self.stoppable_call(self.update_peaks)

  # ---------------------------------------------------------------------------
  #
  def show_spectrum_peaks(self, spectrum):

    self.title = spectrum.name + ' peak list'
    self.top.title(self.title)
    self.spectrum = spectrum
    self.peaks = None
    self.stoppable_call(self.update_peaks)
    self.spectrum_selection.set(spectrum.name)

  # ---------------------------------------------------------------------------
  #
  def update_cb(self):

    self.stoppable_call(self.update_peaks)

  # ---------------------------------------------------------------------------
  #
  def sort_cb(self):

    self.stoppable_call(self.sort_peaks)

  # ---------------------------------------------------------------------------
  #
  def sort_rs(self):

    self.stoppable_call(self.sort_reliability)

  # ---------------------------------------------------------------------------
  #
  def remove_rs0(self):

    self.stoppable_call(self.remove_peaks_rs0)

  # ---------------------------------------------------------------------------
  #
  def setup_cb(self):

    psd = sputil.the_dialog(peak_list_settings_dialog, self.session)
    psd.set_parent_dialog(self, self.settings, self.new_settings)
    psd.top.title(self.title + ' settings')
    psd.show_window(1)

  # ---------------------------------------------------------------------------
  #
  def new_settings(self, settings):

    self.settings = settings
    self.stoppable_call(self.update_peaks)

  # ---------------------------------------------------------------------------
  #
  def update_peaks(self):

    self.progress_report('Getting peaks')
    if self.spectrum:
      peaks = self.spectrum.peak_list()
    else:
      peaks = self.peaks

    if self.settings.sort_by_assignment:
      peaks = sputil.sort_peaks_by_assignment(peaks, self)

    self.field_initializations(peaks)

    if peaks:
      dimension = peaks[0].spectrum.dimension
    else:
      dimension = 0
    self.peak_list.heading['text'] = ('%d peaks\n' % len(peaks) +
                      self.heading(dimension))

    self.peak_list.clear()
    self.stoppable_loop('peaks', 50)
    for rank, peak in enumerate(peaks):
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak, rank), peak)

  # ---------------------------------------------------------------------------
  #
  def sort_peaks(self):

    self.progress_report('Sorting peaks')
    if self.spectrum:
      peaks = self.spectrum.peak_list()
    else:
      peaks = self.peaks

    if peaks:
      dimension = peaks[0].spectrum.dimension
    else:
      dimension = 0
    self.peak_list.heading['text'] = ('%d peaks\n' % len(peaks) +
                      self.heading(dimension))


    # sort by intensity
    data = []
    for peak in peaks:
      data.append((peak.data_height, peak))

    peaks = []
    # sort by x_pos
    data = sorted(data, key=lambda data: data[0], reverse=True)

    for (height, peak) in data:
      peaks.append(peak)

    self.field_initializations(peaks)

    self.peak_list.clear()

    self.stoppable_loop('peaks', 50)
    for rank, peak in enumerate(peaks):
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak, rank), peak)

  # ---------------------------------------------------------------------------
  #
  def sort_total_corr(self):

    self.update_peaks()

    self.progress_report('Sorting peaks by total corresponding peaks')
    if self.spectrum:
      peaks = self.spectrum.peak_list()
    else:
      peaks = self.peaks

    if peaks:
      dimension = peaks[0].spectrum.dimension
    else:
      dimension = 0
    self.peak_list.heading['text'] = ('%d peaks\n' % len(peaks) +
                      self.heading(dimension))

    total_has_value = False
    # sort by total corresponding peaks
    data = []
    for peak in peaks:
        total = total_corresponding(peak)
        if total > 0:
            total_has_value = True
        data.append((total, peak))

    if total_has_value == False:
        tkMessageBox.showwarning(title='Error', message='You need to run the Cross-Validation first!')
        self.progress_report('You need to run the Cross-Validation first!')
        return

    peaks = []
    data = sorted(data, key=lambda data: data[0], reverse=True)

    for (TC, peak) in data:
      peaks.append(peak)

    self.field_initializations(peaks)

    self.peak_list.clear()

    self.stoppable_loop('peaks', 50)
    for rank, peak in enumerate(peaks):
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak, rank), peak)
      
  # ---------------------------------------------------------------------------
  #
  def sort_reliability(self):

    self.update_peaks()

    self.progress_report('Sorting peaks by reliability')
    if self.spectrum:
      peaks = self.spectrum.peak_list()
    else:
      peaks = self.peaks

    if peaks:
      dimension = peaks[0].spectrum.dimension
    else:
      dimension = 0
    self.peak_list.heading['text'] = ('%d peaks\n' % len(peaks) +
                      self.heading(dimension))

    RS_has_value = False
    # sort by reliability score
    data = []
    for peak in peaks:
        RS = reliability_score(peak)
        data.append((RS, peak))
        if RS > 0:
            RS_has_value = True

    if RS_has_value == False:
        tkMessageBox.showwarning(title='Error', message='You need to run the Auto Integration first!')
        self.progress_report('You need to run the Auto Integration first!')
        return

    peaks = []
    data = sorted(data, key=lambda data: data[0], reverse=True)

    for (RS, peak) in data:
      peaks.append(peak)

    self.field_initializations(peaks)

    self.peak_list.clear()

    self.stoppable_loop('peaks', 50)
    for rank, peak in enumerate(peaks):
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak, rank), peak)

  # ---------------------------------------------------------------------------
  #
  def remove_peaks_rs0(self):
    if self.spectrum:
      peaks = self.spectrum.peak_list()
    else:
      peaks = self.peaks

    threshold = float(self.remove_rs0_thresh.variable.get())
    delete_count = 0

    confirmation = tkMessageBox.askokcancel(title='Remove peaks?',
             message='Do you want to remove peaks with ABSOLUTE Reliability Score of ' + str(threshold) + ' and less?')

    if confirmation == True:
        for peak in peaks:
            try:
                if peak.is_assigned == 1:
                # we won't delete a peak that the user has assigned
                    continue

                if abs(reliability_score(peak)) <= threshold:
                    peak.selected = 1
                    delete_count += 1
                    self.session.command_characters("")
            except:
                continue

        print(str(delete_count) + ' peaks were removes')

        self.sort_reliability()

  # ---------------------------------------------------------------------------
  #
  def field_initializations(self, peaks):

    for field in self.settings.fields:
      if field.onoff:
        field.initialize(self.session, peaks, self)

  # ---------------------------------------------------------------------------
  #
  def peak_line(self, peak, rank):

    line = '%-4s' % (rank + 1,)  #default is ''
    for field in self.settings.fields:
      if field.onoff:
        line = line + field.string(peak)
    return line

  # ---------------------------------------------------------------------------
  #
  def heading(self, dim):

    heading = '#   '
    for field in self.settings.fields:
      if field.onoff:
        heading = heading + field.heading(dim)
    return heading

# -----------------------------------------------------------------------------
#
class peak_list_settings:

  def __init__(self):

    fields = []
    for fc in field_classes:
      fields.append(fc())

    self.fields = fields
    self.sort_by_assignment = 1

  # ---------------------------------------------------------------------------
  #
  def show_fields(self, *field_names):

    ftable = {}
    for f in self.fields:
      ftable[f.name] = f

    for name in field_names:
      if name in ftable:
        ftable[name].onoff = 1

# -----------------------------------------------------------------------------

class peak_list_field:
  def __init__(self):
    self.onoff = 0

  def heading(self, dim):
    try:
      getattr(self, 'title')
      return self.pad(self.title(dim), dim)
    except:
      return self.pad(self.name, dim)

  def initialize(self, session, peaks, stoppable):
    pass

  def string(self, peak):
    return self.pad(self.text(peak), peak.spectrum.dimension)

  def pad(self, string, dim):
    size = self.size(dim)
    if size == None:
      return string
    fmt = '{:^%d}' % size
    return fmt.format(string)

  # ---------------------------------------------------------------------------
  # Make check button for peak list settings dialog
  #
  class field_widgets:
    def __init__(self, parent, name):
      cb = tkutil.checkbutton(parent, name, 0)
      cb.button.pack(side='top', anchor='w')
      self.checkbutton = cb
    def get_widget_state(self, field):
      field.onoff = self.checkbutton.state()
    def set_widget_state(self, field):
      self.checkbutton.set_state(field.onoff)

# ---------------------------------------------------------------------------
#
def total_corresponding(peak):
    xcheck_total_start = peak.note.find('Total:')
    if xcheck_total_start == -1:
        return 0
    else:
        return int(peak.note[xcheck_total_start + len('Total:') : ].split(',')[0])
           
# ---------------------------------------------------------------------------
#
def reliability_score(peak):
    if peak.line_width == None:
        return 0

    global manual_coeff, coeff1, coeff2, coeff3, SNR_abs, volume_abs

    volume = peak.volume
    SNR = sputil.peak_height(peak) / peak.spectrum.noise
    linewidth = sum(pyutil.seq_product(peak.line_width, peak.spectrum.hz_per_ppm))

    volume_coeff = 1e7
    SNR_coeff = 10
    linewidth_coeff = 0.1

    try:
        if manual_coeff.get():
            volume_coeff = float(coeff1.variable.get())
            SNR_coeff = float(coeff2.variable.get())
            linewidth_coeff = float(coeff3.variable.get())

            if SNR_abs.get():
                SNR = abs(SNR)

            if volume_abs.get():
                volume = abs(volume)

    except:
        pass

    try:
        RS = (volume / volume_coeff) + (SNR * SNR_coeff) + (linewidth * linewidth_coeff)
    except:
        RS = 0


    return RS

field_classes = []

# ---------------------------------------------------------------------------
#
#class rank_field(peak_list_field):
#  name = 'Rank'
#  def size(self, dim): return 5
#  def text(self, peak): return 1
#field_classes.append(rank_field)

# ---------------------------------------------------------------------------
#
class assignment_field(peak_list_field):
  name = 'Assignment'
  def size(self, dim): return 8 * dim
  def text(self, peak): return sputil.assignment_name(peak.resonances())
field_classes.append(assignment_field)

# -------------------------------------------------------------------------
#
class chemical_shift_field(peak_list_field):
  name = 'Chemical Shift'
  def title(self, dim): return 'Shift (ppm)'
  def size(self, dim): return 8 * dim
  def text(self, peak):
    return pyutil.sequence_string(peak.frequency, ' %7.3f')
field_classes.append(chemical_shift_field)

# -------------------------------------------------------------------------
#
class volume_field(peak_list_field):
  name = 'Volume'
  def size(self, dim): return 12
  def text(self, peak):
    fmt = '{:^%d}' % 12
        
    if peak.volume:
        vol = '%.3g' % peak.volume
        return fmt.format(vol)
        
    return ''
field_classes.append(volume_field)

# -------------------------------------------------------------------------
#
class data_height_field(peak_list_field):
  name = 'Data Height'
  def title(self, dim): return 'Height'
  def size(self, dim): return 10
  def text(self, peak):
    return '%.3g' % sputil.peak_height(peak)
field_classes.append(data_height_field)

# -------------------------------------------------------------------------
#
class signal_to_noise_field(peak_list_field):
  name = 'Signal / Noise'
  def title(self, dim): return 'S/N'
  def size(self, dim): return 10
  def text(self, peak):
    return '%.1f' % (sputil.peak_height(peak) / peak.spectrum.noise)
field_classes.append(signal_to_noise_field)

# -------------------------------------------------------------------------
#
class fit_height_field(peak_list_field):
  name = 'Fit Height'
  def size(self, dim): return 11
  def text(self, peak):
    if peak.fit_height == None: return ''
    return '%.3g' % peak.fit_height
field_classes.append(fit_height_field)

# -------------------------------------------------------------------------
#
class linewidth_field(peak_list_field):
  name = 'Linewidth'
  def title(self, dim): return 'Linewidth (Hz)'
  def size(self, dim): return 9 * dim
  def text(self, peak):
    if peak.line_width == None: return ''
    linewidth = pyutil.seq_product(peak.line_width,
                                   peak.spectrum.hz_per_ppm)
    return pyutil.sequence_string(linewidth, ' %7.2f')
field_classes.append(linewidth_field)

# -------------------------------------------------------------------------
#
class color_field(peak_list_field):
  name = 'Color'
  def size(self, dim): return 8
  def text(self, peak): return '%8s' % peak.color
field_classes.append(color_field)

# -------------------------------------------------------------------------
#
class RS_field(peak_list_field):
  name = 'Reliability Score'
  def title(self, dim): return 'Reliability Score'
  def size(self, dim): return 20
  def text(self, peak): return ' %7.2f' % reliability_score(peak)
field_classes.append(RS_field)

# -------------------------------------------------------------------------
#
class xcheck_field(peak_list_field):
  name = 'Total Corr.'
  def size(self, dim): return 13
  def text(self, peak): return ' %d     ' % total_corresponding(peak)
field_classes.append(xcheck_field)

# -------------------------------------------------------------------------
#
class note_field(peak_list_field):
  name = 'Note'
  def size(self, dim): return 21
  def text(self, peak): return ' %-20s' % peak.note
field_classes.append(note_field)


# -----------------------------------------------------------------------------
# Dialog of possible peak list fields.
#
class peak_list_settings_dialog(tkutil.Settings_Dialog):

  def __init__(self, session):

    tkutil.Settings_Dialog.__init__(self, session.tk, 'Peak List Settings')

    fb = tk.Frame(self.top, borderwidth=3, relief='groove')
    fb.pack(side='top', fill='x')

    #
    # Create the checkbutton and Manual Coefficients section
    #
    self.field_widgets = {}
    for fc in field_classes:
      self.field_widgets[fc] = fc.field_widgets(self.top, fc.name)


    opt = tk.Frame(self.top, borderwidth=3, relief='groove')
    opt.pack(side='top', fill='x')

    global manual_coeff, coeff1, coeff2, coeff3, SNR_abs, volume_abs

    manual_coeff = tk.BooleanVar()
    manual_coeff.set(False)
    checkbox_coeff = tk.Checkbutton(opt, highlightthickness=0, text='Manual Coefficients',
                                    variable=manual_coeff, command=self.show_coeff_settings)
    checkbox_coeff.pack(side='top', anchor='w')
    tkutil.create_hint(checkbox_coeff, 'Manually specify the coefficients for the Reliability Score formula')


    coeff1 = tkutil.entry_field(opt, 'Volume Coeff.: ', width=5, initial='1e7')
    tkutil.create_hint(coeff1.frame, 'Specify the coefficient for the Volume in the Reliability Score formula')

    coeff2 = tkutil.entry_field(opt, 'SNR Coeff.: ', width=5, initial='10')
    tkutil.create_hint(coeff2.frame, 'Specify the coefficient for the Signal to Noise Ratio (SNR) in the Reliability Score formula')


    coeff3 = tkutil.entry_field(opt, 'Linewidth Coeff.: ', width=5, initial='0.1')
    tkutil.create_hint(coeff3.frame, 'Specify the coefficient for the Linewidth in the Reliability Score formula')

    SNR_abs = tk.BooleanVar()
    SNR_abs.set(True)
    self.checkbox_SNR_abs = tk.Checkbutton(opt, highlightthickness=0, text='Absolute SNR',
                                           variable=SNR_abs)
    tkutil.create_hint(self.checkbox_SNR_abs, 'If checked, the Reliability Score will only have absolute values for SNR')

    volume_abs = tk.BooleanVar()
    volume_abs.set(False)
    self.checkbox_volume_abs = tk.Checkbutton(opt, highlightthickness=0, text='Absolute Volume',
                                              variable=volume_abs)
    tkutil.create_hint(self.checkbox_volume_abs, 'If checked, the Reliability Score will only have absolute values for Volume')


    br = tkutil.button_row(self.top,
                      ('Ok', self.ok_cb),
                      ('Apply', self.apply_cb),
                      ('Close', self.close_cb),
                      )
    br.frame.pack(side='top', anchor='w')


  # ---------------------------------------------------------------------------
  #
  def show_coeff_settings(self):
    if manual_coeff.get():
        coeff1.frame.pack(side='top', anchor='w')
        coeff2.frame.pack(side='top', anchor='w')
        coeff3.frame.pack(side='top', anchor='w')
        self.checkbox_SNR_abs.pack(side='bottom', anchor='w')
        self.checkbox_volume_abs.pack(side='bottom', anchor='w')
    else:
        coeff1.frame.pack_forget()
        coeff2.frame.pack_forget()
        coeff3.frame.pack_forget()
        self.checkbox_SNR_abs.pack_forget()
        self.checkbox_volume_abs.pack_forget()


  # ---------------------------------------------------------------------------
  #
  def show_settings(self, settings):

    for f in settings.fields:
        #self.field_widgets[f.__class__].set_widget_state(f)
        try:
            self.field_widgets[f.__class__].set_widget_state(f)
        except:
            pass
            #print f.__class__

  # ---------------------------------------------------------------------------
  #
  def get_settings(self):

    settings = peak_list_settings()
    for f in settings.fields:
        self.field_widgets[f.__class__].get_widget_state(f)

    return settings


# ---------------------------------------------------------------------------
