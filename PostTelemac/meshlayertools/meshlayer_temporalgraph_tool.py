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
from qgis.PyQt.QtCore import QObject, QVariant, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication, QFrame

from qgis.core import QgsCoordinateTransform, QgsPointXY, QgsProject
from qgis.utils import iface

import qgis
import numpy as np
import locale

# local import
from .meshlayer_abstract_tool import *
from ..meshlayerlibs import pyqtgraph as pg

pg.setConfigOption("background", "w")

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "TemporalGraphTool.ui"))


class TemporalGraphTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "TEMPORALGRAPHTOOL"

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)

    # *********************************************************************************************
    # ***************Imlemented functions  **********************************************************
    # ********************************************************************************************

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Line_Graph_48x48_time.png")
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.clickTool = qgis.gui.QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        self.graphtempactive = False
        self.graphtempdatac = []
        self.vectorlayerflowids = None
        self.plotitem = []
        self.timeline = None

        # Signals connection
        self.comboBox_2.currentIndexChanged.connect(self.activateMapTool)
        self.pushButton_limni.clicked.connect(self.computeGraphTemp)
        self.pushButton_graphtemp_pressepapier.clicked.connect(self.copygraphclipboard)

        self.timeline = pg.InfiniteLine(0, pen=pg.mkPen("b", width=2))
        self.datavline = pg.InfiniteLine(0, angle=90, pen=pg.mkPen("r", width=1))
        self.datahline = pg.InfiniteLine(0, angle=0, pen=pg.mkPen("r", width=1))

        self.initGraphWidget()

    def initGraphWidget(self):
        self.pyqtgraphwdg = pg.PlotWidget()
        self.vb = self.pyqtgraphwdg.getViewBox()
        layout = QVBoxLayout()
        layout.addWidget(self.pyqtgraphwdg)
        self.frame.setLayout(layout)
        self.pyqtgraphwdg.addItem(self.timeline)
        self.appendCursor()

    def appendCursor(self):
        self.pyqtgraphwdg.addItem(self.datavline)
        self.pyqtgraphwdg.addItem(self.datahline)

    def removeCursor(self):
        self.pyqtgraphwdg.removeItem(self.datavline)
        self.pyqtgraphwdg.removeItem(self.datahline)

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""
        try:
            self.clickTool.canvasClicked.disconnect()
        except Exception as e:
            pass

        self.timeChanged(self.meshlayer.time_displayed)
        self.meshlayer.timechanged.connect(self.timeChanged)
        self.activateMapTool()

    def onDesactivation(self):
        self.meshlayer.rubberband.reset()
        try:
            self.meshlayer.timechanged.connect(self.timeChanged)
        except:
            pass

    # *********************************************************************************************
    # ***************Behaviour functions  **********************************************************
    # ********************************************************************************************

    def activateMapTool(self):
        if self.comboBox_2.currentIndex() == 0:
            self.propertiesdialog.canvas.setMapTool(self.clickTool)
            self.clickTool.canvasClicked.connect(self.computeGraphTemp)
            self.pushButton_limni.setEnabled(False)
        else:
            self.pushButton_limni.setEnabled(True)
            try:
                self.clickTool.canvasClicked.disconnect(self.computeGraphTemp)
            except Exception as e:
                pass

    def updateParams(self):
        self.comboBox_parametreschooser.clear()
        for i in range(len(self.meshlayer.hydrauparser.parametres)):
            temp1 = [
                str(self.meshlayer.hydrauparser.parametres[i][0])
                + " : "
                + str(self.meshlayer.hydrauparser.parametres[i][1])
            ]
            self.comboBox_parametreschooser.addItems(temp1)

    # *********************************************************************************************
    # ***************Main functions  **********************************************************
    # ********************************************************************************************

    def computeGraphTemp(self, qgspointfromcanvas=None):
        """
        Activated with temporal graph tool - points from layer
        """
        try:
            self.pyqtgraphwdg.scene().sigMouseMoved.disconnect(self.mouseMoved)
        except:
            pass

        try:
            self.vectorlayerflowids = None
            self.selectionmethod = self.comboBox_2.currentIndex()
            if self.selectionmethod == 0:  # temporary point
                if not self.graphtempactive:
                    xformutil = self.meshlayer.xform
                    qgspointtransformed = xformutil.transform(
                        qgspointfromcanvas, QgsCoordinateTransform.ReverseTransform
                    )
                    self.launchThread([[qgspointtransformed.x(), qgspointtransformed.y()]])

            elif self.selectionmethod == 1:
                layer = iface.activeLayer()
                if not (layer.type() == 0 and layer.geometryType() == 0):
                    iface.messageBar().pushCritical("Error", "Choisir une couche vecteur de type ligne")
                else:
                    xformutil = QgsCoordinateTransform(self.meshlayer.realCRS, layer.crs(), QgsProject.instance())
                    layer = iface.activeLayer()
                    iter = layer.getFeatures()
                    geomfinal = []
                    self.vectorlayerflowids = []
                    for i, feature in enumerate(iter):
                        try:
                            self.vectorlayerflowids.append(str(feature[0]))
                        except:
                            self.vectorlayerflowids.append(str(feature.id()))
                        geom = feature.geometry().asPoint()
                        temp1 = xformutil.transform(
                            QgsPointXY(geom[0], geom[1]), QgsCoordinateTransform.ReverseTransform
                        )
                        geom = [temp1.x(), temp1.y()]

                        geomfinal.append(geom)
                    if not self.graphtempactive:
                        self.launchThread(geomfinal)
        except Exception as e:
            self.propertiesdialog.errorMessage("computeGraphTemp : " + str(e))

    def launchThread(self, geom):
        if not self.checkBox.isChecked():
            self.meshlayer.rubberband.reset()

        self.initclass = InitGraphTemp()
        self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
        self.initclass.error.connect(self.propertiesdialog.errorMessage)
        self.initclass.emitnum.connect(self.meshlayer.rubberband.drawFromNum)
        self.initclass.emitprogressbar.connect(self.updateProgressBar)
        self.initclass.finished1.connect(self.workerFinished)
        self.initclass.start(self.meshlayer, self, geom)
        self.graphtempactive = True
        self.pushButton_limni.setEnabled(False)

    def workerFinished(self, list1, list2, list3=None):
        if len(list1) > 0 and len(list2) > 0:
            if not self.checkBox.isChecked():
                if len(self.plotitem) > 0:
                    for plot in self.plotitem:
                        print(type(plot[0]))
                        if isinstance(plot[0], QVariant):
                            continue
                        self.pyqtgraphwdg.getPlotItem().removeItem(plot[0])

                self.plotitem = []

            maxtemp = None
            mintemp = None
            self.pyqtgraphwdg.showGrid(True, True, 0.5)

            for i in range(len(list1)):
                self.plotitem.append(
                    [pg.PlotDataItem(list1[i], list2[i], pen=pg.mkPen("b", width=2)), list1[i], list2[i]]
                )
                self.pyqtgraphwdg.addItem(self.plotitem[-1][0])

                if not maxtemp:
                    maxtemp = max(np.array(list2[i]))
                else:
                    if max(np.array(list2[i])) > maxtemp:
                        maxtemp = max(np.array(list2[i]))
                if not mintemp:
                    mintemp = min(np.array(list2[i]))
                else:
                    if min(np.array(list2[i])) < mintemp:
                        mintemp = min(np.array(list2[i]))

            self.label_max.setText("Max : " + str(round(maxtemp, 3)))
            self.label_min.setText("Min : " + str(round(mintemp, 3)))

            self.graphtempactive = False
            if self.comboBox_2.currentIndex() != 0:
                self.pushButton_limni.setEnabled(True)

            self.propertiesdialog.progressBar.reset()

            self.pyqtgraphwdg.scene().sigMouseMoved.connect(self.mouseMoved)

    def mouseMoved(self, pos):  # si connexion directe du signal "mouseMoved" : la fonction reçoit le point courant
        if self.pyqtgraphwdg.sceneBoundingRect().contains(pos):  # si le point est dans la zone courante
            mousePoint = self.vb.mapSceneToView(pos)  # récupère le point souris à partir ViewBox
            datax = self.plotitem[-1][1]
            datay = self.plotitem[-1][2]
            nearestindex = np.argmin(abs(np.array(datax) - mousePoint.x()))
            x = datax[nearestindex]
            y = datay[nearestindex]
            self.datavline.setPos(x)
            self.datahline.setPos(y)
            self.label_X.setText(str(round(x, 3)))
            self.label_Y.setText(str(round(y, 3)))

    def timeChanged(self, nb):
        self.timeline.setPos(self.meshlayer.hydrauparser.getTimes()[nb])

    def copygraphclipboard(self):
        self.clipboard = QApplication.clipboard()
        strtemp = ""
        datatemp = []
        max = 0
        
        locale.setlocale(locale.LC_ALL, "")

        for plotitem in self.plotitem:
            datax = plotitem[1]
            datay = plotitem[2]
            data = np.array([[datax[i], datay[i]] for i in range(len(datax))])

            if len(data) > 0:
                datatemp.append(data)
                maxtemp = len(data)
                if maxtemp > max:
                    max = maxtemp

        if self.vectorlayerflowids:
            for flowid in self.vectorlayerflowids:
                strtemp = strtemp + "id : " + str(flowid) + "\t\t"
            strtemp += "\n"

        for i in range(maxtemp):
            for j in range(len(datatemp)):
                strtemp += str(datatemp[j][i][0]) + "\t" + str(datatemp[j][i][1]) + "\t"
            strtemp += "\n"

        if locale.localeconv()["decimal_point"] == ",":
            strtemp = strtemp.replace(".", ",")

        self.clipboard.setText(strtemp)

    def updateProgressBar(self, float1):
        self.propertiesdialog.progressBar.setValue(int(float1))


