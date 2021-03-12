# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
X-Check Validation Filtering Module for Sparky

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
  
import peak_list_dialog
from itertools import combinations
import collections
import math
from decimal import Decimal, getcontext

try:
  from matplotlib import use as matplotlib_use
  matplotlib_use('TkAgg')
except:
  print("Exception happened for importing 'matplotlib use'")

from matplotlib.pyplot import subplots, subplots_adjust, ion, show, draw
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
try:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg as NavTB
except:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk as NavTB
#try:
#    # for Mac support
#    from matplotlib.pyplot import pause
#except:
#    pass


class xcheck_dialog(tkutil.Dialog, tkutil.Stoppable):
  def __init__(self, session):

    self.specs_peaks = []

    self.session = session
    tkutil.Dialog.__init__(self, session.tk, 'Resonance Cross-Validation')

   # xcheck_label = tk.Label(self.top, text="X-Check Validation Filtering Module", font=20)
   # xcheck_label.pack(side='top', fill='both', expand=1, pady=15)

   # separator = tk.Frame(self.top, height=2, bd=1, relief="ridge")
   # separator.pack(fill="both", padx=5, pady=5, side ='top')


# frames

    # listbox
    topfrm = tk.Frame(self.top)
    topfrm.pack(side='top', fill='both', expand=0, padx=8)

    # update, select all buttons
    midfrm = tk.Frame(self.top)
    midfrm.pack(fill='both', expand=1, padx=8)

    # settings
    btmfrm = tk.Frame(self.top)
    btmfrm.pack(fill='both', expand=1, padx=8)

    # run buttons 1st row
    buttonsfrm1 = tk.Frame(self.top)
    buttonsfrm1.pack(fill='both', expand=1, padx=(15,0), pady=(10,2))

    # run buttons 2nd row
    buttonsfrm2 = tk.Frame(self.top)
    buttonsfrm2.pack(fill='both', expand=1, padx=(15,0))

    # status
    statusfrm = tk.Frame(self.top)
    statusfrm.pack(fill='both', expand=1, padx=8)


#spectra list

    self.spectra_list = tkutil.scrolling_list(topfrm, 'Select the spectra for cross-validation:', 5, True)
    self.spectra_list.listbox['selectmode'] = 'extended'
    self.spectra_list.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    self.spectra_list.frame.pack(side='top', fill='both', expand=1, pady=(5,5))
    tkutil.create_hint(self.spectra_list.frame, 'You can select multiple experiments by holding down the Ctrl key and clicking on the experiments')

# buttons

    update_button = tk.Button(midfrm, text='Update List', command=self.update_list)
    update_button.pack(side='left', anchor='w', expand=0, pady=(0, 15))
    tkutil.create_hint(update_button, 'This will refresh the list in case a new experiment is loaded')

    select_all_button = tk.Button(midfrm, text='Select All', command=self.select_all)
    select_all_button.pack(side='left', anchor='w', expand=0, pady=(0, 15), padx=1)
    tkutil.create_hint(select_all_button, 'This will select all the loaded experiments for the cross validation')


# tolerance frame

    tolerance_font = tkFont.Font(size=11)
    tolerance_label = tk.Label(btmfrm, text="Tolerances:", font=tolerance_font)
    tolerance_label.pack(side='top', anchor='w')
    tkutil.create_hint(tolerance_label, 'These tolerances are used in comparing peaks from different experiments')

    tol_frm = tk.Frame(btmfrm)
    tol_frm.pack(side='top', fill='both', expand=1)

    self.tol_H = tkutil.entry_field(tol_frm, '1H: ', width=5, initial='0.05')
    self.tol_H.frame.pack(side='left', padx=(20,10))
    tkutil.create_hint(self.tol_H.frame, 'Maximum distance for H to be considered the same resonance')

    self.tol_N = tkutil.entry_field(tol_frm, '15N:', width=5, initial='0.3')
    self.tol_N.frame.pack(side='left', padx=(5,10))
    tkutil.create_hint(self.tol_N.frame, 'Maximum distance for N to be considered the same resonance')

    self.tol_C = tkutil.entry_field(tol_frm, '13C:', width=5, initial='0.35')
    self.tol_C.frame.pack(side='left', padx=(5,10))
    tkutil.create_hint(self.tol_C.frame, 'Maximum distance for C to be considered the same resonance')


