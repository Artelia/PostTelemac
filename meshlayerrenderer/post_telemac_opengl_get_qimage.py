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
from PyQt4 import QtGui, QtCore
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
import cStringIO
import gc
import time

from OpenGL.GL import *
from OpenGL.GL import shaders

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import QGLPixelBuffer, QGLFormat, QGLContext

import numpy
from math import log, ceil, exp

from utilities import complete_filename, format_

from post_telemac_pluginlayer_colormanager import *
from post_telemac_abstract_get_qimage import *

PRECISION = 0.01

def roundUpSize(size):
    """return size roudup to the nearest power of 2"""
    return QSize(pow(2, ceil(log(size.width())/log(2))),
                 pow(2, ceil(log(size.height())/log(2))))


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
        self.triangulation = None   #the reprojected triangulation
        self.meshxreprojected, self.meshyreprojected = None, None
        #mpl figures
        self.tricontourf1 = None    #the contour plot
        self.meshplot = None    #the meshplot
        self.quiverplot = None  #the quiver plot
        self.tritemp = None #the matplotlib triangulation centred on canvas view
        #other
        self.image_mesh = None
        self.goodpointindex  = None
        self.arraypoints = None

        
        #Opengl
        self.__vtxtodraw = numpy.require(vtx, numpy.float32, 'F')
        self.__idxtodraw = numpy.require(idx, numpy.int32, 'F')
        
        self.__vtxcanvas = numpy.require(vtx, numpy.float32, 'F')
        self.__idxcanvas = numpy.require(idx, numpy.int32, 'F')
        
        self.__vtxtotal = numpy.require(vtx, numpy.float32, 'F')
        self.__idxtotal = numpy.require(idx, numpy.int32, 'F')
        
        self.__pixBuf = None
        #self.__legend = legend

        #self.__legend.symbologyChanged.connect(self.__recompileNeeded)

        self.__colorPerElement = False
        self.__recompileShader = False

        self.__vtxtotal[:,2] = 0
        
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
        
        
    #************************************************************************************
    #*************************************** Display behaviour******************************
    #************************************************************************************
    
    def CrsChanged(self):
        ikle = self.meshlayer.hydrauparser.getIkle()
        nodecoords = np.array( [[self.meshxreprojected[i], self.meshyreprojected[i], 0.0]   for i in range(len(self.meshxreprojected))         ] )
        self.resetCoord(nodecoords)
        self.resetIdx(ikle)
        
            
    def change_cm_contour(self,cm_raw):
        """
        change the color map and layer symbology
        """
        self.cmap_contour_leveled = self.colormanager.fromColorrampAndLevels(self.lvl_contour, cm_raw)
        
        qgis.utils.iface.legendInterface().refreshLayerSymbology(self.meshlayer)
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
            except Exception, e:
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
            qgis.utils.iface.legendInterface().refreshLayerSymbology(self.meshlayer)
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
            
            qgis.utils.iface.legendInterface().refreshLayerSymbology(self.meshlayer)
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
                except Exception, e:
                    self.meshlayer.propertiesdialog.errorMessage( 'toggle graduation ' + str(e) )
        
            if self.meshlayer.draw:
                self.meshlayer.triggerRepaint()
            
    #************************************************************************************
    #*************************************** Main func : getimage ******************************
    #************************************************************************************
    



    
    def canvasPaned(self):
        if QtGui.QApplication.instance().thread() != QtCore.QThread.currentThread():
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
        if self.__vtxcanvas == None:
            xMeshcanvas, yMeshcanvas, goodiklecanvas,self.goodpointindex = self.getCoordsIndexInCanvas(self.meshlayer,self.rendererContext)
            #self.resetIdx(goodiklecanvas)
            nodecoords = np.array( [[xMeshcanvas[i], yMeshcanvas[i], 0.0]   for i in range(len(xMeshcanvas))         ] )
            self.__vtxcanvas = numpy.require(nodecoords, numpy.float32, 'F')
            
            self.__idxcanvas = numpy.require(goodiklecanvas, numpy.int32, 'F')
            
            #self.resetCoord(nodecoords)
            #self.meshadaptedtocanvas = True
            
        self.__vtxtodraw = self.__vtxcanvas
        self.__idxtodraw = self.__idxcanvas
        
        
        if QtGui.QApplication.instance().thread() != QtCore.QThread.currentThread():
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
        
        #self.resetCoord()
        #self.resetIdx()
        
        self.__vtxcanvas = None
        self.__idxcanvas = None
        self.goodpointindex = None
        
        
        self.__vtxtodraw = self.__vtxtotal
        self.__idxtodraw = self.__idxtotal
        
        
        
        
        
        if QtGui.QApplication.instance().thread() != QtCore.QThread.currentThread():
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
                    self.debugtext += ['img done : ' + str(round(time.clock()-self.timestart,3))  ]
                    return(self.__img,None)
            except Exception, e:
                print str(e)
                
        else:
            self.__drawInMainThread()
            #self.rendererContext.painter().drawImage(0, 0, self.__img)
            return(self.__img,None)
            
            
            
    def __drawInMainThread(self):
        
        #print rendererContext
        
        try:
        
            self.__imageChangedMutex.lock()
            
            
            
            #xMeshcanvas, yMeshcanvas, goodiklecanvas,self.goodpointindex = self.getCoordsIndexInCanvas(self.meshlayer,self.__rendererContext)
            #self.resetIdx(goodiklecanvas)
            #nodecoords = np.array( [[xMeshcanvas[i], yMeshcanvas[i], 0.0]   for i in range(len(xMeshcanvas))         ] )
            #self.resetCoord(nodecoords)
            
            if False:
                transform = self.rendererContext.coordinateTransform()
                ext = self.rendererContext.extent()
                mapToPixel = self.rendererContext.mapToPixel()
                
                size = QtCore.QSize((ext.xMaximum()-ext.xMinimum())/mapToPixel.mapUnitsPerPixel(),
                             (ext.yMaximum()-ext.yMinimum())/mapToPixel.mapUnitsPerPixel()) \
                                     if abs(mapToPixel.mapRotation()) < .01 else self.sizepx            
            
            includevel = True
            
            """
            if self.goodpointindex == None:
                value = self.meshlayer.value
                if includevel :
                    list1 = [[value[i], self.meshlayer.values[self.meshlayer.hydrauparser.parametrevx][i],  self.meshlayer.values[self.meshlayer.hydrauparser.parametrevy][i]] for i in range(len(value))]
                    list1 = np.array(list1)
            else:
                value = self.meshlayer.value[self.goodpointindex]
                if includevel :
                    list1 = [[self.meshlayer.value[i], self.meshlayer.values[self.meshlayer.hydrauparser.parametrevx][i],  self.meshlayer.values[self.meshlayer.hydrauparser.parametrevy][i]] for i in range(len(self.meshlayer.value))]
                    list1 = np.array(list1)[self.goodpointindex]
            """
            if False:
                value = self.meshlayer.value
                print value
                print value.shape
                list1 = [[value[i], self.meshlayer.values[self.meshlayer.hydrauparser.parametrevx][i],  self.meshlayer.values[self.meshlayer.hydrauparser.parametrevy][i]] for i in range(len(value))]
                list1 = np.array(list1)
                
                
                if True :
                    if self.goodpointindex != None:
                        list1 = list1[self.goodpointindex]
            else:
                if self.meshlayer.hydrauparser.parametrevx!= None and self.meshlayer.hydrauparser.parametrevy != None:
                    list1 = np.stack((self.meshlayer.value, self.meshlayer.values[self.meshlayer.hydrauparser.parametrevx], self.meshlayer.values[self.meshlayer.hydrauparser.parametrevy]), axis=-1)
                else:
                    list1 = np.stack((self.meshlayer.value, np.array([0] * self.meshlayer.hydrauparser.pointcount), np.array([0] * self.meshlayer.hydrauparser.pointcount)), axis=-1)
            
                if True :
                    if self.goodpointindex != None:
                        list1 = list1[self.goodpointindex]
                        
                        
            """
            if rendererContext != None :
                ext = rendererContext.extent()
                mapToPixel = rendererContext.mapToPixel()
                size = QtCore.QSize((ext.xMaximum()-ext.xMinimum())/mapToPixel.mapUnitsPerPixel(),
                                 (ext.yMaximum()-ext.yMinimum())/mapToPixel.mapUnitsPerPixel())
            """
            

            self.__img = self.image(
                    list1,
                    self.sizepx,
                    #size,
                    (.5*(self.ext.xMinimum() + self.ext.xMaximum()),
                     .5*(self.ext.yMinimum() + self.ext.yMaximum())),
                    (self.rendererContext.mapToPixel().mapUnitsPerPixel(),
                     self.rendererContext.mapToPixel().mapUnitsPerPixel()),
                     self.rendererContext.mapToPixel().mapRotation())
            """
            
            self.__img = self.image(
                    list1,
                    self.sizepx,
                    #size,
                    (.5*(ext.xMinimum() + ext.xMaximum()),
                     .5*(ext.yMinimum() + ext.yMaximum())),
                    (rendererContext.mapToPixel().mapUnitsPerPixel(),
                     rendererContext.mapToPixel().mapUnitsPerPixel()),
                     rendererContext.mapToPixel().mapRotation())
            """
                     
            self.__imageChangedMutex.unlock()
                     
        except Exception, e:
            print 'draw ' + str(e)

        
        

                
    """
                


    def getimage(self,meshlayer,rendererContext):
    
        DEBUG = True
        self.debugtext = []
        self.timestart = time.clock()
    
        try:
            painter = rendererContext.painter()
            self.__imageChangedMutex.lock()
            self.__rendererContext = qgis.core.QgsRenderContext(rendererContext)
            self.__rendererContext.setPainter(None)
            self.__size = painter.viewport().size()
            self.__img = None
            self.__imageChangedMutex.unlock()
            
            if False:    #size test
                recttemp = rendererContext.extent()
                rect = [float(recttemp.xMinimum()), float(recttemp.xMaximum()), float(recttemp.yMinimum()), float(recttemp.yMaximum())]
                mupp = float(rendererContext.mapToPixel().mapUnitsPerPixel())
                sizepx = [ round(((rect[1] - rect[0] )/mupp),2) , round(((rect[3]  - rect[2] )/mupp),2) ]
                dpi1 = rendererContext.painter().device().logicalDpiX()
                dpi2 =dpi1
                #matplotlib figure dimension
                width= (sizepx[0])/dpi1
                lenght = (sizepx[1])/dpi1
                
                if False:
                    print 'size opengl : ' + str(self.__size.width())+ ' ' +str(self.__size.height())
                    print 'size mpl : ' + str(width) + ' ' + str(lenght)
                    print 'size mpl2 : ' + str(sizepx) 
                    print str(abs(rendererContext.mapToPixel().mapRotation()) )
            
            if QtGui.QApplication.instance().thread() != QtCore.QThread.currentThread():
                self.__imageChangeRequested.emit()
                
                while not self.__img  and not self.__rendererContext.renderingStopped():
                    # active wait to avoid deadlocking if event loop is stopped
                    # this happens when a render job is cancellled
                    QtCore.QThread.msleep(1)
                
                if not rendererContext.renderingStopped():
                    #if not self.showmesh:
                    #painter.drawImage(0, 0, self.__img)
                    if DEBUG : self.debugtext += ['deplacement : ' + str(round(time.clock()-self.timestart,3))  ]
                    if DEBUG : self.meshlayer.propertiesdialog.textBrowser_2.append(str(self.debugtext))
                    return(True,self.__img,None)
                    
            else:
                self.__drawInMainThread()
                painter.drawImage(0, 0, self.__img)
                return(True,self.__img,None)
            
            
            
            
        except Exception, e :
            meshlayer.propertiesdialog.textBrowser_2.append('getqimage1 : '+str(e))
            return(False,QtGui.QImage(),QtGui.QImage())

            
            
            
    def __drawInMainThread(self):
        self.__imageChangedMutex.lock()
        
        
        transform = self.__rendererContext.coordinateTransform()
        ext = self.__rendererContext.extent()
        mapToPixel = self.__rendererContext.mapToPixel()
        
        size = QtCore.QSize((ext.xMaximum()-ext.xMinimum())/mapToPixel.mapUnitsPerPixel(),
                     (ext.yMaximum()-ext.yMinimum())/mapToPixel.mapUnitsPerPixel()) \
                             if abs(mapToPixel.mapRotation()) < .01 else self.__size



        self.__img = self.image(
                #self.meshlayer.value,
                self.meshlayer.value,
                size,
                (.5*(ext.xMinimum() + ext.xMaximum()),
                 .5*(ext.yMinimum() + ext.yMaximum())),
                (mapToPixel.mapUnitsPerPixel(),
                 mapToPixel.mapUnitsPerPixel()),
                 mapToPixel.mapRotation())
        
        
        self.__imageChangedMutex.unlock()
    
    """
        
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
                tabx = self.meshxreprojected
                taby = self.meshyreprojected
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
        tabx = self.meshxreprojected
        taby = self.meshyreprojected
        
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
        assert roundupImageSize == roundUpSize(roundupImageSize)

        # force alpha format, it should be the default,
        # but isn't all the time (uninitialized)
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

    def resetCoord(self, vtx = None):
        #__vtx
        if vtx != None:
            self.__vtxtotal = numpy.require(vtx, numpy.float32, 'F')
            
        else:
            self.__vtxtotal = np.array( [[self.meshxreprojected[i], self.meshyreprojected[i], 0.0]   for i in range(len(self.meshxreprojected))         ] )
            
        self.__vtxtodraw = self.__vtxtotal
    
    def resetIdx(self,idx = None):
        #__idx
        if idx != None:
            self.__idxtotal = numpy.require(idx, numpy.int32, 'F')
        else:
            self.__idxtotal = self.meshlayer.hydrauparser.getIkle()
            
        self.__idxtodraw = self.__idxtotal 


    def image(self, values, imageSize, center, mapUnitsPerPixel, rotation=0):
        """Return the rendered image of a given size for values defined at each vertex
        or at each element depending on setColorPerElement.
        Values are normalized using valueRange = (minValue, maxValue).
        transparency is in the range [0,1]"""
        
        
        DEBUG = False
        debugstring = ''
        
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
                self.__resize(roundupSz)


            val = numpy.require(values, numpy.float32) \
                    if not isinstance(values, numpy.ndarray)\
                    else values
                    
                    
            if self.__colorPerElement:
                val = numpy.concatenate((val,val,val))
                
            self.__pixBuf.makeCurrent()
            
            
            
            if True:
                
                #define current opengl drawing
                #self.__pixBuf.makeCurrent()
                #?
                if self.__recompileShader:
                    self.__compileShaders()
                    
                #init gl client
                debugstring += ' / init'
                #glClearColor(1., 1., 1., 1.)
                #glClearColor(0., 0., 0., 1.)
                glClearColor(0., 0., 0., 0.)
                # tell OpenGL that the VBO contains an array of vertices
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                glEnable(GL_TEXTURE_2D)

                debugstring +=  '/enable/'
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
                
                debugstring += '/scale/'
                # scale
                glScalef(2./(roundupSz.width()*mapUnitsPerPixel[0]),
                         2./(roundupSz.height()*mapUnitsPerPixel[1]),
                         1)
                # rotate
                glRotatef(-rotation, 0, 0, 1)
                ## translate
                glTranslatef(-center[0],
                             -center[1],
                             0)
                             

                if self.meshlayer.showmesh :   #draw triangle contour but not inside
                    #Draw the object here
                    #Disable texturing, lighting, etc. here
                    #glDisableClientState(GL_TEXTURE_COORD_ARRAY) non...
                    glDisable(GL_TEXTURE_2D)
                    #glDisableClientState(GL_TEXTURE_COORD_ARRAY)
                    #glClear(GL_COLOR_BUFFER_BIT)
                    glUseProgram(0)
                    
                    glColor4f(0.2,0.2,0.2,0.2)
                    glLineWidth(1) #or whatever
                    glPolygonMode(GL_FRONT, GL_LINE)
                    glPolygonMode(GL_BACK, GL_LINE)
                    #Draw the object here


                    #self.__legend._setUniforms(self.__pixBuf)
                    # these vertices contain 2 single precision coordinates
                    glVertexPointerf(self.__vtxtodraw)
                    #glTexCoordPointer(1, GL_FLOAT, 0, val)
                    glDrawElementsui(GL_TRIANGLES, self.__idxtodraw)
                    
                    
                    #glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
                    glPolygonMode(GL_FRONT, GL_FILL)
                    glPolygonMode(GL_BACK, GL_FILL)

                    
                    
                    
                if self.meshlayer.showvelocityparams['show']:
                        #glDisable(GL_TEXTURE_2D)
                        glEnable(GL_PROGRAM_POINT_SIZE)
                        glEnable(GL_TEXTURE_2D)
                        #print self.__vtxtodraw
                        

                            
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
                        glVertexPointerf(self.__vtxtodraw)
                        glTexCoordPointer(3, GL_FLOAT, 0, val)
                        glDrawArrays(GL_POINTS, 0, len(self.__vtxtodraw))
                    
                             
                glEnable(GL_TEXTURE_2D)
                glUseProgram(self.__shaders)
                


                #self.__legend._setUniforms(self.__pixBuf)
                # these vertices contain 2 single precision coordinates
                glVertexPointerf(self.__vtxtodraw)
                glTexCoordPointer(3, GL_FLOAT, 0, val)
                glDrawElementsui(GL_TRIANGLES, self.__idxtodraw)
                
                
                debugstring += '/image/'
            
            
            else:
                self.doRenderWork(val, imageSize, center, mapUnitsPerPixel, rotation)
            
            img = self.__pixBuf.toImage()
            self.__pixBuf.doneCurrent()
            
            if DEBUG :
                print debugstring
            
            return img.copy( .5*(roundupSz.width()-imageSize.width()),
                             .5*(roundupSz.height()-imageSize.height()),
                             imageSize.width(), imageSize.height())
        except Exception, e :
            print str(e)
            return QImage()

    def doRenderWork(self,val, imageSize, center, mapUnitsPerPixel, rotation=0):
        DEBUG = False
        debugstring = ''
    
       #define current opengl drawing
        #self.__pixBuf.makeCurrent()
        #??
        if self.__recompileShader:
            self.__compileShaders()
            
        #init gl client
        debugstring += ' / init'
        #glClearColor(1., 1., 1., 1.)
        #glClearColor(0., 0., 0., 1.)
        glClearColor(0., 0., 0., 0.)
        # tell OpenGL that the VBO contains an array of vertices
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnable(GL_TEXTURE_2D)

        debugstring +=  '/enable/'
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
        
        debugstring += '/scale/'
        # scale
        glScalef(2./(roundupSz.width()*mapUnitsPerPixel[0]),
                 2./(roundupSz.height()*mapUnitsPerPixel[1]),
                 1)
        # rotate
        glRotatef(-rotation, 0, 0, 1)
        ## translate
        glTranslatef(-center[0],
                     -center[1],
                     0)
                     

        if self.meshlayer.showmesh :   #draw triangle contour but not inside
            #Draw the object here
            #Disable texturing, lighting, etc. here
            #glDisableClientState(GL_TEXTURE_COORD_ARRAY) non...
            glDisable(GL_TEXTURE_2D)
            #glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            #glClear(GL_COLOR_BUFFER_BIT)
            glUseProgram(0)
            
            glColor4f(0.2,0.2,0.2,0.2)
            glLineWidth(1) #or whatever
            glPolygonMode(GL_FRONT, GL_LINE)
            glPolygonMode(GL_BACK, GL_LINE)
            #Draw the object here


            #self.__legend._setUniforms(self.__pixBuf)
            # these vertices contain 2 single precision coordinates
            glVertexPointerf(self.__vtxtodraw)
            #glTexCoordPointer(1, GL_FLOAT, 0, val)
            glDrawElementsui(GL_TRIANGLES, self.__idxtodraw)
            
            
            #glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
            glPolygonMode(GL_FRONT, GL_FILL)
            glPolygonMode(GL_BACK, GL_FILL)

            
            
            
        if self.meshlayer.showvelocityparams['show']:
                glDisable(GL_TEXTURE_2D)
                glEnable(GL_PROGRAM_POINT_SIZE)
                
                #print self.__vtxtodraw
                
                if False:
                
                    if False:
                        vertex_shader_vel = shaders.compileShader("""
                                attribute vec3 position;
                                void main()
                                {
                                    gl_Position = vec4(position, 1.0);
                                    gl_PointSize = 5.0;
                                }
                            """, GL_VERTEX_SHADER)
                    
                    
                    if False:
                        vertex_shader_vel = shaders.compileShader("""
                            #version 120
                            const float SQRT_2 = 1.4142135623730951;
                            uniform mat4 ortho;
                            uniform float size, orientation, linewidth, antialias;
                            attribute vec3 position;
                            varying vec2 rotation;
                            varying vec2 v_size;
                            void main ( )
                                {
                                rotation = vec2(cos(orientation), sin(orientation));
                                gl_Position = ortho * vec4(position, 1.0);
                                v_size = M_SQRT_2 * size + 2.0 * (linewidth + 1.5 * antialias);
                                gl_PointSize = v_size;
                                }
                            """, GL_VERTEX_SHADER)
                            
                    if False:
                        vertex_shader_vel = shaders.compileShader("""
                            #version 120 
                            void main()
                            {
                              gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;		
                              gl_TexCoord[0] = gl_MultiTexCoord0;
                            }
                            """, GL_VERTEX_SHADER)
                            
                            
                    if False:
                        fragment_shader_vel = shaders.compileShader("""
                            varying float value;
                            //varying vec2 valuevel;
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
                            //out vec4 outColor;
                            void main()
                                {
                                    gl_FragColor = pixelColor(value);
                                }
                            """, GL_FRAGMENT_SHADER)
                    if False:
                        fragment_shader_vel = shaders.compileShader("""
                            vec4 filled(float distance, float linewidth, float antialias, vec4 fill)
                            {
                                vec4 frag_color;
                                float t = linewidth/2.0 - antialias;
                                float signed_distance = distance;
                                float border_distance = abs(signed_distance) - t;
                                float alpha = border_distance/antialias;
                                alpha = exp(-alpha*alpha);
                                // Within linestroke
                                if( border_distance < 0.0 )
                                    frag_color = fill;
                                // Within shape
                                else if( signed_distance < 0.0 )
                                    frag_color = fill;
                                else
                                    // Outside shape
                                    if( border_distance > (linewidth/2.0 + antialias) )
                                        discard;
                                    else // Line stroke exterior border
                                        frag_color = vec4(fill.rgb, alpha * fill.a);
                                return frag_color;
                            }
                            // Computes the signed distance from a line
                            float line_distance(vec2 p, vec2 p1, vec2 p2) {
                                vec2 center = (p1 + p2) * 0.5;
                                float len = length(p2 - p1);
                                vec2 dir = (p2 - p1) / len;
                                vec2 rel_p = p - center;
                                return dot(rel_p, vec2(dir.y, -dir.x));
                            }
                            // Computes the signed distance from a line segment
                            float segment_distance(vec2 p, vec2 p1, vec2 p2) {
                                vec2 center = (p1 + p2) * 0.5;
                                float len = length(p2 - p1);
                                vec2 dir = (p2 - p1) / len;
                                vec2 rel_p = p - center;
                                float dist1 = abs(dot(rel_p, vec2(dir.y, -dir.x)));
                                float dist2 = abs(dot(rel_p, dir)) - 0.5*len;
                                return max(dist1, dist2);
                            }
                            // Computes the center with given radius passing through p1 & p2
                            vec4 circle_from_2_points(vec2 p1, vec2 p2, float radius)
                            {
                                float q = length(p2-p1);
                                vec2 m = (p1+p2)/2.0;
                                vec2 d = vec2( sqrt(radius*radius - (q*q/4.0)) * (p1.y-p2.y)/q,
                                               sqrt(radius*radius - (q*q/4.0)) * (p2.x-p1.x)/q);
                                return  vec4(m+d, m-d);
                            }
                            float arrow_stealth(vec2 texcoord,
                                                float body, float head,
                                                float linewidth, float antialias)
                            {
                                float w = linewidth/2.0 + antialias;
                                vec2 start = -vec2(body/2.0, 0.0);
                                vec2 end   = +vec2(body/2.0, 0.0);
                                float height = 0.5;
                                // Head : 4 lines
                                float d1 = line_distance(texcoord, end-head*vec2(+1.0,-height),
                                                                   end);
                                float d2 = line_distance(texcoord, end-head*vec2(+1.0,-height),
                                                                   end-vec2(3.0*head/4.0,0.0));
                                float d3 = line_distance(texcoord, end-head*vec2(+1.0,+height), end);
                                float d4 = line_distance(texcoord, end-head*vec2(+1.0,+0.5),
                                                                   end-vec2(3.0*head/4.0,0.0));
                                // Body : 1 segment
                                float d5 = segment_distance(texcoord, start, end - vec2(linewidth,0.0));
                                return min(d5, max( max(-d1, d3), - max(-d2,d4)));
                            }
                            
                            //uniform vec2 iResolution;
                            vec2 iResolution = vec2(100.0,100.0);
                            //uniform vec2 iMouse;
                            vec2 iMouse = vec2( 100.0, 100.0 );
                            void main()
                            {
                                const float M_PI = 3.14159265358979323846;
                                const float SQRT_2 = 1.4142135623730951;
                                const float linewidth = 3.0;
                                const float antialias =  1.0;
                                const float rows = 32.0;
                                const float cols = 32.0;
                                float body = min(iResolution.x/cols, iResolution.y/rows) / SQRT_2;
                                vec2 texcoord = gl_FragCoord.xy;
                                vec2 size   = iResolution.xy / vec2(cols,rows);
                                vec2 center = (floor(texcoord/size) + vec2(0.5,0.5)) * size;
                                texcoord -= center;
                                // float theta = M_PI/3.0 + 0.1*(center.x / cols + center.y / rows);
                                float theta = M_PI-atan(center.y-iMouse.y,  center.x-iMouse.x);
                                float cos_theta = cos(theta);
                                float sin_theta = sin(theta);
                                texcoord = vec2(cos_theta*texcoord.x - sin_theta*texcoord.y,
                                                sin_theta*texcoord.x + cos_theta*texcoord.y);
                                // float d = arrow_curved(texcoord, body, 0.25*body, linewidth, antialias);
                                float d = arrow_stealth(texcoord, body, 0.25*body, linewidth, antialias);
                                // float d = arrow_triangle_90(texcoord, body, 0.15*body, linewidth, antialias);
                                // float d = arrow_triangle_60(texcoord, body, 0.20*body, linewidth, antialias);
                                // float d = arrow_triangle_30(texcoord, body, 0.25*body, linewidth, antialias);
                                // float d = arrow_angle_90(texcoord, body, 0.15*body, linewidth, antialias);
                                // float d = arrow_angle_60(texcoord, body, 0.20*body, linewidth, antialias);
                                // float d = arrow_angle_30(texcoord, body, 0.25*body, linewidth, antialias);
                                gl_FragColor = filled(d, linewidth, antialias, vec4(0,0,0,1));
                                // gl_FragColor = stroke(d, linewidth, antialias, vec4(0,0,0,1));
                            }
                         """, GL_FRAGMENT_SHADER)
                         
                         
                         
                    if False:
                        geom_shader_vel = shaders.compileShader("""
                            layout(points) in;
                            layout(points, max_vertices = 1) out;

                            void main()
                            {
                                gl_Position = gl_in[0].gl_Position;
                                EmitVertex();
                                EndPrimitive();
                            }
                        
                            """, GL_GEOMETRY_SHADER)

                    
                    if False :
                        geom_shader_vel = shaders.compileShader("""
                            layout(points) in;
                            layout(line_strip, max_vertices = 2) out;

                            void main()
                            {
                                gl_Position = gl_in[0].gl_Position + vec4(-0.1, 0.0, 0.0, 0.0);
                                EmitVertex();

                                gl_Position = gl_in[0].gl_Position + vec4(0.1, 0.0, 0.0, 0.0);
                                EmitVertex();

                                EndPrimitive();
                            }
                        
                            """, GL_GEOMETRY_SHADER)
                            

                    
                
                
                if True :
                    
                    
                    if True:
                    
                        vertex_shader_vel = shaders.compileShader("""
                            //varying float valuev;
                            varying vec2 valuevel;
                            varying float w;
                            varying vec3 normal;
                            varying vec4 ecPos;
                            void main()
                            {
                                ecPos = gl_ModelViewMatrix * gl_Vertex;
                                normal = normalize(gl_NormalMatrix * gl_Normal);
                                //value = gl_MultiTexCoord0.st.x;
                                //valuev = gl_MultiTexCoord0.x;
                                valuevel = gl_MultiTexCoord0.yz;
                                //w = valuev > 0.0 ? 1.0 : 0.0;
                                gl_Position = ftransform();
                                gl_PointSize = 10.0;
                            }
                            """, GL_VERTEX_SHADER)
                    
                    if True :
                    
                    
                        geom_shader_vel = shaders.compileShader("""
                            varying vec2 valuevel[];
                            out float value ;
                            
                            layout(points) in;
                            layout(triangle, max_vertices = 3) out;


                            void main()
                            {
                                value = sqrt( valuevel[0].x * valuevel[0].x + valuevel[0].y * valuevel[0].y ) ;
                                //gl_Position = gl_in[0].gl_Position;
                                gl_in[0].gl_Position + vec4(-0.05 * valuevel[0].y, 0.05 * valuevel[0].x, 0.0, 0.0);
                                EmitVertex();

                                
                                gl_in[0].gl_Position + vec4(0.05 * valuevel[0].y, -0.05 * valuevel[0].x, 0.0, 0.0);
                                EmitVertex();
                                
                                gl_Position = gl_in[0].gl_Position + vec4(0.05 * valuevel[0].x, 0.05 * valuevel[0].y, 0.0, 0.0);
                                EmitVertex();

                                EndPrimitive();
                                
                                
                                gl_in[0].gl_Position + vec4(-0.05 * valuevel[0].y, 0.05 * valuevel[0].x, 0.0, 0.0);
                                EmitVertex();

                                
                                gl_in[0].gl_Position + vec4(0.05 * valuevel[0].y, -0.05 * valuevel[0].x, 0.0, 0.0);
                                EmitVertex();
                                
                                gl_Position = gl_in[0].gl_Position + vec4(0.05 * valuevel[0].x, 0.05 * valuevel[0].y, 0.0, 0.0);
                                EmitVertex();

                                EndPrimitive();
                                
                                
                                
                            }
                        
                            """, GL_GEOMETRY_SHADER)
                    
                    if True:
                        fragment_shader_vel = shaders.compileShader("""
                            varying float value;
                            varying vec2 valuevel;
                            """+self.__pixelColorVelocity+"""
                            
                            void main() {
                              //gl_FragColor = vec4(  min( value ,1.0  ), 0.0, 0.0, 1.0);
                              gl_FragColor = pixelColor(value);
                              
                              }
                         """, GL_FRAGMENT_SHADER)
                         
                    self.__shadersvel = shaders.compileProgram(vertex_shader_vel, fragment_shader_vel, geom_shader_vel)
                    
                if False:
                
                    if True:
                    
                        vertex_shader_vel = shaders.compileShader("""
                            #version 120
                            const float SQRT_2 = 1.4142135623730951;
                            uniform mat4 ortho;
                            //uniform float size, orientation, linewidth, antialias;
                            
                            attribute vec3 position;
                            varying vec2 rotation;
                            varying vec2 v_size;
                            void main ()
                            {
                            float orientation = 1.0;
                            
                            rotation = vec2(cos(orientation), sin(orientation));
                            gl_Position = ortho *  vec4(position, 1.0);
                            v_size = M_SQRT_2   *  size + 2.0  *   (linewidth + 1.5  *  antialias);
                            gl_PointSize = v_size;
                            }
                            """, GL_VERTEX_SHADER)
                    
                    
                    if True:
                       fragment_shader_vel = shaders.compileShader("""
                            vec4 filled(float distance, float linewidth, float antialias, vec4 fill)
                            {
                                vec4 frag_color;
                                float t = linewidth/2.0 - antialias;
                                float signed_distance = distance;
                                float border_distance = abs(signed_distance) - t;
                                float alpha = border_distance/antialias;
                                alpha = exp(-alpha*alpha);
                                // Within linestroke
                                if( border_distance < 0.0 )
                                    frag_color = fill;
                                // Within shape
                                else if( signed_distance < 0.0 )
                                    frag_color = fill;
                                else
                                    // Outside shape
                                    if( border_distance > (linewidth/2.0 + antialias) )
                                        discard;
                                    else // Line stroke exterior border
                                        frag_color = vec4(fill.rgb, alpha * fill.a);
                                return frag_color;
                            }
                            // Computes the signed distance from a line
                            float line_distance(vec2 p, vec2 p1, vec2 p2) {
                                vec2 center = (p1 + p2) * 0.5;
                                float len = length(p2 - p1);
                                vec2 dir = (p2 - p1) / len;
                                vec2 rel_p = p - center;
                                return dot(rel_p, vec2(dir.y, -dir.x));
                            }
                            // Computes the signed distance from a line segment
                            float segment_distance(vec2 p, vec2 p1, vec2 p2) {
                                vec2 center = (p1 + p2) * 0.5;
                                float len = length(p2 - p1);
                                vec2 dir = (p2 - p1) / len;
                                vec2 rel_p = p - center;
                                float dist1 = abs(dot(rel_p, vec2(dir.y, -dir.x)));
                                float dist2 = abs(dot(rel_p, dir)) - 0.5*len;
                                return max(dist1, dist2);
                            }
                            // Computes the center with given radius passing through p1 & p2
                            vec4 circle_from_2_points(vec2 p1, vec2 p2, float radius)
                            {
                                float q = length(p2-p1);
                                vec2 m = (p1+p2)/2.0;
                                vec2 d = vec2( sqrt(radius*radius - (q*q/4.0)) * (p1.y-p2.y)/q,
                                               sqrt(radius*radius - (q*q/4.0)) * (p2.x-p1.x)/q);
                                return  vec4(m+d, m-d);
                            }
                            float arrow_stealth(vec2 texcoord,
                                                float body, float head,
                                                float linewidth, float antialias)
                            {
                                float w = linewidth/2.0 + antialias;
                                vec2 start = -vec2(body/2.0, 0.0);
                                vec2 end   = +vec2(body/2.0, 0.0);
                                float height = 0.5;
                                // Head : 4 lines
                                float d1 = line_distance(texcoord, end-head*vec2(+1.0,-height),
                                                                   end);
                                float d2 = line_distance(texcoord, end-head*vec2(+1.0,-height),
                                                                   end-vec2(3.0*head/4.0,0.0));
                                float d3 = line_distance(texcoord, end-head*vec2(+1.0,+height), end);
                                float d4 = line_distance(texcoord, end-head*vec2(+1.0,+0.5),
                                                                   end-vec2(3.0*head/4.0,0.0));
                                // Body : 1 segment
                                float d5 = segment_distance(texcoord, start, end - vec2(linewidth,0.0));
                                return min(d5, max( max(-d1, d3), - max(-d2,d4)));
                            }
                            
                            //uniform vec2 iResolution;
                            vec2 iResolution = vec2(100.0,100.0);
                            //uniform vec2 iMouse;
                            vec2 iMouse = vec2( 100.0, 100.0 );
                            void main()
                            {
                                const float M_PI = 3.14159265358979323846;
                                const float SQRT_2 = 1.4142135623730951;
                                const float linewidth = 3.0;
                                const float antialias =  1.0;
                                const float rows = 32.0;
                                const float cols = 32.0;
                                float body = min(iResolution.x/cols, iResolution.y/rows) / SQRT_2;
                                vec2 texcoord = gl_FragCoord.xy;
                                vec2 size   = iResolution.xy / vec2(cols,rows);
                                vec2 center = (floor(texcoord/size) + vec2(0.5,0.5)) * size;
                                texcoord -= center;
                                // float theta = M_PI/3.0 + 0.1*(center.x / cols + center.y / rows);
                                float theta = M_PI-atan(center.y-iMouse.y,  center.x-iMouse.x);
                                float cos_theta = cos(theta);
                                float sin_theta = sin(theta);
                                texcoord = vec2(cos_theta*texcoord.x - sin_theta*texcoord.y,
                                                sin_theta*texcoord.x + cos_theta*texcoord.y);
                                // float d = arrow_curved(texcoord, body, 0.25*body, linewidth, antialias);
                                float d = arrow_stealth(texcoord, body, 0.25*body, linewidth, antialias);
                                // float d = arrow_triangle_90(texcoord, body, 0.15*body, linewidth, antialias);
                                // float d = arrow_triangle_60(texcoord, body, 0.20*body, linewidth, antialias);
                                // float d = arrow_triangle_30(texcoord, body, 0.25*body, linewidth, antialias);
                                // float d = arrow_angle_90(texcoord, body, 0.15*body, linewidth, antialias);
                                // float d = arrow_angle_60(texcoord, body, 0.20*body, linewidth, antialias);
                                // float d = arrow_angle_30(texcoord, body, 0.25*body, linewidth, antialias);
                                gl_FragColor = filled(d, linewidth, antialias, vec4(0,0,0,1));
                                // gl_FragColor = stroke(d, linewidth, antialias, vec4(0,0,0,1));
                            }
                         """, GL_FRAGMENT_SHADER)
                
                
                    self.__shadersvel = shaders.compileProgram(vertex_shader_vel, fragment_shader_vel)
                    
                    
                #glDisableClientState(GL_TEXTURE_COORD_ARRAY)
                #glClear(GL_COLOR_BUFFER_BIT)
                glUseProgram(self.__shadersvel)
                
                
                
                #glColor4f(0.2,0.2,0.2,0.2)
                glLineWidth(5) #or whatever
                glPolygonMode(GL_FRONT, GL_LINE)
                glPolygonMode(GL_BACK, GL_LINE)
                #Draw the object here
                
                
                
                #self.__legend._setUniforms(self.__pixBuf)
                # these vertices contain 2 single precision coordinates
                glVertexPointerf(self.__vtxtodraw)
                glTexCoordPointer(3, GL_FLOAT, 0, val)
                #glDrawElementsui(GL_LINES, self.__idxtodraw)
                #glDrawElementsui(GL_TRIANGLE_STRIP,range(len(self.__vtxtodraw)))
                
                if self.arraypoints == None:
                    self.arraypoints = range(len(self.__vtxtodraw))
                    
                #glDrawElementsui(GL_POINTS,len(self.arraypoints) )
                glDrawArrays(GL_POINTS, 0, len(self.__vtxtodraw))
                
                glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
                #glPolygonMode(GL_FRONT, GL_FILL)
                #glPolygonMode(GL_BACK, GL_FILL)
            
            
                     
                     
        glEnable(GL_TEXTURE_2D)
        glUseProgram(self.__shaders)
        


        #self.__legend._setUniforms(self.__pixBuf)
        # these vertices contain 2 single precision coordinates
        glVertexPointerf(self.__vtxtodraw)
        glTexCoordPointer(3, GL_FLOAT, 0, val)
        glDrawElementsui(GL_TRIANGLES, self.__idxtodraw)
        
        
        
        if False:   #draw triangle contour but not inside
            #Draw the object here
            #Disable texturing, lighting, etc. here
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisable(GL_TEXTURE_2D)
            glColor4f(1.,1.,1.,0.8)
            glLineWidth(2) #or whatever
            glPolygonMode(GL_FRONT, GL_LINE)
            glPolygonMode(GL_BACK, GL_LINE)
            #Draw the object here
            #glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
            glPolygonMode(GL_FRONT, GL_FILL);
            glPolygonMode(GL_BACK, GL_FILL);
            
            

            
        
        #glDrawElements(GL_TRIANGLES, self.__idx)
        
        debugstring += '/image/'
    
        
