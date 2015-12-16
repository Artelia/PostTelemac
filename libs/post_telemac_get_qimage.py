# -*- coding: utf-8 -*-

#import qgis
from qgis.core import QgsPluginLayerType
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#from qgis.utils import iface 
#import matplotlib
import matplotlib
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib import tri
from matplotlib import colors
from matplotlib import tri
import matplotlib.tri as tri
from matplotlib.mlab import griddata
#import numpy
import numpy as np
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt 
from PyQt4 import QtCore, QtGui
#import telemac python
from ..libs_telemac.utils.files import getFileContent
from ..libs_telemac.parsers.parserSortie import getValueHistorySortie
from ..libs_telemac.parsers.parserSELAFIN import getValueHistorySLF,   getValuePolylineSLF,subsetVariablesSLF
from ..libs_telemac.parsers.parserSELAFIN import SELAFIN
from ..libs_telemac.parsers.parserStrings import parseArrayPaires

#imports divers
from time import ctime
import math
from os import path
import sys
import os.path
import cStringIO
import gc
import time

DEBUG = False


class Selafin2QImage():

    def __init__(self,int=1):
        self.fig =  plt.figure(int)
        self.ax = self.fig.add_subplot(111)
        self.tricontourf1 = None

        
    def getimage(self,selafinlayer,rendererContext):
        """
        Generate a qimage depanding on variables in selafin layer
        3 methods :
            first : map is just panned
            second : selfin parameters are changed
            third : mapcanvas dimension are changed
        
        """
        try:
            timestart = time.clock()
            time1=[]
            #Compute renderer extent
            recttemp = rendererContext.extent()
            rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())]
            mupp = float(rendererContext.mapToPixel().mapUnitsPerPixel())
            sizepx = [ round(((rect[1] - rect[0] )/mupp),2) , round(((rect[3]  - rect[2] )/mupp),2) ]
            dpi1 = rendererContext.painter().device().logicalDpiX()
            dpi2 =dpi1
            #matplotlib figure dimension
            width= (sizepx[0])/dpi1
            lenght = (sizepx[1])/dpi1
            #buffer for qimage
            buf = cStringIO.StringIO()
            #color palette
            #cmap=None

            #Working with CRS - todo
            ct = rendererContext.coordinateTransform()
            if ct:
                recttemp2 = ct.transformBoundingBox(rendererContext.extent())
                rect2 = [float(recttemp2.xMinimum()), float(recttemp2.xMaximum()), float(recttemp2.yMinimum()), float(recttemp2.yMaximum())]

            if False:   #debug thing
                txt = ('rect '+str(rect)+"\n"+ str(mupp) + "\n"+
                        " px "+str(selafinlayer.renderersizepx)+'/'+str(sizepx) + "\n"+
                                                        ' temps '+str(selafinlayer.temps_memoire)+'/'+str(selafinlayer.temps_gachette) +"\n"
                                                        +'param '+ str(selafinlayer.param_memoire)+ " " +str(selafinlayer.param_gachette))
                
                selafinlayer.propertiesdialog.textBrowser_2.append(txt)
            
            
            try:
                #***********************************************************************
                #Case 1 : mapcanvas panned
                if (selafinlayer.renderersizepx==sizepx and selafinlayer.temps_memoire == selafinlayer.temps_gachette 
                    and selafinlayer.param_memoire == selafinlayer.param_gachette 
                    and selafinlayer.lvl_gachette == selafinlayer.lvl_memoire and selafinlayer.alpha_gachette == selafinlayer.alpha 
                    and selafinlayer.cmap == selafinlayer.cmap_gachette and selafinlayer.forcerefresh == False):
                    time1.append("deplacement")
                    #frame1 = plt.gca()

                    if selafinlayer.propertiesdialog.groupBox_schowvel.isChecked() and selafinlayer.propertiesdialog.comboBox_vel_method.currentIndex() in [0,1]:
                        self.temp.remove()
                        tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                        C = np.sqrt(np.array(tabvx)**2 + np.array(tabvy)**2)
                        self.temp = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                   scale=float(1/selafinlayer.propertiesdialog.doubleSpinBox_vel_scale.value()),
                                                   scale_units='xy',
                                                   cmap=  selafinlayer.cmap3_vel,
                                                   norm=selafinlayer.norm3_vel)
                        time1.append("quiver : "+str(round(time.clock()-timestart,3)))

                    #change view of matplotlib figure
                    self.ax.set_ylim([rect[2],rect[3]])
                    self.ax.set_xlim([rect[0],rect[1]])
                    
                    
                    
                    #self.ax.imshow(cmap=  selafinlayer.cmap3)
                    #self.fig.canvas.draw()
                    #self.fig.canvas.update()
                    #self.fig.canvas.flush_events()
                    #gc.collect()

                    time1.append("deplacement : "+str(round(time.clock()-timestart,3)))


                #***********************************************************************
                #Case 2 : figure changed (time,param) with the same mapcanvas dimension
                elif selafinlayer.renderersizepx==sizepx and selafinlayer.forcerefresh == False :
                    #update selafinlayer parameters
                    selafinlayer.param_memoire = selafinlayer.param_gachette
                    selafinlayer.lvl_memoire=selafinlayer.lvl_gachette
                    selafinlayer.temps_memoire=selafinlayer.temps_gachette
                    selafinlayer.alpha = selafinlayer.alpha_gachette
                    selafinlayer.rendererrect = rect
                    selafinlayer.renderersizepx = sizepx
                    selafinlayer.cmap_gachette = selafinlayer.cmap
                    
                    time1.append("nouveau meme taille")
                    
                    if False:
                        ncollections = len(self.ax.collections)
                        for i in range(ncollections):  
                            print str(self.ax.collections[ncollections-1-i].get_cmap())
                            del self.ax.collections[ncollections-1-i]  # Remove collections added in the last loop iteration.
                    else:
                        self.ax.cla()
                        self.ax.axes.axis('off')
                    self.fig.canvas.flush_events()
                    gc.collect()

                    time1.append("avant value : "+str(round(time.clock()-timestart,3)))
                    self.ax.set_ylim([rect[2],rect[3]])
                    self.ax.set_xlim([rect[0],rect[1]])


                    self.tricontourf1= self.ax.tricontourf(selafinlayer.triangulation,selafinlayer.value,selafinlayer.lvl_gachette, 
                                                                            cmap=  selafinlayer.cmap3,norm=selafinlayer.norm3 ,alpha = selafinlayer.alpha/100.0,rasterized=True)
                                                                            
                    
                    if selafinlayer.showmesh:
                        self.meshplot = self.ax.triplot(selafinlayer.triangulation, 'k,-',color = '0.5' , linewidth = 0.5, alpha = selafinlayer.alpha/100.0)
                    
                    time1.append("tricontourf : "+str(round(time.clock()-timestart,3)))
                    
                    
                    if selafinlayer.propertiesdialog.groupBox_schowvel.isChecked():
                        tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                        C = np.sqrt(np.array(tabvx)**2 + np.array(tabvy)**2)
                        self.temp = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                   scale=float(1/selafinlayer.propertiesdialog.doubleSpinBox_vel_scale.value()),
                                                   scale_units='xy',
                                                   cmap=  selafinlayer.cmap3_vel,
                                                   norm=selafinlayer.norm3_vel)
                        time1.append("quiver : "+str(round(time.clock()-timestart,3)))



                #***********************************************************************
                #Case 3 : new figure
                else:
                    #update selafinlayer parameters
                    selafinlayer.param_memoire = selafinlayer.param_gachette
                    selafinlayer.lvl_memoire=selafinlayer.lvl_gachette
                    selafinlayer.temps_memoire=selafinlayer.temps_gachette
                    selafinlayer.renderersizepx = sizepx
                    selafinlayer.alpha = selafinlayer.alpha_gachette
                    selafinlayer.cmap_gachette = selafinlayer.cmap
                    time1.append("nouveau")

                    #matplotlib figure construction
                    self.fig.set_size_inches(width,lenght)
                    self.ax.cla()
                    #no axis nor border
                    self.fig.patch.set_visible(False)
                    self.ax.axes.axis('off')
                    self.ax.set_ylim([rect[2],rect[3]])
                    self.ax.set_xlim([rect[0],rect[1]])
                    #graph 
                    time1.append("value : "+str(round(time.clock()-timestart,3)))

                    self.tricontourf1 = self.ax.tricontourf(selafinlayer.triangulation,selafinlayer.value,selafinlayer.lvl_gachette, 
                                                                            cmap=  selafinlayer.cmap3,norm=selafinlayer.norm3 ,alpha = selafinlayer.alpha/100.0,rasterized=True)
                                                                            
                    if selafinlayer.showmesh:
                        self.meshplot = self.ax.triplot(selafinlayer.triangulation, 'k,-',color = '0.5',linewidth = 0.5, alpha = selafinlayer.alpha/100.0)

                    if selafinlayer.propertiesdialog.groupBox_schowvel.isChecked():
                        tabx,taby,tabvx,tabvy = self.getVelocity(selafinlayer,rendererContext)
                        C = np.sqrt(np.array(tabvx)**2 + np.array(tabvy)**2)
                        self.temp = self.ax.quiver(tabx,taby,tabvx,tabvy,C,
                                                    scale=float(1/selafinlayer.propertiesdialog.doubleSpinBox_vel_scale.value()),
                                                    scale_units='xy',
                                                    cmap=  selafinlayer.cmap3_vel,
                                                    norm=selafinlayer.norm3_vel)
                        time1.append("quiver : "+str(round(time.clock()-timestart,3)))

                    
                    if selafinlayer.forcerefresh == True:
                        selafinlayer.forcerefresh = False

                    self.fig.subplots_adjust(0,0,1,1)
                

                #save qimage
                self.fig.savefig(buf,transparent=True,dpi = dpi2)
                time1.append("savefig : "+str(round(time.clock()-timestart,3)))
                buf.seek(0)
                image = QtGui.QImage.fromData(buf.getvalue())
                time1.append("qimage : "+str(round(time.clock()-timestart,3)))
                

                if DEBUG:
                    selafinlayer.propertiesdialog.textBrowser_2.append("Chargement carte : "+str(time1))
                return (True,image)

            except Exception, e :
                selafinlayer.propertiesdialog.textBrowser_2.append('getqimage1 : '+str(e))
                return(False,QImage())

        except Exception, e :
            selafinlayer.propertiesdialog.textBrowser_2.append('getqimage2 : '+str(e))
            return(False,QImage())
            
            
    def getVelocity(self,selafin,rendererContext):

        tabx=[]
        taby=[]
        tabvx=[]
        tabvy=[]
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        
        
        if selafin.propertiesdialog.comboBox_vel_method.currentIndex() in [0,1]:
            if selafin.propertiesdialog.comboBox_vel_method.currentIndex() == 0:
                nombrecalcul = selafin.propertiesdialog.spinBox_vel_relative.value()
                pasespace = int((rect[1]-rect[0])/nombrecalcul)
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0]/pasespace)*pasespace
                rect[2] = int(rect[2]/pasespace)*pasespace
                rangex = nombrecalcul+3
                rangey = nombrecalcul+3
                pasy = int((rect[3]-rect[2])/nombrecalcul)
            elif selafin.propertiesdialog.comboBox_vel_method.currentIndex() == 1 :
                pasespace = selafin.propertiesdialog.doubleSpinBox_vel_spatial_step.value()
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0]/pasespace)*pasespace
                rect[2] = int(rect[2]/pasespace)*pasespace
                rangex = int((rect[1]-rect[0])/pasespace)+3
                rangey = int((rect[3]-rect[2])/pasespace)+3

            for x2 in range(rangex):
                xtemp = rect[0]+x2*pasx
                for y2 in range(rangey):
                    ytemp = rect[2]+y2*pasy
                    results = selafin.identify(QgsPoint(xtemp,ytemp))
                    vx = float(results[1].values()[selafin.parametrevx])
                    vy = float(results[1].values()[selafin.parametrevy])

                    if not vx == 'nan' and not vy == 'nan':
                        tabx.append(xtemp)
                        taby.append(ytemp)
                        tabvx.append(vx)
                        tabvy.append(vy)
        elif selafin.propertiesdialog.comboBox_vel_method.currentIndex() == 2:
            tabx=selafin.slf.MESHX
            taby = selafin.slf.MESHY
            tabvx=selafin.values[selafin.parametrevx]
            tabvy=selafin.values[selafin.parametrevy]

        return tabx,taby,tabvx,tabvy