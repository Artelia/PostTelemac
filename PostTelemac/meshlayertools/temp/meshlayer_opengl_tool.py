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

import sip

try:
    apis = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
    for api in apis:
        sip.setapi(api, 2)
except ValueError:
    # API has already been set so we can't set it again.
    pass

if False:
    from PyQt4 import uic, QtCore, QtGui
    from PyQt4.QtOpenGL import *
    from PyQt4 import QtCore, QtGui, QtOpenGL

if False:
    try:
        from qgis.PyQt import uic, QtCore, QtGui
        from qgis.PyQt.QtOpenGL import *
        from qgis.PyQt import QtCore, QtGui, QtOpenGL
    except:
        pass


if True:
    try:
        from qgis.PyQt.QtGui import QDialog, QVBoxLayout
    except:
        from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout

    try:
        from PyQt4 import uic, QtCore, QtGui, QtOpenGL
        from PyQt4.QtOpenGL import *
    except:
        from PyQt5 import uic, QtCore, QtGui, QtOpenGL
        from PyQt5.QtOpenGL import *


try:
    from OpenGL.GL import *
    from OpenGL.GL import shaders
    import OpenGL

    OpenGL.ERROR_CHECKING = True
    from OpenGL.GL import *
    from OpenGL.GLU import *
except:
    pass


from .meshlayer_abstract_tool import *


import math
import numpy
import numpy.linalg as linalg


import numpy as np

try:
    import PIL
except:
    pass

import sys

import time

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "OpenGLTool.ui"))


class OpenGLTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "OPENGLTOOL"
    SOFTWARE = ["TELEMAC", "ANUGA"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)
        # self.setupUi(self)

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Video_48x48.png")

        self.pushButton.clicked.connect(self.openglWindow)

    def openglWindow(self):
        if True:
            # app = QtGui.QApplication(["Winfred's PyQt OpenGL"])
            self.widget = OpenGLDialog(self.meshlayer)
            # self.widget.show()

            self.widget.setWindowModality(2)
            r = self.widget.exec_()
            # widget.exec_()

    def onActivation(self):
        pass

    def onDesactivation(self):
        pass


FORM_CLASS2, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "OpenGLTool_widget.ui"))

# class AbstractMeshLayerTool(QtGui.QWidget, FORM_CLASS):
class OpenGLDialog(QDialog, FORM_CLASS2):
    def __init__(self, meshlayer=None, parent=None):
        super(QDialog, self).__init__(parent)
        self.setupUi(self)
        self.meshlayer = meshlayer
        self.verticalz = self.spinBox_z.value()
        self.time = 0
        if self.meshlayer == None:
            self.openglwidget = PyGLWidget(self)
        else:
            self.openglwidget = PyGLWidget(self, self.meshlayer)

        layout = QVBoxLayout()
        layout.addWidget(self.openglwidget)

        self.frame_qglwidget.setLayout(layout)

        self.playing = False

        # self.pushButton_play.clicked.connect(self.playFlood)
        self.pushButton_resetview.clicked.connect(self.resetview)
        self.pushButton_play.clicked.connect(self.playFlood)

        self.horizontalSlider_time.setMaximum(self.openglwidget.parser.itertimecount)
        self.horizontalSlider_time.setPageStep(min(10, int(self.openglwidget.parser.itertimecount / 20)))
        self.horizontalSlider_time.valueChanged.connect(self.change_time)

        self.checkBox_showmesh.stateChanged.connect(self.updateGL)

        self.spinBox_z.valueChanged.connect(self.verticalSet)

        self.setMinimumSize(1000, 800)

    def playFlood(self):
        self.openglwidget.play()

    def change_time(self, nb):
        self.time = nb
        self.openglwidget.changeFreeSurfaceVertex(self.time)
        self.openglwidget.updateGL()

    def updateGL(self):
        self.openglwidget.updateGL()

    def verticalSet(self, nb):
        self.verticalz = nb
        self.openglwidget.loadVertexes()
        self.openglwidget.changeFreeSurfaceVertex(self.time)
        self.openglwidget.updateGL()

    def resetview(self):
        self.openglwidget.reset_view()
        self.openglwidget.updateGL()


