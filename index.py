#!/usr/bin/env python
# -*- coding: utf-8 -*-
#************************************************************
#*                  SMART VERSION 2.0                       *
#*                        Innio                             *
#*                       index.py                           *
#*                 Programa principal                       *
#*                  28/diciembre/2017                       *
#************************************************************

import os
import numpy as np
import sys
import math
import time

import subprocess
import json

from PyQt4 import QtCore, QtGui,uic
from PyQt4.QtCore import *
from PyQt4.QtGui import QPalette,QWidget,QFileDialog,QMessageBox,QPixmap
import requests

from readingSMART import readAntena
from joystick_control import joyStickControl
#from comSerie import comSerial, availablePorts
from telescope_server import Telescope_Server
from EcuatorialToHorizontal import EcuToHor
from tracking import TrackMode
import coords

#Grafica Receptor
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.mlab import griddata
from matplotlib import cm

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import(
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

from subprocess import check_output

class MainWindow(QtGui.QMainWindow):

    #Señal para actualizar el FOV de Stellarium
    act_stell_pos = QtCore.pyqtSignal(str, str)

    def __init__(self):

        QtGui.QMainWindow.__init__(self)

        #Se monta la interfaz de usuario para la pantalla principal
        self.ui = uic.loadUi("views/main.ui")

        #Dimensiones de la pantalla
        screen = QtGui.QDesktopWidget().screenGeometry() 
        #self.SIZE_X = screen.width()
        #self.SIZE_Y = screen.height()

        self.ui.setWindowFlags(self.ui.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        self.ui.setWindowFlags(self.ui.windowFlags() & ~QtCore.Qt.WindowMaximizeButtonHint)

        #Conexiones iniciales
        #Barra de herramientas
        #Archivo
        #--Abrir Stellarium
        self.ui.actionAbrir_Stellarium.triggered.connect(self.openSteX)
        #--Salir
        self.ui.actionSalir.triggered.connect(self.exit)
        #Conexión
        #--Conectar
        self.ui.actionConectar.triggered.connect(self.conectar)
        #--Desconectar
        self.ui.actionDesconectar.triggered.connect(self.desconectar)
        #Antena
        #--Parabólica
        self.ui.actionParabolica.triggered.connect(self.settingPara)
        #--Bocina Piramidal
        self.ui.actionBocina_Piramidal.triggered.connect(self.settingBoc)
        #Graficar
        #--Graficar mediciones
        self.ui.actionGraficar.triggered.connect(self.plotReport)
        #Acerca de
        self.ui.menuAcerca_de.mousePressEvent = self.about

        #Funciones
        #--Home
        self.ui.homeBtn.mousePressEvent = self.home
        #--Go To
        self.ui.goBtn.mousePressEvent = self.goX
        self.go = uic.loadUi("views/directionWindow.ui")
        self.go.okGoBtn.mousePressEvent = self.aceptGO
        self.go.noGoBtn.mousePressEvent = self.refuseGO
        #--Geolocalización
        self.ui.locationBtn.mousePressEvent = self.geoX
        self.geo = uic.loadUi("views/geoWindow.ui")
        self.geo.okGoBtn.mousePressEvent = self.aceptGEO
        self.geo.noGoBtn.mousePressEvent = self.refuseGEO

        #Ajustes MODO
        self.ui.mode.currentChanged.connect(self.modeEdit)

        #Ajustes Iniciales
        #Configuración de la pantalla
        self.lon = 0.0
        self.lat = 0.0
        self.az = 0.0
        self.ele = 0.0
        self.vel = 0

        #Variables auxiliares de posición
        self.newRA = 0
        self.newDEC = 0
        self.sra = 0
        self.sdec = 0

        self.adc = 0.0
        self.file = None

        #Variables de barrido
        self.pasoy = 0
        self.tamanox = 0
        self.tamanoy = 0
        self.totaly = 0
        self.timeBarrido = 0
        self.sweeping = False
        self.connected = False

        self.realAZ = 0.0
        self.realEL = 0.0

        self.i = 0
        self.j = 0
        self.g = 0
        self.k = False

        self.ui.lonLCD.display(self.lon)
        self.ui.latLCD.display(self.lat)
        self.ui.azimuthLCD.display(self.az)
        self.ui.altitudLCD.display(self.ele)
        self.ui.velLCD.display(self.vel)

        self.ui.sweepFrame.setEnabled(False)

        #Gráfica inicial
        self.limit = 200

        self.fig1 = Figure()
        self.f1 = self.fig1.add_subplot(111)
        self.f1.set_xlim(0, self.limit)
        self.f1.set_ylim(600, 3500)
        self.f1.set_ylabel('Potencia')
        self.addmpl(self.fig1)

        #Comunicación JSON
        self.host = '192.168.1.177'
        self.port = '80'

        self.headers = {'SMARTII': 'radiotelescope'}

        self.jsonData = {
            'Mod': 0,     # Auto or Manual - Operation Mode
            'AzDes': 0.0,   # Value Azimut Set Point    (Only Auto)
            'ElDes': 0.0,   # Value Elevation Set Point (Only Auto)
            'AzDir': 0,      # ST - stop. CW or CCW - Set Direction for Azimut turn (only  Manual)
            'ElDir': 0,      # ST - stop. CW or CCW - Set Direction for Elevation turn (only  Manual)
            'S': 0,       # From 0 to 10 - Movement speed (only Manual)
            'AzH': 'N',      # Y or N - Go to zero azimut
            'ElH': 'N',      # Y or N - Go to zero elevation

            'AzNow': 0.0,   # Value read from encoder Azimut axis
            'ElNow': 0.0,   # Value read from encoder Elevation axis
            'Lat': 0.0, # Value Latitude from GPS
            'Lon': 0.0, # Value Longituce from GPS
            'RF': 0.0,        # Vaue read from ADC
            'Mot': 0     # ON or OFF - Are the motors ON or OFF
            }

        #Modo inicial
        self.modeEdit()
        self.clearDIR()

        self.modeM = True

        #MODO AUTOMÁTICO
        self.find = False
        self.track = False
        self.sweep = False
        self.offset = 0.0
        self.recording = False

        self.prevState = 'OFF'

        #--Modo barrido
        self.timeBarrido = 0.0
        self.readTime = 0.75

        #Modo Automático deshabilitado
        self.ui.findCheck.clicked.connect(self.findCheckFcn)
        self.ui.trackCheck.clicked.connect(self.trackCheckFcn)
        self.ui.sweepCheck.clicked.connect(self.sweepCheckFcn)

        self.ui.azimuthDOOM.display(self.az)
        self.ui.altitudDOOM.display(self.ele)
        self.ui.mode.setTabEnabled(1, False)

        #Modo Automático Funciones
        #--Iniciar
        self.ui.startAutoBtn.mousePressEvent = self.startAuto

        #--Detener
        self.ui.stopAutoBtn.mousePressEvent = self.stopAuto

        #Conexion con Stellarium
        self.Server = Telescope_Server(pos_signal=self.act_stell_pos)
        self.Server.daemon = True
        self.Server.start()

        self.Server.stell_pos_recv.connect(self.stellariumRead)

        #Comunicación con la antena
        #if self.readJSON() != "Error":
        #    self.SMART = readAntena(self.readTime)
        #    self.SMART.readPort.connect(self.readJSON)
        #    self.SMART.start()
        #    self.connected = True

        self.ui.show()

    #Send DATA
    def sendJSON(self,json):
        if self.connected:
            try:
                requests.post("http://" + self.host + ":" + self.port, data=json, headers=self.headers)
                
                #print json

            except:
                self.ui.statusbar.showMessage(u'Error de conexión!!!')

    #Checar puerto
    def tryPort(self):
        proc = subprocess.Popen(["ifplugstatus enp1s0"], stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        return out

    #Read DATA
    def readJSON(self):
        try:
            res = requests.post("http://" + self.host + ":" + self.port, data=self.jsonData, headers=self.headers)

            self.decodeJSON(res.text)

            if self.recording == True:
                self.file.write(time.strftime("%H:%M:%S") + "\t" + str(self.realAZ) + "\t" + str(self.realEL) + "\t" + str(self.adc) + "\n")
        except Exception as e:     
            print e     
            self.SMART.cancel()
            QtGui.QMessageBox.warning(self, 'Warning', u"Error de comunicación")
            return "Error"

    def decodeJSON(self,data):
        k = data.encode('utf8').replace("'",'"')

        self.jsonData = json.loads(k)

        flagState = self.jsonData['Mot']
        self.motorState(flagState)

        self.adc = self.jsonData['RF']

        az = self.jsonData['AzN']
        el = self.jsonData['ElN']

        el = el + self.offset

        self.realAZ = az
        self.realEL = el

        lon = self.jsonData['Lon']
        lat = self.jsonData['Lat']

        if lon != 0 and lat != 0:
            self.lon = lon
            self.lat = lat
            self.ui.mode.setTabEnabled(1,True)

        self.writeGEO(lon,lat)

        self.ui.azimuthLCD.display(az)
        self.ui.altitudLCD.display(el)

    def motorState(self,state):
        if self.prevState != state:
            if state == 'OFF':
                self.ui.mode.setTabEnabled(0,False)
                self.ui.mode.setTabEnabled(1,False)

                self.ui.homeBtn.setDisabled(True)
                self.ui.goBtn.setDisabled(True)
                self.ui.locationBtn.setDisabled(True)  

                self.ui.statusbar.showMessage(u'Motores Inactivos!!!')

            else:
                self.ui.mode.setTabEnabled(0,True)
                self.ui.mode.setTabEnabled(1,True)

                self.ui.homeBtn.setDisabled(False)
                self.ui.goBtn.setDisabled(False)
                self.ui.locationBtn.setDisabled(False)

                self.ui.statusbar.showMessage(u'Motores Activos!!!')

        self.prevState = state  

    #***********MODO***********
    def modeEdit(self):
        #MODO MANUAL
        if self.ui.mode.currentIndex() == 0:
            #Se inicia el joystick
            self.JOY = joyStickControl(0.0001)

            #Conexion a la LCD 
            self.JOY.jSvel.connect(self.writeVEL)

            #Conexion a la matriz de LED
            self.JOY.jSmov.connect(self.writeDIR)
            #self.JOY.jMove.connect(self.fromJS)

            self.JOY.start()

            #Funcion Modo Manual
            self.ui.statusbar.showMessage('Modo Manual')
            print "En modo manual"
            self.modeM = True

            self.confManualMode()
        
        #MODO AUTOMATICO
        else:
            self.ui.velLCD.display(0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
            
            #Finalizamos el joystick
            self.JOY.cancel()

            #Funcion Modo Automatico
            self.ui.statusbar.showMessage(u'Modo Automático')
            print "En modo automático"
            self.modeM = False

            self.confAutoMode()

    def confManualMode(self):
        self.vel = 0
    
        self.ui.homeBtn.setDisabled(False)
        self.ui.goBtn.setDisabled(False)
        self.ui.locationBtn.setDisabled(False)

        self.jsonData['Mod'] = 0
        self.jsonData['S'] = 0
        self.sendJSON(self.jsonData)

    def confAutoMode(self):
        self.ui.homeBtn.setDisabled(True)
        self.ui.goBtn.setDisabled(True)
        self.ui.locationBtn.setDisabled(True)  

        self.jsonData['Mod'] = 1
        self.sendJSON(self.jsonData)

        #Abrir Stellarium
        self.modifyPosSte('SkyExplorer RT',str(self.lat),str(self.lon))
        self.openSte()   

    def modifyPosSte(self,cmdText,lat,lon):
        try:
            fullPath = os.path.expanduser('~/.stellarium/data/user_locations.txt')
            if not fullPath:
                archivo = open(fullPath,'a')
                archivo.write(cmdText)
                archivo.close()
                archivo = open(fullPath,'r')
            else:
                archivo = open(fullPath,'r')

            lineas = list(archivo)

            for i in range(len(lineas)):
                if lineas[i][0:14] == cmdText:
                    lineas[i] = cmdText + '\t\tMexico\tX\t0\t' + str(lat) + 'N\t' + str(lon) + 'E\t2144\t2\t\tEarth\n' 
            archivo.close()
            fileNew = open(fullPath,'w')
            strToLine = ''.join(lineas)
            fileNew.write(strToLine)
            fileNew.close()
        except IOError:
            QtGui.QMessageBox.warning(self, 'Warning', u"Fallo al cargar parámetros iniciales")

    def stellariumRead(self, ra, dec, mtime):
        ra = float(ra)
        dec = float(dec)
        mtime = float(mtime)
        (self.sra, self.sdec, stime) = coords.eCoords2str(ra, dec, mtime)

        self.writeInfo()

    #FUNCIONES MODO AUTOMÁTICO
    #Activado del Group Box
    def findCheckFcn(self):
        self.find = True
        self.track = False
        self.sweep = False
        self.ui.findCheck.setChecked(True)
        self.ui.trackCheck.setChecked(False)
        self.ui.sweepCheck.setChecked(False)
        self.ui.sweepFrame.setEnabled(False)

    def trackCheckFcn(self):
        self.timeBarrido = 1.0      #Cada segundo se actualiza la posición
        self.find = False
        self.track = True
        self.sweep = False
        self.ui.findCheck.setChecked(False)
        self.ui.trackCheck.setChecked(True)
        self.ui.sweepCheck.setChecked(False)
        self.ui.sweepFrame.setEnabled(False)

    def sweepCheckFcn(self):
        self.find = False
        self.track = False
        self.sweep = True
        self.ui.findCheck.setChecked(False)
        self.ui.trackCheck.setChecked(False)
        self.ui.sweepCheck.setChecked(True)
        self.ui.sweepFrame.setEnabled(True)

    def startAuto(self,event):
        if self.find == True:
            self.ui.startAutoBtn.setDisabled(False)
        else:
            self.ui.startAutoBtn.setDisabled(True)
        os.system('./src/bash/virtualKey')
        self.mg = 0
        if self.track == True or self.sweep == True:
            if self.sweep == True:
                #self.timeBarrido = 1
                try:
                    self.timeBarrido = int(self.ui.tiempoBarrido.toPlainText())
                    self.pasoy = float(self.ui.pasoAL.toPlainText())
                    self.tamanox = float(self.ui.azVentana.toPlainText())
                    self.tamanoy = float(self.ui.elVentana.toPlainText()) 
                    self.totaly = math.ceil(self.tamanoy/self.pasoy)

                    if self.timeBarrido != 0 and self.pasoy != 0 and self.tamanox != 0 and self.tamanoy != 0:
                        self.sweeping = True
                    else:
                        self.sweeping = False
                        self.ui.startAutoBtn.setDisabled(False)
                except:
                    self.ui.startAutoBtn.setDisabled(False)
                    QtGui.QMessageBox.information(self, u'Datos inválidos', u"Los datos para el barrido no son válidos")
                
            if self.sweeping == True or self.track == True:
                self.recording = True

                #Conexion modo track
                self.Track = TrackMode(self.timeBarrido)
                
                #Se crea nuevo archivo
                fileName = "./reports/Reportes de Medición " + time.strftime("%c") + ".txt"
                self.file = open(fileName,'w')
                self.file.write("Hora" + "\t" + "Azimuth" + "\t" + "Elevación" + "\t" + "Potencia" + "\n")
                self.file.write(time.strftime("%H:%M:%S") + "\t" + str(self.realAZ) + "\t" + str(self.realEL) + "\t" + str(self.adc) + "\n")

                self.Track.lat_lon.connect(self.writeInfo)
                self.Track.start()

    def stopAuto(self,event):
        self.recording = False
        self.stopAutoProcess()

    def stopAutoProcess(self):
        self.ui.startAutoBtn.setDisabled(False)
        try:
            self.Track.cancel()
        except:
            pass
        self.recording = False

        if self.file != None:
            self.file.close()        

    def writeInfo(self):

        self.newRA = 180*coords.hourStr_2_rad(self.sra)/(math.pi*15)
        self.newDEC = 180*coords.degStr_2_rad(self.sdec)/math.pi

        self.ecuToalaz = EcuToHor(self.newRA, self.newDEC, self.lat, self.lon)
        (self.az,self.ele) = self.ecuToalaz.getHor()

        if self.az < 0:
            self.az = self.az + 360

        #Barrido
        if self.sweep == True:
            self.az = self.az - (self.tamanox / 2) + self.g*self.tamanox
            self.ele = self.ele + (self.tamanoy / 2) - self.j*self.pasoy

            self.file.write(time.strftime("%H:%M:%S") + "\t" + str(self.realAZ) + "\t" + str(self.realEL) + "\t" + str(self.adc) + "\n")

            #Contador        
            if self.i >= 1:
                self.i = 0
                self.j = self.j + 1
                self.k = not self.k
                if self.j >= self.totaly:
                    self.j = 0
                    self.g = 0
                    self.k = False
                    self.stopAutoProcess()
            else:
                self.i = self.i + 1
                if self.k == False:
                    self.g = self.g + 1
                else:
                    self.g = self.g - 1

        self.jsonData['AzDes'] = self.az
        self.jsonData['ElDes'] = self.ele

        self.sendJSON(self.jsonData)

        self.ui.azimuthDOOM.display('{0:.4f}'.format(self.az))
        self.ui.altitudDOOM.display('{0:.4f}'.format(self.ele))

    #MODO MANUAL
    def writeVEL(self,vel):
        self.vel = vel
        self.ui.velLCD.display(self.vel)

        self.jsonData['S'] = self.vel
        self.sendJSON(self.jsonData)

        self.ui.statusbar.showMessage('Velocidad configurada')

    def writeDIR(self,az,el):
        if el == 1 and az == 1:
            pixmap = QPixmap('./src/icon/upFull.png')
            self.ui.up.setPixmap(pixmap)
            pixmap = QPixmap('./src/icon/rightFull.png')
            self.ui.right.setPixmap(pixmap)

            self.jsonData['AzDir'] = 1
            self.jsonData['ElDir'] = 1

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Arriba/Derecha')

        elif el == 1 and az == -1:
            pixmap = QPixmap('./src/icon/upFull.png')
            self.ui.up.setPixmap(pixmap) 
            pixmap = QPixmap('./src/icon/leftFull.png')
            self.ui.left.setPixmap(pixmap)

            self.jsonData['AzDir'] = 2
            self.jsonData['ElDir'] = 1

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Arriba/Izquierda')

        elif el == -1 and az == 1:
            pixmap = QPixmap('./src/icon/downFull.png')
            self.ui.down.setPixmap(pixmap) 
            pixmap = QPixmap('./src/icon/rightFull.png')
            self.ui.right.setPixmap(pixmap)

            self.jsonData['AzDir'] = 1
            self.jsonData['ElDir'] = 2

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Abajo/Derecha')

        elif el == -1 and az == -1:
            pixmap = QPixmap('./src/icon/downFull.png')
            self.ui.down.setPixmap(pixmap) 
            pixmap = QPixmap('./src/icon/leftFull.png')
            self.ui.left.setPixmap(pixmap)

            self.jsonData['AzDir'] = 2
            self.jsonData['ElDir'] = 2

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Abajo/Izquierda')

        elif el == 1:
            pixmap = QPixmap('./src/icon/upFull.png')
            self.ui.up.setPixmap(pixmap) 

            self.jsonData['ElDir'] = 1

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Arriba')

        elif el == -1:
            pixmap = QPixmap('./src/icon/downFull.png')
            self.ui.down.setPixmap(pixmap) 

            self.jsonData['ElDir'] = 2

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Abajo')

        elif az == 1:
            pixmap = QPixmap('./src/icon/rightFull.png')
            self.ui.right.setPixmap(pixmap) 

            self.jsonData['AzDir'] = 1

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Derecha')

        elif az == -1:
            pixmap = QPixmap('./src/icon/leftFull.png')
            self.ui.left.setPixmap(pixmap) 

            self.jsonData['AzDir'] = 2

            self.sendJSON(self.jsonData)

            self.ui.statusbar.showMessage('Direcci\xf3n: Izquierda')

        else:
            self.clearDIR()

    def clearDIR(self):
        pixmap = QPixmap('./src/icon/upEmpty.png')
        self.ui.up.setPixmap(pixmap)
        pixmap = QPixmap('./src/icon/downEmpty.png')
        self.ui.down.setPixmap(pixmap)
        pixmap = QPixmap('./src/icon/leftEmpty.png')
        self.ui.left.setPixmap(pixmap)
        pixmap = QPixmap('./src/icon/rightEmpty.png')
        self.ui.right.setPixmap(pixmap)

        self.jsonData['AzDir'] = 0
        self.jsonData['ElDir'] = 0

        self.sendJSON(self.jsonData)

        self.ui.statusbar.showMessage('Modo Manual: Detenido')

    def fromJS(self,vel,az,el):
        print vel,az,el

    #********FUNCIONES*********
    #Home
    def home(self,event):
        self.az = 0.0
        self.ui.azimuthLCD.display(self.az)

        self.jsonData['AzHome'] = 'Y'
        self.sendJSON(self.jsonData)

        self.ui.statusbar.showMessage('Nuevo Home configurado')
    #Go To
    def goX(self,event):
        self.go.show()
        self.go.azimuthEdit.setText('')
        self.go.altitudEdit.setText('')
    #--Aceptar Go
    def aceptGO(self,event):
        azW = self.go.azimuthEdit.toPlainText()
        eleW = self.go.altitudEdit.toPlainText()

        if azW == '' or eleW == '':
            QtGui.QMessageBox.information(self, 'Campos vac\xedos', "Por favor complete todos los campos")
        else:
            try:
                self.az = float(azW)
                self.ele = float(eleW)

                if self.az >= 360 or self.az < 0:
                    self.az = 0

                if self.ele > 90:
                    self.ele = 90
                elif self.ele < 0:
                    self.ele = 0
                    
                self.ui.statusbar.showMessage("Posici\xf3n destino: " + str(self.az) + "," + str(self.ele))
                self.go.close()

                self.jsonData['Mod'] = 0
                self.jsonData['S'] = 0

                self.sendJSON(self.jsonData)
            
            except:
                QtGui.QMessageBox.information(self, u'Valores inválidos', u'Los valores de los campos no son válidos, pruebe con otros :)')                

    #--Cancelar Go
    def refuseGO(self,event):
        self.go.close()
    #Geolocalización
    def geoX(self,event):
        self.geo.show()
        self.geo.longitudEdit.setText('')
        self.geo.latitudEdit.setText('')
    #--Aceptar Geo
    def aceptGEO(self,event):
        lonW = self.geo.longitudEdit.toPlainText()
        latW = self.geo.latitudEdit.toPlainText()

        if lonW == '' or latW == '':
            QtGui.QMessageBox.information(self, 'Campos vac\xedos', "Por favor complete todos los campos")
        else:
            try:
                self.lon = float(lonW)
                self.lat = float(latW)

                if self.lon > 180:
                    self.lon = 180
                if self.lon < -180:
                    self.lon = -180

                if self.lat > 90:
                    self.lat = 90
                elif self.lat < -90:
                    self.lat = -90

                self.writeGEO(self.lon,self.lat)
                    
                self.ui.statusbar.showMessage("Posici\xf3n geogr\xe1fica: " + str(self.lon) + "," + str(self.lat))
                self.geo.close()

                self.ui.mode.setTabEnabled(1,True)

                self.jsonData['Lat'] = self.lat
                self.jsonData['Lon'] = self.lon
                self.sendJSON(self.jsonData)

            except:
                QtGui.QMessageBox.information(self, u'Valores inválidos', u'Los valores de los campos no son válidos, pruebe con otros :)')
    
    #--Cancelar Geo
    def refuseGEO(self,event):
        self.geo.close() 

    def writeGEO(self,lon,lat): 
        if lon < 0:
            self.ui.lonLCD.display(abs(lon))
            self.ui.lonlabel.setText(u'°W')
        else:
            self.ui.lonLCD.display(lon)
            self.ui.lonlabel.setText(u'°E') 

        if lat < 0:
            self.ui.latLCD.display(abs(lat))
            self.ui.latlabel.setText(u'°S')
        else:
            self.ui.latLCD.display(lat)
            self.ui.latlabel.setText(u'°N')          

    #*********MENU BAR*********
    #Archivo
    def openSte(self):
        
        pid = self.get_pid('stellarium')[0]
        
        if pid == 0:
            os.system('stellarium &')
            self.ui.statusbar.showMessage('Iniciando Stellarium')
        else:
            self.ui.statusbar.showMessage('Stellarium ya iniciado')

    def openSteX(self,event):
        self.openSte()

    def get_pid(self,name):
        try:
            pid = check_output(["pidof",name])
        except:
            pid = [0]
        return pid

    def exit(self,event):
        try:
            if self.modeM == True: 
                self.JOY.cancel()
            self.Server.close_socket()
            self.Track.cancel()
            self.SMART.cancel()
        except:
            pass
        self.ui.close()
    #Conectar
    def conectar(self):
        try:
            if self.tryPort() == "enp1s0: link beat detected\n":
                self.SMART = readAntena(self.readTime)
                self.SMART.readPort.connect(self.readJSON)
                self.SMART.start()  
                self.connected = True
            else:
                QtGui.QMessageBox.warning(self, 'Warning', u"Imposible conectarse")
        except Exception as e:
            QtGui.QMessageBox.warning(self, 'Warning', e)

    def desconectar(self):
        try:
            self.SMART.cancel()
        except:
            print 'No pudo desconectarse! :('

    #Antena
    def settingPara(self,event):
        self.offset = 21.4

    def settingBoc(self,event):
        self.offset = 7.2

    def plotReport(self):
        #Lectura del archivo con los datos      
        #Ventana
        w = QWidget()
        #Ajuste de su tamaño 
        w.resize(320, 240)    
        #Título
        w.setWindowTitle("Abrir reporte")
        #Dirección de archivo para abrir
        fileName = QFileDialog.getOpenFileName(w, 'Open File', './')

        w.close()

        try:
            file = open(fileName,"r")

            readfile = file.readlines()
            del(readfile[0])

            vecTime = ['']*len(readfile)
            vecElevacion = [0]*len(readfile)
            vecAzimuth = [0]*len(readfile)
            vecPotencia = [0]*len(readfile)

            k = 0
            for i in readfile:
                tab = 0
                timeM = ""
                ele = ""
                az = ""
                pot = ""

                for j in range(len(i)):
                    if i[j] == "\t":
                        tab = tab + 1
                    else:
                        if tab == 0:
                            timeM = timeM + i[j]
                        elif tab == 1:
                            az = az + i[j]
                        elif tab == 2:
                            ele = ele + i[j]
                        else:
                            pot = pot + i[j]

                vecTime[k] = timeM 
                vecElevacion[k] = float(ele)
                vecAzimuth[k] = float(az) 
                vecPotencia[k] = float(pot)

                k = k + 1

            #Crear Malla
            #Tamaño de ventana
            nAZ = 35
            nEL = 35

            #Datos Nada
            since_az = 235.0
            to_az = 257.0

            since_ele = 64.0
            to_ele = 84.0

            paso_AZ = (to_az - since_az)/nAZ
            paso_EL = (to_ele - since_ele)/nEL

            grid_AZ = [0]*nAZ
            grid_EL = [0]*nEL

            #Malla de promedio
            for m in range(nAZ):
                grid_AZ[m] = since_az + paso_AZ*m
                grid_EL[m] = since_ele + paso_EL*m

            potBines = []
            nTimes = []
            for q in range(nEL):
                potBines.append([0]*nAZ)
                nTimes.append([0]*nAZ)

            for k in range(len(readfile)):
                for m in range(nAZ):
                    if vecAzimuth[k] <= grid_AZ[m]:   
                        break
                for n in range(nEL):
                    if vecElevacion[k] <= grid_EL[n]:
                        break

                potBines[m-1][n-1] = potBines[m-1][n-1] + vecPotencia[k]
                nTimes[m-1][n-1] = nTimes[m-1][n-1] + 1

            plot_AZ = []
            plot_EL = []
            plot_POT = []

            for i in range(nAZ):
                for j in range(nEL):
                    if nTimes[i][j] < 1:
                        nTimes[i][j] = 0
                    else:
                        potBines[i][j] = potBines[i][j]/nTimes[i][j]
                        plot_AZ.append(grid_AZ[i])
                        plot_EL.append(grid_EL[j])
                        plot_POT.append(potBines[i][j])

            #Grafica del objeto
            figFin = plt.figure()

            ax = Axes3D(figFin)

            xi = np.linspace(min(plot_AZ), max(plot_AZ), 100)
            yi = np.linspace(min(plot_EL), max(plot_EL), 100)
            X, Y = np.meshgrid(xi, yi)

            #Interpolación
            Z = griddata(plot_AZ, plot_EL, plot_POT, xi, yi)

            ax.scatter3D(plot_AZ, plot_EL, plot_POT,c=plot_POT,cmap=plt.cm.jet) 
            ax.plot_wireframe(X, Y, Z, cmap=plt.cm.coolwarm, linewidth=0.2, antialiased=True)
            surf = ax.contour(X, Y, Z, cmap=plt.cm.coolwarm, linewidth=10, antialiased=True)

            plt.show()

        except:
            QtGui.QMessageBox.information(self, 'Abrir archivo', "Imposible abrir archivo")
            return None

    #Acerca
    def about(self,event):
        QtGui.QMessageBox.information(self, 'Acerca', "SMART V2.0")

    #GRÁFICA
    def addmpl(self,fig):
        self.canvas = FigureCanvas(fig)
        self.ui.plotRX.addWidget(self.canvas)
        self.canvas.draw()
        self.toolbar = NavigationToolbar(self.canvas, 
                self, coordinates=True)
        self.ui.plotRX.addWidget(self.toolbar)

    #Salir
    def closeEvent(self, event):
        try:
            if self.modeM == True: 
                self.JOY.cancel()
            self.Server.close_socket()
            self.Track.cancel()
            self.SMART.cancel()
            event.accept()
        except:
            event.accept()

#Ejecución del programa
app = QtGui.QApplication(sys.argv)
MyWindow = MainWindow()
sys.exit(app.exec_())