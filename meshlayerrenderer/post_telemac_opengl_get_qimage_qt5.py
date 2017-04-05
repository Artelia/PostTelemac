# -*- coding: utf-8 -*-

"""
/***************************************************************************
 PostTelemac
                                 A QGIS plugin
 Post Traitment or Telemac
                              -------------------
        begin                : 2015-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Artelia
        email                : patrice.Verchere@arteliagroup.com
 ***************************************************************************/
 
 ***************************************************************************/
 get Image class
 Generate a Qimage from selafin file to be displayed in map canvas 
 with tht draw method of posttelemacpluginlayer
 
Versions :
0.0 : debut

 ***************************************************************************/
"""

#import qgis
import qgis.core 
#import PyQT

#import matplotlib
#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
#from matplotlib import tri
#from matplotlib.backends.backend_agg import FigureCanvasAgg
#import numpy
import numpy as np

#other imports
from time import ctime
#import cStringIO
import gc
import time

from OpenGL.GL import *
from OpenGL.GL import shaders

#from PyQt4 import QtGui, QtCore
from qgis.PyQt import QtGui, QtCore
try:
    from qgis.PyQt.QtGui import QApplication
except:
    from qgis.PyQt.QtWidgets import  QApplication
    
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from PyQt4.QtOpenGL import QGLPixelBuffer, QGLFormat, QGLContext
except:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtOpenGL import  QGLFormat, QGLContext

import numpy
from math import log, ceil, exp

#from utilities import complete_filename, format_

from .post_telemac_pluginlayer_colormanager import *
from .post_telemac_abstract_get_qimage import *



PRECISION = 0.01

def roundUpSize(size):
    """return size roudup to the nearest power of 2"""
    if False:
        return  QSize(pow(2, ceil(log(size.width())/log(2))),
                     pow(2, ceil(log(size.height())/log(2)))) 
    else:
        return size


