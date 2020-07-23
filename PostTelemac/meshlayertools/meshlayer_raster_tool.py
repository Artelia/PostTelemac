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


# from PyQt4 import uic, QtCore, QtGui
from qgis.PyQt import uic, QtCore, QtGui
from .meshlayer_abstract_tool import *
import qgis
import time
import numpy as np
from osgeo import gdal
from osgeo import osr

# imports divers
import sys
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "RasterTool.ui"))


class RasterTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "RASTERTOOL"
    SOFTWARE = ["TELEMAC", "ANUGA"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)
        # self.setupUi(self)

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
            rlayer = qgis.core.QgsRasterLayer(strpath, os.path.basename(strpath).split(".")[0])
            if sys.version_info.major == 2:
                qgis.core.QgsMapLayerRegistry.instance().addMapLayer(rlayer)
            elif sys.version_info.major == 3:
                qgis.core.QgsProject.instance().addMapLayer(rlayer)

            self.propertiesdialog.normalMessage(str(os.path.basename(strpath).split(".")[0]) + self.tr(" created"))
        else:  # FIX IT
            self.propertiesdialog.errorMessage("Unknown error, please retry... :'(")


class rasterize(QtCore.QObject):
    def __init__(self, selafin, tool):

        QtCore.QObject.__init__(self)
        self.selafinlayer = selafin
        self.tool = tool
        # self.points = qgspoints
        # self.skdtree = None
        # self.compare = compare

    def createRaster(self):
        try:
            if self.tool.comboBox_rasterextent.currentIndex() == 0:
                rect = self.selafinlayer.xform.transform(
                    qgis.utils.iface.mapCanvas().extent(), qgis.core.QgsCoordinateTransform.ReverseTransform
                )
            elif self.tool.comboBox_rasterextent.currentIndex() == 1:
                rect = self.selafinlayer.xform.transform(
                    self.selafinlayer.extent(), qgis.core.QgsCoordinateTransform.ReverseTransform
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

            paramindex = self.tool.comboBox_parametreschooser_2.currentIndex()

            if False:
                # work for avoiding memory eror with too big meshgrid (20 000 x 20 000 is the max)
                col = (xmax - xmin) / res
                row = (ymax - ymin) / res
                i = 1
                while col / i * row > 1e7:
                    i += 1
                cols = np.linspace(xmin, xmax, i)

                for j in range(i):
                    pass
            else:
                try:
                    xi, yi = np.meshgrid(np.arange(xmin, xmax, res), np.arange(ymin, ymax, res))
                    zi = self.selafinlayer.hydrauparser.interpolator[paramindex](xi, yi)

                except Exception as e:
                    self.status.emit("Raster Tool - Interpolation error " + str(e))
                    self.finished.emit(None)

            nrows, ncols = np.shape(zi)
            self.status.emit("Raster creation - nrows : " + str(nrows) + " - ncols : " + str(ncols))
            raster_ut = os.path.join(
                os.path.dirname(self.selafinlayer.hydraufilepath),
                str(os.path.basename(self.selafinlayer.hydraufilepath).split(".")[0])
                + "_raster_"
                + str(self.selafinlayer.hydrauparser.parametres[paramindex][1]),
            )

            if True:
                try:
                    raster_ut += ".tif"
                    # xres = (xmax-xmin)/float(ncols)
                    # yres = (ymax-ymin)/float(nrows)
                    xres = res
                    yres = res
                    geotransform = (xmin, xres, 0, ymin, 0, yres)

                    # raster_ut = os.path.join(os.path.dirname(self.selafinlayer.hydraufilepath),str(os.path.basename(self.selafinlayer.hydraufilepath).split('.')[0] ) + '_raster_'+str(self.selafinlayer.parametres[paramindex][1])+'.asc')

                    # output_raster = gdal.GetDriverByName('GTiff').Create(raster_ut,ncols, nrows, 1 ,gdal.GDT_Float32,['TFW=YES', 'COMPRESS=PACKBITS'])  # Open the file, see here for information about compression: http://gis.stackexchange.com/questions/1104/should-gdal-be-set-to-produce-geotiff-files-with-compression-which-algorithm-sh
                    output_raster = gdal.GetDriverByName(str("GTiff")).Create(
                        raster_ut, ncols, nrows, 1, gdal.GDT_Float32, ["TFW=YES"]
                    )  # Open the file, see here for information about compression: http://gis.stackexchange.com/questions/1104/should-gdal-be-set-to-produce-geotiff-files-with-compression-which-algorithm-sh
                    output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
                    # self.status.emit('raster created')
                    srs = osr.SpatialReference()  # Establish its coordinate encoding
                    crstemp = self.selafinlayer.crs().authid()
                    if crstemp.startswith("EPSG:"):
                        crsnumber = int(crstemp[5:])
                    else:
                        self.status.emit(str("Please choose a EPSG crs"))
                        self.finished.emit(None)

                    srs.ImportFromEPSG(crsnumber)  # This one specifies SWEREF99 16 30
                    output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system to the file
                    # self.status.emit('Projection set')
                    output_raster.GetRasterBand(1).WriteArray(zi)  # Writes my array to the raster
                except Exception as e:
                    self.status.emit("Error " + str(e))
                    self.finished.emit(None)

            else:
                raster_ut += ".asc"
                """
                header = "ncols     %s\n" % myArray.shape[1]
                header += "nrows    %s\n" % myArray.shape[0]
                header += "xllcorner 277750.0\n"
                header += "yllcorner 6122250.0\n"
                header += "cellsize 1.0\n"
                header += "NODATA_value nan\n"
                """
                header = "ncols     %s\n" % ncols
                header += "nrows    %s\n" % nrows
                header += "xllcorner " + str(xmin) + "\n"
                header += "yllcorner " + str(ymin) + "\n"
                header += "cellsize " + str(res) + "\n"
                header += "NODATA_value -9999\n"

                if False:
                    # au lieu de 'w', il faut utiliser 'a' (pour ajouter en fin de fichier). Sinon ca ecrase tout
                    f = open(raster_ut, "w")
                    f.write(header)

                    """
                    tt = np.isnan(zi)
                    zi[tt] = -9999
                    """
                    try:
                        np.savetxt(f, zi[::-1], fmt="%1.2f")
                        f.close()
                    except Exception as e:
                        self.status.emit(str(e))
                        f.close()
                        self.finished.emit(None)
                else:
                    tt = np.isnan(zi)
                    zi[tt] = -9999
                    np.savetxt(raster_ut, np.flipud(zi), header=header, comments="", fmt="%1.2f")

            self.finished.emit(raster_ut)

        except Exception as e:
            self.status.emit("Raster tool - createRaster : " + str(e))
            self.finished.emit(None)

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    killed = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(str)


# *********************************************************************************************
# *************** Classe de lancement du thread **********************************************************
# ********************************************************************************************


class InitRasterize(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.thread = None
        self.worker = None
        self.processtype = 0

    def start(self, selafin, tool):
        # Launch worker
        self.thread = QtCore.QThread()
        self.worker = rasterize(selafin, tool)
        # self.graphtemp.points = qgspoints
        # self.worker = self.graphtemp

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

    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    finished1 = QtCore.pyqtSignal(str)
