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

    self.tol_H = tkutil.entry_field(tol_frm, '1H: ', width=5, initial='1')
    self.tol_H.frame.pack(side='left', padx=(20,10))
    #tkutil.create_hint(self.tol_H.frame, 'Maximum ')

    self.tol_C = tkutil.entry_field(tol_frm, '13C:', width=5, initial='1')
    self.tol_C.frame.pack(side='left', padx=(5,10))
    #tkutil.create_hint(self.tol_C.frame, 'Maximum ')

    self.tol_N = tkutil.entry_field(tol_frm, '15N:', width=5, initial='1')
    self.tol_N.frame.pack(side='left', padx=(5,10))
    #tkutil.create_hint(self.tol_N.frame, 'Maximum ')


# exclude frame

    exclude_font = tkFont.Font(size=11)
    exclude_label = tk.Label(btmfrm, text="Exclude Range:", font=tolerance_font)
    exclude_label.pack(side='top', anchor='w', pady=(15,0))
    #tkutil.create_hint(exclude_label, 'These ')


    exclude_frm = tk.Frame(btmfrm)
    exclude_frm.pack(side='top', fill='both', expand=1, pady=(5,0))


    self.exclude_from = tkutil.entry_field(exclude_frm, 'From: ', width=5, initial='1')
    self.exclude_from.frame.pack(side='left', padx=(25,0))
    #tkutil.create_hint(self.exclude_from.frame, 'Maximum ')


    self.exclude_to = tkutil.entry_field(exclude_frm, 'To: ', width=5, initial='1')
    self.exclude_to.frame.pack(side='left', padx=(5,10))
    #tkutil.create_hint(self.exclude_to.frame, 'Maximum ')


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

#    print self.specs_nuclei
  # specs_peaks[each_selected_spec] --> all peaks in that spec

    #for spec_peaks in self.specs_peaks:
#    for spec_nuclei in self.specs_nuclei[0]:

#        print spec_nuclei


    for i in range(len(self.specs_nuclei)):
        print self.specs_names[i]
        print self.specs_nuclei[i]



        #for peak in spec_peaks:

            #if peak.assignment.find('?') == -1:     # skip if already assigned
             #   continue

            #print peak.frequency[0]
            #peak.note

















# ---------------------------------------------------------------------------
def show_xcheck_dialog(session):
  sputil.the_dialog(xcheck_dialog, session).show_window(1)
