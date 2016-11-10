# -*- coding: utf-8 -*-

#unicode behaviour
from __future__ import unicode_literals

import qgis.gui
from qgis.core import QgsGeometry , QgsPoint
#import numpy
import numpy as np
#import matplotlib
#from matplotlib.path import Path
#import matplotlib.pyplot as plt
#import PyQT
from PyQt4 import QtCore, QtGui
#imports divers
import time
import math
import shapely
#from shapely.geometry import *
import os
from ..libs_telemac.samplers.meshes import *
    
debug = False



#*********************************************************************************************
#*************** Classe de traitement **********************************************************
#********************************************************************************************


class computeVolume(QtCore.QObject):

    def __init__(self,                
                selafin,line):
                
        
        
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.polygons = line
        
        #self.fig = plt.figure(0)
        
    def computeVolumeMain(self):
        """
        Main method
        
        """
        
        
        
        list1 = []
        list2 = []
        list3 = []
        
        try:
            for i, polygon in enumerate(self.polygons):
                self.status.emit('volume')
                indextriangles = self.getTrianglesWithinPolygon(polygon)
                self.status.emit('indexs triangle : ' + str(indextriangles))
                if len(indextriangles)==0:
                    continue
                    #self.finished.emit([],[],[])
                else:
                    volume = self.computeVolume(indextriangles)
                    if i == 0:
                        list1.append( self.selafinlayer.hydrauparser.getTimes().tolist() )
                        list2.append(volume)
                    else:
                        list2[0] += volume
            self.finished.emit(list1,list2,list3)
            
        except Exception, e :
            self.error.emit('volume calculation error : ' + str(e))
            self.finished.emit([],[],[])
        
        
    def getTrianglesWithinPolygon(self,polygon):
        """
        return a new triangulation based on triangles visbles in the canvas. 
        return index of selafin points correspondind to the new triangulation
        """
        
        #first get triangles in linebounding box ************************************************************
        listpoly = [QgsPoint(polygon[i][0], polygon[i][1]) for i in range(len(polygon)) ]
        #self.status.emit(str(listpoly))
        self.qgspolygone =  QgsGeometry.fromPolygon([listpoly])
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        """
        xMesh, yMesh = selafin.hydrauparser.getMesh()
        xMesh, yMesh = self.getTransformedCoords(xMesh, yMesh)
        """
        
        """
        xMesh = self.meshxreprojected
        yMesh = self.meshyreprojected
        
        """
        
        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()

        trianx = np.array( [ xMesh[mesh[:,0]], xMesh[mesh[:,1]], xMesh[mesh[:,2]]] )
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:,0]], yMesh[mesh[:,1]], yMesh[mesh[:,2]]]
        triany = np.transpose(triany)
        
        valtabx = np.where(np.logical_and(trianx>rect[0], trianx< rect[1]))
        valtaby = np.where(np.logical_and(triany>rect[2], triany< rect[3]))
        #index of triangles in canvas
        goodnums = np.intersect1d(valtabx[0],valtaby[0])
        #goodikle = mesh[goodnums]
        #goodpointindex = np.unique(goodikle)
        
        #second get triangles inside line  ************************************************************
        goodnums2=[]
        for goodnum in goodnums:
            if QgsGeometry.fromPolygon([[QgsPoint(xMesh[i],yMesh[i]) for i in mesh[goodnum]    ]]).within(self.qgspolygone):
                goodnums2.append(goodnum)
                
        
        for goodnum in goodnums2:
            xtoprint = [xMesh[i] for i in mesh[goodnum]  ]
            ytoprint = [yMesh[i] for i in mesh[goodnum]  ]
            #self.status.emit(str(xtoprint)+' ' +str(ytoprint))
            self.emitpoint.emit( xtoprint,ytoprint)
            
        return goodnums2
        
    def computeVolume(self,indextriangles):
        #self.status.emit('surf calc ')
        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        paramfreesurface = self.selafinlayer.hydrauparser.paramfreesurface
        parambottom = self.selafinlayer.hydrauparser.parambottom
        volume = None
        
        #self.status.emit(str(indextriangles))
        
        
        
        for i, indextriangle in enumerate(indextriangles):
            
            self.emitprogressbar.emit(float(float(i)/float(len(indextriangles))*100.0))
                
            #surface calculus
            p1 = np.array( [ xMesh[mesh[indextriangle,0]], yMesh[mesh[indextriangle,0]] ] )
            p2 = np.array( [ xMesh[mesh[indextriangle,1]], yMesh[mesh[indextriangle,1]] ] )
            p3 = np.array( [ xMesh[mesh[indextriangle,2]], yMesh[mesh[indextriangle,2]] ] )

            
            surface = float(np.linalg.norm(np.cross((p2-p1),(p3-p1))))/2.0
            #self.status.emit('surf : ' + str(surface))
            if False:
                h1 =np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1],[paramfreesurface])[0][0]) - np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1],[parambottom])[0][0])
                h2 =np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,1] + 1],[paramfreesurface])[0][0]) - np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,1] + 1],[parambottom])[0][0])
                h3 =np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,2] + 1],[paramfreesurface])[0][0]) - np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,2] + 1],[parambottom])[0][0])
            #else:
            h = np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1,mesh[indextriangle,1] + 1,mesh[indextriangle,2] + 1],[paramfreesurface])) - np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1,mesh[indextriangle,1] + 1,mesh[indextriangle,2] + 1],[parambottom]))
            if False and i == 0 :
                self.status.emit('interm')
                self.status.emit(str(h.shape))
                self.status.emit(str(h))
                self.status.emit(str(h1.shape))
                self.status.emit(str(h1))
                
            if volume == None :
                #volume = surface*(h1+h2+h3)/3
                volume = surface*(h[0,0]+h[0,1]+h[0,2])/3
            else:
                #volume += surface*(h1+h2+h3)/3
                volume += surface*(h[0,0]+h[0,1]+h[0,2])/3
        
        return volume

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(list,list)
    emitprogressbar = QtCore.pyqtSignal(float)

        

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitComputeVolume(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = QtCore.QThread()
        self.worker = None
        self.processtype = 0

    def start(self,                 
                 selafin,
                 line):
        #Launch worker
        self.worker = computeVolume(selafin,line)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.computeVolumeMain)
        self.worker.status.connect(self.writeOutput)
        self.worker.emitpoint.connect(self.emitPoint)
        self.worker.error.connect(self.raiseError)
        self.worker.emitprogressbar.connect(self.updateProgressBar)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        

    
    def raiseError(self,str):
        if self.processtype ==0:
            self.error.emit(str)
        elif self.processtype in [1,2,3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print str
            sys.exit(0)
            
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self,list1,list2,list3):
        self.finished1.emit(list1,list2,list3)

    def emitPoint(self,x,y):
        self.emitpoint.emit(x,y)
        
    def updateProgressBar(self,float1):
        self.emitprogressbar.emit(float1)
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(list,list,list)
    emitpoint = QtCore.pyqtSignal(list,list)
    emitprogressbar = QtCore.pyqtSignal(float)
    
