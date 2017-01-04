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
import scipy
import processing
import shapely
    
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
        self.qgspolygone =  None
        
    def computeVolumeMain(self):
        """
        Main method
        
        """
        
        METHOD = self.selafinlayer.propertiesdialog.comboBox_volumemethod.currentIndex()
        
        if METHOD in [0,2] :
            list1 = []
            list2 = []
            list3 = []
            
            try:
                for i, polygon in enumerate(self.polygons):
                    listpoly = [QgsPoint(polygon[i][0], polygon[i][1]) for i in range(len(polygon)) ]
                    self.qgspolygone =  QgsGeometry.fromPolygon([listpoly])
                    indextriangles = self.getTrianglesWithinPolygon(polygon)
                    
                    if len(indextriangles)==0:
                        continue
                    else:
                        volume = self.computeVolumeMesh(METHOD, indextriangles)
                        if len(list2) ==  0:
                            list1.append( self.selafinlayer.hydrauparser.getTimes().tolist() )
                            list2.append(volume)
                        else:
                            list2[0] += volume
                self.finished.emit(list1,list2,list3)
                
            except Exception, e :
                self.error.emit('volume calculation error : ' + str(e))
                self.finished.emit([],[],[])
                
        elif METHOD in [1,3] :
            list1 = []
            list2 = []
            list3 = []
            
            try:
                for i, polygon in enumerate(self.polygons):
                    listpoly = [QgsPoint(polygon[i][0], polygon[i][1]) for i in range(len(polygon)) ]
                    self.qgspolygone =  QgsGeometry.fromPolygon([listpoly])
                    #self.qgspolygone =  QgsGeometry.fromMultiPolygon([listpoly])
                    indexpoints,points = self.getPointsinPolygon(polygon)
                    indexpoints,points = self.getPointsOutsidePolygon(polygon,indexpoints,points)
                    
                    
                    for point in points.tolist() :
                        self.emitpoint.emit( [point[0]], [point[1]])
                    
                    if len(indexpoints)==0:
                        continue
                    else:
                        volume = self.computeVolumeVoronoiQGis(METHOD, points, indexpoints)
                        if len(list2) ==  0:
                            list1.append( self.selafinlayer.hydrauparser.getTimes().tolist() )
                            list2.append(volume)
                        else:
                            list2[0] += volume
                self.finished.emit(list1,list2,list3)
                
            except Exception, e :
                self.error.emit('volume calculation error : ' + str(e))
                self.finished.emit([],[],[])
                
        else:
            self.finished.emit([],[],[])
            
            
    def computeVolumeVoronoiScipy(self, METHOD , points, indexpoints):
        """
        Voronoi with scipy  method - not fully working
        """
        #getvoronoi table
        voronoi = scipy.spatial.Voronoi(points, furthest_site = False)
        vertices = voronoi.vertices
        regions = voronoi.regions
        #regions = [region for region in regions if (-1 not in region and len(region) > 0)]
        
        tempforresult = []  #contain point index and voronoi area
        for i, region in enumerate(regions):
            if (-1 not in region and len(region) > 0) :
                listpoly = [ QgsPoint(vertices[reg,0], vertices[reg,1]) for reg in region ]
                qgspolygonvoronoi =  QgsGeometry.fromPolygon([listpoly])
                if qgspolygonvoronoi.within(self.qgspolygone):
                    #draw reg
                    x = [vertices[reg,0] for reg in region]
                    y = [vertices[reg,1] for reg in region]
                    self.emitpoint.emit( x, y)
                    
                    area = qgspolygonvoronoi.area()
                    linkedpoint = indexpoints[voronoi.point_region.tolist().index(i)]
                    self.status.emit('Region : ' + str(region) + ' - Point lie : ' + str(linkedpoint) + ' - surface : ' +str(area))
                    tempforresult.append([linkedpoint, area])
        
        
        volume = None
        paramfreesurface = self.selafinlayer.hydrauparser.paramfreesurface
        parambottom = self.selafinlayer.hydrauparser.parambottom
        
        for i, result in enumerate(tempforresult):
            self.emitprogressbar.emit(float(float(i)/float(len(tempforresult))*100.0))
            if METHOD == 1:
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[parambottom, paramfreesurface]))
                if volume == None :
                    volume = result[1]*(h[1,0]-h[0,0])
                else:
                    volume += result[1]*(h[1,0]-h[0,0])
            elif METHOD == 3 :
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[self.selafinlayer.propertiesdialog.comboBox_volumeparam.currentIndex()]))
                if volume == None :
                    volume = result[1]*(h[0,0])
                else:
                    volume += result[1]*(h[0,0])
        return volume
            
            

            
            
    def computeVolumeVoronoiQGis(self, METHOD , points, indexpoints):
        """
        Voronoi with qgis method
        """
        self.status.emit('***** Nouveau calcul *****************')
        
        pointsdico = [shapely.geometry.Point(point[0], point[1]) for point in points ]
        c = processing.algs.qgis.voronoi.Context()
        sl = processing.algs.qgis.voronoi.SiteList(pointsdico)
        voropv = processing.algs.qgis.voronoi.voronoi(sl, c)
        self.status.emit(str(voropv))
        
        if False:
            self.status.emit(str('context *********'))
            self.status.emit(str(points))
            self.status.emit(str(c.vertices))
            self.status.emit(str(c.edges))
            self.status.emit(str(c.polygons))
            self.status.emit(str(' *********'))
            
        verticess = c.vertices
        voronoipolyg = []
        
        for (site, edges) in list(c.polygons.items()):
            #edges or not in he good order - order it
            edgesonly = [[edge[1], edge[2]]   for edge in edges]
            npedges = np.array(edgesonly)
            if -1 in npedges:       #edges with -1 are infinite line in polygon
                continue
            
            #fill goodph with first line
            goodpath = []
            goodpath.append(edges[0][1])
            goodpath.append(edges[0][2])
            
            #then add point in path
            i=3
            for i in range(len(edges) -2  ):
                temps = np.argwhere(npedges == goodpath[-1])
                for temp in temps:
                    if temp[1] == 0 :
                        if npedges[temp[0], 1 ] == goodpath[-2] :
                            continue
                        else:
                            goodpath.append(npedges[temp[0], 1 ])
                            break
                    elif temp[1] == 1 :
                        if npedges[temp[0], 0 ] == goodpath[-2] :
                            continue
                        else:
                            goodpath.append(npedges[temp[0], 0 ])
                            break

            listpoly = [QgsPoint(verticess[path][0], verticess[path][1]) for path in goodpath ]
            qgsvoropolygone =  QgsGeometry.fromPolygon([listpoly])
            
            
            #keep voronoi strictly within entry polygon
            if not qgsvoropolygone.within(self.qgspolygone):
                intersectedpolyg = QgsGeometry.fromPolygon( qgsvoropolygone.intersection(self.qgspolygone).asPolygon() )
            else:
                intersectedpolyg = QgsGeometry.fromPolygon( qgsvoropolygone.asPolygon() )
                
            voronoipolyg.append([indexpoints[site],intersectedpolyg])
            intersectedpolygtab = intersectedpolyg.asPolygon()
            if len(intersectedpolygtab)>0:
                x = [point[0] for point in intersectedpolygtab[0]]
                y = [point[1] for point in intersectedpolygtab[0]]
                self.emitpoint.emit( x, y)

        #volume compuation
        volume = None
        paramfreesurface = self.selafinlayer.hydrauparser.paramfreesurface
        parambottom = self.selafinlayer.hydrauparser.parambottom
        
        for i, result in enumerate( voronoipolyg ):
            self.emitprogressbar.emit(float(float(i)/float(len(voronoipolyg))*100.0))
            if METHOD == 1:
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[parambottom, paramfreesurface]))
                
                if volume == None :
                    volume = result[1].area()*(h[1,0]-h[0,0])
                else:
                    volume += result[1].area()*(h[1,0]-h[0,0])
                    
            elif METHOD == 3 :
                h =  np.array(self.selafinlayer.hydrauparser.getTimeSerie([result[0] +1 ],[self.selafinlayer.propertiesdialog.comboBox_volumeparam.currentIndex()]))
                
                if volume == None :
                    volume = result[1].area()*(h[0,0])
                else:
                    volume += result[1].area()*(h[0,0])
            
        
        
        return volume
            
            
            
    def getPointsinPolygon(self,polygon):
    
        #first get triangles in linebounding box ************************************************************
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 

        xMesh, yMesh = self.selafinlayer.hydrauparser.getMesh()

        valtabx = np.where(np.logical_and(xMesh>rect[0], xMesh< rect[1]))
        valtaby = np.where(np.logical_and(yMesh>rect[2], yMesh< rect[3]))
        
        goodnums = np.intersect1d(valtabx[0],valtaby[0])
        
        #second get triangles inside line  ************************************************************
        goodnums2=[]
        for goodnum in goodnums:
            if QgsGeometry.fromPoint(QgsPoint(xMesh[goodnum],yMesh[goodnum])).within(self.qgspolygone):
                goodnums2.append(goodnum)
                
        points = np.array([[xMesh[i], yMesh[i]] for i in goodnums2 ])
        
        
        return goodnums2,points
        
    def getPointsOutsidePolygon(self,polygon,indexpoints, points):
        """
        return a new triangulation based on triangles visbles in the canvas. 
        return index of selafin points correspondind to the new triangulation
        """
        
        #first get triangles in linebounding box ************************************************************
        
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        
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
        
        #second get triangles intersecting contour of polygon  ************************************************************
        goodnums2=[]
        qgspolygontoline = self.qgspolygone.convertToType(1)
        for goodnum in goodnums:
            if QgsGeometry.fromPolygon([[QgsPoint(xMesh[i],yMesh[i]) for i in mesh[goodnum]    ]]).intersects(qgspolygontoline):
                goodnums2.append(goodnum)
        
        pointstemp = points.tolist()
        
        for goodnum in goodnums2:
            for indexpoint in mesh[goodnum]:
                if not indexpoint in indexpoints:
                    indexpoints.append(indexpoint)
                    pointstemp.append([xMesh[indexpoint], yMesh[indexpoint]])
        
        
        return indexpoints,np.array(pointstemp)
            
    
    
    
        
    def getTrianglesWithinPolygon(self,polygon):
        """
        return a new triangulation based on triangles visbles in the canvas. 
        return index of selafin points correspondind to the new triangulation
        """
        
        #first get triangles in linebounding box ************************************************************
        
        mesh = np.array(self.selafinlayer.hydrauparser.getIkle())
        recttemp = self.qgspolygone.boundingBox()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        
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
        
    def computeVolumeMesh(self,METHOD,indextriangles):
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
            
            
            if METHOD == 0 :
                h = np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1,mesh[indextriangle,1] + 1,mesh[indextriangle,2] + 1],[parambottom, paramfreesurface]))
                
                if False and i == 0 :
                    self.status.emit('interm')
                    self.status.emit(str(h.shape))
                    self.status.emit(str(h))
                    self.status.emit(str(h1.shape))
                    self.status.emit(str(h1))
                    
                if volume == None :
                    #volume = surface*(h1+h2+h3)/3
                    volume = surface*((h[1,0] - h[0,0])+(h[1,1] - h[0,1] )+(h[1,2] - h[0,2]))/3
                else:
                    #volume += surface*(h1+h2+h3)/3
                    volume += surface*((h[1,0] - h[0,0])+(h[1,1] - h[0,1] )+(h[1,2] - h[0,2]))/3
                    
            elif METHOD == 2 :
                h = np.array(self.selafinlayer.hydrauparser.getTimeSerie([mesh[indextriangle,0] + 1,mesh[indextriangle,1] + 1,mesh[indextriangle,2] + 1],[self.selafinlayer.propertiesdialog.comboBox_volumeparam.currentIndex()]))
                
                if volume == None :
                    #volume = surface*(h1+h2+h3)/3
                    volume = surface*((h[0,0])+( h[0,1] )+( h[0,2]))/3
                else:
                    #volume += surface*(h1+h2+h3)/3
                    volume += surface*((h[0,0])+( h[0,1] )+(h[0,2]))/3
        
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
    
    