# *********************************************************************************************
# *************** Thread **********************************************************
# ********************************************************************************************


class GraphTemp(QObject):
    def __init__(self, selafin, graphtemptool, qgspoints, compare):
        QObject.__init__(self)
        self.selafinlayer = selafin
        self.points = qgspoints
        self.compare = compare
        self.graphtemptool = graphtemptool

    def createGraphTemp(self):

        DEBUG = True

        try:
            list1 = []
            list2 = []

            if DEBUG:
                self.status.emit("points " + str(self.points))

            for i in range(len(self.points)):
                abscisse = []
                ordonnees = []
                param = self.graphtemptool.comboBox_parametreschooser.currentIndex()

                if self.selafinlayer.hydrauparser.parametres[param][2] == 0:
                    enumpoint = self.selafinlayer.hydrauparser.getNearestElemNode(self.points[i][0], self.points[i][1])
                    self.emitnum.emit([enumpoint], 0)

                elif self.selafinlayer.hydrauparser.parametres[param][2] == 1:
                    enumpoint = self.selafinlayer.hydrauparser.getNearestFaceNode(self.points[i][0], self.points[i][1])
                    self.emitnum.emit([enumpoint], 1)

                elif self.selafinlayer.hydrauparser.parametres[param][2] == 2:
                    enumpoint = self.selafinlayer.hydrauparser.getNearestFace(self.points[i][0], self.points[i][1])
                    self.emitnum.emit([enumpoint], 2)

                if enumpoint:
                    abscisse = self.selafinlayer.hydrauparser.getTimes().tolist()
                    if self.compare:
                        (
                            triangles,
                            numpointsfinal,
                            pointsfinal,
                            coef,
                        ) = self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getInterpFactorInTriangleFromPoint(
                            [x], [y]
                        )
                        self.status.emit(
                            str(triangles) + " " + str(numpointsfinal) + " " + str(pointsfinal) + " " + str(coef)
                        )
                        layer2serie = 0
                        for i, numpoint in enumerate(numpointsfinal[0]):
                            layer2serie += float(
                                coef[0][i]
                            ) * self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getTimeSerie(
                                [numpoint + 1],
                                [self.selafinlayer.hydrauparser.parametres[param][3]],
                                self.selafinlayer.hydrauparser.parametres,
                            )
                        layer1serie = self.selafinlayer.hydrauparser.getTimeSerie(
                            [enumpoint], [param], self.selafinlayer.hydrauparser.parametres
                        )
                        tempordonees = layer2serie - layer1serie
                    else:
                        tempordonees = self.selafinlayer.hydrauparser.getTimeSerie(
                            [enumpoint], [param], self.selafinlayer.hydrauparser.parametres
                        )

                    ordonnees = tempordonees[0][0].tolist()
                    list1.append(abscisse)
                    list2.append(ordonnees)
            self.finished.emit(list1, list2)
        except Exception as e:
            self.error.emit("meshlayer_temporalgraph_tool - createGraphTemp " + str(e))
            self.finished.emit([], [])

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    killed = pyqtSignal()
    finished = pyqtSignal(list, list)
    emitpoint = pyqtSignal(list, list)
    emitprogressbar = pyqtSignal(float)
    emitnum = pyqtSignal(list, int)


