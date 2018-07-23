#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from threading import Thread, Event
from PyQt4 import QtCore

#Modo seguimiento
class TrackMode(QtCore.QThread):
    
    #Señal para calcular lat y lon
    lat_lon = QtCore.pyqtSignal()
    
    def __init__(self, time):
        QtCore.QThread.__init__(self, None)
        self.time = time
        self.finished = Event()

    def run(self):
        count = 0
        while not self.finished.is_set():
            self.finished.wait(self.time)
            if not self.finished.is_set():
                count = count + 1
                if count >= int(15/self.time):
                    count = 0
                    os.system('./src/bash/virtualKey')
                self.lat_lon.emit()

    def cancel(self):
        self.finished.set()              