# exclude frame

    exclude_font = tkFont.Font(size=11)
    exclude_label = tk.Label(btmfrm, text="Exclude Range:", font=tolerance_font)
    exclude_label.pack(side='top', anchor='w', pady=(15,0))
    tkutil.create_hint(exclude_label, 'Any peak with their H resonance in this range will be excluded from the cross validation')


    exclude_frm = tk.Frame(btmfrm)
    exclude_frm.pack(side='top', fill='both', expand=1, pady=(5,0))


    self.exclude_from = tkutil.entry_field(exclude_frm, 'From: ', width=5, initial='4.7')
    self.exclude_from.frame.pack(side='left', padx=(25,0))
    tkutil.create_hint(self.exclude_from.frame, 'Lower bound for the exclusion range. Any peak with their H resonance in this range will be excluded from the cross validation')


    self.exclude_to = tkutil.entry_field(exclude_frm, 'To: ', width=5, initial='4.9')
    self.exclude_to.frame.pack(side='left', padx=(5,10))
    tkutil.create_hint(self.exclude_to.frame, 'Upper bound for the exclusion range. Any peak with their H resonance in this range will be excluded from the cross validation')


# checkbox

    checkbox_frm = tk.Frame(btmfrm)
    checkbox_frm.pack(side='top', fill='both', expand=1, pady=(15,0))

    self.note_append = tk.BooleanVar()
    self.note_append.set(True)
    checkbox_note_append = tk.Checkbutton(checkbox_frm, highlightthickness=0, text='Append to Note',
                                            variable=self.note_append)
    checkbox_note_append.pack(side='top', anchor='w', padx=(0,0))
    tkutil.create_hint(checkbox_note_append, 'If checked, the result will be appended to the Note property of each peak. If unchecked, the Note will be OVERWRITTEN!')


# separator
    sep = tk.Frame(btmfrm, height=2, bd=1, relief="ridge")
    sep.pack(fill="both", padx=5, pady=(10,5), side='top')


# histogram bins

    bin_font = tkFont.Font(size=11)
    bin_label = tk.Label(btmfrm, text="Histogram Bins:", font=bin_font)
    bin_label.pack(side='top', anchor='w', pady=(5,3))
    tkutil.create_hint(bin_label, 'These bins are used in generating the histograms')

    bins_frm = tk.Frame(btmfrm)
    bins_frm.pack(side='top', fill='both', expand=1, pady=(0,10))

    self.bin_H = tkutil.entry_field(bins_frm, '1H: ', width=5, initial='0.02')
    self.bin_H.frame.pack(side='left', padx=(18,10))
    tkutil.create_hint(self.bin_H.frame, 'Bin steps for H histogram')

    self.bin_N = tkutil.entry_field(bins_frm, '15N:', width=5, initial='0.2')
    self.bin_N.frame.pack(side='left', padx=(3,10))
    tkutil.create_hint(self.bin_N.frame, 'Bin steps for N histogram')
    
    self.bin_C = tkutil.entry_field(bins_frm, '13C:', width=5, initial='0.2')
    self.bin_C.frame.pack(side='left', padx=(3,10))
    tkutil.create_hint(self.bin_C.frame, 'Bin steps for C histogram')


