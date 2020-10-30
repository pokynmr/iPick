# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
iPick GUI for Sparky

@author: Mehdi Rahimi
"""

import Tkinter
import tkMessageBox
import tkFont
import sparky
import sputil
import tkutil
import pyutil
from os import path, popen, remove, system
import subprocess
import time
import sys
import os
import copy


LOG_PATH = '/tmp/'
IPICK_PATH = '/home/samic/MyWorks/CODES/iPick/'

sys.path.append(IPICK_PATH)
try:
    import iPick
except ImportError:
    print('Could not find iPick to import')


class ipick_dialog(tkutil.Dialog, tkutil.Stoppable):
  def __init__(self, session):

    #print(os.getcwd())

    # prepare temp files
    if path.exists(LOG_PATH + 'process.log'):
        remove(LOG_PATH + 'process.log')

    if path.exists('done'):
        remove('done')

    open(LOG_PATH + 'process.log', 'w').write('')


    self.session = session
    self.basic_adv = 'basic'
    # these will be updated later:
    self.resolution = '1'
    self.import_dist = 0.0
    self.import_drop = 0.0
    self.auto_integration = False


    tkutil.Dialog.__init__(self, session.tk, 'iPick')


    ipick_label = Tkinter.Label(self.top, text="Integrated UCSF Peak Picker v1", font=20)
    ipick_label.pack(side='top', fill='both', expand=1, pady=20)



# main frames

    radio_frame = Tkinter.Frame(self.top)
    radio_frame.pack(side='top', fill='both', expand=1, padx=8, pady=5)

    self.basic_frame = Tkinter.Frame(self.top)
    self.basic_frame.pack(side='bottom', fill='both', expand=1)

    self.adv_frame = Tkinter.Frame(self.top)
    self.adv_frame.pack(side='bottom', fill='both', expand=1)


    # separator
    sep = Tkinter.Frame(self.top, height=2, bd=1, relief="ridge")
    sep.pack(fill="both", padx=5, pady=5, side ='top')


# radiobutton basic / advanced

    radio_label = Tkinter.Label(radio_frame, text="Select the operating mode:")
    radio_label.pack(side='left', fill='both')
    self.basic_advanced = Tkinter.StringVar()
    self.basic_advanced.set('1')
    radio_button1 = Tkinter.Radiobutton(radio_frame, text="Basic ", highlightthickness = 0,
                                        variable=self.basic_advanced, value='1', command=self.basic_frame_show)
    radio_button1.pack(side='left')

    radio_button2 = Tkinter.Radiobutton(radio_frame, text="Advanced", highlightthickness = 0,
                                        variable=self.basic_advanced, value='2', command=self.adv_frame_show)
    radio_button2.pack(side='left')

    tkutil.create_hint(radio_button1, 'The "Basic" mode is very easy to use and runs with default settings.')
    tkutil.create_hint(radio_button2, 'The "Advanced" mode allows maximum settings and customization.')



# Basic frame

    # listbox
    b_topfrm = Tkinter.Frame(self.basic_frame)
    b_topfrm.pack(side='top', fill='both', expand=0, padx=8)

    # noise button & noise
    b_midfrm = Tkinter.Frame(self.basic_frame)
    b_midfrm.pack(fill='both', expand=1, padx=8)

    # ipick button & output
    b_btmfrm = Tkinter.Frame(self.basic_frame)
    b_btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    self.b_tree = tkutil.scrolling_list(b_topfrm, 'Select a spectrum for pick peaking:', 5, True)
    self.b_tree.listbox['selectmode'] = 'single'
    #self.b_tree.listbox['xscrollcommand'] = None
    self.b_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.b_tree.heading.config(font=('Courier', 5))
    #self.b_tree.heading['font'] = ('normal')
    self.b_tree.frame.pack(side='top', fill='both', expand=1, pady=(5,10))


    #update_button = Tkinter.Button(b_btmfrm, text='Update List', command=self.update_tree)
    #update_button.pack(side='top', anchor='w', expand=0, pady=(0, 5))


    # import frame
    b_import_frm = Tkinter.Frame(b_btmfrm)
    b_import_frm.pack(side='top', fill='both', expand=1)


    b_import_label = Tkinter.Label(b_import_frm, text="Import peaks:")
    b_import_label.pack(side='left')

    self.b_check_import = Tkinter.BooleanVar()
    self.b_check_import.set(True)
    b_checkbox_import = Tkinter.Checkbutton(b_import_frm, highlightthickness=0, text='Automatically',
                                            variable=self.b_check_import, command=self.import_check)
    b_checkbox_import.pack(side='left', anchor='w')

    self.b_import_button = Tkinter.Button(b_import_frm, text='Manual import', command=self.place_peaks)

    tkutil.create_hint(b_checkbox_import, 'This setting will import all found peaks automatically when the program is done')
    tkutil.create_hint(self.b_import_button, 'You can use the manual import after the peak picking is done')




    b_ipick_button = Tkinter.Button(b_btmfrm, text='Run iPick', font=('bold'),
                                  height=1, width=10, command=self.run_ipick)
    b_ipick_button.pack(side='top', pady=30)
    tkutil.create_hint(b_ipick_button, 'Runs the peak picking algorithm. May take a few minutes to complete')



##############################  for testing
    b_ipick_button = Tkinter.Button(b_btmfrm, text='Pick list', command=self.show_pick_list)
    b_ipick_button.pack(side='top')
##############################




    b_output_label = Tkinter.Label(b_btmfrm, text="Output progress:")
    b_output_label.pack(side='top', anchor='w')

    self.b_output = Tkinter.Text(b_btmfrm, width=50, height=10)
    #b_vsb = Tkinter.Scrollbar(self.b_output, orient="vertical", command=self.b_output.yview)
    #self.b_output.configure(yscrollcommand=b_vsb.set)
    #b_vsb.pack(side="right", fill="y")
    self.b_output.pack(side='top', expand=1, fill='both', anchor='w')



    self.b_status = Tkinter.Label(b_btmfrm, text="Status: Ready!")
    self.b_status.pack(side='top', anchor='w', pady=5)


    # fix the fonts
    suggested_fonts = ['Arial', 'NotoSans', 'Ubuntu', 'SegoeUI', 'Helvetica',
                       'Calibri', 'Verdana', 'DejaVuSans', 'FreeSans']
    for fnt in suggested_fonts:
      if fnt in tkFont.families():
        self.b_tree.listbox['font'] = (fnt, 9)
        self.b_tree.heading['font'] = (fnt, 11)
        break




# Advanced frame

    # listbox
    a_topfrm = Tkinter.Frame(self.adv_frame)
    a_topfrm.pack(side='top', fill='both', expand=0, padx=8)


    # pos neg peaks
    a_midfrm_pos_neg = Tkinter.Frame(self.adv_frame)
    a_midfrm_pos_neg.pack(fill='both', expand=1, padx=8, pady=8)


    # noise contour
    a_midfrm_nois_cont = Tkinter.Frame(self.adv_frame)
    a_midfrm_nois_cont.pack(fill='both', expand=1, padx=8, pady=8)


    # noise button & noise
    a_midfrm = Tkinter.Frame(self.adv_frame)
    a_midfrm.pack(fill='both', expand=1, padx=8, pady=5)


    # resolution
    a_midfrm_res = Tkinter.Frame(self.adv_frame)
    a_midfrm_res.pack(fill='both', expand=1, padx=8, pady=8)


    # ipick button & output
    a_btmfrm = Tkinter.Frame(self.adv_frame)
    a_btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    self.a_tree = tkutil.scrolling_list(a_topfrm, 'Select a spectrum for pick peaking:', 5, True)
    self.a_tree.listbox['selectmode'] = 'single'
    #self.a_tree.listbox['xscrollcommand'] = None
    self.a_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.a_tree.heading.config(font=('Courier', 5))
    #self.a_tree.heading['font'] = ('normal')
    self.a_tree.frame.pack(side='top', fill='both', expand=1, pady=(5,10))


    #a_update_button = Tkinter.Button(a_btmfrm, text='Update List', command=self.update_tree)
    #a_update_button.pack(side='top', anchor='w', expand=0, pady=(0, 5))


    nois_cont_label = Tkinter.Label(a_midfrm_nois_cont, text="Use:")
    nois_cont_label.pack(side='left', fill='both')
    self.nois_cont = Tkinter.StringVar()
    self.nois_cont.set('1')

    radio_nois = Tkinter.Radiobutton(a_midfrm_nois_cont, text="Noise Level", highlightthickness = 0,
                                        variable=self.nois_cont, value='1', command=self.noise_or_contour)
    radio_nois.pack(side='left')

    radio_cont = Tkinter.Radiobutton(a_midfrm_nois_cont, text="Contour Level", highlightthickness = 0,
                                        variable=self.nois_cont, value='2', command=self.noise_or_contour)
    radio_cont.pack(side='left')
    radio_nois.select()
    tkutil.create_hint(radio_nois, 'Use Noise level as the criteria for peak picking')
    tkutil.create_hint(radio_cont, 'Use Contour level as the criteria for peak picking')


    self.a_res = tkutil.entry_field(a_midfrm_nois_cont, '       |     Res: ', width=3, initial='1')
    self.a_res.entry.bind('<Return>', self.set_resolution)
    self.a_res.frame.pack(side='left')
    tkutil.create_hint(self.a_res.frame, 'Resolution. Choose between 1 and 5. Lower means more sensitive')



    self.a_noise_button = Tkinter.Button(a_midfrm, text='Find Noise Level', command=self.noise_level)
    self.a_noise_button.pack(side='left', padx=20)

    self.a_noise = tkutil.entry_field(a_midfrm, 'Noise Level: ', width=16)
    self.a_noise.entry.bind('<Return>', self.noise_level)
    self.a_noise.frame.pack(side='top', fill='x', expand=1)
    tkutil.create_hint(self.a_noise_button, 'Get the automatic noise level selection')
    tkutil.create_hint(self.a_noise.frame, 'The automatic noise level is shown here. You can change it as you like.')


    self.a_contour_button = Tkinter.Button(a_midfrm, text='Find Contour Level', command=self.contour_level)
    #self.a_contour_button.pack(side='left', padx=20)

    self.a_contour = tkutil.entry_field(a_midfrm, 'Contour Level: ', width=12)
    self.a_contour.entry.bind('<Return>', self.contour_level)
    #self.a_contour.frame.pack(side='top', fill='x', expand=1)
    tkutil.create_hint(self.a_contour_button, 'Get the automatic contour level selection')
    tkutil.create_hint(self.a_contour.frame, 'The automatic contour level is shown here. You can change it as you like.')


    pos_neg_label = Tkinter.Label(a_midfrm_pos_neg, text="Select:")
    pos_neg_label.pack(side='left', fill='both')
    self.pos_neg = Tkinter.StringVar()
    self.pos_neg.set('0')

    radio_pos = Tkinter.Radiobutton(a_midfrm_pos_neg, text="Positive peaks", highlightthickness = 0,
                                        variable=self.pos_neg, value='1')
    radio_pos.pack(side='left')

    radio_neg = Tkinter.Radiobutton(a_midfrm_pos_neg, text="Negative peaks", highlightthickness = 0,
                                        variable=self.pos_neg, value='-1')
    radio_neg.pack(side='left')
    radio_both = Tkinter.Radiobutton(a_midfrm_pos_neg, text="Both", highlightthickness = 0,
                                        variable=self.pos_neg, value='0')
    radio_both.pack(side='left')
    radio_both.select()
    tkutil.create_hint(radio_pos, 'Select positive peaks only')
    tkutil.create_hint(radio_neg, 'Select negative peaks only')
    tkutil.create_hint(radio_both, 'Select both positive and negative peaks')


    # separator
    sep = Tkinter.Frame(a_midfrm_res, height=2, bd=1, relief="ridge")
    sep.pack(fill="both", padx=5, pady=(5,5), side = 'top')


    a_automation_font = tkFont.Font(size=11)
    a_automation_label = Tkinter.Label(a_btmfrm, text="Post-processing Automation:", font=a_automation_font)
    a_automation_label.pack(side='top', anchor='w')
    tkutil.create_hint(a_automation_label, 'These options will run after the peak picking process')


    # import frame
    a_import_frm = Tkinter.Frame(a_btmfrm)
    a_import_frm.pack(side='top', expand=1, anchor='w')


    #a_import_label = Tkinter.Label(a_import_frm, text="Import peaks:")
    #a_import_label.pack(side='left', anchor='w')

    self.a_check_import = Tkinter.BooleanVar()
    self.a_check_import.set(True)
    a_checkbox_import = Tkinter.Checkbutton(a_import_frm, highlightthickness=0, text='Automatic Peak Import',
                                            variable=self.a_check_import, command=self.import_check)
    a_checkbox_import.pack(side='left', anchor='w', padx=(14,0), pady=(5,5))

    buttonFont = tkFont.Font(size=9)
    self.a_import_button = Tkinter.Button(a_import_frm, text='Manual Peak Import', font=buttonFont, command=self.place_peaks)

    tkutil.create_hint(a_checkbox_import, 'This setting will import all found peaks automatically when the program is done')
    tkutil.create_hint(self.a_import_button, 'You can use the manual import after the peak picking is done')



    # integration frame
    a_integration_frm = Tkinter.Frame(a_btmfrm)
    a_integration_frm.pack(side='top', fill='both', expand=1)



    self.a_import_dis = tkutil.entry_field(a_integration_frm, 'Import Dist.: ', width=3, initial='.1')
    self.a_import_dis.entry.bind('<Return>', self.set_import_dist)
    self.a_import_dis.frame.pack(side='left', padx=(20,0))
    tkutil.create_hint(self.a_import_dis.frame, 'Maximum distance between two peaks so that the program can consider them as different peaks')


    self.a_import_drop = tkutil.entry_field(a_integration_frm, 'Drop: ', width=3, initial='.01')
    self.a_import_drop.entry.bind('<Return>', self.set_import_drop)
    self.a_import_drop.frame.pack(side='left', padx=(5,10))
    tkutil.create_hint(self.a_import_drop.frame, 'Maximum drop between two peaks so that the program can consider them as different peaks')


    #a_integration_label = Tkinter.Label(a_integration_frm, text="Post-processing of peaks:")
    #a_integration_label.pack(side='left')

    self.a_check_integration = Tkinter.BooleanVar()
    self.a_check_integration.set(False)
    a_checkbox_integration = Tkinter.Checkbutton(a_integration_frm, highlightthickness=0, text='Auto Integration',
                                            variable=self.a_check_integration, command=self.integration_check)
    a_checkbox_integration.pack(side='left', anchor='w', padx=(30,0))
    tkutil.create_hint(a_checkbox_integration, 'Performs integration fitting on all peaks and opens a "Peak List" window so that you can examine them')


    # separator
    #sep = Tkinter.Frame(a_btmfrm, height=2, bd=1, relief="ridge")
    #sep.pack(fill="both", padx=5, pady=(5,12), side = 'top')



    a_ipick_button = Tkinter.Button(a_btmfrm, text='Run iPick', font=('bold'),
                                  height=1, width=10, command=self.run_ipick)
    a_ipick_button.pack(side='top', pady=(30,5))
    tkutil.create_hint(a_ipick_button, 'Runs the peak picking algorithm. May take a few minutes to complete')



    a_output_label = Tkinter.Label(a_btmfrm, text="Output progress:")
    a_output_label.pack(side='top', anchor='w', pady=(8,0))

    self.a_output = Tkinter.Text(a_btmfrm, width=50, height=6)
    #a_vsb = Tkinter.Scrollbar(self.a_output, orient="vertical", command=self.a_output.yview)
    #self.a_output.configure(yscrollcommand=a_vsb.set)
    #a_vsb.pack(side="right", fill="y")
    self.a_output.pack(side='top', expand=1, fill='both', anchor='w')


    self.a_status = Tkinter.Label(a_btmfrm, text="Status: Ready!")
    self.a_status.pack(side='top', anchor='w', pady=5)


    # fix the fonts
    suggested_fonts = ['Arial', 'NotoSans', 'Ubuntu', 'SegoeUI', 'Helvetica',
                       'Calibri', 'Verdana', 'DejaVuSans', 'FreeSans']
    for fnt in suggested_fonts:
      if fnt in tkFont.families():
        self.a_tree.listbox['font'] = (fnt, 9)
        self.a_tree.heading['font'] = (fnt, 11)
        break

    self.update_tree()
    self.basic_frame_show()




  def show_pick_list(self, *args):
      spectrum = self.session.selected_spectrum()
      if spectrum == None:
        return

      if not hasattr(self.session, 'spectrum_dialogs'):
        self.session.spectrum_dialogs = {}
      dialogs = self.session.spectrum_dialogs
      if (dialogs.has_key(spectrum) and not dialogs[spectrum].is_window_destroyed()):
        dialogs[spectrum].show_window(1)
      else:
        d = peak_list_dialog(self.session)
        d.show_window(1)
        d.settings.show_fields('Assignment', 'Chemical Shift')
        d.show_spectrum_peaks(spectrum)
        dialogs[spectrum] = d



# functions

  def get_view(self, spectrum):  # imported from APES
    for view in self.session.project.view_list():
      if view.spectrum == spectrum:
        return view
    return None


  def basic_frame_show(self):
      self.adv_frame.pack_forget()
      self.basic_frame.pack(side='bottom', fill='both', expand=1)
      self.basic_adv = 'basic'



  def adv_frame_show(self):
      self.basic_frame.pack_forget()
      self.adv_frame.pack(side='bottom', fill='both', expand=1)
      self.basic_adv = 'adv'


  def integration_check(self, *args):
      self.auto_integration = self.a_check_integration.get()


  def set_resolution(self, *args):
      self.resolution = self.a_res.variable.get()



  def set_import_dist(self, *args):
      self.import_dist = float(self.a_import_dis.variable.get())



  def set_import_drop(self, *args):
      self.import_drop = float(self.a_import_drop.variable.get())



  def update_tree(self):
    if self.session.project == None:
        tkMessageBox.showinfo(title='Error', message='No spectrum is loaded!')
        return

    self.b_tree.clear()
    self.a_tree.clear()

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    for spec in self.spec_list:
        self.b_tree.append(spec.name)
        self.a_tree.append(spec.name)



  def spectra_selected(self, *args):

    if (self.basic_adv == 'basic'):
        widget = self.b_status
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
    else:
        widget = self.a_status
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]
    widget.config(text="Status: Spectrum selected. Check noise level!")
    widget.update()

    if idx == None:
        tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
        return

    # print(self.spec_list[idx].data_path)

    spec = self.spec_list[idx]
    views = self.session.project.view_list()
    for v in views:
        if v.name == spec.name:
            v.got_focus()
            self.pos_contour = v.positive_levels.lowest
            self.neg_contour = v.negative_levels.lowest
            break



  def noise_level(self):
    if (self.basic_adv == 'basic'):
        widget = self.b_status
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
    else:
        widget = self.a_status
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]

    if idx == None:
        tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
        return

    widget.config(text="Status: Noise level found. Now run iPick!")
    widget.update()

    UCSF_FILE = self.spec_list[idx].data_path

    #reload(iPick)
    self.noise = iPick.get_noise_level(UCSF_FILE)

    if (self.basic_adv == 'basic'):
        self.b_noise.variable.set(self.noise)
    else:
        self.a_noise.variable.set(self.noise)

    #print(self.a_noise.variable.get())



  def contour_level(self):
    if (self.pos_neg.get() == '1'):
        self.a_contour.variable.set(self.pos_contour)

    elif (self.pos_neg.get() == '2'):
        self.a_contour.variable.set(self.neg_contour)

    else:
        self.a_contour.variable.set(self.pos_contour)



  def import_check(self, *args):
    if (self.basic_adv == 'basic'):
        if self.b_check_import.get() :
            self.b_import_button.pack_forget()
        else:
            self.b_import_button.pack(side='left', padx=15)

    else:
        if self.a_check_import.get() :
            self.a_import_button.pack_forget()
        else:
            self.a_import_button.pack(side='left', padx=(60,0), pady=0)



  def noise_or_contour(self, *args):
    if (self.nois_cont.get() == '1'):

        self.a_noise_button.pack(side='left', padx=20)
        self.a_noise.frame.pack(side='top', fill='x', expand=1)

        self.a_contour_button.pack_forget()
        self.a_contour.frame.pack_forget()

    elif (self.nois_cont.get() == '2'):

        self.a_noise_button.pack_forget()
        self.a_noise.frame.pack_forget()

        self.a_contour_button.pack(side='left', padx=20)
        self.a_contour.frame.pack(side='top', fill='x', expand=1)



  def ipick_process(self, UCSF_FILE):
    cmd = ("python " + IPICK_PATH +
            "/iPick.py -i " + UCSF_FILE +
            " -o peaks.list -r " + self.resolution +
            " --sign " + self.pos_neg.get() +
            " --overwrite && touch done")

    proc = subprocess.Popen([cmd], shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)



  def run_ipick(self):

    if (self.basic_adv == 'basic'):
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
        widget = self.b_status
    else:
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]
        widget = self.a_status
    widget.config(text="Status: iPick is running ...")
    widget.update()

    if idx == None:
        tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
        return

    self.set_resolution()

    UCSF_FILE = self.spec_list[idx].data_path

    try:

        if path.exists('peaks.list'):
            remove('peaks.list')

        self.ipick_process(UCSF_FILE)


        while True:
            log = open(LOG_PATH + 'process.log', 'r')


            if (self.basic_adv == 'basic'):
                widget = self.b_output
            else:
                widget = self.a_output


            widget.delete('1.0', Tkinter.END)
            widget.insert(Tkinter.END, log.read())
            widget.see(Tkinter.END)
            widget.update()

            log.close()

            time.sleep(0.5)

            if path.exists('done'):
                try:
                    remove('done')
                except:
                    tkMessageBox.showinfo(title='Error', message='Could not delete "done" file')

                break


    except TypeError as e:

        if (self.basic_adv == 'basic'):
            widget = self.b_status
        else:
            widget = self.a_status

        widget.config(text="Status: File is corrupted.")
        widget.update()
        print(e)
        print(sys.exc_type)

    else:
        log = open(LOG_PATH + 'process.log', 'r')

        if (self.basic_adv == 'basic'):
            widget = self.b_output
        else:
            widget = self.a_output


        widget.delete('1.0', Tkinter.END)
        widget.insert(Tkinter.END, log.read())
        widget.see(Tkinter.END)
        widget.update()

        log.close()


        if (self.basic_adv == 'basic'):
            widget = self.b_status
        else:
            widget = self.a_status
        widget.config(text="Status: iPick is done.")
        widget.update()

        print('Found peaks are also stored in "' + os.getcwd() + '/peaks.list" file.')

        tkMessageBox.showinfo(title='Job Done!', message='Peak picking is finished!')


        if ((self.basic_adv == 'basic') and self.b_check_import.get()) or \
           ((self.basic_adv == 'adv') and self.a_check_import.get()):
                self.place_peaks()



  def distance(self, p1, p2):
    sum_sq = 0
    for i in range(len(p1)):
        sum_sq += (p1[i] - p2[i]) ** 2
    return sum_sq ** 0.5



  def mid_point(self, p1, p2):
    midpoint = []
    for i in range(len(p1)):
        midpoint.append((p1[i] + p2[i]) / 2)
    return tuple(midpoint)



  def place_peaks(self):
    peaks = open('peaks.list', 'r').readlines()
    if len(peaks) < 4:
        tkMessageBox.showinfo(title='Error', message='Peak list file is empty!')
        return


    if (self.basic_adv == 'basic'):
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
    else:
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]

    if idx == None:
        tkMessageBox.showinfo(title='Error', message='The spectrum was not selected!')
        return

    spec = self.spec_list[idx]
    #spec = s.selected_spectrum()
    view = self.get_view(spec)

    self.set_import_dist()
    self.set_import_drop()
    self.integration_check()

    spec_peaks = copy.deepcopy(spec.peak_list())
    #print spec_peaks[1].frequency[0]

    print('\n\nCurrent peaks in the spectra: ' + str(len(spec_peaks)))
    print('New peaks to be processed: ' + str(len(peaks)-2) + '\n')

    #exis_peaks = []
    #for p in spec_peaks:
    #    exis_peaks.append(p.frequency)
    #exis_peaks.sort()


# Check if the new peak already exist on the spectrum

    #TODO: make this comparison faster

    placed_peaks = 0

    for i in range(2, len(peaks)):
        new_peak = peaks[i].split()[1:-1]   # also removes the first and last columns from the peak list file
        new_peak = tuple(float(e) for e in new_peak)
        new_peak_flag = True

        if spec_peaks == []:
            pk = spec.place_peak(new_peak)
            placed_peaks += 1
            if self.auto_integration:
                pk.fit(view)
            continue

        print('\nNew peak #' + str(i-1) + ' from ' + str(len(peaks)-2))

        k = 1
        for exis_peak in spec_peaks:
            print('Comparing with peak #' + str(k) + ' from ' + str(len(spec_peaks)))
            k += 1

            #print exis_peak.frequency[0]
            #print new_peak[0]
            #print self.import_dist
            #print self.distance(exis_peak.frequency, new_peak)

            # this is a pre-condition to make the loop faster
            if ((exis_peak.frequency[0] - new_peak[0]) < self.import_dist * 2):

                if (self.distance(exis_peak.frequency, new_peak) < self.import_dist):
                    print('The new peak is too close to this already existing peak:')
                    print(exis_peak.frequency)

                    #print spec.data_height((117.6,5.2,8.13))
                    midpoint_height = spec.data_height(self.mid_point(exis_peak.frequency, new_peak))

                    new_peak_height = spec.data_height(new_peak)
                    exis_peak_height = spec.data_height(exis_peak.frequency)

                    #print new_peak_height
                    #print exis_peak_height
                    #print midpoint_height

                    if (((new_peak_height - midpoint_height) < self.import_drop) or \
                       ((exis_peak_height - midpoint_height) < self.import_drop)):
                            print('No drop between the peaks. Skipping importing this peak.')
                            new_peak_flag = False
                            break


        if new_peak_flag:
            print('This is a new peak. Importing this peak.')
            pk = spec.place_peak(new_peak)
            placed_peaks += 1
            if self.auto_integration:
                pk.fit(view)


        #if spec.dimension == 2:
        #    spec.place_peak(new_peak)


    print('\nImport Completed! ' + str(placed_peaks) + ' new peaks are placed on the spectrum.')
    self.session.command_characters('lt')
    tkMessageBox.showinfo(title='Import Completed!', message=str(placed_peaks) + ' peaks are placed on the spectrum.')



#####################################################################################


class peak_list_dialog(tkutil.Dialog, tkutil.Stoppable):

  def __init__(self, session):

    self.session = session
    self.title = 'Peak List'
    self.spectrum = None
    self.peaks = ()
    self.settings = peak_list_settings()

    tkutil.Dialog.__init__(self, session.tk, self.title)

    pl = sputil.peak_listbox(self.top)
    pl.frame.pack(side = 'top', fill = 'both', expand = 1)
    pl.listbox.bind('<ButtonRelease-1>', pl.select_peak_cb)
    pl.listbox.bind('<ButtonRelease-2>', pl.goto_peak_cb)
    pl.listbox.bind('<Double-ButtonRelease-1>', pl.goto_peak_cb)
    self.peak_list = pl

    progress_label = Tkinter.Label(self.top, anchor = 'nw')
    progress_label.pack(side = 'top', anchor = 'w')

    br = tkutil.button_row(self.top,
			   ('Update', self.update_cb),
			   ('Sort by Reliability Score', self.sort_rs),
			   ('Sort by height', self.sort_cb),
			   ('Setup...', self.setup_cb),
			   ('Save...', self.peak_list.save_cb),
			   ('Stop', self.stop_cb),
			   ('Close', self.close_cb),
               ('Help', sputil.help_cb(session, 'PeakListPython')),
			   )
    br.frame.pack(side = 'top', anchor = 'w')

    keypress_cb = pyutil.precompose(sputil.command_keypress_cb, session)
    pl.listbox.bind('<KeyPress>', keypress_cb)

    tkutil.Stoppable.__init__(self, progress_label, br.buttons[4])

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
    for peak in peaks:
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak), peak)

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
    for peak in peaks:
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak), peak)

  # ---------------------------------------------------------------------------
  #
  def sort_reliability(self):

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


    # sort by reliability score
    data = []
    for peak in peaks:
        data.append((reliability_score(peak), peak))


    peaks = []
    data = sorted(data, key=lambda data: data[0], reverse=True)

    for (RS, peak) in data:
      peaks.append(peak)

    self.field_initializations(peaks)

    self.peak_list.clear()

    self.stoppable_loop('peaks', 50)
    for peak in peaks:
      self.check_for_stop()
      self.peak_list.append(self.peak_line(peak), peak)

  # ---------------------------------------------------------------------------
  #
  def field_initializations(self, peaks):

    for field in self.settings.fields:
      if field.onoff:
	field.initialize(self.session, peaks, self)

  # ---------------------------------------------------------------------------
  #
  def peak_line(self, peak):

    line = ''
    for field in self.settings.fields:
      if field.onoff:
	line = line + field.string(peak)
    return line

  # ---------------------------------------------------------------------------
  #
  def heading(self, dim):

    heading = ''
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
      if ftable.has_key(name):
        ftable[name].onoff = 1

# -----------------------------------------------------------------------------

class peak_list_field:
  def __init__(self):
    self.onoff = 0

  def heading(self, dim):
    if hasattr(self, 'title'):
      return self.pad(self.title(dim), dim)
    return self.pad(self.name, dim)

  def initialize(self, session, peaks, stoppable):
    pass

  def string(self, peak):
    return self.pad(self.text(peak), peak.spectrum.dimension)

  def pad(self, string, dim):
    size = self.size(dim)
    if size == None:
      return string
    return pyutil.pad_field(string, size)

  # ---------------------------------------------------------------------------
  # Make check button for peak list settings dialog
  #
  class field_widgets:
    def __init__(self, parent, name):
      cb = tkutil.checkbutton(parent, name, 0)
      cb.button.pack(side = 'top', anchor = 'w')
      self.checkbutton = cb
    def get_widget_state(self, field):
      field.onoff = self.checkbutton.state()
    def set_widget_state(self, field):
      self.checkbutton.set_state(field.onoff)


# ---------------------------------------------------------------------------
#

def reliability_score(peak):
    if peak.line_width == None:
        return 0
    linewidth = sum(pyutil.seq_product(peak.line_width, peak.spectrum.hz_per_ppm))
    SNR = abs(sputil.peak_height(peak) / peak.spectrum.noise)
    RS = (peak.volume / 1e5) + (SNR * 3) + (linewidth * 0.3)
    return RS


field_classes = []

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
  def size(self, dim): return 10
  def text(self, peak):
    if peak.volume: return '%.3g' % peak.volume
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
  def size(self, dim): return 6
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
  def size(self, dim): return 8 * dim
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
  def size(self, dim): return 8
  def text(self, peak): return ' %7.2f' % reliability_score(peak)
field_classes.append(RS_field)


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

    fb = Tkinter.Frame(self.top, borderwidth = 3, relief = 'groove')
    fb.pack(side = 'top', fill = 'x')

    #
    # Create the checkbutton and extra widgets for each possible field
    #
    self.field_widgets = {}
    for fc in field_classes:
      self.field_widgets[fc] = fc.field_widgets(self.top, fc.name)

    br = tkutil.button_row(self.top,
                          ('Ok', self.ok_cb),
		            	  ('Apply', self.apply_cb),
			              ('Close', self.close_cb),
			              )
    br.frame.pack(side = 'top', anchor = 'w')

  # ---------------------------------------------------------------------------
  #
  def show_settings(self, settings):

    for f in settings.fields:
        #self.field_widgets[f.__class__].set_widget_state(f)
        try:
            self.field_widgets[f.__class__].set_widget_state(f)
        except:
            print f.__class__

  # ---------------------------------------------------------------------------
  #
  def get_settings(self):

    settings = peak_list_settings()
    for f in settings.fields:
        self.field_widgets[f.__class__].get_widget_state(f)

    return settings


# -----------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def show_ipick_dialog(session):
  sputil.the_dialog(ipick_dialog, session).show_window(1)
