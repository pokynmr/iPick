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
  import tkinter.font as TkFont

import sparky
import sputil
import tkutil
from itertools import combinations
import collections


class xcheck_dialog(tkutil.Dialog, tkutil.Stoppable):
  def __init__(self, session):

    self.session = session
    tkutil.Dialog.__init__(self, session.tk, 'X-Check Validation Filtering')

   # xcheck_label = tk.Label(self.top, text="X-Check Validation Filtering Module", font=20)
   # xcheck_label.pack(side='top', fill='both', expand=1, pady=15)

   # separator = tk.Frame(self.top, height=2, bd=1, relief="ridge")
   # separator.pack(fill="both", padx=5, pady=5, side ='top')


# frames

    # listbox
    topfrm = tk.Frame(self.top)
    topfrm.pack(side='top', fill='both', expand=0, padx=8)

    # buttons
    midfrm = tk.Frame(self.top)
    midfrm.pack(fill='both', expand=1, padx=8)

    # run button & output
    btmfrm = tk.Frame(self.top)
    btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


#spectra list

    self.spectra_list = tkutil.scrolling_list(topfrm, 'Select the spectra for x-checking:', 5, True)
    self.spectra_list.listbox['selectmode'] = 'extended'
    self.spectra_list.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    self.spectra_list.frame.pack(side='top', fill='both', expand=1, pady=(5,5))


# buttons

    update_button = tk.Button(midfrm, text='Update List', command=self.update_list)
    update_button.pack(side='left', anchor='w', expand=0, pady=(0, 15))

    select_all_button = tk.Button(midfrm, text='Select All', command=self.select_all)
    select_all_button.pack(side='left', anchor='w', expand=0, pady=(0, 15), padx=5)


# tolerance frame

    tolerance_font = tkFont.Font(size=11)
    tolerance_label = tk.Label(btmfrm, text="Tolerances:", font=tolerance_font)
    tolerance_label.pack(side='top', anchor='w')
    #tkutil.create_hint(tolerance_label, 'These ')

    tol_frm = tk.Frame(btmfrm)
    tol_frm.pack(side='top', fill='both', expand=1)

    self.tol_H = tkutil.entry_field(tol_frm, '1H: ', width=5, initial='0.1')
    self.tol_H.frame.pack(side='left', padx=(20,10))
    #tkutil.create_hint(self.tol_H.frame, 'Maximum ')

    self.tol_C = tkutil.entry_field(tol_frm, '13C:', width=5, initial='0.1')
    self.tol_C.frame.pack(side='left', padx=(5,10))
    #tkutil.create_hint(self.tol_C.frame, 'Maximum ')

    self.tol_N = tkutil.entry_field(tol_frm, '15N:', width=5, initial='0.1')
    self.tol_N.frame.pack(side='left', padx=(5,10))
    #tkutil.create_hint(self.tol_N.frame, 'Maximum ')


# exclude frame

    exclude_font = tkFont.Font(size=11)
    exclude_label = tk.Label(btmfrm, text="Exclude Range:", font=tolerance_font)
    exclude_label.pack(side='top', anchor='w', pady=(15,0))
    #tkutil.create_hint(exclude_label, 'These ')


    exclude_frm = tk.Frame(btmfrm)
    exclude_frm.pack(side='top', fill='both', expand=1, pady=(5,0))


    self.exclude_from = tkutil.entry_field(exclude_frm, 'From: ', width=5, initial='4.7')
    self.exclude_from.frame.pack(side='left', padx=(25,0))
    #tkutil.create_hint(self.exclude_from.frame, 'Maximum ')


    self.exclude_to = tkutil.entry_field(exclude_frm, 'To: ', width=5, initial='4.9')
    self.exclude_to.frame.pack(side='left', padx=(5,10))
    #tkutil.create_hint(self.exclude_to.frame, 'Maximum ')


# checkbox

    checkbox_frm = tk.Frame(btmfrm)
    checkbox_frm.pack(side='top', fill='both', expand=1, pady=(15,0))

    self.note_append = tk.BooleanVar()
    self.note_append.set(True)
    checkbox_note_append = tk.Checkbutton(checkbox_frm, highlightthickness=0, text='Append to Note',
                                            variable=self.note_append)
    checkbox_note_append.pack(side='top', anchor='w', padx=(0,0))
    tkutil.create_hint(checkbox_note_append, 'If checked, the result will be appended to the Note property of each peak. If unchecked, the Note will be OVERWRITTEN!')


