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

# import qgis
from qgis.utils import iface

import numpy as np

# other imports
from time import ctime

import gc
import time

from OpenGL.GL import *
from OpenGL.GL import shaders

from qgis.PyQt.QtCore import pyqtSignal, QMutex, QThread, Qt, QSize
from qgis.PyQt.QtGui import (
    QColor,
    QImage,
    QSurfaceFormat,
    QOpenGLContext,
    QOffscreenSurface,
    QOpenGLFramebufferObject,
    QOpenGLFramebufferObjectFormat,
)
from qgis.PyQt.QtWidgets import QApplication

from PyQt5.QtOpenGL import QGLFormat, QGLContext

import numpy
from math import log, ceil, exp

from .post_telemac_pluginlayer_colormanager import *
from .post_telemac_abstract_get_qimage import *

PRECISION = 0.01


def roundUpSize(size):
    """return size roudup to the nearest power of 2"""
    if False:
        return QSize(pow(2, ceil(log(size.width()) / log(2))), pow(2, ceil(log(size.height()) / log(2))))
    else:
        return size


class MeshRenderer(AbstractMeshRenderer):

    __imageChangeRequested = pyqtSignal()
    RENDERER_TYPE = "OpenGL"

    def __init__(self, meshlayer, integertemp, vtx=[[0.0, 0.0, 0.0]], idx=[0]):
        AbstractMeshRenderer.__init__(self, meshlayer, integertemp, vtx=[[0.0, 0.0, 0.0]], idx=[0])
        self.goodpointindex = None
        self.arraypoints = None

        # Opengl
        self.__vtxfacetodraw = numpy.require(vtx, numpy.float32, "F")
        self.__idxfacetodraw = numpy.require(idx, numpy.int32, "F")

        self.__vtxcanvas = numpy.require(vtx, numpy.float32, "F")
        self.__idxcanvas = numpy.require(idx, numpy.int32, "F")

        self.__vtxfacetotal = numpy.require(vtx, numpy.float32, "F")
        self.__idxfacetotal = numpy.require(idx, numpy.int32, "F")

        self.__pixBuf = None

        self.__colorPerElement = False
        self.__recompileShader = False

        self.__vtxfacetotal[:, 2] = 0

        self.meshlayer = meshlayer

        self.__imageChangedMutex = QMutex()

        self.__rendererContext = None
        self.__size = None
        self.__img = None

        self.__imageChangeRequested.connect(self.__drawInMainThread)
        self.__pixelColor = ""
        self.__pixelColorVelocity = ""

        self.__graduation = []
        self.__graduationvelocity = []

        self.timemax = 1000

        self.timestart = None

    # ************************************************************************************
    # *************************************** Display behaviour******************************
    # ************************************************************************************

    def CrsChanged(self):
        self.resetFaceNodeCoord()
        self.resetMesh()

    def resetFaceNodeCoord(self, vtx=None):
        try:
            self.__vtxfacetotal = np.array(
                [
                    [self.facenodereprojected[0][i], self.facenodereprojected[1][i], 0.0]
                    for i in range(len(self.facenodereprojected[0]))
                ]
            )
            self.__idxfacetotal = self.meshlayer.hydrauparser.getElemFaces()
            self.__idxfaceonlytotal = self.meshlayer.hydrauparser.getFaces()
            # wherebegin polygon
            self.__idxfacetotalcountidx = [0]
            self.__idxfacetotalcountlen = []

            for elem in self.__idxfacetotal:
                self.__idxfacetotalcountidx.append((self.__idxfacetotalcountidx[-1]) + len(elem))
            self.__idxfacetotalcountidx = np.array(self.__idxfacetotalcountidx)
            self.__idxfacetotalcountlen = np.array([len(elem) for elem in self.__idxfacetotal])
        except Exception as e:
            self.meshlayer.propertiesdialog.errorMessage("resetFaceNodeCoord " + str(e))

        self.__vtxfacetodraw = self.__vtxfacetotal
        self.__idxfacetodraw = self.__idxfacetotal
        self.__idxfaceonlytodraw = self.__idxfaceonlytotal
        self.__idxfacetodraw1Darray = np.array([idx for idxs in self.__idxfacetodraw for idx in idxs])
        self.__idxfaceonlytodraw1Darray = np.array([idx for idxs in self.__idxfaceonlytodraw for idx in idxs])

    def resetMesh(self):
        self.__vtxmesh = np.array(
            [
                [self.facenodereprojected[0][i], self.facenodereprojected[1][i], 0.0]
                for i in range(len(self.facenodereprojected[0]))
            ]
        )
        self.__idxmesh = self.meshlayer.hydrauparser.getFaces()

    def CrsChanged2(self):
        ikle = self.meshlayer.hydrauparser.getIkle()
        nodecoords = np.array(
            [[self.meshxreprojected[i], self.meshyreprojected[i], 0.0] for i in range(len(self.meshxreprojected))]
        )
        self.resetFaceNodeCoord(nodecoords)
        self.resetIdx(ikle)

    def change_cm_contour(self, cm_raw):
        """
        change the color map and layer symbology
        """

        self.cmap_contour_leveled = self.colormanager.fromColorrampAndLevels(self.lvl_contour, cm_raw)

        # if iface is not None:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())

        if isinstance(self.cmap_contour_leveled, list) and len(self.lvl_contour) > 0:
            colortemp = np.array(self.cmap_contour_leveled)
            for i in range(len(colortemp)):
                colortemp[i][3] = min(colortemp[i][3], self.alpha_displayed / 100.0)
            # opengl
            try:
                gradudation = []
                tempun = []
                if len(self.lvl_contour) >= 3:
                    for i, color in enumerate(colortemp):
                        gradudation.append(
                            (
                                QColor.fromRgbF(color[0], color[1], color[2], color[3]),
                                self.lvl_contour[i],
                                self.lvl_contour[i + 1],
                            )
                        )
                else:
                    color = colortemp[0]
                    gradudation.append(
                        (
                            QColor.fromRgbF(color[0], color[1], color[2], color[3]),
                            self.lvl_contour[0],
                            self.lvl_contour[1],
                        )
                    )
                self.setGraduation(gradudation)
            except Exception as e:
                self.meshlayer.propertiesdialog.errorMessage("toggle graduation " + str(e))

        if self.meshlayer.draw:
            self.meshlayer.triggerRepaint()

    def change_cm_vel(self, cm_raw):
        cm = self.colormanager.arrayStepRGBAToCmap(cm_raw)
        self.cmap_mpl_vel, self.norm_mpl_vel, self.color_mpl_vel = self.colormanager.changeColorMap(cm, self.lvl_vel)
        # try:
            # iface.legendInterface().refreshLayerSymbology(self.meshlayer)
        # except Exception as e:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())
        # transparency - alpha changed
        if self.color_mpl_vel.any() != None:
            colortemp = np.array(self.color_mpl_vel.tolist())
            for i in range(len(colortemp)):
                colortemp[i][3] = min(colortemp[i][3], self.alpha_displayed / 100.0)
            # redefine cmap_mpl_contour and norm_mpl_contour :
            self.cmap_mpl_vel, self.norm_mpl_vel = matplotlib.colors.from_levels_and_colors(self.lvl_vel, colortemp)
        # repaint
        if self.meshlayer.draw:
            self.meshlayer.triggerRepaint()
        self.cmap_vel_leveled = self.colormanager.fromColorrampAndLevels(self.lvl_vel, cm_raw)
        # if iface is not None:
            # iface.layerTreeView().refreshLayerLegend()(self.meshlayer.id())

        if isinstance(self.cmap_vel_leveled, list) and len(self.lvl_vel) > 0:
            colortemp = np.array(self.cmap_vel_leveled)
            # opengl
            try:
                gradudation = []
                tempun = []

                if len(self.lvl_vel) >= 3:
                    for i, color in enumerate(colortemp):
                        gradudation.append(
                            (
                                QColor.fromRgbF(color[0], color[1], color[2], color[3]),
                                self.lvl_vel[i],
                                self.lvl_vel[i + 1],
                            )
                        )
                else:
                    color = colortemp[0]
                    gradudation.append(
                        (
                            QColor.fromRgbF(color[0], color[1], color[2], color[3]),
                            self.lvl_vel[0],
                            self.lvl_vel[1],
                        )
                    )
                self.setGraduationVelocity(gradudation)
            except Exception as e:
                self.meshlayer.propertiesdialog.errorMessage("toggle graduation " + str(e))

        if self.meshlayer.draw:
            self.meshlayer.triggerRepaint()

    # ************************************************************************************
    # *************************************** Main func : getimage ******************************
    # ************************************************************************************

    def canvasPaned(self):
        if QApplication.instance().thread() != QThread.currentThread():
            self.__img = None
            self.__imageChangeRequested.emit()
            i = 0
            while not self.__img and not self.rendererContext.renderingStopped() and i < self.timemax:
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                i += 1
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                QThread.msleep(1)

            if not self.rendererContext.renderingStopped():
                return (self.__img, None)
        else:
            self.__drawInMainThread()
            return (self.__img, None)

    def canvasChangedWithSameBBox(self):
        if False and self.__vtxcanvas == None:
            xMeshcanvas, yMeshcanvas, goodiklecanvas, self.goodpointindex = self.getCoordsIndexInCanvas(
                self.meshlayer, self.rendererContext
            )
            nodecoords = np.array([[xMeshcanvas[i], yMeshcanvas[i], 0.0] for i in range(len(xMeshcanvas))])
            self.__vtxcanvas = numpy.require(nodecoords, numpy.float32, "F")

            self.__idxcanvas = numpy.require(goodiklecanvas, numpy.int32, "F")

        if QApplication.instance().thread() != QThread.currentThread():
            self.__img = None
            self.__imageChangeRequested.emit()

            i = 0
            while not self.__img and not self.rendererContext.renderingStopped() and i < self.timemax:
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                i += 1
                # active wait to avoid deadlocking if event loop is stopped
                # this happens when a render job is cancellled
                QThread.msleep(1)

            if not self.rendererContext.renderingStopped():
                return (self.__img, None)
        else:
            self.__drawInMainThread()
            return (self.__img, None)

    def canvasCreation(self):
        self.__vtxcanvas = None
        self.__idxcanvas = None
        self.goodpointindex = None

        self.__vtxfacetodraw = self.__vtxfacetotal
        self.__idxfacetodraw = self.__idxfacetotal

        if QApplication.instance().thread() != QThread.currentThread():
            try:
                self.__img = None
                self.__imageChangeRequested.emit()
                i = 0
                while not self.__img and not self.rendererContext.renderingStopped() and i < self.timemax:
                    # active wait to avoid deadlocking if event loop is stopped
                    # this happens when a render job is cancellled
                    i += 1
                    QThread.msleep(1)

                if not self.rendererContext.renderingStopped():
                    return (self.__img, None)
            except Exception as e:
                self.meshlayer.propertiesdialog.errorMessage("canves creation " + str(e))

        else:
            self.__drawInMainThread()
            return (self.__img, None)

    def __drawInMainThread(self):
        try:
            self.__imageChangedMutex.lock()
            includevel = True
            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 0:
                list1 = self.meshlayer.value
            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 1:
                if self.meshlayer.hydrauparser.parametrevx != None and self.meshlayer.hydrauparser.parametrevy != None:
                    list1 = np.stack(
                        (
                            self.meshlayer.value,
                            self.meshlayer.values[self.meshlayer.hydrauparser.parametrevx],
                            self.meshlayer.values[self.meshlayer.hydrauparser.parametrevy],
                        ),
                        axis=-1,
                    )
                else:
                    list1 = np.stack(
                        (
                            self.meshlayer.value,
                            np.array([0] * self.meshlayer.hydrauparser.facesnodescount),
                            np.array([0] * self.meshlayer.hydrauparser.facesnodescount),
                        ),
                        axis=-1,
                    )
                if self.goodpointindex != None:
                    list1 = list1[self.goodpointindex]

            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 2:
                list1 = self.meshlayer.value

            self.__img = self.image(
                list1,
                self.sizepx,
                # size,
                (0.5 * (self.ext.xMinimum() + self.ext.xMaximum()), 0.5 * (self.ext.yMinimum() + self.ext.yMaximum())),
                (
                    self.rendererContext.mapToPixel().mapUnitsPerPixel(),
                    self.rendererContext.mapToPixel().mapUnitsPerPixel(),
                ),
                self.rendererContext.mapToPixel().mapRotation(),
            )

            self.__imageChangedMutex.unlock()

        except Exception as e:
            self.meshlayer.propertiesdialog.errorMessage("draw " + str(e))

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
                tabx = self.facenodereprojected[0]
                taby = self.facenodereprojected[1]
                goodnum = self.goodpointindex
                tabx = tabx[goodnum]
                taby = taby[goodnum]
            else:
                tabx, taby, goodnum = self.getxynuminrenderer(selafin, rendererContext)
            tabvx = selafin.values[selafin.hydrauparser.parametrevx][goodnum]
            tabvy = selafin.values[selafin.hydrauparser.parametrevy][goodnum]
        return np.array(tabx), np.array(taby), np.array(tabvx), np.array(tabvy)

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
        tabx = self.facenodereprojected[0]
        taby = self.facenodereprojected[1]

        valtabx = np.where(np.logical_and(tabx > rect[0], tabx < rect[1]))
        valtaby = np.where(np.logical_and(taby > rect[2], taby < rect[3]))
        goodnum = np.intersect1d(valtabx[0], valtaby[0])
        tabx = tabx[goodnum]
        taby = taby[goodnum]
        return tabx, taby, goodnum

    # **********************************************************************************************
    # **********************************************************************************************
    # **********************************************************************************************
    #              OPENGL
    # **********************************************************************************************
    # **********************************************************************************************

    def __recompileNeeded(self):
        self.__recompileShader = True

    def __compileShaders(self):
        vertex_shader = shaders.compileShader(
            """
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
            """,
            GL_VERTEX_SHADER,
        )

        fragment_shader = shaders.compileShader(self._fragmentShader(), GL_FRAGMENT_SHADER)
        self.__shaders = shaders.compileProgram(vertex_shader, fragment_shader)
        self.__recompileShader = False

    def toggleGraduation(self):
        self.__graduated = True
        if self.__graduated:
            self.__pixelColor = "vec4 pixelColor(float value)\n{\n"
            for c, min_, max_ in self.__graduation:

                self.__pixelColor += (
                    "    if (float(%g) < value && value <= float(%g)) return vec4(%g, %g, %g, %g);\n"
                    % (min_, max_, c.redF(), c.greenF(), c.blueF(), c.alphaF())
                )
            self.__pixelColor += "    return vec4(0., 0., 0., 0.);\n"
            self.__pixelColor += "}\n"
        else:
            self.__pixelColor = ColorLegend.__pixelColorContinuous
        self.__recompileNeeded()

    def toggleGraduationVelocity(self):
        self.__graduated = True
        if self.__graduated:
            self.__pixelColorVelocity = "vec4 pixelColor(float value)\n{\n"
            for c, min_, max_ in self.__graduationvelocity:
                self.__pixelColorVelocity += (
                    "    if (float(%g) < value && value <= float(%g)) return vec4(%g, %g, %g, %g);\n"
                    % (min_, max_, c.redF(), c.greenF(), c.blueF(), c.alphaF())
                )
            self.__pixelColorVelocity += "    return vec4(0., 0., 0., 0.);\n"
            self.__pixelColorVelocity += "}\n"
        else:
            self.__pixelColorVelocity = ColorLegend.__pixelColorContinuous

    def setGraduation(self, graduation):
        """graduation is a list of tuple (color, min, max) the alpha componant is not considered"""
        self.__graduation = graduation
        self.toggleGraduation()

    def setGraduationVelocity(self, graduation):
        """graduation is a list of tuple (color, min, max) the alpha componant is not considered"""
        self.__graduationvelocity = graduation
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
        return (
            """
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
            """
            + self.__pixelColor
            + """
            void main()
            {
                gl_FragColor = pixelColor(value);
            }
            """
        )

    def __resize(self, roundupImageSize):
        # QGLPixelBuffer size must be power of 2
        assert roundupImageSize == roundUpSize(roundupImageSize)

        # force alpha format, it should be the default,
        self.surfaceFormat = QSurfaceFormat()

        self.context = QOpenGLContext()
        self.context.setFormat(self.surfaceFormat)
        self.context.create()

        self.surface = QOffscreenSurface()
        self.surface.setFormat(self.surfaceFormat)
        self.surface.create()

        self.context.makeCurrent(self.surface)
        self.__compileShaders()
        fmt1 = QOpenGLFramebufferObjectFormat()
        self.__pixBuf = QOpenGLFramebufferObject(roundupImageSize, fmt1)
        self.__pixBuf.takeTexture()
        self.__pixBuf.bind()
        self.context.doneCurrent()

    def image(self, values, imageSize, center, mapUnitsPerPixel, rotation=0):
        """Return the rendered image of a given size for values defined at each vertex
        or at each element depending on setColorPerElement.
        Values are normalized using valueRange = (minValue, maxValue).
        transparency is in the range [0,1]"""

        DEBUGTIME = False

        if DEBUGTIME:
            self.debugtext = []
            self.timestart = time.clock()

        try:
            if not len(values):
                img = QImage(imageSize, QImage.Format_ARGB32)
                img.fill(Qt.transparent)
                return img

            roundupSz = roundUpSize(imageSize)
            if (
                not self.__pixBuf
                or roundupSz.width() != self.__pixBuf.size().width()
                or roundupSz.height() != self.__pixBuf.size().height()
            ):
                self.__resize(roundupSz)

            val = numpy.require(values, numpy.float32) if not isinstance(values, numpy.ndarray) else values

            if self.__colorPerElement:
                val = numpy.concatenate((val, val, val))

            self.context.makeCurrent(self.surface)

            if self.__recompileShader:
                self.__compileShaders()

            glClearColor(0.0, 0.0, 0.0, 0.0)
            # tell OpenGL that the VBO contains an array of vertices
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glEnable(GL_TEXTURE_2D)

            # initialisation de la transparence
            glEnable(GL_BLEND)
            # la couleur de l'objet va etre (1-alpha_de_l_objet) * couleur du fond et (le_reste * couleur originale)
            # glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glBlendFunc(GL_SRC_ALPHA_SATURATE, GL_ONE)

            glShadeModel(GL_FLAT)
            # clear the buffer
            glClear(GL_COLOR_BUFFER_BIT)
            # set orthographic projection (2D only)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # scale
            glScalef(
                2.0 / (roundupSz.width() * mapUnitsPerPixel[0]),
                2.0 / (roundupSz.height() * mapUnitsPerPixel[1]),
                1,
            )

            # rotate
            glRotatef(-rotation, 0, 0, 1)
            ## translate
            glTranslatef(-center[0], -center[1], 0)

            glViewport(0, 0, roundupSz.width(), roundupSz.height())

            if DEBUGTIME:
                self.debugtext += ["init done : " + str(round(time.clock() - self.timestart, 3))]

            if self.meshlayer.showmesh:  # draw triangle contour but not inside
                # Draw the object here
                glDisable(GL_TEXTURE_2D)
                glUseProgram(0)

                glColor4f(0.2, 0.2, 0.2, 0.2)
                glLineWidth(1)  # or whatever
                glPolygonMode(GL_FRONT, GL_LINE)
                glPolygonMode(GL_BACK, GL_LINE)

                # Draw the object here
                glVertexPointerf(self.__vtxmesh)
                glDrawElementsui(GL_LINES, self.__idxmesh)

                # glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
                glPolygonMode(GL_FRONT, GL_FILL)
                glPolygonMode(GL_BACK, GL_FILL)

                if DEBUGTIME:
                    self.debugtext += ["mesh done : " + str(round(time.clock() - self.timestart, 3))]

            if self.meshlayer.showvelocityparams["show"]:
                glEnable(GL_PROGRAM_POINT_SIZE)
                glEnable(GL_TEXTURE_2D)

                vertex_shader_vel = shaders.compileShader(
                    """
                    
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
                        """,
                    GL_VERTEX_SHADER,
                )

                geom_shader_vel = shaders.compileShader(
                    """
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
                    
                        """,
                    GL_GEOMETRY_SHADER,
                )

                fragment_shader_vel = shaders.compileShader(
                    """
                        #version 150
                        //varying float value;
                        //varying vec2 valuevel;
                        in float value;
                        in vec2 valuevel;
                        """
                    + self.__pixelColorVelocity
                    + """
                        
                        void main() {
                         //float valuetest ;
                         //valuetest = sqrt( valuevel.x * valuevel.x + valuevel.y * valuevel.y ) ;
                          //gl_FragColor = vec4(  min( value ,1.0  ), 0.0, 0.0, 1.0);
                          gl_FragColor = pixelColor(value);
                          
                          }
                     """,
                    GL_FRAGMENT_SHADER,
                )

                self.__shadersvel = shaders.compileProgram(vertex_shader_vel, fragment_shader_vel, geom_shader_vel)

                glUseProgram(self.__shadersvel)

                temp = glGetUniformLocation(self.__shadersvel, "mapunitsperpixel")
                glUniform1f(temp, float(mapUnitsPerPixel[0]))
                temp = glGetUniformLocation(self.__shadersvel, "norm")
                glUniform1f(temp, float(self.meshlayer.showvelocityparams["norm"]))
                temp = glGetUniformLocation(self.__shadersvel, "hw")
                glUniform2f(temp, float(roundupSz.width()), float(roundupSz.height()))

                # these vertices contain 2 single precision coordinates
                glVertexPointerf(self.__vtxfacetodraw)
                glTexCoordPointer(3, GL_FLOAT, 0, val)
                glDrawArrays(GL_POINTS, 0, len(self.__vtxfacetodraw))

                if DEBUGTIME:
                    self.debugtext += ["velocity done : " + str(round(time.clock() - self.timestart, 3))]

            if self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 0:
                try:
                    if DEBUGTIME:
                        self.debugtext += ["param render start : " + str(round(time.clock() - self.timestart, 3))]
                    glColor4f(0.2, 0.2, 0.2, 0.2)
                    vtx = self.__vtxfacetodraw[self.__idxfacetodraw1Darray]
                    if DEBUGTIME:
                        self.debugtext += [
                            "param render vertex interm : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glVertexPointerf(vtx)

                    if DEBUGTIME:
                        self.debugtext += ["param render vertex done : " + str(round(time.clock() - self.timestart, 3))]

                    glDisable(GL_TEXTURE_2D)
                    glUseProgram(0)
                    glColor4f(0.2, 0.2, 0.2, 0.2)

                    if DEBUGTIME:
                        self.debugtext += ["param render color begin : " + str(round(time.clock() - self.timestart, 3))]
                    colors = np.zeros((len(val), 4))
                    colors[:, :] = np.NAN

                    for gradu in self.__graduation:
                        tempidx = np.where(np.logical_and(val > gradu[1], val < gradu[2]))
                        if len(tempidx) > 0:
                            colors[tempidx] = [
                                gradu[0].redF(),
                                gradu[0].greenF(),
                                gradu[0].blueF(),
                                gradu[0].alphaF(),
                            ]

                    colors[colors[:, 0] == np.NAN] = np.array([0.0, 0.0, 0.0, 0.0])
                    if DEBUGTIME:
                        self.debugtext += ["param render color end : " + str(round(time.clock() - self.timestart, 3))]

                    first = self.__idxfacetotalcountidx[:-1]
                    count = np.diff(self.__idxfacetotalcountidx)
                    primcount = len(self.__idxfacetotalcountidx) - 1

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first count end : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    colors2 = np.repeat(colors, count, axis=0)

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first colorpointer begin : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glEnableClientState(GL_COLOR_ARRAY)
                    glColorPointer(4, GL_FLOAT, 0, colors2)
                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first colorpointer end : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glMultiDrawArrays(GL_TRIANGLE_FAN, first, count, primcount)
                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first draw array end : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glDisableClientState(GL_COLOR_ARRAY)

                except Exception as e:
                    self.meshlayer.propertiesdialog.errorMessage("face elem rendering " + str(e))

            elif self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 1:
                glEnable(GL_TEXTURE_2D)
                glUseProgram(self.__shaders)
                glVertexPointerf(self.__vtxfacetodraw)
                glTexCoordPointer(3, GL_FLOAT, 0, val)
                glDrawElementsui(GL_TRIANGLES, self.__idxfacetodraw)

            elif self.meshlayer.hydrauparser.parametres[self.meshlayer.param_displayed][2] == 2:
                try:
                    if DEBUGTIME:
                        self.debugtext += ["param render start : " + str(round(time.clock() - self.timestart, 3))]
                    glColor4f(0.2, 0.2, 0.2, 0.2)
                    vtx = self.__vtxfacetodraw[self.__idxfaceonlytodraw1Darray]

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render vertex interm : " + str(round(time.clock() - self.timestart, 3))
                        ]
                    glVertexPointerf(vtx)

                    if DEBUGTIME:
                        self.debugtext += ["param render vertex done : " + str(round(time.clock() - self.timestart, 3))]

                    glDisable(GL_TEXTURE_2D)
                    glUseProgram(0)
                    glColor4f(0.2, 0.2, 0.2, 0.2)

                    if DEBUGTIME:
                        self.debugtext += ["param render color begin : " + str(round(time.clock() - self.timestart, 3))]
                    colors = np.zeros((len(val), 4))
                    colors[:, :] = np.NAN

                    for gradu in self.__graduation:
                        tempidx = np.where(np.logical_and(val > gradu[1], val < gradu[2]))
                        if len(tempidx) > 0:
                            colors[tempidx] = [
                                gradu[0].redF(),
                                gradu[0].greenF(),
                                gradu[0].blueF(),
                                gradu[0].alphaF(),
                            ]

                    colors[colors[:, 0] == np.NAN] = np.array([0.0, 0.0, 0.0, 0.0])

                    if DEBUGTIME:
                        self.debugtext += ["param render color end : " + str(round(time.clock() - self.timestart, 3))]

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first count end : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    colors2 = np.repeat(colors, 2, axis=0)

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first colorpointer begin : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glEnableClientState(GL_COLOR_ARRAY)
                    glColorPointer(4, GL_FLOAT, 0, colors2)

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first colorpointer end : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glLineWidth(5)  # or whatever
                    glDrawArrays(GL_LINES, 0, len(vtx))

                    if DEBUGTIME:
                        self.debugtext += [
                            "param render first draw array end : " + str(round(time.clock() - self.timestart, 3))
                        ]

                    glDisableClientState(GL_COLOR_ARRAY)

                except Exception as e:
                    self.meshlayer.propertiesdialog.errorMessage("face elem rendering " + str(e))

            if DEBUGTIME:
                self.debugtext += ["param done : " + str(round(time.clock() - self.timestart, 3))]

            img = self.__pixBuf.toImage()

            self.context.doneCurrent()

            if DEBUGTIME:
                self.debugtext += ["image done : " + str(round(time.clock() - self.timestart, 3))]
            if DEBUGTIME:
                self.meshlayer.propertiesdialog.textBrowser_2.append(str(self.debugtext))

            return img

        except Exception as e:
            self.meshlayer.propertiesdialog.errorMessage(str(e))
            return QImage()