class MeshRenderer(AbstractMeshRenderer):

    #__imageChangeRequested = QtCore.pyqtSignal(qgis.core.QgsRenderContext)
    __imageChangeRequested = QtCore.pyqtSignal()
    RENDERER_TYPE = "OpenGL"

    def __init__(self, meshlayer, integertemp, vtx = [[0.0,0.0,0.0]], idx=[0]):
        AbstractMeshRenderer.__init__(self,meshlayer, integertemp, vtx = [[0.0,0.0,0.0]], idx=[0])
        #self.fig =  plt.figure(int)
        #self.canvas = FigureCanvasAgg(self.fig)
        #self.meshlayer = meshlayer
        #self.ax = self.fig.add_subplot(111)
        #Reprojected things
        #self.meshxreprojected, self.meshyreprojected = None, None
        self.goodpointindex  = None
        self.arraypoints = None

        
        #Opengl
        self.__vtxfacetodraw = numpy.require(vtx, numpy.float32, 'F')
        self.__idxfacetodraw = numpy.require(idx, numpy.int32, 'F')
        
        self.__vtxcanvas = numpy.require(vtx, numpy.float32, 'F')
        self.__idxcanvas = numpy.require(idx, numpy.int32, 'F')
        
        self.__vtxfacetotal = numpy.require(vtx, numpy.float32, 'F')
        self.__idxfacetotal = numpy.require(idx, numpy.int32, 'F')
        
        self.__pixBuf = None
        #self.__legend = legend

        #self.__legend.symbologyChanged.connect(self.__recompileNeeded)

        self.__colorPerElement = False
        self.__recompileShader = False

        self.__vtxfacetotal[:,2] = 0
        
        self.meshlayer = meshlayer
        
        self.__imageChangedMutex = QtCore.QMutex()
        
        self.__rendererContext = None
        self.__size = None
        self.__img = None
        
        self.__imageChangeRequested.connect(self.__drawInMainThread)
        self.__pixelColor = ''
        self.__pixelColorVelocity = ''
        
        self.__graduation = []
        self.__graduationvelocity = []
        
        self.timemax = 1000
        
        self.timestart = None
        
        
    #************************************************************************************
    #*************************************** Display behaviour******************************
    #************************************************************************************
    
    def CrsChanged(self):
        #ikle = self.meshlayer.hydrauparser.getIkle()
        #mesh = self.meshlayer.hydrauparser.getElemFaces()
        #nodecoords = np.array( [[self.meshxreprojected[i], self.meshyreprojected[i], 0.0]   for i in range(len(self.meshxreprojected))         ] )
        #nodecoords = np.array( [[self.facenodereprojected[0][i], self.facenodereprojected[1][i], 0.0]   for i in range(len(self.facenodereprojected[0]))         ] )
        
        #reset : facenode elemnode
        self.resetFaceNodeCoord()
        #self.resetIdx()
        
        self.resetMesh()
        
    def resetFaceNodeCoord(self, vtx = None):
        #__vtx
        if False:
            if vtx != None:
                self.__vtxfacetotal = numpy.require(vtx, numpy.float32, 'F')
                
            else:
                #self.__vtxfacetotal = np.array( [[self.meshxreprojected[i], self.meshyreprojected[i], 0.0]   for i in range(len(self.meshxreprojected))         ] )
                self.__vtxfacetotal = np.array( [[self.facenodereprojected[0][i], self.facenodereprojected[1][i], 0.0]   for i in range(len(self.facenodereprojected[0]))         ] )
        if True:
            try:
                self.__vtxfacetotal = np.array( [[self.facenodereprojected[0][i], self.facenodereprojected[1][i], 0.0]   for i in range(len(self.facenodereprojected[0]))         ] )
                self.__idxfacetotal = self.meshlayer.hydrauparser.getElemFaces()
                self.__idxfaceonlytotal = self.meshlayer.hydrauparser.getFaces()
                #wherebegin polygon
                self.__idxfacetotalcountidx = [0]
                self.__idxfacetotalcountlen = []
                
                
                
                for elem in self.__idxfacetotal:
                    self.__idxfacetotalcountidx.append((self.__idxfacetotalcountidx[-1] )+len(elem))
                    #self.__idxfacetotalcountlen.append(len(elem))
                self.__idxfacetotalcountidx = np.array(self.__idxfacetotalcountidx)
                self.__idxfacetotalcountlen = np.array( [len(elem) for elem in self.__idxfacetotal ] )
            except Exception as e:
                print('resetFaceNodeCoord ' + str(e))
            
        self.__vtxfacetodraw = self.__vtxfacetotal
        self.__idxfacetodraw = self.__idxfacetotal 
        self.__idxfaceonlytodraw = self.__idxfaceonlytotal
        if False:
            self.__idxfacetodraw1Darray = np.concatenate(self.__idxfacetodraw)
            self.__idxfaceonlytodraw1Darray = np.concatenate(self.__idxfaceonlytodraw)
        if True:
            """
            self.__idxfacetodraw1Darray = self.__idxfacetodraw.ravel()
            self.__idxfaceonlytodraw1Darray = self.__idxfaceonlytodraw.ravel()
            print ( self.__idxfacetodraw1Darray)
            """
            self.__idxfacetodraw1Darray = np.array([idx for idxs in self.__idxfacetodraw for idx in idxs])
            self.__idxfaceonlytodraw1Darray = np.array([idx for idxs in self.__idxfaceonlytodraw for idx in idxs])
        
    if False:
        def resetIdx(self,idx = None):
            #__idx
            if False:
                if idx != None:
                    if False:
                        try:
                            self.__idxfacetotal = numpy.require(idx, numpy.int32, 'F')
                        except Exception as e :
                            self.__idxfacetotal = idx
                    else:
                        self.__idxfacetotal = numpy.require(idx, numpy.int32, 'F')
                else:
                    #self.__idxfacetotal = self.meshlayer.hydrauparser.getIkle()
                    self.__idxfacetotal = self.meshlayer.hydrauparser.getElemFaces()
                    
            if True:
                self.__idxfacetotal = self.meshlayer.hydrauparser.getElemFaces()
                self.__idxfacetotal = self.meshlayer.hydrauparser.getElemFaces()
                
            self.__idxfacetodraw = self.__idxfacetotal 
        
        
    def resetMesh(self):
        self.__vtxmesh  = np.array( [[self.facenodereprojected[0][i], self.facenodereprojected[1][i], 0.0]   for i in range(len(self.facenodereprojected[0]))         ] )
        self.__idxmesh =  self.meshlayer.hydrauparser.getFaces()
        
        
    
    
    def CrsChanged2(self):
        ikle = self.meshlayer.hydrauparser.getIkle()
        nodecoords = np.array( [[self.meshxreprojected[i], self.meshyreprojected[i], 0.0]   for i in range(len(self.meshxreprojected))         ] )
        self.resetFaceNodeCoord(nodecoords)
        self.resetIdx(ikle)
        
            
    def change_cm_contour(self,cm_raw):
        """
        change the color map and layer symbology
        """
        self.cmap_contour_leveled = self.colormanager.fromColorrampAndLevels(self.lvl_contour, cm_raw)
        try:
            qgis.utils.iface.legendInterface().refreshLayerSymbology(self.meshlayer)
        except Exception as e:
            #print('openglgetimage -change_cm_contour ' +   str(e))
            #self.meshlayer.propertiesdialog.errorMessage( 'openglgetimage -change_cm_contour ' + str(e) )
            qgis.utils.iface.layerTreeView().refreshLayerSymbology(self.meshlayer.id())
        #transparency - alpha changed
        if self.cmap_contour_leveled != None and len(self.lvl_contour) > 0:
            colortemp = np.array(self.cmap_contour_leveled)
            for i in range(len(colortemp)):
                colortemp[i][3] = min(colortemp[i][3],self.alpha_displayed/100.0)
            #opengl
            try:
                gradudation=[]
                tempun = []
                
                if len(self.lvl_contour)>=3 :
                    for i,color in enumerate(colortemp):
                        gradudation.append(  (QtGui.QColor.fromRgbF(color[0],color[1],color[2] ,color[3]),  self.lvl_contour[i] , self.lvl_contour[i+1]    )   )
                else:
                    color = colortemp[0]
                    gradudation.append(  (QtGui.QColor.fromRgbF(color[0],color[1],color[2] ,color[3]),  self.lvl_contour[0] , self.lvl_contour[1]    )   )
                self.setGraduation(gradudation)
            except Exception as e:
                self.meshlayer.propertiesdialog.errorMessage( 'toggle graduation ' + str(e) )
    
        if self.meshlayer.draw:
            self.meshlayer.triggerRepaint()
            
            
    def change_cm_vel(self,cm_raw):
        """
        change_cm_vel
        change the color map and layer symbology
        """
        if False:
            cm = self.colormanager.arrayStepRGBAToCmap(cm_raw)
            self.cmap_mpl_vel,self.norm_mpl_vel , self.color_mpl_vel = self.colormanager.changeColorMap(cm,self.lvl_vel)
            try:
                qgis.utils.iface.legendInterface().refreshLayerSymbology(self.meshlayer)
            except Exception as e:
                #print('openglgetimage -change_cm_contour ' +   str(e))
                #self.meshlayer.propertiesdialog.errorMessage( 'openglgetimage -change_cm_contour ' + str(e) )
                qgis.utils.iface.layerTreeView().refreshLayerSymbology(self.meshlayer.id())
            #transparency - alpha changed
            if self.color_mpl_vel != None:
                colortemp = np.array(self.color_mpl_vel.tolist())
                for i in range(len(colortemp)):
                    colortemp[i][3] = min(colortemp[i][3],self.alpha_displayed/100.0)
                #redefine cmap_mpl_contour and norm_mpl_contour :
                self.cmap_mpl_vel,self.norm_mpl_vel = matplotlib.colors.from_levels_and_colors(self.lvl_vel,colortemp)
            #repaint
            if self.meshlayer.draw:
                self.meshlayer.triggerRepaint()
        else:
            #print 'change vl'
            self.cmap_vel_leveled = self.colormanager.fromColorrampAndLevels(self.lvl_vel, cm_raw)
            try:
                qgis.utils.iface.legendInterface().refreshLayerSymbology(self.meshlayer)
            except Exception as e:
                #print('openglgetimage -change_cm_contour ' +   str(e))
                #self.meshlayer.propertiesdialog.errorMessage( 'openglgetimage -change_cm_contour ' + str(e) )
                qgis.utils.iface.layerTreeView().refreshLayerSymbology(self.meshlayer.id())
                
            #transparency - alpha changed
            if self.cmap_vel_leveled != None and len(self.lvl_vel) > 0:
                colortemp = np.array(self.cmap_vel_leveled)
                if False :
                    for i in range(len(colortemp)):
                        colortemp[i][3] = min(colortemp[i][3],self.alpha_displayed/100.0)
                #opengl
                try:
                    gradudation=[]
                    tempun = []
                    
                    if len(self.lvl_vel)>=3 :
                        for i,color in enumerate(colortemp):
                            gradudation.append(  (QtGui.QColor.fromRgbF(color[0],color[1],color[2] ,color[3]),  self.lvl_vel[i] , self.lvl_vel[i+1]    )   )
                    else:
                        color = colortemp[0]
                        gradudation.append(  (QtGui.QColor.fromRgbF(color[0],color[1],color[2] ,color[3]),  self.lvl_vel[0] , self.lvl_vel[1]    )   )
                    self.setGraduationVelocity(gradudation)
                except Exception as e:
                    self.meshlayer.propertiesdialog.errorMessage( 'toggle graduation ' + str(e) )
        
            if self.meshlayer.draw:
                self.meshlayer.triggerRepaint()
            
    #************************************************************************************
    #*************************************** Main func : getimage ******************************
    #************************************************************************************
    



    
    def canvasPaned(self):
        if QApplication.instance().thread() != QtCore.QThread.currentThread():
            self.__img = None
            #self.__imageChangeRequested.emit(rendererContext)
            self.__imageChangeRequested.emit()
            
            i = 0
            while not self.__img  and not self.rendererContext.renderingStopped() and i < self.timemax :
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                i += 1
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                QtCore.QThread.msleep(1)
            
            if not self.rendererContext.renderingStopped():
                #if not self.showmesh:
                #painter.drawImage(0, 0, self.__img)
                return(self.__img,None)
                
        else:
            self.__drawInMainThread()
            #self.rendererContext.painter().drawImage(0, 0, self.__img)
            return(self.__img,None)
            
        
    def canvasChangedWithSameBBox(self):
        if False and self.__vtxcanvas == None:
            xMeshcanvas, yMeshcanvas, goodiklecanvas,self.goodpointindex = self.getCoordsIndexInCanvas(self.meshlayer,self.rendererContext)
            #self.resetIdx(goodiklecanvas)
            nodecoords = np.array( [[xMeshcanvas[i], yMeshcanvas[i], 0.0]   for i in range(len(xMeshcanvas))         ] )
            self.__vtxcanvas = numpy.require(nodecoords, numpy.float32, 'F')
            
            self.__idxcanvas = numpy.require(goodiklecanvas, numpy.int32, 'F')
            
            #self.resetFaceNodeCoord(nodecoords)
            #self.meshadaptedtocanvas = True
            
        #self.__vtxfacetodraw = self.__vtxcanvas
        #self.__idxfacetodraw = self.__idxcanvas
        
        
        if QApplication.instance().thread() != QtCore.QThread.currentThread():
            self.__img = None
            #self.__imageChangeRequested.emit(rendererContext)
            self.__imageChangeRequested.emit()
            
            i = 0
            while not self.__img  and not self.rendererContext.renderingStopped() and i < self.timemax :
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                i += 1
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                QtCore.QThread.msleep(1)
            
            if not self.rendererContext.renderingStopped():
                #if not self.showmesh:
                #painter.drawImage(0, 0, self.__img)
                return(self.__img,None)
                
        else:
            self.__drawInMainThread()
            #self.rendererContext.painter().drawImage(0, 0, self.__img)
            return(self.__img,None)
    
        
    def canvasCreation(self):
        #self.meshadaptedtocanvas = False
        
        #self.resetFaceNodeCoord()
        #self.resetIdx()
        
        self.__vtxcanvas = None
        self.__idxcanvas = None
        self.goodpointindex = None
        
        
        self.__vtxfacetodraw = self.__vtxfacetotal
        self.__idxfacetodraw = self.__idxfacetotal
        
        
        
        
        
        if QApplication.instance().thread() != QtCore.QThread.currentThread():
            try:
                self.__img = None
                #self.__imageChangeRequested.emit(rendererContext)
                self.__imageChangeRequested.emit()
                i = 0
                while not self.__img  and not self.rendererContext.renderingStopped() and i < self.timemax :
                    # active wait to avoid deadlocking if event loop is stopped
                    # this happens when a render job is cancellled
                    i += 1
                    QtCore.QThread.msleep(1)
                
                
                if not self.rendererContext.renderingStopped():
                    #if not self.showmesh:
                    #painter.drawImage(0, 0, self.__img)
                    #self.debugtext += ['img done : ' + str(round(time.clock()-self.timestart,3))  ]
                    return(self.__img,None)
            except Exception as e:
                print( str(e) )
                
        else:
            self.__drawInMainThread()
            #self.rendererContext.painter().drawImage(0, 0, self.__img)
            return(self.__img,None)
            
            
            
    def __drawInMainThread(self):
        
        #print rendererContext
        
        try:
        
            self.__imageChangedMutex.lock()
            
            includevel = True
            
            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 0 :
                list1 = self.meshlayer.value
            
            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 1:
            
                if self.meshlayer.hydrauparser.parametrevx!= None and self.meshlayer.hydrauparser.parametrevy != None:
                    list1 = np.stack((self.meshlayer.value, self.meshlayer.values[self.meshlayer.hydrauparser.parametrevx], self.meshlayer.values[self.meshlayer.hydrauparser.parametrevy]), axis=-1)
                else:
                    list1 = np.stack((self.meshlayer.value, np.array([0] * self.meshlayer.hydrauparser.facesnodescount), np.array([0] * self.meshlayer.hydrauparser.facesnodescount)), axis=-1)
            
                if True :
                    if self.goodpointindex != None:
                        list1 = list1[self.goodpointindex]
                        
                        
            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 2 :
                list1 = self.meshlayer.value
                        
                        

            self.__img = self.image(
                    list1,
                    self.sizepx,
                    #size,
                    (.5*(self.ext.xMinimum() + self.ext.xMaximum()),
                     .5*(self.ext.yMinimum() + self.ext.yMaximum())),
                    (self.rendererContext.mapToPixel().mapUnitsPerPixel(),
                     self.rendererContext.mapToPixel().mapUnitsPerPixel()),
                     self.rendererContext.mapToPixel().mapRotation())

                     
            self.__imageChangedMutex.unlock()
                     
        except Exception as e:
            print( 'draw ' + str(e) )

        
        
    #************************************************************************************
    #*************************************** Secondary func  ******************************
    #************************************************************************************
        
            
    def getVelocity(self,selafin,rendererContext):
        tabx=[]
        taby=[]
        tabvx=[]
        tabvy=[]
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        #print str(selafin.showvelocityparams)
        if selafin.showvelocityparams['type'] in [0,1]:
            if selafin.showvelocityparams['type'] == 0:
                nombrecalcul = selafin.showvelocityparams['step'] 
                pasespace = int((rect[1]-rect[0])/nombrecalcul)
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0]/pasespace)*pasespace
                rect[2] = int(rect[2]/pasespace)*pasespace
                rangex = nombrecalcul+3
                rangey = nombrecalcul+3
                pasy = int((rect[3]-rect[2])/nombrecalcul)
            elif selafin.showvelocityparams['type'] == 1 :
                pasespace = selafin.showvelocityparams['step'] 
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0]/pasespace)*pasespace
                rect[2] = int(rect[2]/pasespace)*pasespace
                rangex = int((rect[1]-rect[0])/pasespace)+3
                rangey = int((rect[3]-rect[2])/pasespace)+3
            
            x = np.arange(rect[0],rect[0]+rangex*pasx,pasx) 
            y = np.arange(rect[2],rect[2]+rangey*pasy,pasy)
            mesh = np.meshgrid(x,y)
            tabx = np.ravel(mesh[0].tolist())
            taby = np.ravel(mesh[1].tolist())
            if not selafin.triinterp :
                selafin.initTriinterpolator()
            """
            tabvx =  selafin.triinterp[selafin.parametrevx].__call__(tabx,taby)
            tabvy =  selafin.triinterp[selafin.parametrevy].__call__(tabx,taby)
            """
            tempx1, tempy1 = self.getTransformedCoords(tabx,taby,False)
            tabvx =  selafin.triinterp[selafin.hydrauparser.parametrevx].__call__(tempx1,tempy1)
            tabvy =  selafin.triinterp[selafin.hydrauparser.parametrevy].__call__(tempx1,tempy1)

        elif selafin.showvelocityparams['type'] == 2:
            if not self.goodpointindex == None :
                #tabx, taby = selafin.hydrauparser.getMesh()
                """
                tabx = self.meshxreprojected
                taby = self.meshyreprojected
                """
                tabx = self.facenodereprojected[0]
                taby = self.facenodereprojected[1]
                
                goodnum = self.goodpointindex
                tabx = tabx[goodnum]
                taby = taby[goodnum]
            else:
                tabx, taby, goodnum = self.getxynuminrenderer(selafin,rendererContext)
            tabvx=selafin.values[selafin.hydrauparser.parametrevx][goodnum]
            tabvy=selafin.values[selafin.hydrauparser.parametrevy][goodnum]
        return np.array(tabx),np.array(taby),np.array(tabvx),np.array(tabvy)
        

        
    def getxynuminrenderer(self,selafin,rendererContext):
        """
        Return index of selafin points in the visible canvas with corresponding x and y value
        """
        recttemp = rendererContext.extent()
        rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())] 
        """
        tabx, taby = selafin.hydrauparser.getMesh()
        tabx, taby = self.getTransformedCoords(tabx,taby)
        """
        """
        tabx = self.meshxreprojected
        taby = self.meshyreprojected
        """
        tabx = self.facenodereprojected[0]
        taby = self.facenodereprojected[1]
        
        valtabx = np.where(np.logical_and(tabx>rect[0], tabx< rect[1]))
        valtaby = np.where(np.logical_and(taby>rect[2], taby< rect[3]))
        goodnum = np.intersect1d(valtabx[0],valtaby[0])
        tabx = tabx[goodnum]
        taby = taby[goodnum]
        #badnum = np.setxor1d(valtabx[0],valtaby[0])
        return tabx,taby,goodnum
        
        

        
        
        
        
    #**********************************************************************************************
    #**********************************************************************************************
    #**********************************************************************************************
    #              OPENGL
    #**********************************************************************************************
    #**********************************************************************************************
        
    def __recompileNeeded(self):
        self.__recompileShader = True



    def __compileShaders(self):
    
        vertex_shader = shaders.compileShader("""
            varying float value;
            varying float w;
            varying vec3 normal;
            varying vec4 ecPos;
            void main()
            {
                ecPos = gl_ModelViewMatrix * gl_Vertex;
                normal = normalize(gl_NormalMatrix * gl_Normal);
                value = gl_MultiTexCoord0.st.x;
                w = value > 0.0 ? 1.0 : 0.0;
                gl_Position = ftransform();;
            }
            """, GL_VERTEX_SHADER)

        fragment_shader = shaders.compileShader(
            self._fragmentShader(), GL_FRAGMENT_SHADER)

        self.__shaders = shaders.compileProgram(vertex_shader, fragment_shader)
        #self.__legend._setUniformsLocation(self.__shaders)
        self.__recompileShader = False
        
    def toggleGraduation(self):
        #self.__graduated = bool(flag)
        self.__graduated = True
        #print self.__graduation
        if self.__graduated:
            self.__pixelColor = "vec4 pixelColor(float value)\n{\n"

            for c, min_, max_ in self.__graduation:
                """
                self.__pixelColor += "    if (float(%g) < value && value <= float(%g)) return vec4(%g, %g, %g, 1.);\n"%(
                        min_, max_, c.redF(), c.greenF(), c.blueF())
                """
                self.__pixelColor += "    if (float(%g) < value && value <= float(%g)) return vec4(%g, %g, %g, %g);\n"%(
                        min_, max_, c.redF(), c.greenF(), c.blueF(), c.alphaF())
            self.__pixelColor += "    return vec4(0., 0., 0., 0.);\n"
            self.__pixelColor += "}\n";
        else:
            self.__pixelColor = ColorLegend.__pixelColorContinuous
        #self.symbologyChanged.emit()
        self.__recompileNeeded()
        
    def toggleGraduationVelocity(self):
        #self.__graduated = bool(flag)
        self.__graduated = True
        #print self.__graduation
        if self.__graduated:
            self.__pixelColorVelocity = "vec4 pixelColor(float value)\n{\n"

            for c, min_, max_ in self.__graduationvelocity:
                """
                self.__pixelColor += "    if (float(%g) < value && value <= float(%g)) return vec4(%g, %g, %g, 1.);\n"%(
                        min_, max_, c.redF(), c.greenF(), c.blueF())
                """
                self.__pixelColorVelocity += "    if (float(%g) < value && value <= float(%g)) return vec4(%g, %g, %g, %g);\n"%(
                        min_, max_, c.redF(), c.greenF(), c.blueF(), c.alphaF())
            self.__pixelColorVelocity += "    return vec4(0., 0., 0., 0.);\n"
            self.__pixelColorVelocity += "}\n";
            #print self.__pixelColorVelocity 
        else:
            self.__pixelColorVelocity = ColorLegend.__pixelColorContinuous
        #self.symbologyChanged.emit()
        #self.__recompileNeeded()
        
        
    def setGraduation(self, graduation):
        """graduation is a list of tuple (color, min, max) the alpha componant is not considered"""
        
        self.__graduation = graduation
        #print self.__graduation
        self.toggleGraduation()
        
    def setGraduationVelocity(self, graduation):
        """graduation is a list of tuple (color, min, max) the alpha componant is not considered"""
        
        self.__graduationvelocity = graduation
        #print self.__graduation
        self.toggleGraduationVelocity()
        
    def _fragmentShader(self):
        """Return a string containing the definition of the GLSL pixel shader
            vec4 pixelColor(float value)
        This may contain global shader variables and should therefore
        be included in the fragment shader between the global variables
        definition and the main() declaration.
        Note that:
            varying float value
        must be defined by the vertex shader
        """
        return """
            varying float value;
            varying float w;
            varying vec3 normal;
            varying vec4 ecPos;
            uniform float transparency;
            uniform float minValue;
            uniform float maxValue;
            uniform bool logscale;
            uniform bool withNormals;
            uniform sampler2D tex;
            """+self.__pixelColor+"""
            void main()
            {
                gl_FragColor = pixelColor(value);
            }
            """
        
        

    def __resize(self, roundupImageSize):
        # QGLPixelBuffer size must be power of 2
        assert  roundupImageSize == roundUpSize(roundupImageSize)


        # force alpha format, it should be the default,
        # but isn't all the time (uninitialized)

        
        if False:
            fmt = QGLFormat()
            fmt.setAlpha(True)
            
            self.__pixBuf = QGLPixelBuffer(roundupImageSize, fmt)
            assert self.__pixBuf.format().alpha()
            self.__pixBuf.makeCurrent()
            self.__pixBuf.bindToDynamicTexture(self.__pixBuf.generateDynamicTexture())
            self.__compileShaders()
            self.__pixBuf.doneCurrent()
            
            self.__pixBufMesh = QGLPixelBuffer(roundupImageSize, fmt)
            assert self.__pixBufMesh.format().alpha()
            self.__pixBufMesh.makeCurrent()
            self.__pixBufMesh.bindToDynamicTexture(self.__pixBufMesh.generateDynamicTexture())
            self.__compileShaders()
            self.__pixBufMesh.doneCurrent()
            
        if True:
            #self.surface = QOffscreenSurface()
            self.surfaceFormat = QSurfaceFormat()
            
            self.context = QOpenGLContext()
            self.context.setFormat(self.surfaceFormat)
            self.context.create()
            
            self.surface = QOffscreenSurface()
            self.surface.setFormat(self.surfaceFormat)
            self.surface.create()
            
            self.context.makeCurrent(self.surface)
            self.__compileShaders()
            if True:
                fmt1 = QOpenGLFramebufferObjectFormat()
                self.__pixBuf = QOpenGLFramebufferObject(roundupImageSize,fmt1)
                self.__pixBuf.takeTexture()
                self.__pixBuf.bind()
            else:
                self.__pixBuf = QOpenGLFramebufferObject(roundupImageSize)
            self.context.doneCurrent()


    def image(self, values, imageSize, center, mapUnitsPerPixel, rotation=0):
        """Return the rendered image of a given size for values defined at each vertex
        or at each element depending on setColorPerElement.
        Values are normalized using valueRange = (minValue, maxValue).
        transparency is in the range [0,1]"""
        
        DEBUGTIME = False
        

        if DEBUGTIME :
            self.debugtext = []
            self.timestart = time.clock()
        
        
        if False:
            if QApplication.instance().thread() != QThread.currentThread():
                raise RuntimeError("trying to use gl draw calls in a thread")
                
        try:
            if not len(values):
                img = QImage(imageSize, QImage.Format_ARGB32)
                img.fill(Qt.transparent)
                return img

            roundupSz = roundUpSize(imageSize)
            if not self.__pixBuf \
                    or roundupSz.width() != self.__pixBuf.size().width() \
                    or roundupSz.height() != self.__pixBuf.size().height():
                #print('resize')
                self.__resize(roundupSz)


            val = numpy.require(values, numpy.float32) \
                    if not isinstance(values, numpy.ndarray)\
                    else values
                    
                    
            if self.__colorPerElement:
                val = numpy.concatenate((val,val,val))
            
            #try:
            #self.__pixBuf.makeCurrent()
            #self.context.makeCurrent()
            self.context.makeCurrent(self.surface)
            
            
            
            
            
            if True:
                
                #define current opengl drawing
                #self.__pixBuf.makeCurrent()
                #?
                if self.__recompileShader:
                    self.__compileShaders()
                    
                #init gl client
                #glClearColor(1., 1., 1., 1.)
                #glClearColor(0., 0., 0., 1.)
                glClearColor(0., 0., 0., 0.)
                # tell OpenGL that the VBO contains an array of vertices
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                glEnable(GL_TEXTURE_2D)

                if True:
                    #initialisation de la transparence
                    glEnable(GL_BLEND)
                    #la couleur de l'objet va etre (1-alpha_de_l_objet) * couleur du fond et (le_reste * couleur originale)
                    #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                    glBlendFunc(GL_SRC_ALPHA_SATURATE, GL_ONE)
                else:
                    glDisable(GL_BLEND)
                    glEnable(GL_ALPHA_TEST);
                    glAlphaFunc(GL_GREATER, 0.1) # Or some fitting threshold for your texture

                glShadeModel(GL_FLAT)
                # clear the buffer
                glClear(GL_COLOR_BUFFER_BIT)
                # set orthographic projection (2D only)
                glMatrixMode(GL_MODELVIEW)
                glLoadIdentity()
                
                

                
                # scale
                if True:
                    glScalef(2./(roundupSz.width()*mapUnitsPerPixel[0]),
                             2./(roundupSz.height()*mapUnitsPerPixel[1]),
                             1)
                else:
                    glScalef(2./(roundupSz.height()*mapUnitsPerPixel[0]),
                             2./(roundupSz.width()*mapUnitsPerPixel[1]),
                             1)
                         
                         
                # rotate
                glRotatef(-rotation, 0, 0, 1)
                ## translate
                glTranslatef(-center[0],
                             -center[1],
                             0)
                             
                glViewport(0,0,roundupSz.width(),roundupSz.height() )
                             
                             
                if DEBUGTIME : self.debugtext += ['init done : ' + str(round(time.clock()-self.timestart,3))  ]
                             

                if self.meshlayer.showmesh :   #draw triangle contour but not inside
                    #Draw the object here
                    glDisable(GL_TEXTURE_2D)
                    glUseProgram(0)
                    
                    if True:
                    
                        glColor4f(0.2,0.2,0.2,0.2)
                        glLineWidth(1) #or whatever
                        glPolygonMode(GL_FRONT, GL_LINE)
                        glPolygonMode(GL_BACK, GL_LINE)

                        #Draw the object here
                        glVertexPointerf(self.__vtxmesh)
                        glDrawElementsui(GL_LINES, self.__idxmesh)
                        
                        #glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
                        glPolygonMode(GL_FRONT, GL_FILL)
                        glPolygonMode(GL_BACK, GL_FILL)
                        
                        
                    
                    if False:
                        glPointSize(20.0)
                        glBegin(GL_POINTS)
                        
                        glColor3f( 1.,0,0  )
                        
                        glVertex3f(center[0], center[1], 0 )
                        
                        glColor3f( 0,0,1.  )
                        
                        glVertex3f(self.rect[0], self.rect[2], 0 )
                        
                        glVertex3f(self.rect[1], self.rect[2], 0 )
                        
                        glVertex3f(self.rect[0], self.rect[3], 0 )
                    
                        glEnd()
                    

                    if DEBUGTIME : self.debugtext += ['mesh done : ' + str(round(time.clock()-self.timestart,3))  ]
                    
                    
                if True:
                    if self.meshlayer.showvelocityparams['show']:
                            #glDisable(GL_TEXTURE_2D)
                            glEnable(GL_PROGRAM_POINT_SIZE)
                            glEnable(GL_TEXTURE_2D)
                            #print self.__vtxfacetodraw
                            

                                
                            if True:
                            
                                vertex_shader_vel = shaders.compileShader("""
                                
                                    #version 120
                                    varying float valuev;
                                    varying vec2 valuevel;
                                    varying vec2 hw;
                                    varying vec3 normal;
                                    varying vec4 ecPos;
                                    
                                    
                                    //out vec2 valuevel;
                                    //out vec2 hw;
                                    //out vec3 normal;
                                    //out vec4 ecPos;
                                    
                                    //varying float value ;
                                    void main()
                                    {
                                        ecPos = gl_ModelViewMatrix * gl_Vertex;
                                        normal = normalize(gl_NormalMatrix * gl_Normal);
                                        //value = gl_MultiTexCoord0.st.x;
                                        //valuev = gl_MultiTexCoord0.x;
                                        
                                        valuevel = gl_MultiTexCoord0.yz;
                                        //w = valuev > 0.0 ? 1.0 : 0.0;
                                        //gl_Position = ftransform();
                                        gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
                                        //gl_PointSize = 10.0;
                                    }
                                    """, GL_VERTEX_SHADER)
                            
                            if True :
                                """
                                https://www.opengl.org/wiki/Geometry_Shader_Examples
                                """
                            
                                geom_shader_vel = shaders.compileShader("""
                                    #version 150
                                    uniform float mapunitsperpixel;
                                    uniform float norm;
                                    uniform vec2 hw[];
                                    //varying in vec2 valuevel[];
                                    //varying vec2 valuevel[];
                                    in vec2 valuevel[];
                                    //varying in vec2 valuevel;
                                    out float value ;
                                    //out varying value ;
                                    //varying float value[] ;
                                    layout(points) in;
                                    //layout(line_strip, max_vertices = 2) out;
                                    layout(triangle_strip, max_vertices = 9) out;
                                    //layout(triangles, max_vertices = 6) out;

                                    void main()
                                    {
                                        float normfinal ;
                                        float valuedraw ;
                                        //float value ;
                                        //float normfinal = 1.0 ;
                                        
                                        float headsize = 2.0 ;
                                            
                                        //normfinal = norm ;
                                       
                                       value = sqrt( valuevel[0].x * valuevel[0].x + valuevel[0].y * valuevel[0].y ) ;
                                       
                                       if ( norm < 0.0 ) 
                                            {
                                            normfinal =  - 1.0 / norm ;
                                            valuedraw = value ;
                                            }
                                        else
                                            {
                                            normfinal = norm ;
                                            valuedraw = 1.0 ;
                                            }
                                        
                                        
                                        vec4 center = gl_in[0].gl_Position ;
                                        vec4 head = gl_in[0].gl_Position + vec4( valuevel[0].x  / hw[0].x  , valuevel[0].y / hw[0].y  , 0.0, 0.0) / mapunitsperpixel / normfinal / valuedraw ;
                                        
                                        vec4 arrowr = gl_in[0].gl_Position + vec4(  valuevel[0].y / headsize / hw[0].x , - valuevel[0].x / headsize  / hw[0].y  , 0.0, 0.0) / mapunitsperpixel / normfinal / valuedraw  ;
                                        vec4 arrowl =  gl_in[0].gl_Position + vec4(- valuevel[0].y / headsize / hw[0].x  ,  valuevel[0].x / headsize / hw[0].y  , 0.0, 0.0) / mapunitsperpixel / normfinal / valuedraw ;
                                        
                                        vec4 base = gl_in[0].gl_Position * 2  - ( head)  ;
                                        
                                        vec4 baser = base + ( arrowr - head ) / 2 ;
                                        
                                        vec4 basel = base + ( arrowl - head ) / 2 ;
                                        
                                        gl_Position = arrowl ;
                                        EmitVertex();
                                        gl_Position = arrowr ;
                                        EmitVertex();
                                        gl_Position = head ;
                                        EmitVertex();
                                        
                                        EndPrimitive();
                                        
                                        gl_Position = head ;
                                        EmitVertex();
                                        gl_Position = base ;
                                        EmitVertex();
                                        gl_Position = baser ;
                                        EmitVertex();
                                        
                                        EndPrimitive();
                                        
                                        gl_Position = head ;
                                        EmitVertex();
                                        gl_Position = base ;
                                        EmitVertex();
                                        gl_Position = basel ;
                                        EmitVertex();
                                        
                                        EndPrimitive();
                                        
                                    }
                                
                                    """, GL_GEOMETRY_SHADER)
                            
                            if True:
                                fragment_shader_vel = shaders.compileShader("""
                                    #version 150
                                    //varying float value;
                                    //varying vec2 valuevel;
                                    in float value;
                                    in vec2 valuevel;
                                    """+self.__pixelColorVelocity+"""
                                    
                                    void main() {
                                     //float valuetest ;
                                     //valuetest = sqrt( valuevel.x * valuevel.x + valuevel.y * valuevel.y ) ;
                                      //gl_FragColor = vec4(  min( value ,1.0  ), 0.0, 0.0, 1.0);
                                      gl_FragColor = pixelColor(value);
                                      
                                      }
                                 """, GL_FRAGMENT_SHADER)
                                 
                            self.__shadersvel = shaders.compileProgram(vertex_shader_vel, fragment_shader_vel, geom_shader_vel)
                                
                                
                                
                            #glDisableClientState(GL_TEXTURE_COORD_ARRAY)
                            #glClear(GL_COLOR_BUFFER_BIT)
                            glUseProgram(self.__shadersvel)
                            
                            
                            temp = glGetUniformLocation( self.__shadersvel, 'mapunitsperpixel' )
                            glUniform1f( temp , float(mapUnitsPerPixel[0]))
                            temp = glGetUniformLocation( self.__shadersvel, 'norm' )
                            glUniform1f( temp , float(self.meshlayer.showvelocityparams['norm'] )  )
                            temp = glGetUniformLocation( self.__shadersvel, 'hw' )
                            #glUniform2f( temp ,  float( imageSize.height() )  , float( imageSize.width() )   )
                            #glUniform2f( temp ,  float( imageSize.width() )  , float( imageSize.height() )   )
                            glUniform2f( temp ,  float( roundupSz.width() )  , float( roundupSz.height() )   )
                            
                            # these vertices contain 2 single precision coordinates
                            glVertexPointerf(self.__vtxfacetodraw)
                            glTexCoordPointer(3, GL_FLOAT, 0, val)
                            glDrawArrays(GL_POINTS, 0, len(self.__vtxfacetodraw))
                            
                            if DEBUGTIME : self.debugtext += ['velocity done : ' + str(round(time.clock()-self.timestart,3))  ]
                        
                    
                    
                    if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 0 :
                        try:
                            if False:
                                glEnable(GL_TEXTURE_2D)
                                glColor4f(0.2,0.2,0.2,0.2)
                                glVertexPointerf(self.__vtxfacetodraw)
                                
                                temp = np.array(sum(self.__idxfacetodraw.tolist(),[]))
                                #print self.__idxfacetodraw.shape
                                #print self.__idxfacetodraw.flatten().shape
                                #glDrawElementsui( GL_TRIANGLE_FAN, self.__idxfacetodraw)
                                for elem in self.__idxfacetodraw:
                                    if len(elem)>2:
                                        glDrawElementsui( GL_TRIANGLE_FAN, np.array(elem))
                                        
                            if False:
                                glUseProgram(0)
                                glDisable(GL_TEXTURE_2D)
                                glEnableClientState( GL_VERTEX_ARRAY )
                                #glEnable(GL_TEXTURE_2D)
                                glColor4f(0.2,0.2,0.2,0.2)
                                #print self.__graduation
                                glVertexPointerf(self.__vtxfacetodraw)
                                print( len(self.__idxfacetodraw) )
                                
                                #print 'len ' + str( len(self.__idxfacetodraw) ) + ' ' + str(len(val))
                                #print self.__graduation
                                
                                for i, elem in enumerate(self.__idxfacetodraw):
                                    if len(elem)>2:
                                        if val[i] > self.__graduation[-1][2]:
                                            continue
                                        j = 0
                                        while j < len(self.__graduation) and val[i] > self.__graduation[j][1]  :
                                            j+=1
                                        j+= -1

                                        #print j
                                        glColor4f(self.__graduation[j][0].redF(), self.__graduation[j][0].greenF(), self.__graduation[j][0].blueF() ,  self.__graduation[j][0].alphaF()   )
                                        #c.redF(), c.greenF(), c.blueF(), c.alphaF())
                                        
                                        
                                        if True:
                                            try:
                                                #print str(i) + '  ' + str(elem)
                                                glDrawElements(GL_TRIANGLE_FAN, len(elem), GL_UNSIGNED_BYTE, elem)
                                                #print str(i) + '  ' + str(elem)
                                            except Exception as e:
                                                print( str(e) )
                                        
                                        if False:
                                            glBegin(GL_TRIANGLE_FAN)
                                            for id in elem:
                                                glVertex2f(self.__vtxfacetodraw[id][0],self.__vtxfacetodraw[id][1])
                                            glEnd()
                                    
                            if True:
                                if DEBUGTIME : self.debugtext += ['param render start : ' + str(round(time.clock()-self.timestart,3))  ]
                                #glDisable(GL_TEXTURE_2D)
                                #glEnableClientState( GL_VERTEX_ARRAY )
                                glColor4f(0.2,0.2,0.2,0.2)
                                
                                if True:
                                    
                                    
                                    #print 'vertex'
                                    #vtx = self.__vtxfacetodraw[sum(self.__idxfacetodraw,[])]
                                    vtx = self.__vtxfacetodraw[self.__idxfacetodraw1Darray]
                                    if DEBUGTIME : self.debugtext += ['param render vertex interm : ' + str(round(time.clock()-self.timestart,3))  ]
                                    #print vtx
                                    #print np.array(vtx).shape
                                    #print str( vtx[0:10]    ) 
                                    glVertexPointerf(vtx)
                                    
                                if False:
                                    glVertexPointerf(self.__vtxfacetodraw)
                                    
                                if DEBUGTIME : self.debugtext += ['param render vertex done : ' + str(round(time.clock()-self.timestart,3))  ]
                                
                                if False:
                                    print( str(np.array(sum(self.__idxfacetodraw,[])).shape ) + ' ' + str() )
                                    print( str( self.__idxfacetotalcountidx[0:10]    ) + ' ' +str( self.__idxfacetotalcountidx[-10:] ))
                                    print( str( self.__idxfacetotalcountlen[0:10]    ) + ' ' +str( self.__idxfacetotalcountlen[-10:] ))
                                    print( str(  np.max( self.__idxfacetotalcountidx )  ))
                                    
                                    print( self.__idxfacetotalcountidx[0:2])
                                    print( self.__idxfacetotalcountlen[0:2])
                            

                                
                                
                                if True:
                                    #print 'render 1'
                                    glDisable(GL_TEXTURE_2D)
                                    glUseProgram(0)
                                    #glEnableClientState(GL_COLOR_ARRAY)
                                    glColor4f(0.2,0.2,0.2,0.2)
                                    """
                                    first = bounds[:-1]
                                    count = np.diff(bounds)
                                    primcount = len(bounds) - 1
                                    gl.glMultiDrawArrays(primtype, first, count, primcount)
                                    """
                                    
                                    #print 'render 2'
                                    if DEBUGTIME : self.debugtext += ['param render color begin : ' + str(round(time.clock()-self.timestart,3))  ]
                                    colors = np.zeros((len(val),4))
                                    #colors = np.zeros((np.max(np.array(sum(self.__idxfacetodraw,[])))+1,4))
                                    
                                    #print val.shape
                                    #print self.__idxfacetodraw.shape
                                    
                                    
                                    colors[:,:] = np.NAN
                                    #print colors
                                    
                                    
                                    for gradu in self.__graduation:
                                        #temp = np.where(val > gradu[1])
                                        #print np.where(np.logical_and(val > gradu[1], val < gradu[2]))
                                        tempidx = np.where(np.logical_and(val > gradu[1], val < gradu[2]))
                                        if len(tempidx)>0:
                                            #print np.array([gradu[0].redF()   , gradu[0].greenF() , gradu[0].blueF() ,gradu[0].alphaF() ])
                                            colors[tempidx] = [gradu[0].redF()   , gradu[0].greenF() , gradu[0].blueF() ,gradu[0].alphaF() ]
                                        #colors[np.logical_and(val > gradu[1], val < gradu[2])] = np.array([gradu[0].redF()   , gradu[0].greenF() , gradu[0].blueF() ,gradu[0].alphaF() ])
                                        
                                        #self.__graduation[j][0].redF(), self.__graduation[j][0].greenF(), self.__graduation[j][0].blueF() ,  self.__graduation[j][0].alphaF()
                                    
                                    #print colors
                                    colors[colors[:,0] == np.NAN] = np.array([0.,0.,0.,0.])
                                    #print colors.shape
                                    #print np.max(np.array(sum(self.__idxfacetodraw,[])))
                                    
                                    #colors2 = colors[sum(self.__idxfacetodraw,[])]
                                    if DEBUGTIME : self.debugtext += ['param render color end : ' + str(round(time.clock()-self.timestart,3))  ]
                                        
                                    #print 'render 3'
                                    first = self.__idxfacetotalcountidx[:-1]
                                    count = np.diff(self.__idxfacetotalcountidx)
                                    primcount = len(self.__idxfacetotalcountidx) - 1
                                    
                                    if DEBUGTIME : self.debugtext += ['param render first count end : ' + str(round(time.clock()-self.timestart,3))  ]
                                    
                                    if False:
                                        trueidx = np.where(count>2)
                                        first = first[trueidx]
                                        count = count[trueidx]
                                        primcount = len(first)
                                        
                                    #print '3bis'
                                    
                                    colors2 = np.repeat(colors,count, axis = 0)
                                    
                                    #print colors2.shape
                                    #print vtx.shape
                                    
                                    if DEBUGTIME : self.debugtext += ['param render first colorpointer begin : ' + str(round(time.clock()-self.timestart,3))  ]
                                    if True:
                                        glEnableClientState(GL_COLOR_ARRAY)
                                        #glColorPointerf(colors2)
                                        glColorPointer(4, GL_FLOAT, 0, colors2)
                                    if DEBUGTIME : self.debugtext += ['param render first colorpointer end : ' + str(round(time.clock()-self.timestart,3))  ]
                                    #colors = colors[trueidx]
                                    
                                    #print colors
                                    
                                    #print str(first[0:10]) + ' ' +str(first[-10:]) + ' ' + str(len(first))
                                    #print str(count[0:10])+ ' ' +str(count[-10:])+ ' ' + str(len(count))
                                    #print str( primcount )
                                    
                                    #print count[0]
                                    #print self.__idxfacetodraw[0:count]
                                    #idxtemp = np.array(sum(self.__idxfacetodraw,[]) )
                                    #print idxtemp
                                    #print 'render 4'
                                    glMultiDrawArrays(GL_TRIANGLE_FAN, first, count, primcount)
                                    if DEBUGTIME : self.debugtext += ['param render first draw array end : ' + str(round(time.clock()-self.timestart,3))  ]
                                    #glMultiDrawElements(GL_TRIANGLE_FAN, count[0], GL_UNSIGNED_BYTE, self.__idxfacetodraw, 1 )
                                    #glMultiDrawElements(GL_TRIANGLE_FAN, count, GL_UNSIGNED_BYTE, idxtemp, 10 )
                                    #print 'render 5'
                                    glDisableClientState(GL_COLOR_ARRAY)
                                
                                if False:
                                    glUseProgram(0)
                                    glEnable(GL_PRIMITIVE_RESTART)
                                    glPrimitiveRestartIndex(99999)
                                    if False and self.setprimitive :
                                        glPrimitiveRestartIndex(-1)
                                        self.setprimitive = False
                                    temp = []
                                    for i, elem in enumerate(self.__idxfacetodraw):
                                        if len(elem)>2:
                                            if i>0:
                                            
                                                temp1 = np.array(elem).tolist()
                                                temp1.insert(0,99999)
                                                temp.append(temp1)
                                            else:
                                                temp1 = np.array(elem).tolist()
                                                temp.append(temp1)
                                    idx1 = np.array(sum(temp,[]) )
                                    print(self.__idxfacetodraw[0:20])
                                    print(idx1[0:20])
                                    print(self.__vtxfacetodraw[0:4])
                                    
                                    
                                    #glDrawElements(GL_TRIANGLE_FAN, 20, GL_UNSIGNED_INT, idx1)
                                    glDrawElements(GL_TRIANGLE_FAN, 5, GL_UNSIGNED_BYTE, idx1)
                                
                                #glMultiDrawArrays(GL_TRIANGLE_FAN, self.__idxfacetotalcountidx[0:2], self.__idxfacetotalcountlen[0:2], 2) #; // 2 fans
                                    
                        except Exception as e:
                            print( 'face elem rendering ' + str(e) )
                        
                    
                    elif self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 1 :

                        glEnable(GL_TEXTURE_2D)
                        glUseProgram(self.__shaders)
                        
                        #self.__legend._setUniforms(self.__pixBuf)
                        # these vertices contain 2 single precision coordinates
                        glVertexPointerf(self.__vtxfacetodraw)
                        glTexCoordPointer(3, GL_FLOAT, 0, val)
                        glDrawElementsui(GL_TRIANGLES, self.__idxfacetodraw)
                        
                    elif self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 2 :
                        try:

                            if True:
                                """
                                self.__vtxfacetodraw = self.__vtxfacetotal
                                self.__idxfacetodraw = self.__idxfacetotal 
                                self.__idxfaceonlytodraw = self.__idxfaceonlytotal
                                self.__idxfacetodraw1Darray = np.concatenate(self.__idxfacetodraw)
                                self.__idxfaceonlytodraw1Darray = np.concatenate(self.__idxfaceonlytodraw)
                                """
                                
                                if DEBUGTIME : self.debugtext += ['param render start : ' + str(round(time.clock()-self.timestart,3))  ]
                                #glDisable(GL_TEXTURE_2D)
                                #glEnableClientState( GL_VERTEX_ARRAY )
                                glColor4f(0.2,0.2,0.2,0.2)
                                
                                if True:
                                    vtx = self.__vtxfacetodraw[self.__idxfaceonlytodraw1Darray]
                                    if DEBUGTIME : self.debugtext += ['param render vertex interm : ' + str(round(time.clock()-self.timestart,3))  ]
                                    #print vtx
                                    #print np.array(vtx).shape
                                    #print str( vtx[0:10]    ) 
                                    glVertexPointerf(vtx)
                                    
                                #print 'vtxshape ' + str(vtx.shape)
                                    
                                    
                                if DEBUGTIME : self.debugtext += ['param render vertex done : ' + str(round(time.clock()-self.timestart,3))  ]
                                
                                if False:
                                    print( str(np.array(sum(self.__idxfacetodraw,[])).shape ) + ' ' + str() )
                                    print( str( self.__idxfacetotalcountidx[0:10]    ) + ' ' +str( self.__idxfacetotalcountidx[-10:] ) )
                                    print( str( self.__idxfacetotalcountlen[0:10]    ) + ' ' +str( self.__idxfacetotalcountlen[-10:] ) )
                                    print( str(  np.max( self.__idxfacetotalcountidx )  ) )
                                    
                                    print( self.__idxfacetotalcountidx[0:2] )
                                    print( self.__idxfacetotalcountlen[0:2] )
                            

                                
                                
                                if True:
                                    #print 'render 1'
                                    glDisable(GL_TEXTURE_2D)
                                    glUseProgram(0)
                                    #glEnableClientState(GL_COLOR_ARRAY)
                                    glColor4f(0.2,0.2,0.2,0.2)
                                    """
                                    first = bounds[:-1]
                                    count = np.diff(bounds)
                                    primcount = len(bounds) - 1
                                    gl.glMultiDrawArrays(primtype, first, count, primcount)
                                    """
                                    
                                    #print 'render 2'
                                    if DEBUGTIME : self.debugtext += ['param render color begin : ' + str(round(time.clock()-self.timestart,3))  ]
                                    colors = np.zeros((len(val),4))
                                    #colors = np.zeros((np.max(np.array(sum(self.__idxfacetodraw,[])))+1,4))
                                    
                                    #print val.shape
                                    #print self.__idxfacetodraw.shape
                                    
                                    
                                    colors[:,:] = np.NAN
                                    #print colors
                                    
                                    
                                    for gradu in self.__graduation:
                                        #temp = np.where(val > gradu[1])
                                        #print np.where(np.logical_and(val > gradu[1], val < gradu[2]))
                                        tempidx = np.where(np.logical_and(val > gradu[1], val < gradu[2]))
                                        if len(tempidx)>0:
                                            #print np.array([gradu[0].redF()   , gradu[0].greenF() , gradu[0].blueF() ,gradu[0].alphaF() ])
                                            colors[tempidx] = [gradu[0].redF()   , gradu[0].greenF() , gradu[0].blueF() ,gradu[0].alphaF() ]
                                        #colors[np.logical_and(val > gradu[1], val < gradu[2])] = np.array([gradu[0].redF()   , gradu[0].greenF() , gradu[0].blueF() ,gradu[0].alphaF() ])
                                        
                                        #self.__graduation[j][0].redF(), self.__graduation[j][0].greenF(), self.__graduation[j][0].blueF() ,  self.__graduation[j][0].alphaF()
                                    
                                    #print colors
                                    colors[colors[:,0] == np.NAN] = np.array([0.,0.,0.,0.])
                                    #print colors.shape
                                    #print np.max(np.array(sum(self.__idxfacetodraw,[])))
                                    
                                    #colors2 = colors[sum(self.__idxfacetodraw,[])]
                                    if DEBUGTIME : self.debugtext += ['param render color end : ' + str(round(time.clock()-self.timestart,3))  ]
                                        
                                    #print 'render 3'
                                    #first = self.__idxfacetotalcountidx[:-1]
                                    #count = np.diff(self.__idxfacetotalcountidx)
                                    #primcount = len(self.__idxfacetotalcountidx) - 1
                                    
                                    if DEBUGTIME : self.debugtext += ['param render first count end : ' + str(round(time.clock()-self.timestart,3))  ]
                                    
                                        
                                    #print '3bis'
                                    
                                    colors2 = np.repeat(colors,2, axis = 0)
                                    
                                    #print colors2.shape
                                    #print vtx.shape
                                    
                                    if DEBUGTIME : self.debugtext += ['param render first colorpointer begin : ' + str(round(time.clock()-self.timestart,3))  ]
                                    if True:
                                        glEnableClientState(GL_COLOR_ARRAY)
                                        #glColorPointerf(colors2)
                                        glColorPointer(4, GL_FLOAT, 0, colors2)
                                    if DEBUGTIME : self.debugtext += ['param render first colorpointer end : ' + str(round(time.clock()-self.timestart,3))  ]
                                    #colors = colors[trueidx]
                                    
                                    #print colors
                                    
                                    #print str(first[0:10]) + ' ' +str(first[-10:]) + ' ' + str(len(first))
                                    #print str(count[0:10])+ ' ' +str(count[-10:])+ ' ' + str(len(count))
                                    #print str( primcount )
                                    
                                    #print count[0]
                                    #print self.__idxfacetodraw[0:count]
                                    #idxtemp = np.array(sum(self.__idxfacetodraw,[]) )
                                    #print idxtemp
                                    #print 'render 4'
                                    #print 'draw'
                                    glLineWidth(5) #or whatever
                                    glDrawArrays(GL_LINES, 0, len(vtx))
                                    #print 'draw2'
                                    #glDrawArrays(GL_POINTS, 0, len(self.__vtxfacetodraw))
                                    if DEBUGTIME : self.debugtext += ['param render first draw array end : ' + str(round(time.clock()-self.timestart,3))  ]
                                    #glMultiDrawElements(GL_TRIANGLE_FAN, count[0], GL_UNSIGNED_BYTE, self.__idxfacetodraw, 1 )
                                    #glMultiDrawElements(GL_TRIANGLE_FAN, count, GL_UNSIGNED_BYTE, idxtemp, 10 )
                                    #print 'render 5'
                                    glDisableClientState(GL_COLOR_ARRAY)
                                

                                    
                        except Exception as e:
                            print( 'face elem rendering ' + str(e) )
                    




                
                if DEBUGTIME : self.debugtext += ['param done : ' + str(round(time.clock()-self.timestart,3))  ]
            
            
            else:
                self.doRenderWork(val, imageSize, center, mapUnitsPerPixel, rotation)
            
            img = self.__pixBuf.toImage()
            #self.__pixBuf.doneCurrent()
            self.context.doneCurrent()
            
            if DEBUGTIME : self.debugtext += ['image done : ' + str(round(time.clock()-self.timestart,3))  ]
            if DEBUGTIME : self.meshlayer.propertiesdialog.textBrowser_2.append(str(self.debugtext))
            
            """
            if False:
                tempcopy = img.copy( 0,
                                 0,
                                 imageSize.width(), imageSize.height())
            
                             
            if True:
                tempcopy = img.copy( .5*(roundupSz.width()-imageSize.width()),
                                 .5*(roundupSz.height()-imageSize.height()),
                                 imageSize.width(), imageSize.height())
            if False:
                tempcopy = img.copy( -imageSize.width()/2.,
                                 -imageSize.height()/2.,
                                 imageSize.width(), imageSize.height())
                                 
            if False:
                tempcopy = img.copy( 1.0*(roundupSz.width()-imageSize.width()),
                                 1.0*(roundupSz.height()-imageSize.height()),
                                 imageSize.width(), imageSize.height())
                             
            if False:
                tempcopy.setDotsPerMeterX(int(self.dpi*39.3701))
                tempcopy.setDotsPerMeterY(int(self.dpi*39.3701))
                
            
            return img.copy( .5*(roundupSz.width()-imageSize.width()),
                             .5*(roundupSz.height()-imageSize.height()),
                             imageSize.width(), imageSize.height())
            
            
            
            if False:
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('Rendering report ***********************************'))
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('raw image size px : ') + str(img.size()))
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('image size px : ') + str(tempcopy.size()))
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('pixbuff size px : ') + str(self.__pixBuf.size()))
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('roundupSz size px : ') + str( roundupSz.width() )  +' ' +str(roundupSz.height())   )
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('decoup pixbuff : ') + str(.5*(roundupSz.width()-imageSize.width()))
                                                                     +' ' +str(.5*(roundupSz.height()-imageSize.height()) ) +' ' +str(imageSize.width()) 
                                                                     +' ' +str(imageSize.height()) )
                self.meshlayer.propertiesdialog.textBrowser_2.append(str('bbox : ') + str(self.rect))
                
                
            """

            
            if True:
                return img
                
            """
            if False:
                return tempcopy
            if False:
                img = QImage(QSize(imageSize.width()-10, imageSize.height()-10), QImage.Format_ARGB32)
                img.fill(Qt.blue)
                print('sizepx',self.sizepx)
                print(img.size())
                
                return img
            """
                             
                             
        except Exception as e :
            print( str(e) )
            return QImage()