# run button & status

    xcheck_button = tk.Button(buttonsfrm1, text='Run Cross-Validation', command=self.run_xcheck_button)
    xcheck_button.pack(side='left')
    tkutil.create_hint(xcheck_button, 'Runs the cross validation using the settings above')


    peaklist_button = tk.Button(buttonsfrm1, text='Peak List', width=10, command=self.show_peak_list)
    peaklist_button.pack(side='left')
    tkutil.create_hint(peaklist_button, 'Shows the Peak list')
    
    
    hist_button = tk.Button(buttonsfrm2, text='Peak Histogram', width=16,  command=self.run_histogram)
    hist_button.pack(side='left')
    tkutil.create_hint(hist_button, 'Generates and shows the histograms for the peak resonances.')



    stop_button = tk.Button(buttonsfrm2, text='Stop', command=self.stop_cb)
    stop_button.pack(side='left')
    tkutil.create_hint(stop_button, 'Stops the cross validations process')

#TODO: Add the section for CrossValidation to the extensions.html file
    help_button = tk.Button(buttonsfrm2, text='Help', command=sputil.help_cb(session, 'CrossValidation'))
    help_button.pack(side='left')
    tkutil.create_hint(help_button, 'Opens a help page with more information about this module.')

    self.status = tk.Label(statusfrm, text="Status: Ready!")
    self.status.pack(side='left', anchor='w', pady=(10,5), padx=(5,0))

    progress_label = tk.Label(statusfrm)
    progress_label.pack(side='left', anchor='w')

    tkutil.Stoppable.__init__(self, progress_label, stop_button)

# fix the fonts

    suggested_fonts = ['Arial', 'NotoSans', 'Ubuntu', 'SegoeUI', 'Helvetica',
                       'Calibri', 'Verdana', 'DejaVuSans', 'FreeSans']
    for fnt in suggested_fonts:
      if fnt in tkFont.families():
        self.spectra_list.listbox['font'] = (fnt, 9)
        self.spectra_list.heading['font'] = (fnt, 11)
        break


    self.update_list()


# ---------------------------------------------------------------------------
# functions
# ---------------------------------------------------------------------------

  def select_all(self):
    self.spectra_list.listbox.select_set(0, tk.END)
    self.spectra_selected()

    self.status.config(text="Status: Selection is complete.")
    self.status.update()


# ---------------------------------------------------------------------------
  def update_list(self):
    if self.session.project == None:
        tkMessageBox.showwarning(title='Error', message='No spectrum is loaded!')
        return

    self.spectra_list.clear()

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    for spec in self.spec_list:
        self.spectra_list.append(spec.name)


# ---------------------------------------------------------------------------
  def spectra_selected(self, *args):

    data_list = self.spectra_list.selected_line_data()
    if len(data_list) < 1:
        tkMessageBox.showwarning(title='Error', message='No spectrum was selected!')
        return
    selected_spec_ids = self.spectra_list.selected_line_numbers()

    self.status.config(text="Status: Selection is complete.")
    self.status.update()

    if selected_spec_ids == None:
        tkMessageBox.showwarning(title='Error', message='No spectrum was selected!')
        return

    self.specs_names = []
    self.specs_peaks = []
    self.specs_nuclei = []

    for spec_id in selected_spec_ids:
        self.specs_peaks.append(self.spec_list[spec_id].peak_list())
        self.specs_nuclei.append(self.spec_list[spec_id].nuclei)
        self.specs_names.append(self.spec_list[spec_id].name)
    

# ---------------------------------------------------------------------------
  def run_xcheck_button(self):

    self.stoppable_call(self.run_xcheck)


