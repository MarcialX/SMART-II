#!/usr/bin/env python
# -*- coding: utf-8 -*-
#************************************************************
#*                  SMART VERSION 2.0                       *
#*                        Innio                             *
#*                  joystick_control.py                     *
#*                 Control del Joystick                     *
#*                  28/diciembre/2017                       *
#************************************************************

import pygame
from PyQt4 import QtCore
from threading import Thread, Event
import logging

logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(funcName)s - %(levelname)s: %(message)s")

class joyStickControl(QtCore.QThread):

    jSvel = QtCore.pyqtSignal(int)  #Vel
    jSmov = QtCore.pyqtSignal(int,int)  #Az, El
    jMove = QtCore.pyqtSignal(int,int, int) #Go To (Envío a la antena)
    
    def __init__(self, interval):
        QtCore.QThread.__init__(self, None)
        self.vectButton = [0,2]
        self.axis = [0,0]
        self.vel = 0
        self.interval = interval
        self.event = None
        self.finished = Event()     
	
        pygame.init()
        pygame.joystick.init()
        
        try:
            self.joyStick = pygame.joystick.Joystick(0)
            self.joyStick.init()
            logging.debug("Joystick connected!!!")
        except:
            logging.debug("Failed connection!!!")

    def detected(self):
        for self.event in pygame.event.get():

            if self.event.type == pygame.JOYBUTTONDOWN:
                for i in self.vectButton:
                    if self.joyStick.get_button(i) == 1:
                        if i == 0:
                            self.vel = self.vel + 1;
                            if self.vel > 21:
                                self.vel = 0
                        elif i == 2:
                            self.vel = self.vel - 1;
                            if self.vel < 0:
                                self.vel = 21
                        self.jSvel.emit(self.vel)
                        self.jMove.emit(self.vel, self.axis[0], self.axis[1])

            if self.event.type == pygame.JOYHATMOTION:
                for i in range(2):
                    self.axis[i] = self.joyStick.get_hat(0)[i]

                self.jSmov.emit(self.axis[0], self.axis[1])
                self.jMove.emit(self.vel, self.axis[0], self.axis[1])       

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                self.detected()
        
    def printInfo(self,vel,az,el):
        logging.debug('Vel: ' + str(vel) + ',AZ: ' + str(az) + ',EL: ' + str(el))          

    def cancel(self):
        self.finished.set()