class PyGLWidget(QtOpenGL.QGLWidget):

    # Qt signals
    signalGLMatrixChanged = QtCore.pyqtSignal()
    rotationBeginEvent = QtCore.pyqtSignal()
    rotationEndEvent = QtCore.pyqtSignal()
    paintdone = QtCore.pyqtSignal()

    def __init__(self, dialog, meshlayer=None, parent=None):
        self.meshlayer = meshlayer
        self.dialog = dialog
        format = QtOpenGL.QGLFormat()
        format.setSampleBuffers(True)
        QtOpenGL.QGLWidget.__init__(self, format, parent)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setMouseTracking(True)
        self.time = 0

        self.modelview_matrix_ = []
        self.translate_vector_ = [0.0, 0.0, 0.0]
        self.viewport_matrix_ = []
        self.projection_matrix_ = []
        self.near_ = 0.01
        self.far_ = 100000.0
        self.fovy_ = 45.0
        self.radius_ = 0.0
        self.last_point_2D_ = QtCore.QPoint()
        self.last_point_ok_ = False
        self.last_point_3D_ = [1.0, 0.0, 0.0]
        self.isInRotation_ = False

        self.texture = True

        self.rays = []
        self.pointtodraw = []

        self.ratioxy = 1000.0
        self.precision = GL_FLOAT
        # self.precision = GL_DOUBLE

        if meshlayer != None:

            self.parser = self.meshlayer.hydrauparser

        else:
            sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
            from meshlayerparsers.posttelemac_selafin_parser import PostTelemacSelafinParser

            self.parser = PostTelemacSelafinParser()
            self.parser.loadHydrauFile(os.path.join(os.path.dirname(__file__), "exemples", "Test1.res"))
        self.loadVertexes()
        self.changeFreeSurfaceVertex(0)

        if self.texture:
            try:
                if True:
                    self.im = PIL.Image.open(os.path.join(os.path.dirname(__file__), "textures", "grassbis.png"))
                    # self.im = PIL.Image.open(os.path.join(os.path.dirname(__file__) ,'textures','grass2.jpg') )
                    # print self.im.mode
                    try:  # older version of pil
                        if self.im.mode == "RGBA":
                            self.ix, self.iy, self.image = (
                                self.im.size[0],
                                self.im.size[1],
                                self.im.tostring("raw", "RGBA", 0, -1),
                            )
                        elif self.im.mode == "RGB":
                            self.ix, self.iy, self.image = (
                                self.im.size[0],
                                self.im.size[1],
                                self.im.tostring("raw", "RGBX", 0, -1),
                            )
                        # except SystemError:
                    except Exception as e:
                        # print 'grass ' + str(e)
                        # self.ix, self.iy, self.image = self.im.size[0], self.im.size[1], self.im.tobytes("raw", "RGBX", 0, -1)
                        if self.im.mode == "RGBA":
                            self.ix, self.iy, self.image = (
                                self.im.size[0],
                                self.im.size[1],
                                self.im.tobytes("raw", "RGBA", 0, -1),
                            )  # works on unbuntu witj .jpg
                        elif self.im.mode == "RGB":
                            self.ix, self.iy, self.image = (
                                self.im.size[0],
                                self.im.size[1],
                                self.im.tobytes("raw", "RGBX", 0, -1),
                            )  # works on unbuntu witj .jpg
                        # self.ix, self.iy, self.image = self.im.size[0], self.im.size[1],  numpy.array(list(self.im.getdata()), numpy.int8)  #works on win witj .png
                if False:
                    glActiveTexture(GL_TEXTURE0)
                    ID = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, ID)
                    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

                    glTexImage2D(GL_TEXTURE_2D, 0, 3, self.ix, self.iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image)
                    # glTexImage2D( GL_TEXTURE_2D, 0, 3, 100.0/self.ratioxy , 100*self.iy/self.ix/self.ratioxy , 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image )

                    glBindTexture(GL_TEXTURE_2D, ID)

                if True:
                    self.im2 = PIL.Image.open(os.path.join(os.path.dirname(__file__), "textures", "water3.png"))
                    # self.im2 = PIL.Image.open(os.path.join(os.path.dirname(__file__) ,'textures','water3.jpg') )
                    # print self.im2.mode
                    try:
                        if self.im2.mode == "RGBA":
                            self.ix2, self.iy2, self.image2 = (
                                self.im2.size[0],
                                self.im2.size[1],
                                self.im2.tostring("raw", "RGBA", 0, -1),
                            )
                        elif self.im2.mode == "RGB":
                            self.ix2, self.iy2, self.image2 = (
                                self.im2.size[0],
                                self.im2.size[1],
                                self.im2.tostring("raw", "RGBX", 0, -1),
                            )
                        # except SystemError:
                    except Exception as e:
                        # print 'water ' + str(e)

                        self.ix2, self.iy2, self.image2 = (
                            self.im2.size[0],
                            self.im2.size[1],
                            self.im2.tobytes("raw", "RGBX", 0, -1),
                        )  # works on unbuntu witj .jpg
                        # self.ix2, self.iy2, self.image2 = self.im2.size[0], self.im2.size[1], numpy.array(list(self.im2.getdata()), numpy.int8)
                if False:
                    glActiveTexture(GL_TEXTURE1)
                    ID = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, ID)
                    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

                    glTexImage2D(GL_TEXTURE_2D, 0, 3, self.ix2, self.iy2, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image2)
                    glBindTexture(GL_TEXTURE_2D, ID)
            except:
                pass

        # connections
        # self.signalGLMatrixChanged.connect(self.printModelViewMatrix)
        """
        # Radius of sphere
        self.radius = radius

        # Number of latitudes in sphere
        self.lats = 100

        # Number of longitudes in sphere
        self.longs = 100

        self.user_theta = 0
        self.user_height = 0
        """
        # Direction of light
        self.direction = [-1.0, -1.0, -1.0, 1.0]

        # Intensity of light
        self.intensity = [0.7, 0.7, 0.7, 1.0]

        # Intensity of ambient light
        self.ambient_intensity = [0.3, 0.3, 0.3, 1.0]

        # The surface type(Flat or Smooth)
        self.surface = GL_FLAT
        # print 'init ok'

    def play(self):
        print("click " + str(self.dialog.playing))
        if self.dialog.playing == False:
            self.dialog.playing == True
            self.paintdone.connect(self.play2)
            self.updateGL()
        else:
            self.dialog.playing == False
            self.paintdone.disconnect(self.play2)

    def play2(self):
        time.sleep(1)
        self.time += 1
        self.changeFreeSurfaceVertex(self.time)
        print("before" + str(self.time))

        self.updateGL()
        print("after")
        time.sleep(1)

    def loadVertexes(self):
        # self.meshx, self.meshy = self.parser.getMesh()
        self.meshx, self.meshy = self.parser.getFacesNodes()
        """
        self.vtxtodraw = ( np.stack((self.meshx, 
                                self.meshy, 
                                self.parser.getRawValues(0)[self.parser.parambottom]*self.dialog.verticalz )  , 
                                axis=-1)   ) /self.ratioxy
        """
        self.vtxtodraw = (
            np.stack(
                (self.meshx, self.meshy, self.parser.getValues(0)[self.parser.parambottom] * self.dialog.verticalz),
                axis=-1,
            )
        ) / self.ratioxy

        self.centermesh = (
            np.array([(max(self.meshx) + min(self.meshx)) / 2, (max(self.meshy) + min(self.meshy)) / 2, 0.0])
            / self.ratioxy
        )

        norm = np.zeros(self.vtxtodraw.shape, dtype=self.vtxtodraw.dtype)
        tris = self.vtxtodraw[self.parser.getElemFaces()]

        n = np.cross(tris[::, 1] - tris[::, 0], tris[::, 2] - tris[::, 0])
        self.normalize_v3(n)
        self.nomrtemp = n

        norm[self.parser.getElemFaces()[:, 0]] += n
        norm[self.parser.getElemFaces()[:, 1]] += n
        norm[self.parser.getElemFaces()[:, 2]] += n
        self.normalize_v3(norm)
        self.norm = norm

        self.radius_ = math.atan(self.fovy_ / 180 * math.pi) * max(
            (max(self.vtxtodraw[:, 0]) - min(self.vtxtodraw[:, 0])),
            (max(self.vtxtodraw[:, 1]) - min(self.vtxtodraw[:, 1])),
        )

    def changeFreeSurfaceVertex(self, time):

        if self.parser.parametreh != None:
            # zvalue = self.parser.getRawValues(time)[self.parser.parametreh]
            zvalue = self.parser.getValues(time)[self.parser.parametreh]

            indexzvalue = np.where(zvalue >= 0.05)

            # ikle = self.parser.getIkle()
            ikle = self.parser.getElemFaces()

            ikle1D = ikle.ravel()
            temp = np.in1d(ikle1D, indexzvalue)
            temp1 = temp.reshape(-1, 3)
            # print 'temp \n' + str(temp1)
            # print 'temp \n' + str(temp1.shape)
            # print 'ikle \n' + str(ikle.shape)

            # tempindex = np.where(temp1 == np.array([True,True,True]) )
            # tempindex = np.all(temp1 == np.array([True,True,True]), axis = 1)
            tempindex = np.all(temp1 == True, axis=1)

            # print 'tempindex \n' + str( tempindex )
            # print 'ikle \n' + str( ikle )
            iklewater = ikle[tempindex]

            # print 'iklewater \n' + str( iklewater )
            # print 'iklewater shape\n' + str( iklewater.shape )

            """
            self.vtxtodrawwater = np.stack((self.meshx, 
                                    self.meshy, 
                                    self.parser.getRawValues(time)[self.parser.paramfreesurface]*self.dialog.verticalz )  , 
                                    axis=-1)  /self.ratioxy  
            """
            self.vtxtodrawwater = (
                np.stack(
                    (
                        self.meshx,
                        self.meshy,
                        self.parser.getValues(time)[self.parser.paramfreesurface] * self.dialog.verticalz,
                    ),
                    axis=-1,
                )
                / self.ratioxy
            )

            self.iklewater = iklewater

            norm = np.zeros(self.vtxtodrawwater.shape, dtype=self.vtxtodrawwater.dtype)
            tris = self.vtxtodrawwater[self.iklewater]

            n = np.cross(tris[::, 1] - tris[::, 0], tris[::, 2] - tris[::, 0])
            self.normalize_v3(n)
            self.nomrtemp = n

            norm[self.iklewater[:, 0]] += n
            norm[self.iklewater[:, 1]] += n
            norm[self.iklewater[:, 2]] += n
            self.normalize_v3(norm)
            self.normwater = norm

    @QtCore.pyqtSlot()
    def printModelViewMatrix(self):
        print(self.modelview_matrix_)

    def initializeGL(self):
        # OpenGL state
        # glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearColor(135.0 / 255.0, 206.0 / 255.0, 235.0 / 255.0, 0.0)
        glEnable(GL_DEPTH_TEST)
        self.reset_view()

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        self.set_projection(self.near_, self.far_, self.fovy_)
        self.updateGL()

    def normalize_v3(self, arr):
        """ Normalize a numpy array of 3 component vectors shape=(n,3) """
        lens = np.sqrt(arr[:, 0] ** 2 + arr[:, 1] ** 2 + arr[:, 2] ** 2)
        arr[:, 0] /= lens
        arr[:, 1] /= lens
        arr[:, 2] /= lens
        return arr

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_MODELVIEW)
        glLoadMatrixd(self.modelview_matrix_)

        if True:

            # ********************************************************************
            # *****************  MESH *************************
            # ********************************************************************

            if self.dialog.checkBox_showmesh.isChecked():
                if True:  # working
                    glUseProgram(0)
                    glDisable(GL_LIGHTING)
                    glEnableClientState(GL_VERTEX_ARRAY)
                    # glDisableClientState( GL_NORMAL_ARRAY )
                    # glEnable(GL_TEXTURE_2D)
                    glShadeModel(GL_SMOOTH)
                    # glColor4f(0.2,0.2,0.2,0.2)
                    glLineWidth(1)  # or whatever
                    glPolygonMode(GL_FRONT, GL_LINE)
                    glPolygonMode(GL_BACK, GL_LINE)
                    glColor4f(1.0, 1.0, 1.0, 1.0)

                    glVertexPointerf(self.vtxtodraw)
                    # glVertexPointer(3, self.precision, 0, self.vtxtodraw)
                    # glTexCoordPointer(1, GL_FLOAT, 0, val)
                    glDrawElementsui(GL_TRIANGLES, self.parser.getElemFaces())

                    glPolygonMode(GL_FRONT, GL_FILL)
                    glPolygonMode(GL_BACK, GL_FILL)

            # ********************************************************************
            # *****************  CENTER POINT      *************************
            # ********************************************************************

            glUseProgram(0)
            for point in self.pointtodraw:
                glPointSize(20.0)
                glBegin(GL_POINTS)

                glColor3f(1, 0, 0)
                glVertex3f(point[0], point[1], point[2])

                glEnd()

            # ********************************************************************
            # *****************  TErrain  *************************
            # ********************************************************************

            if True:
                # glUseProgram(0)

                # *****************  Light  *************************************

                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_NORMAL_ARRAY)
                glEnable(GL_TEXTURE_2D)
                # glEnable(GL_DEPTH_TEST)
                # glEnable(GL_CULL_FACE)

                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # not what i wnat
                # glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

                if True:
                    # Enable lighting
                    glEnable(GL_LIGHTING)

                    # Set light model
                    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, self.ambient_intensity)

                    # Enable light number 0
                    glEnable(GL_LIGHT0)

                    # Set position and intensity of light
                    # glLightfv(GL_LIGHT0, GL_POSITION, self.direction)
                    glLightfv(GL_LIGHT0, GL_DIFFUSE, self.intensity)

                    # Setup the material
                    glEnable(GL_COLOR_MATERIAL)
                    glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)

                # glShadeModel(self.surface)
                glShadeModel(GL_SMOOTH)

                # *****************  Terrain   *************************************

                if True:
                    if self.texture:
                        if True:
                            try:
                                ID = glGenTextures(1)
                                # glBindTexture(GL_TEXTURE_2D, ID)
                                glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

                                glTexImage2D(
                                    GL_TEXTURE_2D, 0, 3, self.ix, self.iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image
                                )
                                # glTexImage2D( GL_TEXTURE_2D, 0, 3, 100.0/self.ratioxy , 100*self.iy/self.ix/self.ratioxy , 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image )

                            except:
                                pass

                        if True:

                            glEnable(GL_TEXTURE_2D)
                            # glActiveTexture(GL_TEXTURE0)
                            if True:
                                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                            if False:
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                            # glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
                            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
                            # glBindTexture(GL_TEXTURE_2D, ID)
                            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                            glTexCoordPointerf(self.vtxtodraw)
                            # glTexCoordPointer(3, self.precision, 0, self.vtxtodraw)

                # shader = shaders.compileProgram(vertex_shader_vel)
                # glUseProgram(shader)

                # glColor4f(77./255., 158./255., 58./255.,1.0)
                glColor4f(1.0, 1.0, 1.0, 1.0)
                if True:
                    glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.0, 0.8, 0.8, 1.0])

                    glVertexPointerf(self.vtxtodraw)
                    # glVertexPointer(3, self.precision, 0, self.vtxtodraw)

                    if True:
                        no = self.norm[self.parser.getElemFaces()]
                        # glNormalPointerf(no)
                        glNormalPointerf(self.norm)
                        # glNormalPointer(self.precision, 0, self.norm)
                        # glNormalPointerf(self.nomrtemp)
                    # glTexCoordPointer(1, GL_FLOAT, 0, val)
                    glDrawElementsui(GL_TRIANGLES, self.parser.getElemFaces())

                # *****************  water   *************************************

                if True:
                    if self.texture:
                        if True:
                            try:
                                ID = glGenTextures(1)
                                # glBindTexture(GL_TEXTURE_2D, ID)
                                glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

                                glTexImage2D(
                                    GL_TEXTURE_2D, 0, 3, self.ix2, self.iy2, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image2
                                )
                            except:
                                pass
                        if True:
                            glEnable(GL_TEXTURE_2D)
                            # glActiveTexture(GL_TEXTURE1)
                            if False:
                                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                            if True:
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                            # glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
                            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
                            # glBindTexture(GL_TEXTURE_2D, ID)
                            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                            glTexCoordPointerf(self.vtxtodraw)

                if True:
                    glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.2, 0.2, 0.2, 1.0])
                    glColor4f(1.0, 1.0, 1.0, 0.8)
                    glVertexPointerf(self.vtxtodrawwater)

                    if False:
                        no = self.normwater[self.parser.getElemFaces()]
                        # glNormalPointerf(no)
                        glNormalPointerf(self.normwater)
                        # glNormalPointerf(self.nomrtemp)
                    # glTexCoordPointer(1, GL_FLOAT, 0, val)
                    glDrawElementsui(GL_TRIANGLES, self.iklewater)

                # *****************  ray    *************************************

                if False:
                    glUseProgram(0)
                    for ray in self.rays:
                        eye = ray[0]
                        ray_eye = ray[1]
                        glLineWidth(5.0)
                        glBegin(GL_LINES)
                        glColor3f(0, 0, 0)
                        glVertex3f(eye[0], eye[1], eye[2])
                        glVertex3f(eye[0] + ray_eye[0] * 100, eye[1] + ray_eye[1] * 100, eye[2] + ray_eye[2] * 100)

                        glEnd()

                glDisable(GL_COLOR_MATERIAL)
                glDisable(GL_LIGHT0)
                glDisable(GL_LIGHTING)
                glDisableClientState(GL_NORMAL_ARRAY)
                glDisable(GL_TEXTURE_2D)

        # print 'paintdone'
        self.paintdone.emit()

    def set_projection(self, _near, _far, _fovy):
        self.near_ = _near
        self.far_ = _far
        self.fovy_ = _fovy
        self.makeCurrent()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fovy_, float(self.width()) / float(self.height()), self.near_, self.far_)
        self.updateGL()

    def set_center(self, _cog):
        # print _cog
        self.center_ = _cog
        self.view_all()

    """
    def set_radius(self, _radius):
        self.radius_ = _radius
        self.set_projection(_radius / 100.0, _radius * 100.0, self.fovy_)
        self.reset_view()
        self.translate([0, 0, -_radius * 2.0])
        self.view_all()
        self.updateGL()
    """

    def reset_view(self):
        # scene pos and size
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.modelview_matrix_ = glGetDoublev(GL_MODELVIEW_MATRIX)
        # self.set_center([0.0, 0.0, 0.0])
        self.set_center(self.centermesh)

    def reset_rotation(self):
        self.modelview_matrix_[0] = [1.0, 0.0, 0.0, 0.0]
        self.modelview_matrix_[1] = [0.0, 1.0, 0.0, 0.0]
        self.modelview_matrix_[2] = [0.0, 0.0, 1.0, 0.0]
        glMatrixMode(GL_MODELVIEW)
        glLoadMatrixd(self.modelview_matrix_)
        self.updateGL()

    def translate(self, _trans):
        # Translate the object by _trans
        # Update modelview_matrix_
        self.makeCurrent()
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # print 'before \n' + str(glGetDoublev(GL_MODELVIEW_MATRIX))
        glTranslated(_trans[0], _trans[1], _trans[2])
        # print 'after \n' + str(glGetDoublev(GL_MODELVIEW_MATRIX))
        glMultMatrixd(self.modelview_matrix_)
        self.modelview_matrix_ = glGetDoublev(GL_MODELVIEW_MATRIX)

        self.dialog.textEdit_modelview.setText(str(np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX)))))
        # self.dialog.textEdit_projectionview.setText(  str( np.transpose(  np.array(glGetDoublev(GL_PROJECTION_MATRIX) )  )  )     )

        # print self.modelview_matrix_

        if False:
            self.translate_vector_[0] = self.modelview_matrix_[3][0]
            self.translate_vector_[1] = self.modelview_matrix_[3][1]
            self.translate_vector_[2] = self.modelview_matrix_[3][2]
            self.signalGLMatrixChanged.emit()

    def rotate(self, _axis, _angle):

        t = np.dot(
            np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX))),
            np.array([self.center_[0], self.center_[1], self.center_[2], 1.0]),
        )

        self.makeCurrent()

        glLoadIdentity()
        glTranslatef(t[0], t[1], t[2])
        glRotated(_angle, _axis[0], _axis[1], _axis[2])
        glTranslatef(-t[0], -t[1], -t[2])
        glMultMatrixd(self.modelview_matrix_)
        self.modelview_matrix_ = glGetDoublev(GL_MODELVIEW_MATRIX)

        self.dialog.textEdit_modelview.setText(str(np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX)))))
        # self.dialog.textEdit_projectionview.setText(  str( np.transpose(  np.array(glGetDoublev(GL_PROJECTION_MATRIX) )  )  )     )

        self.signalGLMatrixChanged.emit()

    def view_all(self):

        t = -np.dot(
            np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX))),
            np.array([self.center_[0], self.center_[1], self.center_[2], 1.0]),
        )

        if False:
            print(
                max(
                    (max(self.vtxtodraw[:, 0]) - min(self.vtxtodraw[:, 0])) / 2,
                    (max(self.vtxtodraw[:, 1]) - min(self.vtxtodraw[:, 1])) / 2,
                )
            )
            print(math.atan(self.fovy_ / 180 * math.pi))
            print(self.radius_)

            eye, ray_eye = self.getRay(0, 0)
            meshpoint = self.getNearestPointFromRay(eye, ray_eye)

            print(eye)

        t[2] = t[2] - self.radius_
        # print t
        self.translate(t)

    def map_to_sphere(self, _v2D):
        _v3D = [0.0, 0.0, 0.0]
        # inside Widget?
        if (_v2D.x() >= 0) and (_v2D.x() <= self.width()) and (_v2D.y() >= 0) and (_v2D.y() <= self.height()):
            # map Qt Coordinates to the centered unit square [-0.5..0.5]x[-0.5..0.5]
            x = float(_v2D.x() - 0.5 * self.width()) / self.width()
            y = float(0.5 * self.height() - _v2D.y()) / self.height()

            _v3D[0] = x
            _v3D[1] = y
            # use Pythagoras to comp z-coord (the sphere has radius sqrt(2.0*0.5*0.5))
            z2 = 2.0 * 0.5 * 0.5 - x * x - y * y
            # numerical robust sqrt
            _v3D[2] = math.sqrt(max(z2, 0.0))

            # normalize direction to unit sphere
            n = linalg.norm(_v3D)
            _v3D = numpy.array(_v3D) / n

            return True, _v3D
        else:
            return False, _v3D

    def wheelEvent(self, _event):
        # Use the mouse wheel to zoom in/out

        newPoint2D = _event.pos()
        eye, ray_eye = self.getRay(newPoint2D.x(), newPoint2D.y())
        meshpoint = self.getNearestPointFromRay(eye, ray_eye)

        dist = np.linalg.norm(eye - meshpoint)

        try:
            d = float(_event.delta()) / 200 * dist / 2
        except:
            d = float(_event.angleDelta().y()) / 200 * dist / 2

        vect = (np.array(meshpoint) - np.array(eye)) / dist * d
        vect = np.array([vect[0], vect[1], vect[2], 0])

        vect2 = np.dot(np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX))), vect)

        # self.translate([0.0, 0.0, d])
        self.translate([-vect2[0], -vect2[1], d])

        self.updateGL()

        self.dialog.textEdit_modelview.setText(str(np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX)))))
        # self.dialog.textEdit_projectionview.setText(  str( np.transpose(  np.array(glGetDoublev(GL_PROJECTION_MATRIX) )  )  )     )

        _event.accept()

    def mousePressEvent(self, _event):
        self.last_point_2D_ = _event.pos()
        self.last_point_ok_, self.last_point_3D_ = self.map_to_sphere(self.last_point_2D_)
        newPoint2D = _event.pos()

        eye, ray_eye = self.getRay(newPoint2D.x(), newPoint2D.y())
        # self.rays.append([eye,ray_eye ] )
        self.center_ = self.getNearestPointFromRay(eye, ray_eye)
        # self.pointtodraw.append(self.center_)
        self.pointtodraw = [self.center_]

        if _event.buttons() == QtCore.Qt.LeftButton:
            # print 'click left'
            pass

        elif _event.buttons() == QtCore.Qt.RightButton:
            # print 'click right'
            pass

    def getRay(self, mousex=None, mousey=None):

        # get Ray
        try:
            if mousex != None and mousey != None:
                if False:
                    x = (2.0 * newPoint2D.x()) / self.width() - 1.0
                    y = 1.0 - (2.0 * newPoint2D.y()) / self.height()
                    z = 1.0
                if True:
                    x = (2.0 * mousex) / self.width() - 1.0
                    y = 1.0 - (2.0 * mousey) / self.height()
                    z = 1.0

                # self.printDialog( str(x) + ' ' +str(y) )

                ray_nds = np.array([x, y, -1, 1])
                ray_eye = np.dot(numpy.linalg.inv(np.transpose(np.array(glGetDoublev(GL_PROJECTION_MATRIX)))), ray_nds)
                ray_eye = np.array([ray_eye[0], ray_eye[1], -1.0, 0.0])
                # in world coords
                ray_eye = np.dot(numpy.linalg.inv(np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX)))), ray_eye)

                if False:
                    try:
                        matrix1 = np.array(glGetDoublev(GL_PROJECTION_MATRIX))[0:3]
                        self.printDialog("matrix1" + str(matrix1))
                        matrix11 = matrix1[:, 0:3]
                        self.printDialog("matrix11" + str(matrix11))
                        matrix2 = numpy.linalg.inv(np.transpose(matrix11))
                        self.printDialog("matrix2" + str(matrix2))

                        ray_nds = np.array([x, y, -1])
                        ray_eye = np.dot(matrix2, ray_nds)

                        self.printDialog("ray_eye" + str(ray_eye))

                        # ray_eye = np.dot(numpy.linalg.inv ( np.transpose( np.array(glGetDoublev( GL_PROJECTION_MATRIX) )  ) ) , ray_nds )
                    except Exception as e:
                        self.printDialog("ray eye 2 " + str(e))
                        ray_eye = ray_nds

                        ray_eye = np.array([ray_eye[0], ray_eye[1], -1.0, 0.0])

            else:
                ray_eye = None

            # get eye
            eyetemp = np.array([0, 0, 0, 1])
            eye = np.dot(numpy.linalg.inv(np.transpose(np.array(glGetDoublev(GL_MODELVIEW_MATRIX)))), eyetemp)[0:3]

            # self.printDialog('ray_eye final \n' + str(eye)+'\n'+str(ray_eye))
            return (eye, ray_eye)
        except Exception as e:
            self.printDialog("ray eye " + str(e))
            return (self.centermesh, np.array([0, 0, -1, 1]))

    def getNearestPointFromRay(self, eye, ray_eye):
        dist = np.linalg.norm(np.cross(self.vtxtodraw - eye, ray_eye[0:3]), axis=1) / np.linalg.norm(ray_eye[0:3])
        temp1 = np.where(dist == min(dist))
        return self.vtxtodraw[temp1][0]

    def printDialog(self, temp):
        self.dialog.textEdit_log.append(str(temp))

    def mouseMoveEvent(self, _event):
        newPoint2D = _event.pos()

        if False:
            # newPoint2D = _event.pos()
            eye, ray_eye = self.getRay(newPoint2D.x(), newPoint2D.y())
            meshpoint = self.getNearestPointFromRay(eye, ray_eye)
            if not self.isInRotation_:
                self.pointtodraw = [meshpoint]

        if (
            (newPoint2D.x() < 0)
            or (newPoint2D.x() > self.width())
            or (newPoint2D.y() < 0)
            or (newPoint2D.y() > self.height())
        ):
            return

        # Left button: rotate around center_
        # Middle button: translate object
        # Left & middle button: zoom in/out

        value_y = 0
        newPoint_hitSphere, newPoint3D = self.map_to_sphere(newPoint2D)

        dx = float(newPoint2D.x() - self.last_point_2D_.x())
        dy = float(newPoint2D.y() - self.last_point_2D_.y())

        w = float(self.width())
        h = float(self.height())

        # enable GL context
        self.makeCurrent()

        # move in z direction
        if ((_event.buttons() & QtCore.Qt.LeftButton) and (_event.buttons() & QtCore.Qt.MidButton)) or (
            _event.buttons() & QtCore.Qt.LeftButton and _event.modifiers() & QtCore.Qt.ControlModifier
        ):
            value_y = self.radius_ * dy * 2.0 / h
            self.translate([0.0, 0.0, value_y])
        # move in x,y direction
        elif _event.buttons() == QtCore.Qt.MidButton:
            # print 'middle'
            if True:
                # z is z eye
                z = -(
                    self.modelview_matrix_[0][2] * self.center_[0]
                    + self.modelview_matrix_[1][2] * self.center_[1]
                    + self.modelview_matrix_[2][2] * self.center_[2]
                    + self.modelview_matrix_[3][2]
                ) / (
                    self.modelview_matrix_[0][3] * self.center_[0]
                    + self.modelview_matrix_[1][3] * self.center_[1]
                    + self.modelview_matrix_[2][3] * self.center_[2]
                    + self.modelview_matrix_[3][3]
                )

                # print 'z \n ' + str(z)
                # print 'eye ' + str(eye)

                fovy = 45.0
                aspect = w / h
                n = 0.01 * self.radius_
                up = math.tan(fovy / 2.0 * math.pi / 180.0) * n
                right = aspect * up

                self.translate([2.0 * dx / w * right / n * z, -2.0 * dy / h * up / n * z, 0.0])

        # rotate
        elif _event.buttons() == QtCore.Qt.LeftButton:
            # print 'left moved'
            if not self.isInRotation_:
                self.isInRotation_ = True
                self.rotationBeginEvent.emit()

            axis = [0.0, 0.0, 0.0]
            angle = 0.0

            if self.last_point_ok_ and newPoint_hitSphere:
                axis = numpy.cross(self.last_point_3D_, newPoint3D)
                cos_angle = numpy.dot(self.last_point_3D_, newPoint3D)
                if abs(cos_angle) < 1.0:
                    angle = math.acos(cos_angle) * 180.0 / math.pi
                    angle *= 2.0
                if True:
                    # axis[1] = 0.0
                    self.rotate(axis, angle)
                if False:
                    print("axis  \n" + str(axis))
                    axis = [axis[0], axis[1], axis[2], 0]
                    axismodel = np.dot(numpy.linalg.inv(np.array(glGetDoublev(GL_MODELVIEW_MATRIX))), axis)
                    # axismodel =  np.dot(numpy.linalg.inv ( np.array(glGetDoublev(GL_PROJECTION_MATRIX) )  ) , axis )
                    # axismodel =  np.dot(numpy.linalg.inv ( np.array(glGetDoublev(GL_MODELVIEW_MATRIX) )  ) , axismodel )
                    # GL_PROJECTION_MATRIX
                    print("axis model \n" + str(axismodel))
                    axismodel[1] = 0.0
                    print("axis model2 \n" + str(axismodel))
                    axismodif = np.dot(np.array(glGetDoublev(GL_MODELVIEW_MATRIX)), axismodel)
                    # axismodif = np.dot( np.array(glGetDoublev(GL_PROJECTION_MATRIX) )   , axismodel )
                    print("axis modif \n" + str(axismodif))

                    axisfinal = [axismodif[0], axismodif[1], axismodif[2]]
                    # print axis
                    self.rotate(axisfinal, angle)
                if False:
                    axis = [axis[0], axis[1], axis[2], 0.0]
                    print(axis)
                    axistemp = np.dot(numpy.linalg.inv(np.array(glGetDoublev(GL_MODELVIEW_MATRIX))), axis)
                    axistemp = np.array([axistemp[0], axistemp[1], 0, 0])
                    axistemp = np.dot((np.array(glGetDoublev(GL_MODELVIEW_MATRIX))), axistemp)
                    print("axistemp \n " + str(axistemp))
                    self.rotate(np.array([axistemp[0], axistemp[1], axistemp[2]]), angle)

            # print 'modelview rotation \n ' + str( self.modelview_matrix_ )

        elif _event.buttons() == QtCore.Qt.RightButton:
            print("right moved")

        # remember this point
        self.last_point_2D_ = newPoint2D
        self.last_point_3D_ = newPoint3D
        self.last_point_ok_ = newPoint_hitSphere

        # trigger redraw
        self.updateGL()

    def mouseReleaseEvent(self, _event):
        if self.isInRotation_:
            self.isInRotation_ = False
            self.rotationEndEvent.emit()
        self.last_point_ok_ = False
        self.pointtodraw = []