# ---------------------------------------------------------------------------
  def run_xcheck(self, *args):

    self.status.config(text="Status: Running ...")
    self.status.update()

  # specs_peaks[each_selected_spec] --> all peaks in that spec
  # specs_nuclei[i] -- > i.e.  ('15N', '13C', '1H')  or  ('13C', '1H', '1H')

    num_of_specs = len(self.specs_peaks)
    combinations_list = list(combinations(range(num_of_specs), 2))
    # list(combinations(range(3), 2))  -- >  [(0, 1), (0, 2), (1, 2)]
    # 8 spec is 28 combinations!

    if num_of_specs == 1:
        tkMessageBox.showwarning(title='Error!', message='You need to select at least two experiments to validate against each other')
        return
    
    for spec in self.specs_peaks:
        for peak in spec:
            if self.note_append.get():
                # if the user is re-running xcheck, remove the previous results
                if len(peak.note) == 0:
                    peak.note = 'xcheck:'
                else:
                    xcheck_str_start = peak.note.find('xcheck:')
                    if xcheck_str_start == 0:
                        peak.note = 'xcheck:'
                    elif xcheck_str_start > 0:   
                        peak.note = peak.note[ : xcheck_str_start] + 'xcheck:'
                    else:
                        peak.note += ';xcheck:'
            else:
                peak.note = 'xcheck:'


    total_peaks = 0
    for spec_pair in combinations_list:
        s1 = spec_pair[0]
        s2 = spec_pair[1]
        if (self.specs_nuclei[s1][0] != self.specs_nuclei[s2][0]):
            continue
        total_peaks += len(self.specs_peaks[s1]) * len(self.specs_peaks[s2])
            
            
    processed_peaks = 0
    for spec_pair in combinations_list:
        self.top.update()

        s1 = spec_pair[0]
        s2 = spec_pair[1]

        print("Comparing " + self.specs_names[s1] + " with " + self.specs_names[s2] + ":")

        if (self.specs_nuclei[s1][0] != self.specs_nuclei[s2][0]):
            print("Will not compare a N-HSQC based experiments with a C-HSQC one")
            print('_' * 50)
            continue

        tol = float(self.tol_C.variable.get())
        if self.specs_nuclei[s1][0] == '15N':
            tol = float(self.tol_N.variable.get())

        tol_H = float(self.tol_H.variable.get())
        exclude_from = float(self.exclude_from.variable.get())
        exclude_to = float(self.exclude_to.variable.get())

        print('Total peaks in the first one: ' + str(len(self.specs_peaks[s1])))
        print('Total peaks in the second one: ' + str(len(self.specs_peaks[s2])))

        for i, peak1 in enumerate(self.specs_peaks[s1]):

            #print('Peak ' + str(i) + ': ', end='')
            #print 'Peak1 ' + str(i) + ': '
            #print(peak1.frequency)

            #if peak1.assignment.find('?') == -1:
            if peak1.is_assigned == 1:
                continue    # skip if already assigned

            if ((peak1.frequency[-1] > exclude_from) and (peak1.frequency[-1] < exclude_to)):
                continue

            match_flag = 0
            for j, peak2 in enumerate(self.specs_peaks[s2]):
            
                #print 'Peak2 ' + str(j) + ': '
                #print(peak2.frequency)

                #if peak2.assignment.find('?') == -1:
                if peak2.is_assigned == 1:
                    continue    # skip if already assigned

                if ((peak2.frequency[-1] > exclude_from) and (peak2.frequency[-1] < exclude_to)):
                    continue

                if abs(peak1.frequency[0] - peak2.frequency[0]) < tol:
                    if abs(peak1.frequency[-1] - peak2.frequency[-1]) < tol_H:

                        print("\nMatch:")
                        print(peak1.frequency)
                        print(peak2.frequency)
                        match_flag = 1
                        peak1.note += self.specs_names[s2] + ','
                        peak2.note += self.specs_names[s1] + ','
                        break

            if match_flag == 0:
                print('\n' + '*' * 20 + '\nNo match:')
                print(peak1.frequency)
                
                
            processed_peaks += len(self.specs_peaks[s2]) 
            percent = "{:2.0f}".format(100 * processed_peaks / total_peaks)
            self.status.config(text="Status: Running ... (" + percent + "%)")
            self.status.update()
            

        print('_' * 50)


