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
  import tkinter.font as tkFont

try:
  import sparky
  from sparky import sputil, tkutil, pyutil
except:
  import poky
  from poky import sputil, tkutil, pyutil

import peak_list_dialog
import xcheck

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
    self.auto_integration = True
    self.spectrum = None
    self.previous_spectrum = None
    self.last_PEAKLIST_FILE = None
    self.spectrum_list_selection = None


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
    radio_button1 = tk.Radiobutton(radio_frame, text="Basic ", highlightthickness=0,
                                        variable=self.basic_advanced, value='1', command=self.basic_frame_show)
    radio_button1.pack(side='left')

    radio_button2 = tk.Radiobutton(radio_frame, text="Advanced", highlightthickness=0,
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

    # buttons
    b_buttons_frm1 = tk.Frame(self.basic_frame)
    b_buttons_frm1.pack(fill='both', expand=1, padx=(20,0), pady=(30,2))
    
    b_buttons_frm2 = tk.Frame(self.basic_frame)
    b_buttons_frm2.pack(fill='both', expand=1, padx=(20,0), pady=(0,30))

    # output
    b_btmfrm = tk.Frame(self.basic_frame)
    b_btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    self.b_tree = tkutil.scrolling_list(b_list_frm, 'Select a spectrum for pick peaking:', 5, True)
    self.b_tree.listbox['selectmode'] = 'extended'
    #self.b_tree.listbox['xscrollcommand'] = None
    self.b_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.b_tree.heading.config(font=('Courier', 5))
    #self.b_tree.heading['font'] = ('normal')
    self.b_tree.frame.pack(side='top', fill='both', expand=1, pady=(5,10))


    b_import_label = tk.Label(b_import_frm, text="Import peaks:")
    b_import_label.pack(side='left', padx=8)

    self.b_check_import = tk.BooleanVar()
    self.b_check_import.set(True)
    b_checkbox_import = tk.Checkbutton(b_import_frm, highlightthickness=0, text='Automatically',
                                            variable=self.b_check_import, command=self.import_check)
    b_checkbox_import.pack(side='left', anchor='w')

    self.b_import_button = tk.Button(b_import_frm, text='Manual import', command=self.place_peaks)

    tkutil.create_hint(b_checkbox_import, 'This setting will import all found peaks automatically when the program is done')
    tkutil.create_hint(self.b_import_button, 'You can use the manual import after the peak picking is done')


    b_ipick_button = tk.Button(b_buttons_frm1, text='Run iPick', width=22, command=self.run_ipick_multi)
    b_ipick_button.pack(side='left')
    tkutil.create_hint(b_ipick_button, 'Runs the peak picking algorithm. May take a few minutes to complete')

    update_button = tk.Button(b_buttons_frm1, text='Update List', width=10, command=self.update_tree)
    update_button.pack(side='left', anchor='w', expand=0)

    self.b_stop_button = tk.Button(b_buttons_frm1, text='Stop', command=self.stop_button)
    self.b_stop_button.pack(side='left')
    tkutil.create_hint(self.b_stop_button, 'Stops any processing')

   
    b_xcheck_button = tk.Button(b_buttons_frm2, text='Cross-Validation', width=22, command=self.run_xcheck)
    b_xcheck_button.pack(side='left')
    tkutil.create_hint(b_xcheck_button, 'Opens the Cross-Validation module for investigating the peaks / finding noise peaks')

    b_ipick_button = tk.Button(b_buttons_frm2, text='Peak List', width=10, command=self.show_peak_list)
    b_ipick_button.pack(side='left')
    tkutil.create_hint(b_ipick_button, 'Opens the Peak List for the selected spectrum')


#TODO: Add the section for iPick to the extensions.html file
    help_button = tk.Button(b_buttons_frm2, text='Help', command=sputil.help_cb(session, 'iPick'))
    help_button.pack(side='left')
    tkutil.create_hint(help_button, 'Opens a help page with more information about this module.')

    b_progress_label = tk.Label(b_buttons_frm2)
    b_progress_label.pack(side='left', anchor='w')

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
    self.nois_cont.set('2')

    radio_cont = tk.Radiobutton(a_nois_cont_frm, text="Contour Level", highlightthickness=0,
                                        variable=self.nois_cont, value='2', command=self.noise_or_contour)
    radio_cont.pack(side='left')

    radio_nois = tk.Radiobutton(a_nois_cont_frm, text="Noise Level", highlightthickness=0,
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

    radio_pos = tk.Radiobutton(a_pos_neg_frm, text="Positive peaks", highlightthickness=0,
                                        variable=self.pos_neg, value='1')
    radio_pos.pack(side='left')

    radio_neg = tk.Radiobutton(a_pos_neg_frm, text="Negative peaks", highlightthickness=0,
                                        variable=self.pos_neg, value='-1')
    radio_neg.pack(side='left')
    radio_both = tk.Radiobutton(a_pos_neg_frm, text="Both", highlightthickness=0,
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
    self.a_check_integration.set(True)
    a_checkbox_integration = tk.Checkbutton(a_integration_frm, highlightthickness=0, text='Auto Integration',
                                            variable=self.a_check_integration, command=self.integration_check)
    a_checkbox_integration.pack(side='left', anchor='w', padx=(30,0))
    tkutil.create_hint(a_checkbox_integration, 'Performs integration fitting on all peaks and opens a "Peak List" window so that you can examine them')



    # integration_radio frame
    self.a_integration_radio_frm = tk.Frame(a_postpro_frm)
    #a_integration_radio_frm.pack(side='top', fill='both', expand=1, pady=(10,0), padx=10)

    integration_radio_label = tk.Label(self.a_integration_radio_frm, text="Integration mode:")
    integration_radio_label.pack(side='left', fill='both')
    self.integration_radio = tk.StringVar()
    self.integration_radio.set('1')
    integration_radio_button1 = tk.Radiobutton(self.a_integration_radio_frm, text="Individual fit", highlightthickness=0,
                                        variable=self.integration_radio, value='1')
    integration_radio_button1.pack(side='left')
    tkutil.create_hint(integration_radio_button1, 'Each peak will be fitted individually not considering the neighbor peaks')

    integration_radio_button2 = tk.Radiobutton(self.a_integration_radio_frm, text="Group fit", highlightthickness=0,
                                        variable=self.integration_radio, value='2', command=self.groupfit_selected)
    integration_radio_button2.pack(side='left')
    tkutil.create_hint(integration_radio_button2, 'Peaks will be fitted as a group by considering the neighbor peaks')

    integration_option_button = tk.Button(self.a_integration_radio_frm, text='Options', font=buttonFont, command=self.open_integration_options)
    integration_option_button.pack(side='left', padx=(5,0))

    self.a_integration_radio_frm.pack(side='top', fill='both', expand=1, pady=(5,0), padx=5)

    # separator
    #sep = tk.Frame(a_btmfrm, height=2, bd=1, relief="ridge")
    #sep.pack(fill="both", padx=5, pady=(5,12), side='top')


    # buttons frames
    a_buttons_frm1 = tk.Frame(a_btmfrm)
    a_buttons_frm1.pack(fill='both', expand=1, padx=(15,0), pady=(10,2))

    a_buttons_frm2 = tk.Frame(a_btmfrm)
    a_buttons_frm2.pack(fill='both', expand=1, padx=(15,0), pady=(0,10))
    

    a_ipick_button = tk.Button(a_buttons_frm1, text='Run iPick', width=22, command=self.run_ipick)
    a_ipick_button.pack(side='left')
    tkutil.create_hint(a_ipick_button, 'Runs the peak picking algorithm. May take a few minutes to complete')

    a_update_button = tk.Button(a_buttons_frm1, text='Update List', width=10, command=self.update_tree)
    a_update_button.pack(side='left', anchor='w', expand=0)

    self.a_stop_button = tk.Button(a_buttons_frm1, text='Stop', command=self.stop_button)
    self.a_stop_button.pack(side='left')
    tkutil.create_hint(self.a_stop_button, 'Stops any processing')
    

    a_xcheck_button = tk.Button(a_buttons_frm2, text='Cross-Validation', width=22, command=self.run_xcheck)
    a_xcheck_button.pack(side='left')
    tkutil.create_hint(a_xcheck_button, 'Opens the Cross-Validation module for investigating the peaks / finding noise peaks')

    a_ipick_button = tk.Button(a_buttons_frm2, text='Peak List', width=10, command=self.show_peak_list)
    a_ipick_button.pack(side='left')
    tkutil.create_hint(b_ipick_button, 'Open the Peak List for the selected spectrum')


    a_help_button = tk.Button(a_buttons_frm2, text='Help', command=sputil.help_cb(session, 'iPick'))
    a_help_button.pack(side='left')
    tkutil.create_hint(a_help_button, 'Opens a help page with more information about this module.')

    a_progress_label = tk.Label(a_buttons_frm2)
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
    self.top.bind('<ButtonRelease-1>', self.refocus_spec_list)



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
  def refocus_spec_list(self, *args):
    if self.spectrum_list_selection == None:
        return

    if (self.basic_adv == 'basic'):
        widget = self.b_tree
    else:
        widget = self.a_tree

    widget.listbox.select_clear(0, "end")
    widget.listbox.selection_set(self.spectrum_list_selection)
    widget.listbox.see(self.spectrum_list_selection)
    widget.listbox.activate(self.spectrum_list_selection)
    widget.listbox.selection_anchor(self.spectrum_list_selection)


# ---------------------------------------------------------------------------
  def open_integration_options(self):
    self.session.command_characters('it')


# ---------------------------------------------------------------------------
  def groupfit_selected(self, *args):
    d = groupfit_dialog(self.session)
    d.show_window(1)


# ---------------------------------------------------------------------------
  def show_peak_list(self, *args):
      if self.spectrum == None:
        tkMessageBox.showwarning(title='Error', message='You need to select a spectrum first!')
        return
      try:
        getattr(self.session, 'spectrum_dialogs')
      except:
        self.session.spectrum_dialogs = {}
      dialogs = self.session.spectrum_dialogs
      if (self.spectrum in dialogs and \
          not dialogs[self.spectrum].is_window_destroyed()):
        dialogs[self.spectrum].show_window(1)
      else:
        d = peak_list_dialog.peak_list_dialog(self.session)
        d.show_window(1)
        d.settings.show_fields('Assignment', 'Chemical Shift', 'Reliability Score')
        d.show_spectrum_peaks(self.spectrum)
        dialogs[self.spectrum] = d
        d.sort_reliability()
   

# ---------------------------------------------------------------------------
  #
  def run_xcheck(self, *args):

    xcheck.show_xcheck_dialog(self.session)


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
            self.a_integration_radio_frm.pack(side='top', fill='both', expand=1, pady=(5,0), padx=5)
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

    widget.config(text="Status: Spectrum selected.")
    widget.update()

    if len(data_list) > 1:
        self.spectrum_list_selection = None
    else:
        self.spectrum_list_selection = idx

    if idx == None:
        tkMessageBox.showwarning(title='Error', message='The spectrum was not selected!')
        return

    # print(self.spec_list[idx].data_path)

    self.spectrum = self.spec_list[idx]
    views = self.session.project.view_list()
    for v in views:
        if v.name == self.spectrum.name:
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
    else:
        widget = self.a_status

    if self.spectrum == None:
        tkMessageBox.showwarning(title='Error', message='You need to select a spectrum first!')
        return

    widget.config(text="Status: Noise level found.")
    widget.update()

    UCSF_FILE = self.spectrum.data_path

    #reload(iPick)
    self.noise = iPick.get_noise_level(UCSF_FILE)

    self.a_noise.variable.set(self.noise)

    #print(self.a_noise.variable.get())


# ---------------------------------------------------------------------------
  def contour_level(self):

    if self.spectrum == None:
        tkMessageBox.showwarning(title='Error', message='You need to select a spectrum first!')
        return

    if (self.pos_neg.get() == '1'):
        self.a_contour.variable.set(self.pos_contour)

    elif (self.pos_neg.get() == '2'):
        self.a_contour.variable.set(self.neg_contour)

    else:
        self.a_contour.variable.set(self.pos_contour)
#TODO: this is only considering the pos peaks


# ---------------------------------------------------------------------------
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
            " -i " + "\"" + UCSF_FILE + "\"" +
            " -o " + "\"" + self.PEAKLIST_FILE + "\"" +
            " -r " + self.resolution +
            " -c " + CPUs +
            " --sign " + self.pos_neg.get() +
            " --overwrite")


    if (self.nois_cont.get() == '1'):
        # using noise level
        cmd = (PYTHON_BIN + " " + os.path.join(IPICK_PATH, "iPick.py") +
                " -i " + "\"" + UCSF_FILE + "\"" +
                " -o " + "\"" + self.PEAKLIST_FILE + "\"" +
                " -r " + self.resolution +
                " -c " + CPUs +
                " --sign " + self.pos_neg.get() +
                " --threshold " + self.a_noise.variable.get() +
                " --overwrite")


    elif (self.nois_cont.get() == '2'):
        # using contour level
        cmd = (PYTHON_BIN + " " + os.path.join(IPICK_PATH, "iPick.py") +
               " -i " + "\"" + UCSF_FILE + "\"" +
               " -o " + "\"" + self.PEAKLIST_FILE + "\"" +
               " -r " + self.resolution +
               " -c " + CPUs +
               " --sign " + self.pos_neg.get() +
               " --threshold " + self.a_contour.variable.get() +
               " --overwrite")

    print(cmd)

    if OS_WINDOWS:
        self.proc = subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
    else:
        self.proc = subprocess.Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True, preexec_fn=os.setsid)


# ---------------------------------------------------------------------------
  def run_ipick_multi(self):
    """ Running the iPick for multiple selections at once """
    data_list = self.b_tree.selected_line_data()
    if len(data_list) < 1:
        tkMessageBox.showwarning(title='Error', message='No spectrum was selected!')
        return

    for spec_id in self.b_tree.selected_line_numbers():
        self.spectrum = self.spec_list[spec_id]
        views = self.session.project.view_list()
        for v in views:
            if v.name == self.spectrum.name:
                v.got_focus()
                self.pos_contour = v.positive_levels.lowest
                self.neg_contour = v.negative_levels.lowest
                break
        self.contour_level()
        self.run_ipick()


# ---------------------------------------------------------------------------
  def run_ipick(self):

    if (self.basic_adv == 'basic'):
        widget = self.b_status
    else:
        widget = self.a_status
    widget.config(text="Status: iPick is running ...")
    widget.update()

    if self.spectrum == None:
        tkMessageBox.showwarning(title='Error', message='You need to select a spectrum first!')
        return

    if self.previous_spectrum == self.spectrum:
        confirmation = tkMessageBox.askokcancel(title='Re-run iPick?',
             message='You have already run iPick for this experiment. Do you want to run it again?')

        if confirmation == False:
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

    UCSF_FILE = self.spectrum.data_path


    try:

        self.find_peaklist_file()

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

        widget.config(text="Status: Peak list file is corrupted.")
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
            widget.config(text="Status: Peak picking is done.")
            widget.update()

            print('Found peaks are also stored in "' + self.PEAKLIST_FILE + '" file.')

            #tkMessageBox.showinfo(title='Job Done!', message='Peak picking is finished!')


            if ((self.basic_adv == 'basic') and self.b_check_import.get()) or \
               ((self.basic_adv == 'adv') and self.a_check_import.get()):
                    self.stoppable_call(self.place_peaks)

    self.stopped_flag = 0
    self.a_stop_button['state'] = 'disabled'
    self.b_stop_button['state'] = 'disabled'

    self.previous_spectrum = self.spectrum


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
  def find_peaklist_file(self):
  
    UCSF_FILE = self.spectrum.data_path

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


# ---------------------------------------------------------------------------
  def place_peaks(self):
    if (self.basic_adv == 'basic'):
        status = self.b_status
    else:
        status = self.a_status
    status.config(text="Status: Importing the peaks (0%)")
    status.update()

    self.find_peaklist_file()
    
    try:
        print("Importing the peaks from: " + self.PEAKLIST_FILE)
    except:
        tkMessageBox.showwarning(title='Error', message='You need to run iPick first!')
        return

    if self.last_PEAKLIST_FILE == self.PEAKLIST_FILE:
        confirmation = tkMessageBox.askokcancel(title='Continue?',
             message='You have already imported these peaks. Do you want to import them again?')
        if confirmation == False:
            self.show_peak_list()
            return

    peaks = open(self.PEAKLIST_FILE, 'r').readlines()
    if len(peaks) < 4:
        tkMessageBox.showwarning(title='Error', message='Peak list file is empty!')
        return


    if len(peaks) > 5000:
        confirmation = tkMessageBox.askokcancel(title='Continue?',
             message='iPick will try to import ' + str(len(peaks)) + ' peaks. This can take a long time. Do you want to continue?')
        if confirmation == False:
            self.show_peak_list()
            return

    if self.spectrum == None:
        tkMessageBox.showwarning(title='Error', message='You need to select a spectrum first!')
        return

    #spec = s.selected_spectrum()
    view = self.get_view(self.spectrum)

    self.set_import_dist()
    self.set_import_drop()
    self.integration_check()

    spec_peaks = self.spectrum.peak_list()
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
        new_peak = tuple(map(lambda i, j: i + j, new_peak_tuple, self.spectrum.scale_offset))

        new_peak_flag = True

        if spec_peaks == []:
            pk = self.spectrum.place_peak(new_peak)
            placed_peaks += 1
            if self.auto_integration:
                pk.fit(view)
            continue

        print('\nNew peak #' + str(i-1) + ' from ' + str(len(peaks)-2))
        percent = "{:2.0f}".format(100 * (i-1) / len(peaks)-2)
        status.config(text="Status: Importing the peaks (" + percent + "%)")
        status.update()

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

                    #print self.spectrum.data_height((117.6,5.2,8.13))
                    midpoint_height = self.spectrum.data_height(self.mid_point(exis_peak.frequency, new_peak))

                    new_peak_height = self.spectrum.data_height(new_peak)
                    exis_peak_height = self.spectrum.data_height(exis_peak.frequency)

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
            pk = self.spectrum.place_peak(new_peak)
            placed_peaks += 1

            if self.auto_integration:
                if self.integration_radio.get() == '1':
                    pk.fit(view)
#                else:
#                    pk.selected = 1
#                    self.session.command_characters("pi")

    if self.integration_radio.get() == '2':
        for p in self.spectrum.peak_list():
            p.selected = 1
        self.session.command_characters("pi")
        for p in self.spectrum.peak_list():
            p.selected = 0

    status.config(text="Status: Importing the peaks is completed.")
    status.update()

    print('\nImport Completed! ' + str(placed_peaks) + ' new peaks are placed on the spectrum.')
    #tkMessageBox.showinfo(title='Import Completed!', message=str(placed_peaks) + ' peaks are placed on the spectrum.')

    #self.session.command_characters('lt')
    time.sleep(0.3)     # a delay is needed for the peak list to update
    self.show_peak_list()    # show _our_ peak list instead of the default one

    self.last_PEAKLIST_FILE = self.PEAKLIST_FILE



#####################################################################################

class groupfit_dialog(tkutil.Dialog, tkutil.Stoppable):

  def __init__(self, session):

    self.session = session
    tkutil.Dialog.__init__(self, session.tk, 'Group fit')

    main_frame = tk.Frame(self.top, )
    main_frame.pack(side='top', fill='both', expand=1, padx=10, pady=10)

    instruction_label = tk.Label(main_frame, justify='left',
                                 text="Please open the Integration tool (two-letter-code `it`) for \neach experiment (you can use the Options button) \nand then change the settings as follows. \nYou need to repeat this for each experiment.\n\n1. Change the Integration method to \"Pseudo-Voigt fit\"\n2. Un-check all the checkboxes.\n3. Check the \"Group peaks in contour boundary\".")
    instruction_label.pack(side='top', anchor='w', pady=(0,10))

    #from PIL import ImageTk, Image
    #results in:
    #ImportError: The _imaging C module is not installed

#    widget = tk.Label(main_frame, compound='top')
#    widget.image = tk.PhotoImage(file=os.path.join(IPICK_PATH, 'fit.png'))
#    widget['image'] = widget.image
#    widget.pack()
#    tkutil.create_hint(widget, 'This is a picture of the settings you need to apply')

    close_instruction_label = tk.Label(main_frame, justify='left',
                                       text="You can close this window when you applied the changes \nin each Integration tool window.\n\nNote: the fitting process can take a long time when there \nare many peaks in your experiment.")
    close_instruction_label.pack(side='top', anchor='w', pady=(15,5))

    close_button = tk.Button(main_frame, text='Close', command=self.close_cb)
    close_button.pack(side='top', pady=(5,10))


# -----------------------------------------------------------------------------
# ---------------------------------------------------------------------------
def show_ipick_dialog(session):
  sputil.the_dialog(ipick_dialog, session).show_window(1)
