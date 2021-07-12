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

from qgis.PyQt.QtGui import QImage

from qgis.utils import iface

from .post_telemac_pluginlayer_colormanager import *
from .post_telemac_abstract_get_qimage import *

import matplotlib
import numpy as np
import gc
import time
from time import ctime
from io import BytesIO

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import tri
from matplotlib.backends.backend_agg import FigureCanvasAgg

DEBUG = False
PRECISION = 0.01


class MeshRenderer(AbstractMeshRenderer):

    RENDERER_TYPE = "MatPlotLib"

    def __init__(self, meshlayer, int=1):
        AbstractMeshRenderer.__init__(self, meshlayer, int)
        self.fig = plt.figure(int)
        self.ax = self.fig.add_subplot(111)
        # Reprojected things
        self.triangulation = None  # the reprojected triangulation
        # mpl figures
        self.tricontourf1 = None  # the contour plot
        self.meshplot = None  # the meshplot
        self.quiverplot = None  # the quiver plot
        self.tritemp = None  # the matplotlib triangulation centred on canvas view
        # other
        self.image_mesh = None
        self.goodpointindex = None

        # colors
        self.cmap_mpl_contour = None  # cmap modified to correspond levels values
        self.norm_mpl_contour = None
        self.cmap_mpl_vel = None
        self.norm_mpl_vel = None

    # ************************************************************************************
    # *************************************** Display behaviour******************************
    # ************************************************************************************

    def change_cm_contour(self, cm_raw):
        """
        change the color map and layer symbology
        """
        cm = self.colormanager.arrayStepRGBAToCmap(cm_raw)
        self.cmap_mpl_contour, self.norm_mpl_contour, self.cmap_contour_leveled = self.colormanager.changeColorMap(
            cm, self.lvl_contour
        )
        # if iface is not None:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())
        if isinstance(self.cmap_contour_leveled, np.ndarray):
            colortemp = np.array(self.cmap_contour_leveled)
            for i in range(len(colortemp)):
                colortemp[i][3] = min(colortemp[i][3], self.alpha_displayed / 100.0)
            self.cmap_mpl_contour, self.norm_mpl_contour = matplotlib.colors.from_levels_and_colors(
                self.lvl_contour, colortemp
            )

        if self.meshlayer.draw:
            self.meshlayer.triggerRepaint()

    def change_cm_vel(self, cm_raw):
        """
        change_cm_vel
        change the color map and layer symbology
        """
        cm = self.colormanager.arrayStepRGBAToCmap(cm_raw)
        self.cmap_mpl_vel, self.norm_mpl_vel, self.cmap_vel_leveled = self.colormanager.changeColorMap(cm, self.lvl_vel)
        # if iface is not None:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())
        if isinstance(self.cmap_vel_leveled, np.ndarray):
            colortemp = np.array(self.cmap_vel_leveled.tolist())
            for i in range(len(colortemp)):
                colortemp[i][3] = min(colortemp[i][3], self.alpha_displayed / 100.0)
            self.cmap_mpl_vel, self.norm_mpl_vel = matplotlib.colors.from_levels_and_colors(self.lvl_vel, colortemp)
        if self.meshlayer.draw:
            self.meshlayer.triggerRepaint()

    def CrsChanged(self):
        ikle = self.meshlayer.hydrauparser.getElemFaces()
        self.meshxreprojected, self.meshyreprojected = self.facenodereprojected
        self.triangulation = matplotlib.tri.Triangulation(self.meshxreprojected, self.meshyreprojected, np.array(ikle))

    # ************************************************************************************
    # *************************************** Main func : getimage ******************************
    # ************************************************************************************

    def canvasPaned(self):

        DEBUG = False

        if DEBUG:
            self.debugtext.append("deplacement")

        self.ax.set_ylim([self.rect[2], self.rect[3]])
        self.ax.set_xlim([self.rect[0], self.rect[1]])

        if DEBUG:
            self.debugtext.append("deplacement : " + str(round(time.clock() - self.timestart, 3)))
        if DEBUG:
            self.debugtext.append("rect : " + str(self.rect))

        image_contour = self.saveImage(1, self.dpi)

        return image_contour, self.image_mesh

    def canvasChangedWithSameBBox(self):

        DEBUG = False

        if DEBUG:
            self.debugtext.append("nouveau meme taille")
        if DEBUG:
            self.debugtext.append("avant value : " + str(round(time.clock() - self.timestart, 3)))

        # Removing older graph
        ncollections = len(self.ax.collections)
        for i in range(ncollections):
            # print str(self.ax.collections[0])
            self.ax.collections[0].remove()
        self.fig.canvas.flush_events()
        gc.collect()

        # first time - if image of mesh is not created
        if self.image_mesh == None and self.meshlayer.showmesh:
            # create image mesh
            self.image_mesh = self.saveImage(1, self.dpi)
            # remove mesh graph
            self.ax.cla()
            self.ax.axes.axis("off")

        if not self.tritemp:  # create temp triangulation
            xMeshcanvas, yMeshcanvas, goodiklecanvas, self.goodpointindex = self.getCoordsIndexInCanvas(
                self.meshlayer, self.rendererContext
            )
            self.tritemp = matplotlib.tri.Triangulation(xMeshcanvas, yMeshcanvas, goodiklecanvas)

            if DEBUG:
                self.debugtext.append("tritemp : " + str(round(time.clock() - self.timestart, 3)))

        self.tricontourf1 = self.ax.tricontourf(
            self.tritemp,
            self.meshlayer.value[self.goodpointindex],
            self.lvl_contour,
            cmap=self.cmap_mpl_contour,
            norm=self.norm_mpl_contour,
            # alpha = meshlayer.alpha_displayed/100.0,
            nchunk=10,
        )

        if DEBUG:
            self.debugtext.append("tricontourf : " + str(round(time.clock() - self.timestart, 3)))

        if self.meshlayer.showvelocityparams["show"]:
            tabx, taby, tabvx, tabvy = self.getVelocity(self.meshlayer, self.rendererContext)
            C = np.sqrt(tabvx ** 2 + tabvy ** 2)

            tabx = tabx[np.where(C > PRECISION)]
            taby = taby[np.where(C > PRECISION)]
            tabvx = tabvx[np.where(C > PRECISION)]
            tabvy = tabvy[np.where(C > PRECISION)]
            C = C[np.where(C > PRECISION)]

            if self.meshlayer.showvelocityparams["norm"] >= 0:
                self.quiverplot = self.ax.quiver(
                    tabx,
                    taby,
                    tabvx,
                    tabvy,
                    C,
                    scale=self.meshlayer.showvelocityparams["norm"],
                    scale_units="xy",
                    cmap=self.cmap_mpl_vel,
                    norm=self.norm_mpl_vel,
                )
            else:
                UN = np.array(tabvx) / C
                VN = np.array(tabvy) / C
                self.quiverplot = self.ax.quiver(
                    tabx,
                    taby,
                    UN,
                    VN,
                    C,
                    cmap=self.cmap_mpl_vel,
                    scale=-1 / self.meshlayer.showvelocityparams["norm"],
                    scale_units="xy",
                )

            if DEBUG:
                self.debugtext.append("quiver : " + str(round(time.clock() - self.timestart, 3)))

        self.ax.set_ylim([self.rect[2], self.rect[3]])
        self.ax.set_xlim([self.rect[0], self.rect[1]])
        image_contour = self.saveImage(1, self.dpi)
        return image_contour, self.image_mesh

    def canvasCreation(self):

        DEBUG = False

        if DEBUG:
            time1.append("nouveau")

        # matplotlib figure construction
        self.fig.set_size_inches(self.width, self.lenght)
        self.ax.cla()
        # no axis nor border
        self.fig.patch.set_visible(False)
        self.ax.axes.axis("off")
        self.ax.set_ylim([self.rect[2], self.rect[3]])
        self.ax.set_xlim([self.rect[0], self.rect[1]])
        # self.mask = None
        self.tritemp = None
        self.image_mesh = None
        self.goodpointindex = None

        # graph
        if DEBUG:
            self.debugtext.append("value : " + str(round(time.clock() - self.timestart, 3)))

        self.tricontourf1 = self.ax.tricontourf(
            self.triangulation,
            self.meshlayer.value,
            self.lvl_contour,
            cmap=self.cmap_mpl_contour,
            norm=self.norm_mpl_contour,
            extend="neither",
        )

        if self.meshlayer.showmesh:
            self.meshplot = self.ax.triplot(
                self.triangulation, "k,-", color="0.5", linewidth=0.5, alpha=self.alpha_displayed / 100.0
            )

        if self.meshlayer.showvelocityparams["show"]:
            tabx, taby, tabvx, tabvy = self.getVelocity(self.meshlayer, self.rendererContext)
            C = np.sqrt(tabvx ** 2 + tabvy ** 2)

            tabx = tabx[np.where(C > PRECISION)]
            taby = taby[np.where(C > PRECISION)]
            tabvx = tabvx[np.where(C > PRECISION)]
            tabvy = tabvy[np.where(C > PRECISION)]
            C = C[np.where(C > PRECISION)]

            if self.meshlayer.showvelocityparams["norm"] >= 0:
                self.quiverplot = self.ax.quiver(
                    tabx,
                    taby,
                    tabvx,
                    tabvy,
                    C,
                    scale=self.meshlayer.showvelocityparams["norm"],
                    scale_units="xy",
                    cmap=self.cmap_mpl_vel,
                    norm=self.norm_mpl_vel,
                )
            else:
                UN = np.array(tabvx) / C
                VN = np.array(tabvy) / C
                self.quiverplot = self.ax.quiver(
                    tabx,
                    taby,
                    UN,
                    VN,
                    C,
                    cmap=self.cmap_mpl_vel,
                    scale=-1 / self.meshlayer.showvelocityparams["norm"],
                    scale_units="xy",
                )

            if DEBUG:
                self.debugtext.append("quiver : " + str(round(time.clock() - self.timestart, 3)))

        self.fig.subplots_adjust(0, 0, 1, 1)
        image_contour = self.saveImage(1, self.dpi)
        return image_contour, self.image_mesh

    # ************************************************************************************
    # *************************************** Secondary func  ******************************
    # ************************************************************************************

    def getVelocity(self, selafin, rendererContext):
        tabx = []
        taby = []
        tabvx = []
        tabvy = []
        recttemp = rendererContext.extent()
        rect = [
            float(recttemp.xMinimum()),
            float(recttemp.xMaximum()),
            float(recttemp.yMinimum()),
            float(recttemp.yMaximum()),
        ]
        if selafin.showvelocityparams["type"] in [0, 1]:
            if selafin.showvelocityparams["type"] == 0:
                nombrecalcul = selafin.showvelocityparams["step"]
                pasespace = int((rect[1] - rect[0]) / nombrecalcul)
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0] / pasespace) * pasespace
                rect[2] = int(rect[2] / pasespace) * pasespace
                rangex = nombrecalcul + 3
                rangey = nombrecalcul + 3
                pasy = int((rect[3] - rect[2]) / nombrecalcul)
            elif selafin.showvelocityparams["type"] == 1:
                pasespace = selafin.showvelocityparams["step"]
                pasx = pasespace
                pasy = pasespace
                rect[0] = int(rect[0] / pasespace) * pasespace
                rect[2] = int(rect[2] / pasespace) * pasespace
                rangex = int((rect[1] - rect[0]) / pasespace) + 3
                rangey = int((rect[3] - rect[2]) / pasespace) + 3

            x = np.arange(rect[0], rect[0] + rangex * pasx, pasx)
            y = np.arange(rect[2], rect[2] + rangey * pasy, pasy)
            mesh = np.meshgrid(x, y)
            tabx = np.ravel(mesh[0].tolist())
            taby = np.ravel(mesh[1].tolist())
            if not selafin.triinterp:
                selafin.initTriinterpolator()
            tempx1, tempy1 = self.getTransformedCoords(tabx, taby, False)
            tabvx = selafin.triinterp[selafin.hydrauparser.parametrevx].__call__(tempx1, tempy1)
            tabvy = selafin.triinterp[selafin.hydrauparser.parametrevy].__call__(tempx1, tempy1)

        elif selafin.showvelocityparams["type"] == 2:
            if not self.goodpointindex == None:
                tabx = self.meshxreprojected
                taby = self.meshyreprojected
                goodnum = self.goodpointindex
                tabx = tabx[goodnum]
                taby = taby[goodnum]
            else:
                tabx, taby, goodnum = self.getxynuminrenderer(selafin, rendererContext)
            tabvx = selafin.values[selafin.hydrauparser.parametrevx][goodnum]
            tabvy = selafin.values[selafin.hydrauparser.parametrevy][goodnum]
        return np.array(tabx), np.array(taby), np.array(tabvx), np.array(tabvy)

    def saveImage(self, ratio, dpi2):
        """
        Return a qimage of the matplotlib figure
        """
        try:
            buf = BytesIO()
            self.fig.canvas.print_figure(buf, dpi=dpi2)
            buf.seek(0)
            image = QImage.fromData(buf.getvalue())
            if ratio > 1.0:
                image = image.scaled(image.width() * ratio, image.height() * ratio)
            return image
        except Exception as e:
            self.meshlayer.propertiesdialog.textBrowser_2.append("getqimagesave : " + str(e))
            return None

    def getxynuminrenderer(self, selafin, rendererContext):
        """
        Return index of selafin points in the visible canvas with corresponding x and y value
        """
        recttemp = rendererContext.extent()
        rect = [
            float(recttemp.xMinimum()),
            float(recttemp.xMaximum()),
            float(recttemp.yMinimum()),
            float(recttemp.yMaximum()),
        ]

        tabx = self.meshxreprojected
        taby = self.meshyreprojected

        valtabx = np.where(np.logical_and(tabx > rect[0], tabx < rect[1]))
        valtaby = np.where(np.logical_and(taby > rect[2], taby < rect[3]))
        goodnum = np.intersect1d(valtabx[0], valtaby[0])
        tabx = tabx[goodnum]
        taby = taby[goodnum]
        return tabx, taby, goodnum