# Update the Note to count the frequency
    for spec in self.specs_peaks:
        for peak in spec:
                xcheck_str_start = peak.note.find('xcheck:')

                main_note = ''
                if xcheck_str_start > 0:
                    main_note = peak.note[ : xcheck_str_start]

                xcheck = peak.note[xcheck_str_start + len('xcheck:') : ].strip(',')
                if xcheck == '':
                    new_note = main_note + 'xcheck:0'

                else:
                    xcheck_array = xcheck.split(',')
                    new_note = main_note + 'xcheck:'

                    this_peak_total = 0
                    this_peak_details = ''
                    for (exp, freq) in collections.Counter(xcheck_array).items():
                        this_peak_total += freq
                        this_peak_details += exp + ':' + str(freq) + ','
                    new_note += 'Total:' + str(this_peak_total) + ',' + this_peak_details

                peak.note = new_note.strip(',')

    self.status.config(text="Status: Done!")
    self.status.update()
    tkMessageBox.showinfo(title='Done!', message='Now check the Peak List (lt) for each experiment and see the Note property.')


# ---------------------------------------------------------------------------
  def run_histogram(self, *args):
    if len(self.specs_peaks) == 0:
        tkMessageBox.showwarning(title='Error!', message='You need to select at least one experiment to generate the histograms')
        return

    self.status.config(text="Status: Running ...")
    self.status.update()

    H_hist, N_hist, C_hist = {}, {}, {}

    for spec in range(len(self.specs_peaks)):
        #print(self.specs_nuclei[spec])

        for nuclei in range(len(self.specs_nuclei[spec])):

            if self.specs_nuclei[spec][nuclei] == '1H':
                this_hist = H_hist
                bin_step = float(self.bin_H.variable.get())
            elif self.specs_nuclei[spec][nuclei] == '15N':
                this_hist = N_hist
                bin_step = float(self.bin_N.variable.get())
            elif self.specs_nuclei[spec][nuclei] == '13C':
                this_hist = C_hist
                bin_step = float(self.bin_C.variable.get())

#            for peak in self.specs_peaks[spec]:
#                this_freq = int(peak.frequency[nuclei])
#
#                for this_bin in [this_freq-1, this_freq, this_freq+1]:
#                    if this_hist.has_key(this_bin):
#                        this_hist[this_bin] = this_hist[this_bin] + 1
#                    else:
#                        this_hist[this_bin] = 1

            round_digit = int(-1 * math.floor(math.log10(abs(bin_step))))
            # finds the number of digits to round of
            # gives 1 for 0.1 or 0.5
            # gives -1 for 10 or 13
            # gives -2 for 100 or 124
            # gives 2 for 0.01 or 0.06477

            for peak in self.specs_peaks[spec]:
                this_freq = round(peak.frequency[nuclei], round_digit)
                upper_freq = round(this_freq+bin_step, round_digit)
                lower_freq = round(this_freq-bin_step, round_digit)

                for this_bin in [lower_freq, this_freq, upper_freq]:
                    if this_bin in this_hist:
                        this_hist[this_bin] = this_hist[this_bin] + 1
                    else:
                        this_hist[this_bin] = 1


    self.status.config(text="Status: Done!")
    self.status.update()

    d = hist_dialog(self.session)
    d.show_window(1)
    d.show_histograms(H_hist, N_hist, C_hist,
                        self.find_bin_width(H_hist),
                        self.find_bin_width(N_hist),
                        self.find_bin_width(C_hist))


# ---------------------------------------------------------------------------
  def find_bin_width(self, hist):
    hist_list = sorted(hist.keys())
    getcontext().prec = 5
    diff = 9999
    for i in range(len(hist_list)-1):
        this_diff = abs(float(Decimal(hist_list[i]) - Decimal(hist_list[i+1])))
        if this_diff < diff:
            diff = this_diff
    return diff


# ---------------------------------------------------------------------------
  def remove_peaks(self, *args):

    confirmation = tkMessageBox.askokcancel(title='Remove peaks?',
             message='Do you want to remove peaks that have no corresponding peaks (determined by cross validation)?')

    if confirmation == True:
        for spec in self.specs_peaks:
            for peak in spec:
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

        tkMessageBox.showinfo(title='Done!', message='Peaks with zero corresponding peaks have been deleted')


