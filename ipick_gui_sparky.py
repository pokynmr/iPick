# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
iPick GUI for Sparky

@author: Mehdi Rahimi
"""

import os
import signal
import subprocess
import time
import sys
import tempfile
import multiprocessing

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
import pyutil

if os.path.exists('/usr/bin/python') or ('anaconda' in os.environ['PATH']) or ('python' in os.environ['PATH']):
    PYTHON_BIN = 'python'
    PYTHON_INSTALLED = True
else:
    # if the version for the python packaged with Sparky changed, correct the lines bellow:
    PYTHON_BIN = os.path.join(sparky.installation_path(), 'python2.7', 'bin', 'python2.7')      # Linux
    if not os.path.exists(PYTHON_BIN):
        PYTHON_BIN = os.path.join(sparky.installation_path(), 'python2.7', 'python')    # Windows
    PYTHON_INSTALLED = False

IPICK_PATH = os.path.abspath(os.path.dirname(__file__))
LOG_FILE = os.path.join(tempfile.gettempdir(), 'process.log')   # '/tmp/process.log' for Linux/Mac
DONE_FILE = os.path.join(tempfile.gettempdir(), 'done')

sys.path.append(IPICK_PATH)
try:
    import iPick
except ImportError:
    print('Could not find iPick to import')
    tkMessageBox.showwarning(title='Error', message='Could not find iPick!')

OS_WINDOWS = False
if ((sys.platform == 'win32') or (sys.platform == 'cygwin')):
    OS_WINDOWS = True

manual_coeff, coeff1, coeff2, coeff3, SNR_abs, volume_abs = [[]] * 6

class ipick_dialog(tkutil.Dialog, tkutil.Stoppable):
  def __init__(self, session):

    #print(os.getcwd())

    # prepare temp files
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    if os.path.exists(DONE_FILE):
        os.remove(DONE_FILE)

    open(LOG_FILE, 'w').write('')


    self.session = session
    self.basic_adv = 'basic'
    self.stopped_flag = 0
    # these will be updated later:
    self.resolution = '1'
    self.import_dist = 0.0
    self.import_drop = 0.0
    self.auto_integration = False


    tkutil.Dialog.__init__(self, session.tk, 'iPick (Integrated UCSF Peak Picker)')


    #ipick_label = tk.Label(self.top, text="Integrated UCSF Peak Picker v1", font=20)
    #ipick_label.pack(side='top', fill='both', expand=1, pady=(20,10))



# main frames

    radio_frame = tk.Frame(self.top)
    radio_frame.pack(side='top', fill='both', expand=1, padx=8, pady=(15,5))

    self.basic_frame = tk.Frame(self.top)
    self.basic_frame.pack(side='bottom', fill='both', expand=1)

    self.adv_frame = tk.Frame(self.top)
    self.adv_frame.pack(side='bottom', fill='both', expand=1)


    # separator
    sep = tk.Frame(self.top, height=2, bd=1, relief="ridge")
    sep.pack(fill="both", padx=5, pady=5, side ='top')


# radiobutton basic / advanced

    radio_label = tk.Label(radio_frame, text="Select the operating mode:")
    radio_label.pack(side='left', fill='both')
    self.basic_advanced = tk.StringVar()
    self.basic_advanced.set('1')
    radio_button1 = tk.Radiobutton(radio_frame, text="Basic ", highlightthickness = 0,
                                        variable=self.basic_advanced, value='1', command=self.basic_frame_show)
    radio_button1.pack(side='left')

    radio_button2 = tk.Radiobutton(radio_frame, text="Advanced", highlightthickness = 0,
                                        variable=self.basic_advanced, value='2', command=self.adv_frame_show)
    radio_button2.pack(side='left')

    tkutil.create_hint(radio_button1, 'The "Basic" mode is very easy to use and runs with default settings.')
    tkutil.create_hint(radio_button2, 'The "Advanced" mode allows maximum settings and customization.')



# Basic frame

    # listbox
    b_list_frm = tk.Frame(self.basic_frame)
    b_list_frm.pack(side='top', fill='both', expand=0, padx=8)

    # import frame
    b_import_frm = tk.Frame(self.basic_frame)
    b_import_frm.pack(side='top', fill='both', expand=1)

    # noise button & noise
    b_buttons_frm = tk.Frame(self.basic_frame)
    b_buttons_frm.pack(fill='both', expand=1, padx=8)

    # output
    b_btmfrm = tk.Frame(self.basic_frame)
    b_btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    self.b_tree = tkutil.scrolling_list(b_list_frm, 'Select a spectrum for pick peaking:', 5, True)
    self.b_tree.listbox['selectmode'] = 'single'
    #self.b_tree.listbox['xscrollcommand'] = None
    self.b_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.b_tree.heading.config(font=('Courier', 5))
    #self.b_tree.heading['font'] = ('normal')
    self.b_tree.frame.pack(side='top', fill='both', expand=1, pady=(5,10))


    b_import_label = tk.Label(b_import_frm, text="Import peaks:")
    b_import_label.pack(side='left')

    self.b_check_import = tk.BooleanVar()
    self.b_check_import.set(True)
    b_checkbox_import = tk.Checkbutton(b_import_frm, highlightthickness=0, text='Automatically',
                                            variable=self.b_check_import, command=self.import_check)
    b_checkbox_import.pack(side='left', anchor='w')

    self.b_import_button = tk.Button(b_import_frm, text='Manual import', command=self.place_peaks)

    tkutil.create_hint(b_checkbox_import, 'This setting will import all found peaks automatically when the program is done')
    tkutil.create_hint(self.b_import_button, 'You can use the manual import after the peak picking is done')




    b_ipick_button = tk.Button(b_buttons_frm, text='Run iPick', width=18, command=self.run_ipick)
    b_ipick_button.pack(side='left', pady=30)
    tkutil.create_hint(b_ipick_button, 'Runs the peak picking algorithm. May take a few minutes to complete')


    #update_button = tk.Button(b_buttons_frm, text='Update List', command=self.update_tree)
    #update_button.pack(side='left', anchor='w', expand=0)


    b_ipick_button = tk.Button(b_buttons_frm, text='Pick list', command=self.show_pick_list)
    b_ipick_button.pack(side='left')
    tkutil.create_hint(b_ipick_button, 'Open the Peak List for the selected spectrum')

    self.b_stop_button = tk.Button(b_buttons_frm, text='Stop', command=self.stop_button)
    self.b_stop_button.pack(side='left')
    tkutil.create_hint(self.b_stop_button, 'Stops any processing')


#TODO: Add the section for iPick to the extensions.html file
    help_button = tk.Button(b_buttons_frm, text='Help', command=sputil.help_cb(session, 'iPick'))
    help_button.pack(side='left')
    tkutil.create_hint(help_button, 'Opens a help page with more information about this module.')

    b_progress_label = tk.Label(b_buttons_frm)
    b_progress_label.pack(side = 'left', anchor = 'w')

    tkutil.Stoppable.__init__(self, b_progress_label, self.b_stop_button)


    b_output_label = tk.Label(b_btmfrm, text="Output progress:")
    b_output_label.pack(side='top', anchor='w')

    self.b_output = tk.Text(b_btmfrm, width=50, height=10)
    #b_vsb = tk.Scrollbar(self.b_output, orient="vertical", command=self.b_output.yview)
    #self.b_output.configure(yscrollcommand=b_vsb.set)
    #b_vsb.pack(side="right", fill="y")
    self.b_output.pack(side='top', expand=1, fill='both', anchor='w')



    self.b_status = tk.Label(b_btmfrm, text="Status: Ready!")
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
    a_listbox_frm = tk.Frame(self.adv_frame)
    a_listbox_frm.pack(side='top', fill='both', expand=0, padx=8)


    # pos neg peaks
    a_pos_neg_frm = tk.Frame(self.adv_frame)
    a_pos_neg_frm.pack(fill='both', expand=1, padx=8, pady=(8,0))


    # noise contour
    a_nois_cont_frm = tk.Frame(self.adv_frame)
    a_nois_cont_frm.pack(fill='both', expand=1, padx=8, pady=(8,0))


    # noise button & noise
    a_nois_cont_but_frm = tk.Frame(self.adv_frame)
    a_nois_cont_but_frm.pack(fill='both', expand=1, padx=8, pady=5)


    # resolution
    a_resolution_frm = tk.Frame(self.adv_frame)
    a_resolution_frm.pack(fill='both', expand=1, padx=8, pady=(8,0))


    # post-processing
    a_postpro_frm = tk.Frame(self.adv_frame)
    a_postpro_frm.pack(fill='both', expand=1, padx=8, pady=(0,8))


    # ipick button & output
    a_btmfrm = tk.Frame(self.adv_frame)
    a_btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    self.a_tree = tkutil.scrolling_list(a_listbox_frm, 'Select a spectrum for pick peaking:', 5, True)
    self.a_tree.listbox['selectmode'] = 'single'
    #self.a_tree.listbox['xscrollcommand'] = None
    self.a_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.a_tree.heading.config(font=('Courier', 5))
    #self.a_tree.heading['font'] = ('normal')
    self.a_tree.frame.pack(side='top', fill='both', expand=1, pady=(5,10))


    #a_update_button = tk.Button(a_btmfrm, text='Update List', command=self.update_tree)
    #a_update_button.pack(side='top', anchor='w', expand=0, pady=(0, 5))


    nois_cont_label = tk.Label(a_nois_cont_frm, text="Use:")
    nois_cont_label.pack(side='left', fill='both')
    self.nois_cont = tk.StringVar()
    self.nois_cont.set('1')

    radio_cont = tk.Radiobutton(a_nois_cont_frm, text="Contour Level", highlightthickness = 0,
                                        variable=self.nois_cont, value='2', command=self.noise_or_contour)
    radio_cont.pack(side='left')

    radio_nois = tk.Radiobutton(a_nois_cont_frm, text="Noise Level", highlightthickness = 0,
                                        variable=self.nois_cont, value='1', command=self.noise_or_contour)
    radio_nois.pack(side='left')

    radio_cont.select()
    tkutil.create_hint(radio_nois, 'Use Noise level as the criteria for peak picking')
    tkutil.create_hint(radio_cont, 'Use Contour level as the criteria for peak picking')


    self.a_res = tkutil.entry_field(a_nois_cont_frm, '       |     Res: ', width=3, initial='1')
    self.a_res.entry.bind('<Return>', self.set_resolution)
    self.a_res.frame.pack(side='left')
    tkutil.create_hint(self.a_res.frame, 'Resolution. Choose between 1 and 5. Lower means more sensitive')



    self.a_noise_button = tk.Button(a_nois_cont_but_frm, text='Find Noise Level', command=self.noise_level)
    #self.a_noise_button.pack(side='left', padx=20)

    self.a_noise = tkutil.entry_field(a_nois_cont_but_frm, 'Noise Level: ', width=16)
    self.a_noise.entry.bind('<Return>', self.noise_level)
    #self.a_noise.frame.pack(side='top', fill='x', expand=1)
    tkutil.create_hint(self.a_noise_button, 'Get the automatic noise level selection')
    tkutil.create_hint(self.a_noise.frame, 'The automatic noise level is shown here. You can change it as you like.')


    self.a_contour_button = tk.Button(a_nois_cont_but_frm, text='Find Contour Level', command=self.contour_level)
    self.a_contour_button.pack(side='left', padx=20)

    self.a_contour = tkutil.entry_field(a_nois_cont_but_frm, 'Contour Level: ', width=12)
    self.a_contour.entry.bind('<Return>', self.contour_level)
    self.a_contour.frame.pack(side='top', fill='x', expand=1)
    tkutil.create_hint(self.a_contour_button, 'Get the automatic contour level selection')
    tkutil.create_hint(self.a_contour.frame, 'The automatic contour level is shown here. You can change it as you like.')


    pos_neg_label = tk.Label(a_pos_neg_frm, text="Select:")
    pos_neg_label.pack(side='left', fill='both')
    self.pos_neg = tk.StringVar()
    self.pos_neg.set('0')

    radio_pos = tk.Radiobutton(a_pos_neg_frm, text="Positive peaks", highlightthickness = 0,
                                        variable=self.pos_neg, value='1')
    radio_pos.pack(side='left')

    radio_neg = tk.Radiobutton(a_pos_neg_frm, text="Negative peaks", highlightthickness = 0,
                                        variable=self.pos_neg, value='-1')
    radio_neg.pack(side='left')
    radio_both = tk.Radiobutton(a_pos_neg_frm, text="Both", highlightthickness = 0,
                                        variable=self.pos_neg, value='0')
    radio_both.pack(side='left')
    radio_both.select()
    tkutil.create_hint(radio_pos, 'Select positive peaks only')
    tkutil.create_hint(radio_neg, 'Select negative peaks only')
    tkutil.create_hint(radio_both, 'Select both positive and negative peaks')


    # separator
    sep = tk.Frame(a_postpro_frm, height=2, bd=1, relief="ridge")
    sep.pack(fill="both", padx=5, pady=(0,7), side='top')


    a_automation_font = tkFont.Font(size=11)
    a_automation_label = tk.Label(a_postpro_frm, text="Post-processing Automation:", font=a_automation_font)
    a_automation_label.pack(side='top', anchor='w')
    tkutil.create_hint(a_automation_label, 'These options will run after the peak picking process')


    # import frame
    a_import_frm = tk.Frame(a_postpro_frm)
    a_import_frm.pack(side='top', expand=1, anchor='w')


    #a_import_label = tk.Label(a_import_frm, text="Import peaks:")
    #a_import_label.pack(side='left', anchor='w')

    self.a_check_import = tk.BooleanVar()
    self.a_check_import.set(True)
    a_checkbox_import = tk.Checkbutton(a_import_frm, highlightthickness=0, text='Automatic Peak Import',
                                            variable=self.a_check_import, command=self.import_check)
    a_checkbox_import.pack(side='left', anchor='w', padx=(14,0), pady=(5,5))

    buttonFont = tkFont.Font(size=9)
    self.a_import_button = tk.Button(a_import_frm, text='Manual Peak Import', font=buttonFont, command=self.place_peaks)

    tkutil.create_hint(a_checkbox_import, 'This setting will import all found peaks automatically when the program is done')
    tkutil.create_hint(self.a_import_button, 'You can use the manual import after the peak picking is done')



    # integration frame
    a_integration_frm = tk.Frame(a_postpro_frm)
    a_integration_frm.pack(side='top', fill='both', expand=1)


    self.a_import_dis = tkutil.entry_field(a_integration_frm, 'Import Dist.: ', width=3, initial='.1')
    self.a_import_dis.entry.bind('<Return>', self.set_import_dist)
    self.a_import_dis.frame.pack(side='left', padx=(20,0))
    tkutil.create_hint(self.a_import_dis.frame, 'Maximum distance between two peaks so that the program can consider them as different peaks')


    self.a_import_drop = tkutil.entry_field(a_integration_frm, 'Drop: ', width=3, initial='.01')
    self.a_import_drop.entry.bind('<Return>', self.set_import_drop)
    self.a_import_drop.frame.pack(side='left', padx=(5,10))
    tkutil.create_hint(self.a_import_drop.frame, 'Maximum drop between two peaks so that the program can consider them as different peaks')


    #a_integration_label = tk.Label(a_integration_frm, text="Post-processing of peaks:")
    #a_integration_label.pack(side='left')

    self.a_check_integration = tk.BooleanVar()
    self.a_check_integration.set(False)
    a_checkbox_integration = tk.Checkbutton(a_integration_frm, highlightthickness=0, text='Auto Integration',
                                            variable=self.a_check_integration, command=self.integration_check)
    a_checkbox_integration.pack(side='left', anchor='w', padx=(30,0))
    tkutil.create_hint(a_checkbox_integration, 'Performs integration fitting on all peaks and opens a "Peak List" window so that you can examine them')



    # integration_radio frame
    self.a_integration_radio_frm = tk.Frame(a_postpro_frm)
    #a_integration_radio_frm.pack(side='top', fill='both', expand=1, pady=(10,0), padx=10)

    integration_radio_label = tk.Label(self.a_integration_radio_frm, text="Auto Integration mode:")
    integration_radio_label.pack(side='left', fill='both')
    self.integration_radio = tk.StringVar()
    self.integration_radio.set('1')
    integration_radio_button1 = tk.Radiobutton(self.a_integration_radio_frm, text="Individual fit", highlightthickness = 0,
                                        variable=self.integration_radio, value='1')
    integration_radio_button1.pack(side='left')
    tkutil.create_hint(integration_radio_button1, 'Each peak will be fitted individually not considering the neighbor peaks')

    integration_radio_button2 = tk.Radiobutton(self.a_integration_radio_frm, text="Group fit", highlightthickness = 0,
                                        variable=self.integration_radio, value='2', command=self.groupfit_selected)
    integration_radio_button2.pack(side='left')
    tkutil.create_hint(integration_radio_button2, 'Peaks will be fitted as a group by considering the neighbor peaks')


    # separator
    #sep = tk.Frame(a_btmfrm, height=2, bd=1, relief="ridge")
    #sep.pack(fill="both", padx=5, pady=(5,12), side = 'top')


    # buttons frame
    a_buttons_frm = tk.Frame(a_btmfrm)
    a_buttons_frm.pack(side='top', fill='both', expand=1, pady=(10,8))


    a_ipick_button = tk.Button(a_buttons_frm, text='Run iPick', width=18, command=self.run_ipick)
    a_ipick_button.pack(side='left')
    tkutil.create_hint(a_ipick_button, 'Runs the peak picking algorithm. May take a few minutes to complete')


    #a_update_button = tk.Button(a_buttons_frm, text='Update List', command=self.update_tree)
    #a_update_button.pack(side='left', anchor='w', expand=0)


    a_ipick_button = tk.Button(a_buttons_frm, text='Pick list', command=self.show_pick_list)
    a_ipick_button.pack(side='left')
    tkutil.create_hint(b_ipick_button, 'Open the Peak List for the selected spectrum')

    self.a_stop_button = tk.Button(a_buttons_frm, text='Stop', command=self.stop_button)
    self.a_stop_button.pack(side='left')
    tkutil.create_hint(self.a_stop_button, 'Stops any processing')

    a_help_button = tk.Button(a_buttons_frm, text='Help', command=sputil.help_cb(session, 'iPick'))
    a_help_button.pack(side='left')
    tkutil.create_hint(a_help_button, 'Opens a help page with more information about this module.')

    a_progress_label = tk.Label(a_buttons_frm)
    a_progress_label.pack(side='left', anchor='w')

    tkutil.Stoppable.__init__(self, a_progress_label, self.a_stop_button)


    a_output_label = tk.Label(a_btmfrm, text="Output progress:")
    a_output_label.pack(side='top', anchor='w', pady=(8,0))

    self.a_output = tk.Text(a_btmfrm, width=50, height=6)
    #a_vsb = tk.Scrollbar(self.a_output, orient="vertical", command=self.a_output.yview)
    #self.a_output.configure(yscrollcommand=a_vsb.set)
    #a_vsb.pack(side="right", fill="y")
    self.a_output.pack(side='top', expand=1, fill='both', anchor='w')


    self.a_status = tk.Label(a_btmfrm, text="Status: Ready!")
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



# ---------------------------------------------------------------------------
# functions
# ---------------------------------------------------------------------------
  def stop_button(self, *args):
    try:

        if not OS_WINDOWS:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)

    #    import psutil
    #    process = psutil.Process(self.proc.pid)
    #    for proc in process.children(recursive=True):
    #        proc.kill()
    #    process.kill()

        done_file = open(DONE_FILE, 'w')
        done_file.close()

        time.sleep(0.5)

        if (self.basic_adv == 'basic'):
            output = self.b_output
            status = self.b_status
        else:
            output = self.a_output
            status = self.a_status

        output.delete('1.0', tk.END)
        output.update()

        status.config(text="Status: Process Stopped!")
        status.update()

        self.stopped_flag = 1


        self.stop_cb()
        self.a_stop_button['state'] = 'disabled'
        self.b_stop_button['state'] = 'disabled'

    except:
        pass


# ---------------------------------------------------------------------------
  def groupfit_selected(self, *args):
    d = groupfit_dialog(self.session)
    d.show_window(1)


# ---------------------------------------------------------------------------
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
        d.settings.show_fields('Assignment', 'Chemical Shift', 'Reliability Score')
        d.show_spectrum_peaks(spectrum)
        dialogs[spectrum] = d


# ---------------------------------------------------------------------------
  def get_view(self, spectrum):  # imported from APES
    for view in self.session.project.view_list():
      if view.spectrum == spectrum:
        return view
    return None

# ---------------------------------------------------------------------------
  def basic_frame_show(self):
      self.adv_frame.pack_forget()
      self.basic_frame.pack(side='bottom', fill='both', expand=1)
      self.basic_adv = 'basic'

# ---------------------------------------------------------------------------
  def adv_frame_show(self):
      self.basic_frame.pack_forget()
      self.adv_frame.pack(side='bottom', fill='both', expand=1)
      self.basic_adv = 'adv'

# ---------------------------------------------------------------------------
  def integration_check(self, *args):
      self.auto_integration = self.a_check_integration.get()
      if self.a_check_integration.get():
            self.a_integration_radio_frm.pack(side='top', fill='both', expand=1, pady=(10,0), padx=10)
      else:
            self.a_integration_radio_frm.pack_forget()


# ---------------------------------------------------------------------------
  def set_resolution(self, *args):
      self.resolution = self.a_res.variable.get()

# ---------------------------------------------------------------------------
  def set_import_dist(self, *args):
      self.import_dist = float(self.a_import_dis.variable.get())

# ---------------------------------------------------------------------------
  def set_import_drop(self, *args):
      self.import_drop = float(self.a_import_drop.variable.get())


# ---------------------------------------------------------------------------
  def update_tree(self):
    if self.session.project == None:
        tkMessageBox.showwarning(title='Error', message='No spectrum is loaded!')
        return

    self.b_tree.clear()
    self.a_tree.clear()

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    for spec in self.spec_list:
        self.b_tree.append(spec.name)
        self.a_tree.append(spec.name)


# ---------------------------------------------------------------------------
  def spectra_selected(self, *args):

    if (self.basic_adv == 'basic'):
        widget = self.b_status
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
    else:
        widget = self.a_status
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]
    widget.config(text="Status: Spectrum selected. Check the contour level!")
    widget.update()

    if idx == None:
        tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
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

    self.a_contour.variable.set('')
    self.a_noise.variable.set('')


# ---------------------------------------------------------------------------
  def noise_level(self):
    if (self.basic_adv == 'basic'):
        widget = self.b_status
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
    else:
        widget = self.a_status
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]

    if idx == None:
        tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
        return

    widget.config(text="Status: Noise level found.")
    widget.update()

    UCSF_FILE = self.spec_list[idx].data_path

    #reload(iPick)
    self.noise = iPick.get_noise_level(UCSF_FILE)

    self.a_noise.variable.set(self.noise)

    #print(self.a_noise.variable.get())


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
  def ipick_process(self, UCSF_FILE):

    CPUs = str(multiprocessing.cpu_count())
    if not PYTHON_INSTALLED:
        CPUs = '1'

    cmd = (PYTHON_BIN + " " + os.path.join(IPICK_PATH, "iPick.py") +
            " -i " + UCSF_FILE +
            " -o " + self.PEAKLIST_FILE +
            " -r " + self.resolution +
            " -c " + CPUs +
            " --sign " + self.pos_neg.get() +
            " --overwrite")


    if (self.nois_cont.get() == '1'):
        # using noise level
        cmd = (PYTHON_BIN + " " + os.path.join(IPICK_PATH, "iPick.py") +
                " -i " + UCSF_FILE +
                " -o " + self.PEAKLIST_FILE +
                " -r " + self.resolution +
                " -c " + CPUs +
                " --sign " + self.pos_neg.get() +
                " --threshold " + self.a_noise.variable.get() +
                " --overwrite")


    elif (self.nois_cont.get() == '2'):
        # using contour level
        cmd = (PYTHON_BIN + " " + os.path.join(IPICK_PATH, "iPick.py") +
               " -i " + UCSF_FILE +
               " -o " + self.PEAKLIST_FILE +
               " -r " + self.resolution +
               " -c " + CPUs +
               " --sign " + self.pos_neg.get() +
               " --threshold " + self.a_contour.variable.get() +
               " --overwrite")

    print cmd

    if OS_WINDOWS:
        self.proc = subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
    else:
        self.proc = subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True, preexec_fn=os.setsid)


# ---------------------------------------------------------------------------
  def run_ipick(self):

    if (self.basic_adv == 'basic'):
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
        widget = self.b_status
    else:
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]
        widget = self.a_status
    widget.config(text="Status: iPick is running ...")
    widget.update()

    if idx == None:
        tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
        return

    self.set_resolution()

    if (self.nois_cont.get() == '1'):
        # using the noise level
        if self.a_noise.variable.get() == '':
            self.noise_level()

    elif (self.nois_cont.get() == '2'):
        # using the contour level
        if self.a_contour.variable.get() == '':
            self.contour_level()

    UCSF_FILE = self.spec_list[idx].data_path


    try:

        experiment_file = os.path.split(UCSF_FILE)[1]
        experiment_name = os.path.splitext(experiment_file)[0]
        peak_list = experiment_name + '.list'

        self.PEAKLIST_FILE = os.path.join(tempfile.gettempdir(), peak_list)

        # try putting the peak list file in the Lists folder
        try:
            Spectra_folder = os.path.split(UCSF_FILE)[0]
            project_folder = os.path.split(Spectra_folder)[0]
            Lists_folder = os.path.join(project_folder, 'Lists')
            if os.path.exists(Lists_folder) and os.access(Lists_folder, os.W_OK | os.X_OK):
                self.PEAKLIST_FILE = os.path.join(Lists_folder, peak_list)
        except:
            pass


        if os.path.exists(self.PEAKLIST_FILE):
            os.remove(self.PEAKLIST_FILE)

        #self.ipick_process(UCSF_FILE)
        self.stoppable_call(self.ipick_process, UCSF_FILE)
        self.b_stop_button['state'] = 'normal'
        self.a_stop_button['state'] = 'normal'


        while True:
            log = open(LOG_FILE, 'r')


            if (self.basic_adv == 'basic'):
                widget = self.b_output
            else:
                widget = self.a_output


            widget.delete('1.0', tk.END)
            widget.insert(tk.END, log.read())
            widget.see(tk.END)
            widget.update()

            log.close()

            time.sleep(0.5)

            if os.path.exists(DONE_FILE):
                try:
                    os.remove(DONE_FILE)
                except:
                    tkMessageBox.showwarning(title='Error', message='Could not delete "done" file')

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
#        log = open(LOG_FILE, 'r')
#
#        if (self.basic_adv == 'basic'):
#            widget = self.b_output
#        else:
#            widget = self.a_output
#
#
#        widget.delete('1.0', tk.END)
#        widget.insert(tk.END, log.read())
#        widget.see(tk.END)
#        widget.update()
#
#        log.close()

        if self.stopped_flag == 0:

            if (self.basic_adv == 'basic'):
                widget = self.b_status
            else:
                widget = self.a_status
            widget.config(text="Status: peak picking is done.")
            widget.update()

            print('Found peaks are also stored in "' + self.PEAKLIST_FILE + '" file.')

            tkMessageBox.showinfo(title='Job Done!', message='Peak picking is finished!')


            if ((self.basic_adv == 'basic') and self.b_check_import.get()) or \
               ((self.basic_adv == 'adv') and self.a_check_import.get()):
                    self.stoppable_call(self.place_peaks)

    self.stopped_flag = 0
    self.a_stop_button['state'] = 'disabled'
    self.b_stop_button['state'] = 'disabled'


# ---------------------------------------------------------------------------
  def distance(self, p1, p2):
    sum_sq = 0
    for i in range(len(p1)):
        sum_sq += (p1[i] - p2[i]) ** 2
    return sum_sq ** 0.5


# ---------------------------------------------------------------------------
  def mid_point(self, p1, p2):
    midpoint = []
    for i in range(len(p1)):
        midpoint.append((p1[i] + p2[i]) / 2)
    return tuple(midpoint)


# ---------------------------------------------------------------------------
  def place_peaks(self):
    if (self.basic_adv == 'basic'):
        status = self.b_status
    else:
        status = self.a_status
    status.config(text="Status: Importing the peaks ...")
    status.update()


    peaks = open(self.PEAKLIST_FILE, 'r').readlines()
    if len(peaks) < 4:
        tkMessageBox.showwarning(title='Error', message='Peak list file is empty!')
        return


    if len(peaks) > 5000:
        confirmation = tkMessageBox.askyesno(title='Continue?',
             message='iPick will try to import ' + str(len(peaks)) + ' peaks. This can take a long time. Do you want to continue?')

        if confirmation == False:
            self.show_pick_list()
            return


    if (self.basic_adv == 'basic'):
        data_list = self.b_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.b_tree.selected_line_numbers()[0]
    else:
        data_list = self.a_tree.selected_line_data()
        if len(data_list) < 1:
            tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
            return
        idx = self.a_tree.selected_line_numbers()[0]

    if idx == None:
        tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
        return

    spec = self.spec_list[idx]
    #spec = s.selected_spectrum()
    view = self.get_view(spec)

    self.set_import_dist()
    self.set_import_drop()
    self.integration_check()

    spec_peaks = spec.peak_list()
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
        self.top.update()
        new_peak_list = peaks[i].split()[1:-1]   # also removes the first and last columns from the peak list file
        new_peak_tuple = tuple(float(e) for e in new_peak_list)
        new_peak = tuple(map(lambda i, j: i + j, new_peak_tuple, spec.scale_offset))

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
                if self.integration_radio.get() == '1':
                    pk.fit(view)
#                else:
#                    pk.selected = 1
#                    self.session.command_characters("pi")

    if self.integration_radio.get() == '2':
        for p in spec.peak_list():
            p.selected = 1
        self.session.command_characters("pi")
        for p in spec.peak_list():
            p.selected = 0

    status.config(text="Status: Importing the peaks is completed.")
    status.update()

    print('\nImport Completed! ' + str(placed_peaks) + ' new peaks are placed on the spectrum.')
    tkMessageBox.showinfo(title='Import Completed!', message=str(placed_peaks) + ' peaks are placed on the spectrum.')

    #self.session.command_characters('lt')
    time.sleep(0.3)     # a delay is needed for the peak list to update
    self.show_pick_list()    # show _our_ peak list instead of the default one



#####################################################################################

class groupfit_dialog(tkutil.Dialog, tkutil.Stoppable):

  def __init__(self, session):

    self.session = session
    tkutil.Dialog.__init__(self, session.tk, 'Group fit')

    main_frame = tk.Frame(self.top, )
    main_frame.pack(side='top', fill='both', expand=1, padx=10, pady=10)

    instruction_label = tk.Label(main_frame, justify='left',
                                 text="Please open the Integration tool (two-letter-code it) for \neach experiment (select the spectra window and type \"it\") \nand then change the setting based on the picture below. \nYou need to repeat this for each experiment.")
    instruction_label.pack(side='top', anchor='w', pady=(0,20))

    #from PIL import ImageTk, Image
    #results in:
    #ImportError: The _imaging C module is not installed

    widget = tk.Label(main_frame, compound='top')
    widget.image = tk.PhotoImage(file=os.path.join(IPICK_PATH, 'fit.png'))
    widget['image'] = widget.image
    widget.pack()
    tkutil.create_hint(widget, 'This is a picture of the settings you need to apply')

    close_instruction_label = tk.Label(main_frame, justify='left',
                                       text="You can close this window when you applied the changes \nin each Integration tool window.\n\nNote: the fitting process can take a long time when there \nare many peaks in your experiment.")
    close_instruction_label.pack(side='top', anchor='w', pady=(15,5))

    close_button = tk.Button(main_frame, text='Close', command=self.close_cb)
    close_button.pack(side='top', pady=(5,10))



#####################################################################################


class peak_list_dialog(tkutil.Dialog, tkutil.Stoppable):

  def __init__(self, session):

    self.session = session
    self.title = 'Peak List'
    self.spectrum = None
    self.peaks = ()
    self.settings = peak_list_settings()

    tkutil.Dialog.__init__(self, session.tk, self.title)

    self.pl = sputil.peak_listbox(self.top)
    self.pl.frame.pack(side = 'top', fill = 'both', expand = 1)
    self.pl.listbox['selectmode'] = 'extended'
    self.pl.listbox.bind('<ButtonRelease-1>', self.peak_selected)
    self.pl.listbox.bind('<ButtonRelease-2>', self.pl.goto_peak_cb)
    self.pl.listbox.bind('<Double-ButtonRelease-1>', self.pl.goto_peak_cb)
    self.peak_list = self.pl

    progress_label = tk.Label(self.top, anchor = 'nw')
    progress_label.pack(side = 'top', anchor = 'w')

    br = tkutil.button_row(self.top,
			   ('Update', self.update_cb),
			   ('Setup...', self.setup_cb),
			   ('Sort by height', self.sort_cb),
			   ('Sort by Reliability Score', self.sort_rs),
			   )
    br.frame.pack(side = 'top', anchor = 'w')

    rs_frame = tk.Frame(self.top)
    rs_frame.pack(anchor = 'w')

#    br2 = tkutil.button_row(rs_frame,
#			   ('Sort by height', self.sort_cb),
#			   #('Remove peaks with Reliability Score of 0', self.remove_rs0),
#			   )
#    br2.frame.pack(side = 'left', anchor = 'w')

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
    cv_frame.pack(anchor = 'w')

    cv = tkutil.button_row(cv_frame,
			   ('Cross-Validation Module', self.run_xcheck),
			   ('Save...', self.peak_list.save_cb),
			   ('Stop', self.stop_cb),
			   ('Close', self.close_cb),
               ('Help', sputil.help_cb(session, 'PeakListPython')),
			   )
    cv.frame.pack(side = 'left', anchor = 'w')

    tkutil.create_hint(cv.buttons[0], 'Use the Cross-Validation tool for removing noise peaks')
    tkutil.create_hint(cv.buttons[1], 'Save the Peak List data as being shown')

    keypress_cb = pyutil.precompose(sputil.command_keypress_cb, session)
    self.pl.listbox.bind('<KeyPress>', keypress_cb)

    tkutil.Stoppable.__init__(self, progress_label, cv.buttons[2])

  # ---------------------------------------------------------------------------
  #
  def run_xcheck(self, *args):

    try:
        import xcheck
        xcheck.show_xcheck_dialog(self.session)

    except:
        print('Could not find Cross Validation module to import')
        tkMessageBox.showwarning(title='Error', message='Could not find Cross Validation module!')

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

    confirmation = tkMessageBox.askyesno(title='Remove peaks?',
             message='Do you want to remove peaks with ABSOLUTE Reliability Score of ' + str(threshold) + ' and less?')

    if confirmation == True:
        for peak in peaks:
            if peak.is_assigned == 1:
            # we won't delete a peak that the user has assigned
                continue

            if abs(reliability_score(peak)) <= threshold:
                peak.selected = 1
                self.session.command_characters("")
                delete_count += 1

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

    line = str(rank + 1)  #default is ''
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
  def title(self, dim): return 'Reliability Score'
  def size(self, dim): return 10 * dim
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

    fb = tk.Frame(self.top, borderwidth = 3, relief = 'groove')
    fb.pack(side = 'top', fill = 'x')

    #
    # Create the checkbutton and Manual Coefficients section
    #
    self.field_widgets = {}
    for fc in field_classes:
      self.field_widgets[fc] = fc.field_widgets(self.top, fc.name)


    opt = tk.Frame(self.top, borderwidth = 3, relief = 'groove')
    opt.pack(side = 'top', fill = 'x')

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
    br.frame.pack(side = 'top', anchor = 'w')


  # ---------------------------------------------------------------------------
  #
  def show_coeff_settings(self):
    if manual_coeff.get():
        coeff1.frame.pack(side='top', anchor = 'w')
        coeff2.frame.pack(side='top', anchor = 'w')
        coeff3.frame.pack(side='top', anchor = 'w')
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


# -----------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def show_ipick_dialog(session):
  sputil.the_dialog(ipick_dialog, session).show_window(1)
