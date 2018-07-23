#!/usr/bin/python
# -*- coding: utf-8 -*-

import math
import logging
import coords
import datetime
from time import gmtime

#Se obtendra la conversion de coordenadas ecuatoriales a altazimutales

class EcuToHor():

    def __init__(self,ra,dec,lat,lon):

        self.az = float()
        self.el = float()
        self.lon = lon
        self.lat = lat
        self.ra = 15*math.pi*ra/180
        self.dec = math.pi*dec/180

        self.hour = float(gmtime()[3])
        self.min = float(gmtime()[4])
        self.sec = float(gmtime()[5])
        
        self.day = int(gmtime()[2])
        self.month = int(gmtime()[1])
        self.year = int(gmtime()[0])
        
    def getTime(self):
        nowTime = gmtime()
        hc = float(self.hour) + float(self.min)/60 + float(self.sec)/3600
        return hc

    def getLON(self):
        nowLON =  self.lon
        realLON = coords.rad_2_hour(abs(nowLON)*math.pi/180)
        if nowLON < 0:
            realLON = realLON * -1
        return realLON

    def getLAT(self):
        nowLAT =  self.lat
        realLAT = nowLAT*math.pi/180
        return realLAT

    def getJD(self):     
        now = datetime.datetime.utcnow()
        nowdays = (now- datetime.datetime(2000,1,1,12,0,0)).total_seconds()        
        ndays = nowdays/(24*3600)
        return ndays

    def siderealTime(self):
        HSGO = 18.697374558 + 24.06570982441908*self.getJD() + self.getLON()
        if HSGO > 24:
            mg = int(HSGO/24)
            HSGO = HSGO - mg*24
        return HSGO

    def localHour(self):
        H = math.pi*self.siderealTime()/12 - self.ra
        return H

    def getHor(self):
        self.az = math.atan2((math.sin(self.getLAT())*math.cos(self.localHour()) - math.cos(self.getLAT())*math.tan(self.dec)), math.sin(-self.localHour()))
        self.el = math.asin(math.sin(self.dec)*math.sin(self.getLAT()) + math.cos(self.dec)*math.cos(self.localHour())*math.cos(self.getLAT()))
        return 180*self.az/math.pi + 90, 180*self.el/math.pi

    def decdeg2dms(self, dd):
        mnt,sec = divmod(dd*3600,60)
        deg,mnt = divmod(mnt,60)
        return deg,mnt,sec
    
if __name__ == "__main__":
    a = EcuToHor(4.598694444,16.50844444,19.0317616667,-98.31565)
    (az,el) = a.getHor()
    azm = a.decdeg2dms(az)
    elv = a.decdeg2dms(el)
    print azm
    print elv
    
