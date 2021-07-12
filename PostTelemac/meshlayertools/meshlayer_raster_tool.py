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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal

from qgis.core import QgsRasterLayer, QgsProject, QgsCoordinateTransform
from qgis.utils import iface

from osgeo import gdal
from osgeo import osr

import time
import numpy as np
import sys
import os

from .meshlayer_abstract_tool import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "RasterTool.ui"))


class RasterTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "RASTERTOOL"
    SOFTWARE = ["TELEMAC", "ANUGA"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "layer_raster_add.png")
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.pushButton_createraster.clicked.connect(self.rasterCreation)

    def onActivation(self):
        pass

    def onDesactivation(self):
        pass

    def updateParams(self):
        self.comboBox_parametreschooser_2.clear()
        for i in range(len(self.meshlayer.hydrauparser.parametres)):
            temp1 = [
                str(self.meshlayer.hydrauparser.parametres[i][0])
                + " : "
                + str(self.meshlayer.hydrauparser.parametres[i][1])
            ]
            self.comboBox_parametreschooser_2.addItems(temp1)

    def rasterCreation(self):
        self.initclass = InitRasterize()
        self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
        self.initclass.finished1.connect(self.rasterCreationFinished)
        self.propertiesdialog.normalMessage("Raster creation started")
        self.initclass.start(self.meshlayer, self)

    def rasterCreationFinished(self, strpath):
        if strpath != "":
            rlayer = QgsRasterLayer(strpath, os.path.basename(strpath).split(".")[0])
            QgsProject.instance().addMapLayer(rlayer)
            self.propertiesdialog.normalMessage(str(os.path.basename(strpath).split(".")[0]) + self.tr(" created"))
        else:  # FIX IT
            self.propertiesdialog.errorMessage("Unknown error, please retry... :'(")


class rasterize(QObject):
    def __init__(self, selafin, tool):
        QObject.__init__(self)
        self.selafinlayer = selafin
        self.tool = tool

    def createRaster(self):
        try:
            if self.tool.comboBox_rasterextent.currentIndex() == 0:
                rect = self.selafinlayer.xform.transform(
                    iface.mapCanvas().extent(), QgsCoordinateTransform.ReverseTransform
                )
            elif self.tool.comboBox_rasterextent.currentIndex() == 1:
                rect = self.selafinlayer.xform.transform(
                    self.selafinlayer.extent(), QgsCoordinateTransform.ReverseTransform
                )
            # res
            res = self.tool.spinBox_rastercellsize.value()
            # grid creation
            xmin, xmax, ymin, ymax = [
                int(rect.xMinimum()),
                int(rect.xMaximum()),
                int(rect.yMinimum()),
                int(rect.yMaximum()),
            ]
            # check interpolator
            # FIX IT : first click don't work...
            if self.selafinlayer.hydrauparser.interpolator is None:
                self.selafinlayer.hydrauparser.createInterpolator()
            success = self.selafinlayer.hydrauparser.updateInterpolatorEmit(self.selafinlayer.time_displayed)
            self.status.emit("Raster Tool - Interpolator check " + str(self.selafinlayer.hydrauparser.interpolator))

            paramindex = self.tool.comboBox_parametreschooser_2.currentIndex()

            try:
                xi, yi = np.meshgrid(np.arange(xmin, xmax, res), np.arange(ymin, ymax, res))
                zi = self.selafinlayer.hydrauparser.interpolator[paramindex](xi, yi)

            except Exception as e:
                self.status.emit("Raster Tool - Interpolation error " + str(e))
                self.finished.emit(None)

            nrows, ncols = np.shape(zi)
            raster_ut = os.path.join(
                os.path.dirname(self.selafinlayer.hydraufilepath),
                str(os.path.basename(self.selafinlayer.hydraufilepath).split(".")[0])
                + "_raster_"
                + str(self.selafinlayer.hydrauparser.parametres[paramindex][1]),
            )

            try:
                raster_ut += ".tif"
                xres = res
                yres = res
                geotransform = (xmin, xres, 0, ymin, 0, yres)
                output_raster = gdal.GetDriverByName(str("GTiff")).Create(
                    raster_ut, ncols, nrows, 1, gdal.GDT_Float32, ["TFW=YES", "COMPRESS=LZW", "PREDICTOR=2", "ZLEVEL=9"]
                )
                output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
                srs = osr.SpatialReference()  # Establish its coordinate encoding
                crstemp = self.selafinlayer.crs().authid()
                if crstemp.startswith("EPSG:"):
                    crsnumber = int(crstemp[5:])
                else:
                    self.status.emit(str("Please choose a EPSG crs"))
                    self.finished.emit(None)

                srs.ImportFromEPSG(crsnumber)  # This one specifies SWEREF99 16 30
                output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system to the file
                output_raster.GetRasterBand(1).WriteArray(zi)  # Writes my array to the raster
            except Exception as e:
                self.status.emit("Error GDAL create : " + str(e))
                self.finished.emit(None)

            self.finished.emit(raster_ut)

        except Exception as e:
            self.status.emit("Raster Tool - createRaster : " + str(e))
            self.finished.emit(None)

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    killed = pyqtSignal()
    finished = pyqtSignal(str)


# *********************************************************************************************
# *************** Classe de lancement du thread **********************************************************
# ********************************************************************************************


class InitRasterize(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = None
        self.worker = None
        self.processtype = 0

    def start(self, selafin, tool):
        # Launch worker
        self.thread = QThread()
        self.worker = rasterize(selafin, tool)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.createRaster)
        self.worker.status.connect(self.writeOutput)
        self.worker.error.connect(self.raiseError)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def raiseError(self, str):
        if self.processtype == 0:
            self.status.emit(str)
        elif self.processtype in [1, 2, 3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print(str)
            sys.exit(0)

    def writeOutput(self, str1):
        self.status.emit(str(str1))

    def workerFinished(self, str):
        self.finished1.emit(str)

    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished1 = pyqtSignal(str)
