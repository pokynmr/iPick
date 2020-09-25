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
import multiprocessing
import time
import tkMessageBox


class ipick_dialog(tkutil.Dialog, tkutil.Stoppable):
  def __init__(self, session):


    # prepare temp files
    if path.exists('process.log'):
        remove('process.log')

    if path.exists('peaks.list'):
        remove('peaks.list')

    if path.exists('done'):
        remove('done')

    open('process.log', 'w').write('')


    self.session = session
    tkutil.Dialog.__init__(self, session.tk, 'iPick')

    # listbox
    topfrm = Tkinter.Frame(self.top)
    topfrm.pack(side='top', fill='both', expand=0, padx=8)

    # noise button & noise
    midfrm = Tkinter.Frame(self.top)
    midfrm.pack(fill='both', expand=1, padx=8)

    # ipick button & output
    btmfrm = Tkinter.Frame(self.top)
    btmfrm.pack(side='bottom', fill='both', expand=1, padx=8)


    ipick_label = Tkinter.Label(topfrm, text="Integrated UCSF Peak Picker v1", font=20)
    ipick_label.pack(side='top', fill='both', expand=1, pady=30)


    self.tree = tkutil.scrolling_list(topfrm, 'Select the spectra for pick peaking:', 5, True)
    self.tree.listbox['selectmode'] = 'single'
    #self.tree.listbox['xscrollcommand'] = None
    self.tree.listbox.bind('<ButtonRelease-1>', self.spectra_selected)
    #self.tree.heading.config(font=('Courier', 5))
    #self.tree.heading['font'] = ('normal')
    self.tree.frame.pack(side='top', fill='both', expand=1, pady=10)


    #update_button = Tkinter.Button(btmfrm, text='Update List', command=self.update_tree)
    #update_button.pack(side='top', anchor='w', expand=0, pady=(0, 5))


    noise_button = Tkinter.Button(midfrm, text='Select Noise Level', command=self.noise_level)
    noise_button.pack(side='left', padx=20)


    self.noise = tkutil.entry_field(midfrm, 'Noise Level: ', width=10)
    self.noise.entry.bind('<Return>', self.noise_level)
    self.noise.frame.pack(side='top', fill='x', expand=1)


    ipick_button = Tkinter.Button(btmfrm, text='Run iPick', font=('bold'), 
                                  height=1, width=10, command=self.run_ipick)
    ipick_button.pack(side='top', pady=30)


    output_label = Tkinter.Label(btmfrm, text="Output progress:")
    output_label.pack(side='top', anchor='w')

    self.output = Tkinter.Text(btmfrm, width=50, height=20)
    self.output.pack(side='top', expand=1, fill='both', anchor='w')


    self.status = Tkinter.Label(btmfrm, text="Status: Ready!")
    self.status.pack(side='top', anchor='w', pady=5)


    # fix the fonts
    suggested_fonts = ['Arial', 'NotoSans', 'Ubuntu', 'SegoeUI', 'Helvetica',
                       'Calibri', 'Verdana', 'DejaVuSans', 'FreeSans']
    for fnt in suggested_fonts:
      if fnt in tkFont.families():
        self.tree.listbox['font'] = (fnt, 9)
        self.tree.heading['font'] = (fnt, 11)
        break

    self.update_tree()

  

  def update_tree(self):
    if self.session.project == None: return

    self.tree.clear()

    self.spec_list = self.session.project.spectrum_list()
    self.spec_list.sort(key=lambda x: x.name, reverse=False)

    for spec in self.spec_list:
        self.tree.append(spec.name)


  def spectra_selected(self, *args):
    self.status.config(text="Status: Spectra selected. Check noise level!")
    self.status.update()



  def noise_level(self):
    data_list = self.tree.selected_line_data()
    if len(data_list) < 1: return

    idx = self.tree.selected_line_numbers()[0]
    if idx == None: return

    self.status.config(text="Status: Noise level found. Now run iPick!")
    self.status.update()

    UCSF_FILE = self.spec_list[idx].data_path

    print self.noise.variable.get()



  def read_log():
    while True:
        log = open('process.log', 'r').read()

        self.output.delete('1.0', tk.END)
        self.output.insert(tk.END, log)
        self.output.update()

        if path.exists('done'):
            try:
                remove('done')
            except:
                tkMessageBox.showinfo(title='Error', message='Could not delete "done" file')

            return


  def ipick_process(UCSF_FILE):
    #Popen("python /home/samic/MyWorks/CODES/iPick/iPick.py -i " + UCSF_FILE + " -o peaks.list > process.log && touch done")
    #system("python /home/samic/MyWorks/CODES/iPick/iPick.py -i " + UCSF_FILE + " -o peaks.list > process.log && touch done")
    #system("python iPick.py -i " + UCSF_FILE + " -o peaks.list && touch done")
    system("ls > process.log && touch done")



  def run_ipick(self):
    data_list = self.tree.selected_line_data()
    if len(data_list) < 1: return

    idx = self.tree.selected_line_numbers()[0]
    if idx == None: return

    self.status.config(text="Status: iPick is running ...")
    self.status.update()


    UCSF_FILE = self.spec_list[idx].data_path

    try:

        ##for line in popen("ls"):
        ##for line in iPick3.modular(UCSF_FILE, "iPeak.list"):
	    ##    output.insert("end", line)

        #result = StringIO()

        #sys.stdout = result
        #iPick3.modular(UCSF_FILE, "iPeak.list")
        #result_string = result.getvalue()

        #for line in result_string:
    	#        output.insert("end", line)



        #from signal import signal, SIGPIPE, SIG_DFL
        #signal(SIGPIPE,SIG_DFL) 

        #sys.stdout = open('process.log', 'w')


        t1 = multiprocessing.Process(target=ipick_process, args=(UCSF_FILE,))
        #t2 = multiprocessing.Process(target=read_log)

        t1.start()
        #t2.start()

        #t1.join()
        #t2.join()


        while True:
            log = open('process.log', 'r').read()

            self.output.delete('1.0', tk.END)
            self.output.insert(tk.END, log)
            self.output.update()

            time.sleep(0.5)

            if path.exists('done'):
                try:
                    remove('done')
                except:
                    tkMessageBox.showinfo(title='Error', message='Could not delete "done" file')
   
                break


    except TypeError:
        self.status.config(text="Status: File is corrupted.")
        self.status.update()

    else:
        log = open('process.log', 'r').read()

        self.output.delete('1.0', tk.END)
        self.output.insert(tk.END, log)
        self.output.update()

        remove('process.log')

        self.status.config(text="Status: iPick is done.")
        self.status.update()

        tkMessageBox.showinfo(title='Job Done!', message='Found peaks are stored in "peaks.list" file.')




def show_ipick_dialog(session):
  sputil.the_dialog(ipick_dialog, session).show_window(1)