# ---------------------------------------------------------------------------
  def show_peak_list(self, *args):
    if self.session.project == None:
        tkMessageBox.showwarning(title='Error', message='No spectrum is loaded!')
        return

    spec = self.spec_list[0]
    try:
        for spec in self.spec_list:
            if spec.name == self.specs_names[0]:
                break
    except:
        pass

    d = peak_list_dialog.peak_list_dialog(self.session)
    d.show_window(1)
    d.settings.show_fields('Assignment', 'Chemical Shift', 'Note')
    d.show_spectrum_peaks(spec)
    #d.sort_reliability()




#####################################################################################

class hist_dialog(tkutil.Dialog, tkutil.Stoppable):

  def __init__(self, session):

    self.session = session
    tkutil.Dialog.__init__(self, session.tk, 'Peak Histograms')

    #progress_label = tk.Label(self.top, anchor='nw', text="Output progress:")
    #progress_label.pack(side='top', anchor='w')

    self.plot_frame = tk.Frame(self.top)
    self.plot_frame.pack(side='top', expand=1, padx=4, pady=(3,0))
    
    button_frame = tk.Frame(self.top)
    button_frame.pack(side='top', pady=(0,15), anchor='center')

    self.show_select_button = tk.Button(button_frame, text='Zoom in on selected peak(s)', command=self.show_peak_in_hist)
    self.show_select_button.pack(side='left')
    tkutil.create_hint(self.show_select_button, 'Select one or more peaks in the experiment and click this button to show them on the histograms')
        
    self.zoom_out_button = tk.Button(button_frame, text='Zoom Out', command=self.zoom_out)
    self.zoom_out_button.pack(side='left', padx=2)
    tkutil.create_hint(self.zoom_out_button, 'Zoom out the view on all figures')


# ---------------------------------------------------------------------------
  def show_histograms(self, H_hist, N_hist, C_hist, H_bin, N_bin, C_bin):
    print('\nH:')
    print(H_hist)
    print('\nN:')
    print(N_hist)
    print('\nC:')
    print(C_hist)
    self.H_hist, self.N_hist, self.C_hist = H_hist, N_hist, C_hist

    self.fig, self.axes = subplots(figsize=(20, 5), nrows=1, ncols=3)

    self.fig.set_facecolor("white")
    subplots_adjust(left=0.04, bottom=0.1, right=0.98, top=0.90, wspace=0.14)

    self.axes[0].bar(list(H_hist.keys()), H_hist.values(), color='#3dff3d', width=H_bin, edgecolor='#32D032')
    self.axes[0].set_title ("H", fontsize=16)
    self.axes[0].set_ylabel("Number of occurrences", fontsize=12)
    self.axes[0].set_xlabel("Chemical shift (ppm)", fontsize=12)
    draw()

    self.axes[1].bar(list(N_hist.keys()), N_hist.values(), color='#00ffff', width=N_bin, edgecolor='#00E3E3')
    self.axes[1].set_title ("N", fontsize=16)
    self.axes[1].set_ylabel("Number of occurrences", fontsize=12)
    self.axes[1].set_xlabel("Chemical shift (ppm)", fontsize=12)
    draw()

    self.axes[2].bar(list(C_hist.keys()), C_hist.values(), color='#ffe23d', width=C_bin, edgecolor='#E0C837')
    self.axes[2].set_title ("C", fontsize=16)
    self.axes[2].set_ylabel("Number of occurrences", fontsize=12)
    self.axes[2].set_xlabel("Chemical shift (ppm)", fontsize=12)
    draw()

    self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
    self.canvas.get_tk_widget().pack()
    self.canvas.draw()

    toolbar = NavTB(self.canvas, self.plot_frame)
    toolbar.update()
    
    self.ax0_xlim = self.axes[0].get_xlim()
    self.ax0_ylim = self.axes[0].get_ylim()
    self.ax1_xlim = self.axes[1].get_xlim()
    self.ax1_ylim = self.axes[1].get_ylim()
    self.ax2_xlim = self.axes[2].get_xlim()
    self.ax2_ylim = self.axes[2].get_ylim()


