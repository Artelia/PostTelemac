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
from qgis.PyQt.QtCore import QObject, QMutex, QSize, pyqtSignal
from qgis.PyQt.QtGui import QImage

from qgis.core import QgsPointXY, QgsCoordinateTransform, QgsRenderContext
from qgis.utils import iface

from .post_telemac_pluginlayer_colormanager import *

import numpy as np
import time


class AbstractMeshRenderer(QObject):

    __CRSChangeRequested = pyqtSignal()

    def __init__(self, meshlayer, integertemp=0, vtx=[[0.0, 0.0, 0.0]], idx=[0]):
        QObject.__init__(self)
        self.meshlayer = meshlayer
        self.colormanager = PostTelemacColorManager(self.meshlayer, self)
        self.alpha_displayed = 100.0
        """
        self.meshxreprojected = None
        self.meshyreprojected = None
        """

        self.elemnodereprojected = (None, None)
        self.facenodereprojected = (None, None)

        self.__CRSChangeRequested.connect(self.CrsChanged)

        self.cmap_contour_raw = None  # original color map, unchanged with levels
        self.cmap_contour_leveled = None  # cmap modified to correspond levels values
        self.cmap_vel_raw = None
        self.cmap_vel_leveled = None

        self.lvl_contour = []
        self.lvl_vel = []

        self.__imageChangedMutex = QMutex()

        self.sizepx = None
        self.rendererContext = None
        self.ext = None
        self.__img = None

        self.previousdrawrenderersizepx = None
        self.previousdrawlvl = None
        self.previousdrawtime = None
        self.previousdrawparam = None
        self.previousdrawalpha = None
        self.previousdrawcmcontour = None
        self.previousdrawcmvelocity = None
        self.alreadypanned = False

        self.debugtext = []

    # *****************************************************************
    # funtions to be completed
    # *****************************************************************

    def change_cm_contour(self, cm):
        pass

    def change_cm_vel(self, cm):
        pass

    def CrsChanged(self):
        pass

    def canvasPaned(self):
        return (QImage(), QImage())

    def canvasChangedWithSameBBox(self):
        return (QImage(), QImage())

    def canvasCreation(self):
        return (QImage(), QImage())

    # *****************************************************************
    # abstractclass functions
    # *****************************************************************

    def changeTriangulationCRS(self):

        try:
            if self.meshlayer != None and self.meshlayer.hydrauparser != None:
                x, y = self.meshlayer.hydrauparser.getElemNodes()
                if len(x) > 0:
                    xtemp, ytemp = self.getTransformedCoords(x, y)
                    self.elemnodereprojected = (np.array(xtemp), np.array(ytemp))
                x, y = self.meshlayer.hydrauparser.getFacesNodes()
                if len(x) > 0:
                    xtemp, ytemp = self.getTransformedCoords(x, y)
                    self.facenodereprojected = (np.array(xtemp), np.array(ytemp))

                self.__CRSChangeRequested.emit()

        except Exception as e:
            self.meshlayer.propertiesdialog.errorMessage("Abstract get image - changeTriangulationCRS : " + str(e))

    def getTransformedCoords(self, xcoords, ycoords, direction=True):
        coordinatesAsPoints = [QgsPointXY(xcoords[i], ycoords[i]) for i in range(len(xcoords))]
        if direction:
            transformedCoordinatesAsPoints = [self.meshlayer.xform.transform(point) for point in coordinatesAsPoints]
        else:
            transformedCoordinatesAsPoints = [
                self.meshlayer.xform.transform(point, QgsCoordinateTransform.ReverseTransform)
                for point in coordinatesAsPoints
            ]
        xcoordsfinal = [point.x() for point in transformedCoordinatesAsPoints]
        ycoordsfinal = [point.y() for point in transformedCoordinatesAsPoints]
        return xcoordsfinal, ycoordsfinal

    def color_palette_changed_contour(self, colorramp, inverse):
        self.cmap_contour_raw = self.colormanager.qgsvectorgradientcolorrampv2ToColumncolor(colorramp, inverse)
        self.change_cm_contour(self.cmap_contour_raw)

    def color_palette_changed_vel(self, colorramp, inverse):
        self.cmap_vel_raw = self.colormanager.qgsvectorgradientcolorrampv2ToColumncolor(colorramp, inverse)
        self.change_cm_vel(self.cmap_vel_raw)

    def changeAlpha(self, nb):
        self.alpha_displayed = float(nb)
        self.change_cm_contour(self.cmap_contour_raw)
        self.change_cm_vel(self.cmap_vel_raw)

    def change_lvl_contour(self, tab):
        """
        change the levels, update color map and layer symbology
        """
        self.lvl_contour = tab
        self.change_cm_contour(self.cmap_contour_raw)
        # if not iface is None:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())

        self.meshlayer.propertiesdialog.lineEdit_levelschoosen.setText(str(self.lvl_contour))
        self.meshlayer.triggerRepaint()

    def change_lvl_vel(self, tab):
        """
        change the levels, update color map and layer symbology
        """
        self.lvl_vel = tab
        self.change_cm_vel(self.cmap_vel_raw)
        # if not iface is None:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())

        self.meshlayer.propertiesdialog.lineEdit_levelschoosen.setText(str(self.lvl_vel))
        self.meshlayer.triggerRepaint()

    def getCoordsIndexInCanvas(self, meshlayer, rendererContext):
        """
        return a new triangulation based on triangles visbles in the canvas.
        return index of selafin points correspondind to the new triangulation
        """
        mesh = np.array(meshlayer.hydrauparser.getElemFaces())

        recttemp = rendererContext.extent()
        rect = [
            float(recttemp.xMinimum()),
            float(recttemp.xMaximum()),
            float(recttemp.yMinimum()),
            float(recttemp.yMaximum()),
        ]
        """
        xMesh, yMesh = selafin.hydrauparser.getMesh()
        xMesh, yMesh = self.getTransformedCoords(xMesh, yMesh)
        """
        """
        xMesh = self.meshxreprojected
        yMesh = self.meshyreprojected
        """
        xMesh, yMesh = self.facenodereprojected

        trianx = np.array([xMesh[mesh[:, 0]], xMesh[mesh[:, 1]], xMesh[mesh[:, 2]]])
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:, 0]], yMesh[mesh[:, 1]], yMesh[mesh[:, 2]]]
        triany = np.transpose(triany)

        valtabx = np.where(np.logical_and(trianx > rect[0], trianx < rect[1]))
        valtaby = np.where(np.logical_and(triany > rect[2], triany < rect[3]))
        # index of triangles in canvas
        goodnum = np.intersect1d(valtabx[0], valtaby[0])

        goodikle = mesh[goodnum]
        goodpointindex = np.unique(goodikle)

        oldpoint = goodpointindex
        newpoints = np.arange(0, len(oldpoint), 1)

        mask = np.in1d(goodikle, oldpoint)
        idx = np.searchsorted(oldpoint, goodikle.ravel()[mask])
        goodikle.ravel()[mask] = newpoints[idx]

        return xMesh[goodpointindex], yMesh[goodpointindex], np.array(goodikle), goodpointindex

    def getMaskMesh3(self, selafin, rendererContext):
        """
        Not used - case if we want a mask mesh for tricontour
        """
        mesh = np.array(selafin.hydrauparser.getIkle())
        recttemp = rendererContext.extent()
        rect = [
            float(recttemp.xMinimum()),
            float(recttemp.xMaximum()),
            float(recttemp.yMinimum()),
            float(recttemp.yMaximum()),
        ]
        xMesh, yMesh = selafin.hydrauparser.getMesh()
        maskMesh = np.array([1.0] * len(mesh))

        trianx = np.array([xMesh[mesh[:, 0]], xMesh[mesh[:, 1]], xMesh[mesh[:, 2]]])
        trianx = np.transpose(trianx)
        triany = [yMesh[mesh[:, 0]], yMesh[mesh[:, 1]], yMesh[mesh[:, 2]]]
        triany = np.transpose(triany)

        valtabx = np.where(np.logical_and(trianx > rect[0], trianx < rect[1]))
        valtaby = np.where(np.logical_and(triany > rect[2], triany < rect[3]))

        goodnum = np.intersect1d(valtabx[0], valtaby[0])

        maskMesh[goodnum] = 0.0

        return maskMesh

    def getimage(self, meshlayer, rendererContext):
        # initialize rendered image dimension

        DEBUG = False
        if DEBUG:
            self.debugtext = []
            self.timestart = time.clock()

        painter = rendererContext.painter()
        self.__imageChangedMutex.lock()
        self.rendererContext = QgsRenderContext(rendererContext)
        self.rendererContext.setPainter(None)

        self.ext = self.rendererContext.extent()
        self.rect = [
            float(self.ext.xMinimum()),
            float(self.ext.xMaximum()),
            float(self.ext.yMinimum()),
            float(self.ext.yMaximum()),
        ]

        ratio = 1.0
        mupp = float(rendererContext.mapToPixel().mapUnitsPerPixel())
        self.sizepx = QSize(
            int(((self.rect[1] - self.rect[0]) / mupp / ratio)), int(((self.rect[3] - self.rect[2]) / mupp / ratio))
        )

        self.dpi = rendererContext.painter().device().logicalDpiX()
        self.width = float((self.sizepx.width())) / float(self.dpi)  # widht of canvas in inches
        self.lenght = float((self.sizepx.height())) / float(self.dpi)  # height of canvas in inches

        self.__imageChangedMutex.unlock()

        try:
            # ***********************************************************************
            # Case 1 : mapcanvas panned
            if (
                self.previousdrawrenderersizepx == self.sizepx
                and self.previousdrawtime == meshlayer.time_displayed
                and self.previousdrawparam == meshlayer.param_displayed
                and self.lvl_contour == self.previousdrawlvl
                and self.alpha_displayed == self.previousdrawalpha
                and self.previousdrawcmcontour == self.cmap_contour_raw
                and meshlayer.forcerefresh == False
            ):

                if DEBUG:
                    self.debugtext += ["deplacement : " + str(round(time.clock() - self.timestart, 3))]

                if self.alreadypanned:  # the whole mesh has been regenerated
                    img1, img2 = self.canvasPaned()
                else:  # maybe working with case 2 : need t oregenerate the whole mesh
                    img1, img2 = self.canvasCreation()
                    self.alreadypanned = True

            # Case 2 : figure changed (time,param) with the same mapcanvas dimension
            elif self.previousdrawrenderersizepx == self.sizepx and meshlayer.forcerefresh == False:
                # update meshlayer parameters
                self.previousdrawparam = meshlayer.param_displayed
                self.previousdrawlvl = self.lvl_contour
                self.previousdrawtime = meshlayer.time_displayed
                self.previousdrawalpha = self.alpha_displayed
                self.previousdrawrenderersizepx = self.sizepx
                self.previousdrawcmcontour = self.cmap_contour_raw
                self.alreadypanned = False

                if DEBUG:
                    self.debugtext += ["paramchanged : " + str(round(time.clock() - self.timestart, 3))]

                img1, img2 = self.canvasChangedWithSameBBox()

            # ***********************************************************************
            # Case 3 : new figure
            else:
                # update meshlayer parameters
                self.previousdrawparam = meshlayer.param_displayed
                self.previousdrawlvl = self.lvl_contour
                self.previousdrawtime = meshlayer.time_displayed
                self.previousdrawalpha = self.alpha_displayed
                self.previousdrawrenderersizepx = self.sizepx
                self.previousdrawcmcontour = self.cmap_contour_raw
                self.alreadypanned = False
                if self.meshlayer.forcerefresh == True:
                    self.meshlayer.forcerefresh = False

                if DEBUG:
                    self.debugtext += ["new fig : " + str(round(time.clock() - self.timestart, 3))]

                img1, img2 = self.canvasCreation()

            if DEBUG:
                self.debugtext += ["fin : " + str(round(time.clock() - self.timestart, 3))]
            if DEBUG:
                self.meshlayer.propertiesdialog.textBrowser_2.append(str(self.debugtext))
            return (True, img1, img2)

        except Exception as e:
            meshlayer.propertiesdialog.textBrowser_2.append("Get rendered image : " + str(e))
            return (False, QImage(), QImage())
