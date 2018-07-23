#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from threading import Thread, Event
from PyQt4 import QtCore

#Modo seguimiento
class readAntena(QtCore.QThread):
    
    #Señal para lectura del SMART
    readPort = QtCore.pyqtSignal()
    
    def __init__(self, time):
        QtCore.QThread.__init__(self, None)
        self.time = time
        self.finished = Event()

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self.time)
            if not self.finished.is_set():
                self.readPort.emit()

    def cancel(self):
        self.finished.set()              