# *********************************************************************************************
# *************** Classe de lancement du thread **********************************************************
# ********************************************************************************************


class InitGraphTemp(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = None
        self.worker = None
        self.processtype = 0
        self.compare = False

    def start(self, selafin, graphtemptool, qgspoints):
        # Launch worker
        self.thread = QThread()
        self.worker = GraphTemp(selafin, graphtemptool, qgspoints, self.compare)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.createGraphTemp)
        self.worker.status.connect(self.writeOutput)
        self.worker.error.connect(self.writeError)
        self.worker.emitpoint.connect(self.emitPoint)
        self.worker.emitnum.connect(self.emitNum)
        self.worker.emitprogressbar.connect(self.updateProgressBar)
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

    def writeError(self, str1):
        self.error.emit(str(str1))

    def workerFinished(self, list1, list2):
        self.finished1.emit(list1, list2)

    def emitPoint(self, x, y):
        self.emitpoint.emit(x, y)

    def updateProgressBar(self, float1):
        self.emitprogressbar.emit(float1)

    def emitNum(self, list1, int1):
        self.emitnum.emit(list1, int1)

    status = pyqtSignal(str)
    error = pyqtSignal(str)
    emitnum = pyqtSignal(list, int)
    finished1 = pyqtSignal(list, list)
    emitpoint = pyqtSignal(list, list)
    emitprogressbar = pyqtSignal(float)
