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
import copy

LOG_PATH = '/tmp/'
IPICK_PATH = '/home/samic/MyWorks/CODES/iPick/'

sys.path.append(IPICK_PATH)
try:
    import iPick
except ImportError:
    print('Could not find iPick')


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


    self.b_tree = tkutil.scrolling_list(b_topfrm, 'Select the spectrum for pick peaking:', 5, True)
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


    self.a_tree = tkutil.scrolling_list(a_topfrm, 'Select the spectrum for pick peaking:', 5, True)
    self.a_tree.listbox['selectmode'] = 'single'
    #self.a_tree.listbox['xscrollcommand'] = None
    self.a_tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.a_tree.heading.config(font=('Courier', 5))
    #self.a_tree.heading['font'] = ('normal')
    self.a_tree.frame.pack(side='top', fill='both', expand=1, pady=10)


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



    self.a_noise_button = Tkinter.Button(a_midfrm, text='Find Noise Level', command=self.noise_level)
    self.a_noise_button.pack(side='left', padx=20)

    self.a_noise = tkutil.entry_field(a_midfrm, 'Noise Level: ', width=16)
    self.a_noise.entry.bind('<Return>', self.noise_level)
    self.a_noise.frame.pack(side='top', fill='x', expand=1)



    self.a_contour_button = Tkinter.Button(a_midfrm, text='Find Contour Level', command=self.contour_level)
    #self.a_contour_button.pack(side='left', padx=20)

    self.a_contour = tkutil.entry_field(a_midfrm, 'Contour Level: ', width=12)
    self.a_contour.entry.bind('<Return>', self.contour_level)
    #self.a_contour.frame.pack(side='top', fill='x', expand=1)



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



    self.a_res = tkutil.entry_field(a_midfrm_res, 'Resolution: ', width=3, initial='1')
    self.a_res.entry.bind('<Return>', self.set_resolution)
    self.a_res.frame.pack(side='left', fill='x', expand=1)


    self.a_import_dis = tkutil.entry_field(a_midfrm_res, 'Import Dist.: ', width=3, initial='.1')
    self.a_import_dis.entry.bind('<Return>', self.set_import_dist)
    self.a_import_dis.frame.pack(side='left')

    self.a_import_drop = tkutil.entry_field(a_midfrm_res, 'Drop: ', width=3, initial='.01')
    self.a_import_drop.entry.bind('<Return>', self.set_import_drop)
    self.a_import_drop.frame.pack(side='left', padx=(2,10))



    a_ipick_button = Tkinter.Button(a_btmfrm, text='Run iPick', font=('bold'),
                                  height=1, width=10, command=self.run_ipick)
    a_ipick_button.pack(side='top', pady=18)




    # import frame
    a_import_frm = Tkinter.Frame(a_btmfrm)
    a_import_frm.pack(side='top', fill='both', expand=1)


    a_import_label = Tkinter.Label(a_import_frm, text="Import peaks:")
    a_import_label.pack(side='left')

    self.a_check_import = Tkinter.BooleanVar()
    self.a_check_import.set(True)
    a_checkbox_import = Tkinter.Checkbutton(a_import_frm, highlightthickness=0, text='Automatically',
                                            variable=self.a_check_import, command=self.import_check)
    a_checkbox_import.pack(side='left', anchor='w')

    self.a_import_button = Tkinter.Button(a_import_frm, text='Manual import', command=self.place_peaks)




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
      self.basic_adv = 'basic'



  def adv_frame_show(self):
      self.basic_frame.pack_forget()
      self.adv_frame.pack(side='bottom', fill='both', expand=1)
      self.basic_adv = 'adv'



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
            self.a_import_button.pack(side='left', padx=15)



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

    self.set_import_dist()
    self.set_import_drop()

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
            spec.place_peak(new_peak)
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
            spec.place_peak(new_peak)
            placed_peaks += 1


        #if spec.dimension == 2:
        #    spec.place_peak(new_peak)


    print('\nImport Completed! ' + str(placed_peaks) + ' new peaks are placed on the spectrum.')
    self.session.command_characters('lt')
    tkMessageBox.showinfo(title='Import Completed!', message=str(placed_peaks) + ' peaks are placed on the spectrum.')



def show_ipick_dialog(session):
  sputil.the_dialog(ipick_dialog, session).show_window(1)
