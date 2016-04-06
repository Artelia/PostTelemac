# -*- coding: utf-8 -*-

#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4 import QtCore, QtGui
#import numpy
from numpy import *
import numpy as np
#import gdal
from osgeo import gdal
from osgeo import osr
#imports divers
from time import ctime
import math
import sys
import os.path



#*********************************************************************************************
#*************** Classe de traitement **********************************************************
#********************************************************************************************

        
class rasterize(QtCore.QObject):
    
    def __init__(self, selafin):
        
        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        #self.points = qgspoints
        #self.skdtree = None
        #self.compare = compare


    def createRaster(self):
        try:
            if self.selafinlayer.propertiesdialog.comboBox_rasterextent.currentIndex() == 0 :
                rect = self.selafinlayer.xform.transform(iface.mapCanvas().extent(), QgsCoordinateTransform.ReverseTransform)
            elif self.selafinlayer.propertiesdialog.comboBox_rasterextent.currentIndex() == 1 :
                rect = self.selafinlayer.xform.transform(self.selafinlayer.extent(), QgsCoordinateTransform.ReverseTransform)
            #res 
            res = self.selafinlayer.propertiesdialog.spinBox_rastercellsize.value()
            #grid creation
            xmin,xmax,ymin,ymax = [int(rect.xMinimum()), int(rect.xMaximum()), int(rect.yMinimum()), int(rect.yMaximum()) ]
            
            
            try:
                xi, yi = np.meshgrid(np.arange(xmin, xmax, res), np.arange(ymin, ymax, res))
            except Exception, e:
                self.status.emit(str(e))
                self.finished.emit(None)
            
            self.selafinlayer.initTriinterpolator()
            paramindex = self.selafinlayer.propertiesdialog.comboBox_parametreschooser_2.currentIndex()
            zi = self.selafinlayer.triinterp[paramindex](xi, yi)
            
            nrows,ncols = np.shape(zi)
            self.status.emit('Raster creation - nrows : ' + str(nrows)+' - ncols : ' + str(ncols))
            
            #xres = (xmax-xmin)/float(ncols)
            #yres = (ymax-ymin)/float(nrows)
            xres = res
            yres = res
            geotransform=(xmin,xres,0,ymin,0, yres) 

             
            raster_ut = os.path.join(os.path.dirname(self.selafinlayer.hydraufilepath),str(os.path.basename(self.selafinlayer.hydraufilepath).split('.')[0] ) + '_raster_'+str(self.selafinlayer.parametres[paramindex][1])+'.tif')
            
            #output_raster = gdal.GetDriverByName('GTiff').Create(raster_ut,ncols, nrows, 1 ,gdal.GDT_Float32,['TFW=YES', 'COMPRESS=PACKBITS'])  # Open the file, see here for information about compression: http://gis.stackexchange.com/questions/1104/should-gdal-be-set-to-produce-geotiff-files-with-compression-which-algorithm-sh
            output_raster = gdal.GetDriverByName('GTiff').Create(raster_ut,ncols, nrows, 1 ,gdal.GDT_Float32,['TFW=YES'])  # Open the file, see here for information about compression: http://gis.stackexchange.com/questions/1104/should-gdal-be-set-to-produce-geotiff-files-with-compression-which-algorithm-sh
            output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
            srs = osr.SpatialReference()                 # Establish its coordinate encoding
            crstemp = self.selafinlayer.crs().authid()
            if crstemp.startswith('EPSG:'):
                crsnumber = int(crstemp[5:])
            else:
                self.status.emit(str('Please choose a EPSG crs'))
                self.finished.emit(None)
                
            srs.ImportFromEPSG(crsnumber)                     # This one specifies SWEREF99 16 30
            output_raster.SetProjection( srs.ExportToWkt() )   # Exports the coordinate system to the file
            output_raster.GetRasterBand(1).WriteArray(zi)   # Writes my array to the raster
 
 
            self.finished.emit(raster_ut)
        except Exception, e:
            self.status.emit(str(e))
            self.finished.emit(None)

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(str)

      

#*********************************************************************************************
#*************** Classe de lancement du thread **********************************************************
#********************************************************************************************


class InitRasterize(QtCore.QObject):
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = None
        self.worker = None
        self.processtype = 0


    def start(self, selafin):
                 
        #Launch worker
        self.thread = QtCore.QThread()
        self.worker = rasterize(selafin)
        #self.graphtemp.points = qgspoints
        #self.worker = self.graphtemp
        
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.createRaster)
        self.worker.status.connect(self.writeOutput)
        self.worker.error.connect(self.raiseError)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
        

    
    def raiseError(self,str):
        if self.processtype ==0:
            self.status.emit(str)
        elif self.processtype in [1,2,3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print str
            sys.exit(0)
            
    def writeOutput(self,str1):
        self.status.emit(str(str1))
        
    def workerFinished(self,str):
        self.finished1.emit(str)
        

        
            
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(str)
    
    
    