class VolumeMapTool(qgis.gui.QgsMapTool):

    def __init__(self, canvas,button):
        qgis.gui.QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QtGui.QCursor(QtCore.Qt.CrossCursor)
        self.button = button

    def canvasMoveEvent(self,event):
        self.emit( QtCore.SIGNAL("moved"), {'x': event.pos().x(), 'y': event.pos().y()} )


    def canvasReleaseEvent(self,event):
        if event.button() == QtCore.Qt.RightButton:
            self.emit( QtCore.SIGNAL("rightClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )
        else:
            self.emit( QtCore.SIGNAL("leftClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )

    def canvasDoubleClickEvent(self,event):
        self.emit( QtCore.SIGNAL("doubleClicked"), {'x': event.pos().x(), 'y': event.pos().y()} )

    def activate(self):
        qgis.gui.QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)
        #print  'activate'
        #self.button.setEnabled(False)
        #self.button.setCheckable(True)
        #self.button.setChecked(True)



    def deactivate(self):
        self.emit( QtCore.SIGNAL("deactivate") )
        #self.button.setCheckable(False)
        #self.button.setEnabled(True)
        #print  'deactivate'
        qgis.gui.QgsMapTool.deactivate(self)


    def setCursor(self,cursor):
        self.cursor = QtGui.QCursor(cursor)
    
    