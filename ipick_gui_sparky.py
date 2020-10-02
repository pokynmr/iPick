# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
iPick GUI for Sparky

@author: Mehdi Rahimi
"""

import Tkinter
import sparky
import sputil
import tkutil
import tkFont
from os import path, popen, remove, system
import subprocess
import time
import tkMessageBox
import sys
import os

IPICK_PATH = '/home/samic/MyWorks/CODES/iPick/'
sys.path.append(IPICK_PATH)
try:
    import iPick
except ImportError:
    print('Could not fild iPick')


class ipick_dialog(tkutil.Dialog, tkutil.Stoppable):
  def __init__(self, session):

    #print(os.getcwd())

    # prepare temp files
    if path.exists('/tmp/process.log'):
        remove('/tmp/process.log')

    if path.exists('done'):
        remove('done')

    open('/tmp/process.log', 'w').write('')


    self.session = session
    self.resolution = 1

    tkutil.Dialog.__init__(self, session.tk, 'iPick')


    ipick_label = Tkinter.Label(self.top, text="Integrated UCSF Peak Picker v1", font=20)
    ipick_label.pack(side='top', fill='both', expand=1, pady=30)



# main frames

    radio_frame = Tkinter.Frame(self.top)
    radio_frame.pack(side='top', fill='both', expand=1, padx=8, pady=5)

    self.basic_frame = Tkinter.Frame(self.top)
    self.basic_frame.pack(side='bottom', fill='both', expand=1)

    self.adv_frame = Tkinter.Frame(self.top)
    self.adv_frame.pack(side='bottom', fill='both', expand=1)



# radiobutton basic / advanced

    radio_label = Tkinter.Label(radio_frame, text="Select the operating mode:")
    radio_label.pack(side='left', fill='both')

    basic_adv = Tkinter.IntVar()
    #basic_adv.set(1)
    radio_button1 = Tkinter.Radiobutton(radio_frame, text="Baisc ", highlightthickness = 0,
                                        variable=basic_adv, value=1, command=self.basic_frame_show)

    radio_button1.pack(side='left')

    radio_button2 = Tkinter.Radiobutton(radio_frame, text="Advanced", highlightthickness = 0,
                                        variable=basic_adv, value=2, command=self.adv_frame_show)
    radio_button2.pack(side='left')

    radio_button1.select()



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


    self.b_tree = tkutil.scrolling_list(b_topfrm, 'Select the spectra for pick peaking:', 5, True)
    self.b_tree.listbox['selectmode'] = 'single'
    #self.b_tree.listbox['xscrollcommand'] = None
    self.b_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.b_tree.heading.config(font=('Courier', 5))
    #self.b_tree.heading['font'] = ('normal')
    self.b_tree.frame.pack(side='top', fill='both', expand=1, pady=10)


    #update_button = Tkinter.Button(b_btmfrm, text='Update List', command=self.update_tree)
    #update_button.pack(side='top', anchor='w', expand=0, pady=(0, 5))


    b_ipick_button = Tkinter.Button(b_btmfrm, text='Run iPick', font=('bold'), 
                                  height=1, width=10, command=self.run_ipick)
    b_ipick_button.pack(side='top', pady=30)


    b_output_label = Tkinter.Label(b_btmfrm, text="Output progress:")
    b_output_label.pack(side='top', anchor='w')

    self.b_output = Tkinter.Text(b_btmfrm, width=50, height=15)
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

    # noise button & noise
    a_midfrm = Tkinter.Frame(self.adv_frame)
    a_midfrm.pack(fill='both', expand=1, padx=8, pady=5)

    # noise contour
    a_midfrm_nois_cont = Tkinter.Frame(self.adv_frame)
    a_midfrm_nois_cont.pack(fill='both', expand=1, padx=8, pady=8)

    # pos neg peaks
    a_midfrm_pos_neg = Tkinter.Frame(self.adv_frame)
    a_midfrm_pos_neg.pack(fill='both', expand=1, padx=8, pady=8)

    # resolution
    a_midfrm_res = Tkinter.Frame(self.adv_frame)
    a_midfrm_res.pack(fill='both', expand=1, padx=8, pady=8)

    # ipick button & output
    a_btmfrm = Tkinter.Frame(self.adv_frame)
    a_btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    self.a_tree = tkutil.scrolling_list(a_topfrm, 'Select the spectra for pick peaking:', 5, True)
    self.a_tree.listbox['selectmode'] = 'single'
    #self.a_tree.listbox['xscrollcommand'] = None
    self.a_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.a_tree.heading.config(font=('Courier', 5))
    #self.a_tree.heading['font'] = ('normal')
    self.a_tree.frame.pack(side='top', fill='both', expand=1, pady=10)


    #a_update_button = Tkinter.Button(a_btmfrm, text='Update List', command=self.update_tree)
    #a_update_button.pack(side='top', anchor='w', expand=0, pady=(0, 5))


    a_noise_button = Tkinter.Button(a_midfrm, text='Select Noise Level', command=self.noise_level)
    a_noise_button.pack(side='left', padx=20)


    self.a_noise = tkutil.entry_field(a_midfrm, 'Noise Level: ', width=15)
    self.a_noise.entry.bind('<Return>', self.noise_level)
    self.a_noise.frame.pack(side='top', fill='x', expand=1)



    nois_cont_label = Tkinter.Label(a_midfrm_nois_cont, text="Use:")
    nois_cont_label.pack(side='left', fill='both')
    nois_cont = Tkinter.IntVar()
    #nois_cont.set(1)
    radio_nois = Tkinter.Radiobutton(a_midfrm_nois_cont, text="Noise Level", highlightthickness = 0,
                                        variable=nois_cont, value=1, command=self.noise_or_contour)
    radio_nois.pack(side='left')

    radio_cont = Tkinter.Radiobutton(a_midfrm_nois_cont, text="Contour Level", highlightthickness = 0,
                                        variable=nois_cont, value=2, command=self.noise_or_contour)
    radio_cont.pack(side='left')
    radio_nois.select()




    pos_neg_label = Tkinter.Label(a_midfrm_pos_neg, text="Select:")
    pos_neg_label.pack(side='left', fill='both')
    pos_neg = Tkinter.IntVar()
    #pos_neg.set(1)
    radio_pos = Tkinter.Radiobutton(a_midfrm_pos_neg, text="Positive peaks", highlightthickness = 0,
                                        variable=pos_neg, value=1, command=self.pos_neg_peaks)
    radio_pos.pack(side='left')

    radio_neg = Tkinter.Radiobutton(a_midfrm_pos_neg, text="Negative peaks", highlightthickness = 0,
                                        variable=pos_neg, value=2, command=self.pos_neg_peaks)
    radio_neg.pack(side='left')
    radio_both = Tkinter.Radiobutton(a_midfrm_pos_neg, text="Both", highlightthickness = 0,
                                        variable=pos_neg, value=3, command=self.pos_neg_peaks)
    radio_both.pack(side='left')
    radio_pos.select()



    self.a_res = tkutil.entry_field(a_midfrm_res, 'Resolution: ', width=10, initial='1')
    self.a_res.entry.bind('<Return>', self.set_resolution)
    self.a_res.frame.pack(side='top', fill='x', expand=1)



    a_ipick_button = Tkinter.Button(a_btmfrm, text='Run iPick', font=('bold'), 
                                  height=1, width=10, command=self.run_ipick)
    a_ipick_button.pack(side='top', pady=20)


    a_output_label = Tkinter.Label(a_btmfrm, text="Output progress:")
    a_output_label.pack(side='top', anchor='w')

    self.a_output = Tkinter.Text(a_btmfrm, width=50, height=10)
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








# functions


  def basic_frame_show(self):
      self.adv_frame.pack_forget()
      self.basic_frame.pack(side='bottom', fill='both', expand=1)



  def adv_frame_show(self):
      self.basic_frame.pack_forget()
      self.adv_frame.pack(side='bottom', fill='both', expand=1)



  def set_resolution(self, *args):
      self.resolution = self.a_res.variable.get()



  def update_tree(self):
    if self.session.project == None: return

    self.b_tree.clear()
    self.a_tree.clear()

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    for spec in self.spec_list:
        self.b_tree.append(spec.name)
        self.a_tree.append(spec.name)



  def spectra_selected(self, *args):
    self.a_status.config(text="Status: Spectra selected. Check noise level!")
    self.a_status.update()
    self.b_status.config(text="Status: Spectra selected. Run iPick!")
    self.b_status.update()

    data_list = self.b_tree.selected_line_data()
    if len(data_list) < 1: return

    idx = self.b_tree.selected_line_numbers()[0]
    if idx == None: return

    spec = self.spec_list[idx]
    views = self.session.project.view_list()
    for v in views:
        if v.name == spec.name:
            v.got_focus()
            self.pos_contour = v.positive_levels
            self.neg_contour = v.negative_levels
            break



  def noise_level(self):
    data_list = self.a_tree.selected_line_data()
    if len(data_list) < 1: return

    idx = self.a_tree.selected_line_numbers()[0]
    if idx == None: return

    self.a_status.config(text="Status: Noise level found. Now run iPick!")
    self.a_status.update()

    UCSF_FILE = self.spec_list[idx].data_path

    #reload(iPick)
    self.noise = iPick.get_noise_level(UCSF_FILE)
    self.a_noise.variable.set(self.noise)

    #print(self.a_noise.variable.get())



#TODO

  def pos_neg_peaks(self, *args):
    pass


  def noise_or_contour(self, *args):
    pass




  def ipick_process(self, UCSF_FILE):
    #Popen("python /home/samic/MyWorks/CODES/iPick/iPick.py -i " + UCSF_FILE + " -o peaks.list > process.log && touch done")

    cmd = ("python " + IPICK_PATH +
            "/iPick.py -i " + UCSF_FILE + 
            " -o peaks.list -R " + self.resolution + 
            " --overwrite && touch done")

    proc = subprocess.Popen([cmd], shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    #cmd = "python /home/samic/Desktop/test.py > process.log && touch done"
    #system(cmd)




  def run_ipick(self):
    data_list = self.b_tree.selected_line_data()
    if len(data_list) < 1: return

    idx = self.b_tree.selected_line_numbers()[0]
    if idx == None: return

    self.b_status.config(text="Status: iPick is running ...")
    self.b_status.update()

    self.set_resolution()

    UCSF_FILE = self.spec_list[idx].data_path

    try:

        if path.exists('peaks.list'):
            remove('peaks.list')

        self.ipick_process(UCSF_FILE)


        while True:
        #for i in range(20):
            log = open('/tmp/process.log', 'r')

            self.b_output.delete('1.0', Tkinter.END)
            self.b_output.insert(Tkinter.END, log.read())
            self.b_output.see(Tkinter.END)
            self.b_output.update()

            log.close()

            time.sleep(0.5)

            if path.exists('done'):
                try:
                    remove('done')
                except:
                    tkMessageBox.showinfo(title='Error', message='Could not delete "done" file')
   
                break


    except TypeError as e:
        self.b_status.config(text="Status: File is corrupted.")
        self.b_status.update()
        print(e)
        print(sys.exc_type)

    else:
        log = open('/tmp/process.log', 'r')

        self.b_output.delete('1.0', Tkinter.END)
        self.b_output.insert(Tkinter.END, log.read())
        self.b_output.see(Tkinter.END)
        self.b_output.update()

        log.close()

        remove('/tmp/process.log')

        self.b_status.config(text="Status: iPick is done.")
        self.b_status.update()
        
        print('Found peaks are also stored in "' + os.getcwd() + '/peaks.list" file.')

        tkMessageBox.showinfo(title='Job Done!', message='Found peaks are placed on the spectrum.')
        self.place_peaks()
        

        


  def place_peaks(self):
    peaks = open('peaks.list', 'r').readlines()
    if len(peaks) < 4: return


    data_list = self.b_tree.selected_line_data()
    if len(data_list) < 1: return

    idx = self.b_tree.selected_line_numbers()[0]
    if idx == None: return

    spec = self.spec_list[idx]
    #spec = self.session.selected_spectrum()

    for i in range(2, len(peaks)):
        peak = peaks[i].split()
        if spec.dimension == 2:
            spec.place_peak((float(peak[1]), float(peak[2])))
        elif spec.dimension == 3:
            spec.place_peak((float(peak[1]), float(peak[2]), float(peak[3])))
        elif spec.dimension == 4:
            spec.place_peak((float(peak[1]), float(peak[2]), float(peak[3]), float(peak[4])))

    self.session.command_characters('lt')
    


def show_ipick_dialog(session):
  sputil.the_dialog(ipick_dialog, session).show_window(1)