# run button & status

    xcheck_button = tk.Button(btmfrm, text='Run X-Checking', font=('bold'),
                                  height=1, command=self.run_xcheck)
    xcheck_button.pack(side='top', pady=30)


    self.status = tk.Label(btmfrm, text="Status: Ready!")
    self.status.pack(side='top', anchor='w', pady=5)


# fix the fonts

    suggested_fonts = ['Arial', 'NotoSans', 'Ubuntu', 'SegoeUI', 'Helvetica',
                       'Calibri', 'Verdana', 'DejaVuSans', 'FreeSans']
    for fnt in suggested_fonts:
      if fnt in tkFont.families():
        self.spectra_list.listbox['font'] = (fnt, 9)
        self.spectra_list.heading['font'] = (fnt, 11)
        break


    self.update_list()



# functions

  def select_all(self):
    self.spectra_list.listbox.select_set(0, tk.END)
    self.spectra_selected()

    self.status.config(text="Status: Selection is complete.")
    self.status.update()



  def update_list(self):
    if self.session.project == None:
        tkMessageBox.showinfo(title='Error', message='No spectrum is loaded!')
        return

    self.spectra_list.clear()

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    for spec in self.spec_list:
        self.spectra_list.append(spec.name)


  def spectra_selected(self, *args):

    data_list = self.spectra_list.selected_line_data()
    if len(data_list) < 1:
        tkMessageBox.showinfo(title='Error', message='No spectrum was selected!')
        return
    selected_spec_ids = self.spectra_list.selected_line_numbers()

    self.status.config(text="Status: Selection is complete.")
    self.status.update()

    if selected_spec_ids == None:
        tkMessageBox.showinfo(title='Error', message='No spectrum was selected!')
        return

    self.specs_names = []
    self.specs_peaks = []
    self.specs_nuclei = []
    for spec_id in selected_spec_ids:
        self.specs_peaks.append(self.spec_list[spec_id].peak_list())
        self.specs_nuclei.append(self.spec_list[spec_id].nuclei)
        self.specs_names.append(self.spec_list[spec_id].name)


  def run_xcheck(self, *args):

    self.status.config(text="Status: Running ...")
    self.status.update()

  # specs_peaks[each_selected_spec] --> all peaks in that spec
  # specs_nuclei[i] -- > i.e.  ('15N', '13C', '1H')  or  ('13C', '1H', '1H')

    num_of_specs = len(self.specs_peaks)
    combinations_list = list(combinations(range(num_of_specs), 2))
    # list(combinations(range(3), 2))  -- >  [(0, 1), (0, 2), (1, 2)]
    # 8 spec is 28 combinations!

    for spec in self.specs_peaks:
        for peak in spec:
            if self.note_append.get():
                peak.note += ';xcheck:'
            else:
                peak.note = 'xcheck:'

    for spec_pair in combinations_list:
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

            if peak1.assignment.find('?') == -1:
                continue    # skip if already assigned

            if ((peak1.frequency[-1] > exclude_from) and (peak1.frequency[-1] < exclude_to)):
                continue

            match_flag = 0
            for j, peak2 in enumerate(self.specs_peaks[s2]):

                #print 'Peak2 ' + str(j) + ': '
                #print(peak2.frequency)

                if peak2.assignment.find('?') == -1:
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

        print('_' * 50)


# Update the Note to count the frequency
    for spec in self.specs_peaks:
        for peak in spec:
                xcheck_str_start = peak.note.find('xcheck:')

                main_note = ''
                if xcheck_str_start > 0:
                    main_note = peak.note[ : xcheck_str_start] + ';'

                xcheck = peak.note[xcheck_str_start + len('xcheck:') : ].strip(',')
                if xcheck == '':
                    new_note = main_note + 'xcheck:0'

                else:
                    xcheck_array = xcheck.split(',')
                    new_note = main_note + 'xcheck:'

                    for (exp, freq) in collections.Counter(xcheck_array).items():
                            new_note += exp + ':' + str(freq) + ','

                peak.note = new_note.strip(',')

    self.status.config(text="Status: Done!")
    self.status.update()
    tkMessageBox.showinfo(title='Done!', message='Now check the Peak List (lt) for each experiment and see the Note property.')


# ---------------------------------------------------------------------------
def show_xcheck_dialog(session):
  sputil.the_dialog(xcheck_dialog, session).show_window(1)