# ---------------------------------------------------------------------------
  def show_peak_in_hist(self, *args):
    spec = self.session.selected_spectrum()
    peaks = self.session.selected_peaks()
    text_style = dict(size=30)
    
    if not peaks:
        tkMessageBox.showwarning(title='Error', message='You need to select some peaks on a spectrum first!')
        return

    try:
        if self.txt:
            for txt in self.txt:
                txt.remove()
    except:
        pass


    self.txt = []
    H_list = []
    N_list = []
    C_list = []
    for n in range(len(spec.nuclei)):
        if spec.nuclei[n] == '1H':
                this_axes = self.axes[0]
                this_range = H_list
        elif spec.nuclei[n] == '15N':
                this_axes = self.axes[1]
                this_range = N_list
        elif spec.nuclei[n] == '13C':
                this_axes = self.axes[2]
                this_range = C_list

        for peak in peaks:
            self.txt.append(this_axes.text(peak.frequency[n], 0, 'x', **text_style))
            this_range.append(peak.frequency[n])
           
            
    # zoom in        
    if H_list:
        H_min = min(H_list)
        H_max = max(H_list)
        H_hrange = (H_max - H_min) * 2
        max_range = max(self.ax0_xlim) - min(self.ax0_xlim)
        if (H_hrange > max_range) or (H_hrange < max_range*0.1):
            H_hrange = max_range*0.1
        
        H_heights = []
        for i in H_list:
            val = self.H_hist.get(i) or self.H_hist[min(self.H_hist.keys(), key = lambda key: abs(key-i))] 
            H_heights.append(val)
            
        self.axes[0].set_xlim(H_min - H_hrange, H_max + H_hrange)
        self.axes[0].set_ylim(0, max(H_heights)*1.1)  # 10% more than the highest bar for "those" shifts
    
    if N_list:
        N_min = min(N_list)
        N_max = max(N_list)
        N_hrange = (N_max - N_min) * 2
        max_range = max(self.ax1_xlim) - min(self.ax1_xlim)
        if (N_hrange > max_range) or (N_hrange < max_range*0.1):
            N_hrange = max_range*0.1
        
        N_heights = []
        for i in N_list:
            val = self.N_hist.get(i) or self.N_hist[min(self.N_hist.keys(), key = lambda key: abs(key-i))] 
            N_heights.append(val)
            
        self.axes[1].set_xlim(N_min - N_hrange, N_max + N_hrange)
        self.axes[1].set_ylim(0, max(N_heights)*1.1)  
    
    if C_list:
        C_min = min(C_list)
        C_max = max(C_list)
        C_hrange = (C_max - C_min) * 2
        max_range = max(self.ax2_xlim) - min(self.ax2_xlim)
        if (C_hrange > max_range) or (C_hrange < max_range*0.1):
            C_hrange = max_range*0.1
        
        C_heights = []
        for i in C_list:
            val = self.C_hist.get(i) or self.C_hist[min(self.C_hist.keys(), key = lambda key: abs(key-i))] 
            C_heights.append(val)
            
        self.axes[2].set_xlim(C_min - C_hrange, C_max + C_hrange)
        self.axes[2].set_ylim(0, max(C_heights)*1.1)         
            
            
    self.canvas.draw()


# ---------------------------------------------------------------------------
  def zoom_out(self, *args):
    self.axes[0].set_xlim(self.ax0_xlim)
    self.axes[0].set_ylim(self.ax0_ylim)
    self.axes[1].set_xlim(self.ax1_xlim)
    self.axes[1].set_ylim(self.ax1_ylim)
    self.axes[2].set_xlim(self.ax2_xlim)
    self.axes[2].set_ylim(self.ax2_ylim)
    self.canvas.draw()
    

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def show_xcheck_dialog(session):
  sputil.the_dialog(xcheck_dialog, session).show_window(1)
