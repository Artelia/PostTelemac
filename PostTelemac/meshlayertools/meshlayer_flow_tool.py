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
from qgis.PyQt.QtCore import Qt, QObject, QThread, pyqtSignal
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QVBoxLayout, QApplication

from qgis.core import (
    QgsProject,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsGeometry,
)
from qgis.gui import QgsMapTool
from qgis.utils import iface

try:
    import shapely
except:
    pass
import math
import numpy as np
import matplotlib
import sys

# local import
from .meshlayer_abstract_tool import *
from ..meshlayerlibs import pyqtgraph as pg

try:
    from ..meshlayerparsers.libs_telemac.samplers.meshes import *
except:
    pass

pg.setConfigOption("background", "w")

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "FlowTool.ui"))


class FlowTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "FLOWTOOL"
    SOFTWARE = ["TELEMAC", "ANUGA"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)

    # *********************************************************************************************
    # ***************Imlemented functions  **********************************************************
    # ********************************************************************************************

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Line_Graph_48x48.png")
        self.graphtempactive = False
        self.graphtempdatac = []
        self.vectorlayerflowids = None
        self.maptool = None
        self.pointstoDraw = []
        self.meshlayer.rubberband.createRubberbandFace()
        self.meshlayer.rubberband.createRubberbandFaceNode()
        # Tools tab - temporal graph
        self.pyqtgraphwdg = pg.PlotWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.pyqtgraphwdg)
        self.vb = self.pyqtgraphwdg.getViewBox()
        self.frame.setLayout(layout)
        # Signals connection
        self.comboBox_3.currentIndexChanged.connect(self.activateMapTool)
        self.pushButton_4.clicked.connect(self.copygraphclipboard)
        self.pushButton_flow.clicked.connect(self.computeFlow)
        self.propertiesdialog.meshlayerschangedsignal.connect(self.layerChanged)
        self.plotitem = []
        self.timeline = pg.InfiniteLine(0, pen=pg.mkPen("b", width=2))
        self.pyqtgraphwdg.addItem(self.timeline)
        self.datavline = pg.InfiniteLine(0, angle=90, pen=pg.mkPen("r", width=1))
        self.datahline = pg.InfiniteLine(0, angle=0, pen=pg.mkPen("r", width=1))
        self.appendCursor()

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""
        self.activateMapTool()
        self.timeChanged(self.meshlayer.time_displayed)
        self.meshlayer.timechanged.connect(self.timeChanged)

    def onDesactivation(self):
        self.meshlayer.rubberband.reset()
        try:
            self.meshlayer.timechanged.connect(self.timeChanged)
        except:
            pass

    # *********************************************************************************************
    # ***************Behaviour functions  **********************************************************
    # ********************************************************************************************

    def appendCursor(self):
        self.pyqtgraphwdg.addItem(self.datavline)
        self.pyqtgraphwdg.addItem(self.datahline)

    def removeCursor(self):
        self.pyqtgraphwdg.removeItem(self.datavline)
        self.pyqtgraphwdg.removeItem(self.datahline)

    def layerChanged(self):
        # enable flow if depth, velocities are present in parser params
        if (
            self.meshlayer.hydrauparser.parametreh != None
            and self.meshlayer.hydrauparser.parametrevx != None
            and self.meshlayer.hydrauparser.parametrevy != None
        ):
            self.setEnabled(True)
        else:
            self.setEnabled(False)

    def activateMapTool(self):
        if self.comboBox_3.currentIndex() == 0:
            self.pushButton_flow.setEnabled(False)
            self.computeFlow()
        else:
            self.pushButton_flow.setEnabled(True)
            try:
                self.deactivateTool()
            except Exception as e:
                pass

    # *********************************************************************************************
    # ***************Main functions  **********************************************************
    # ********************************************************************************************

    def computeFlow(self):
        """
        Activated with flow graph tool
        """

        self.dblclktemp = None
        self.textquit0 = "Click for polyline and double click to end (right click to cancel then quit)"
        self.textquit1 = "Select the polyline in a vector layer (Right click to quit)"
        self.vectorlayerflowids = None
        self.graphtodo = 1
        self.selectionmethod = self.comboBox_3.currentIndex()

        if self.selectionmethod in [0]:
            if not self.maptool:
                self.maptool = FlowMapTool(self.meshlayer.canvas, self.pushButton_flow)
            self.connectTool()
            self.meshlayer.canvas.setMapTool(self.maptool)
            self.meshlayer.rubberband.reset()
            self.pointstoDraw = []
            self.pointstoCal = []
            self.lastClicked = [[-9999999999.9, 9999999999.9]]
            self.lastFreeHandPoints = []
        elif self.selectionmethod in [1, 2]:
            layer = iface.activeLayer()
            if not (layer.type() == 0 and layer.geometryType() == 1):
                QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a (poly)line vector layer"))
            elif self.selectionmethod == 1 and len(layer.selectedFeatures()) == 0:
                QMessageBox.warning(
                    iface.mainWindow(), "PostTelemac", self.tr("Select a line in a (poly)line vector layer")
                )
            else:
                self.initclass1 = []
                self.checkBox.setChecked(True)
                iter = layer.selectedFeatures()
                if self.selectionmethod == 2 or len(iter) == 0:
                    iter = layer.getFeatures()
                geomfinal = []
                self.vectorlayerflowids = []
                xformutil = QgsCoordinateTransform(self.meshlayer.realCRS, layer.crs(), QgsProject.instance())
                for i, feature in enumerate(iter):
                    try:
                        self.vectorlayerflowids.append(str(feature[0]))
                    except:
                        self.vectorlayerflowids.append(str(feature.id()))
                    geoms = feature.geometry().asPolyline()
                    geoms = [[geom[0], geom[1]] for geom in geoms]
                    geoms = geoms + [geoms[-1]]
                    geomstemp = []
                    for geom in geoms:
                        qgspoint = xformutil.transform(
                            QgsPointXY(geom[0], geom[1]),
                            QgsCoordinateTransform.ReverseTransform,
                        )
                        geomstemp.append([qgspoint.x(), qgspoint.y()])
                    geomfinal.append(geomstemp)

                self.launchThread(geomfinal)

    def launchThread(self, geom):
        self.initclass = InitComputeFlow()
        self.initclass.status.connect(self.propertiesdialog.textBrowser_2.append)
        self.initclass.error.connect(self.propertiesdialog.errorMessage)
        self.initclass.emitpoint.connect(self.addPointRubberband)
        self.initclass.emitprogressbar.connect(self.updateProgressBar)
        self.initclass.finished1.connect(self.workerFinished)
        self.meshlayer.rubberband.reset()
        self.propertiesdialog.normalMessage("Start computing flow")
        self.initclass.start(self.meshlayer, self.comboBox_flowmethod.currentIndex(), geom)
        self.pushButton_flow.setEnabled(False)

    def workerFinished(self, list1, list2, list3=None):
        print("workerFinished", list1, list2)
        if not self.checkBox.isChecked():
            if len(self.plotitem) > 0:
                for plot in self.plotitem:
                    self.pyqtgraphwdg.removeItem(plot[0])
            self.plotitem = []

        maxtemp = None
        mintemp = None
        self.pyqtgraphwdg.showGrid(True, True, 0.5)

        for i in range(len(list1)):
            self.plotitem.append(
                [self.pyqtgraphwdg.plot(list1[i], list2[i], pen=pg.mkPen("b", width=2)), list1[i], list2[i]]
            )
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

        if maxtemp is not None and mintemp is not None:
            self.label_flow_resultmax.setText("Max : " + str(round(maxtemp, 3)))
            self.label__flow_resultmin.setText("Min : " + str(round(mintemp, 3)))

        self.propertiesdialog.normalMessage("Computing volume finished")
        if self.comboBox_3.currentIndex() != 0:
            self.pushButton_flow.setEnabled(True)
        self.propertiesdialog.progressBar.reset()
        self.pyqtgraphwdg.scene().sigMouseMoved.connect(self.mouseMoved)

    def mouseMoved(self, pos):
        if self.pyqtgraphwdg.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
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
                strtemp = strtemp + "id : " + str(flowid) + "\t" + "\t"

        for i in range(maxtemp):
            for j in range(len(datatemp)):
                strtemp += str(datatemp[j][i][0]) + "\t" + str(datatemp[j][i][1]) + "\t"
            strtemp += "\n"

        self.clipboard.setText(strtemp)

    def addPointRubberband(self, x, y):
        if isinstance(x, list):
            points = []
            if len(x) > 1:
                for i in range(len(x)):
                    points.append(self.meshlayer.xform.transform(QgsPointXY(x[i], y[i])))
                self.meshlayer.rubberband.rubberbandface.addGeometry(QgsGeometry.fromPolygonXY([points]), None)
            else:
                qgspoint = self.meshlayer.xform.transform(QgsPointXY(x[0], y[0]))

                self.meshlayer.rubberband.rubberbandface.addPoint(qgspoint)
                self.meshlayer.rubberband.rubberbandfacenode.addPoint(qgspoint)
        else:
            qgspoint = self.meshlayer.xform.transform(QgsPointXY(x, y))
            self.meshlayer.rubberband.rubberbandface.addPoint(qgspoint)

    def updateProgressBar(self, float1):
        self.propertiesdialog.progressBar.setValue(int(float1))

    # *********************************************************************************************
    # *************** Map Tool  **********************************************************
    # ********************************************************************************************

    def connectTool(self):
        self.maptool.moved.connect(self.moved)
        self.maptool.rightClicked.connect(self.rightClicked)
        self.maptool.leftClicked.connect(self.leftClicked)
        self.maptool.doubleClicked.connect(self.doubleClicked)
        self.maptool.desactivate.connect(self.deactivateTool)

    def deactivateTool(self):  # enable clean exit of the plugin
        self.maptool.moved.disconnect(self.moved)
        self.maptool.rightClicked.disconnect(self.rightClicked)
        self.maptool.leftClicked.disconnect(self.leftClicked)
        self.maptool.doubleClicked.disconnect(self.doubleClicked)
        self.maptool.desactivate.disconnect(self.deactivateTool)

    def moved(self, position):  # draw the polyline on the temp layer (rubberband)
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"], position["y"])
                self.meshlayer.rubberband.reset()
                for i in range(0, len(self.pointstoDraw)):
                    self.meshlayer.rubberband.rubberbandface.addPoint(
                        QgsPointXY(self.pointstoDraw[i][0], self.pointstoDraw[i][1])
                    )
                self.meshlayer.rubberband.rubberbandface.addPoint(QgsPointXY(mapPos.x(), mapPos.y()))

    def rightClicked(self, position):  # used to quit the current action
        if self.selectionmethod == 0:
            mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"], position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            if len(self.pointstoDraw) > 0:
                self.pointstoDraw = []
                self.pointstoCal = []
                self.meshlayer.rubberband.reset()
            else:
                self.cleaning()

    def leftClicked(self, position):  # Add point to analyse
        mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"], position["y"])
        newPoints = [[mapPos.x(), mapPos.y()]]

        if self.selectionmethod == 0:
            if newPoints == self.dblclktemp:
                self.dblclktemp = None
                if self.comboBox_3.currentIndex() != 0:
                    self.cleaning()
            else:
                if len(self.pointstoDraw) == 0:
                    self.meshlayer.rubberband.reset()
                self.pointstoDraw += newPoints

    def doubleClicked(self, position):
        if self.selectionmethod == 0:
            # Validation of line
            mapPos = self.meshlayer.canvas.getCoordinateTransform().toMapCoordinates(position["x"], position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            self.pointstoDraw += newPoints
            # convert points to pluginlayer crs
            xform = self.meshlayer.xform
            pointstoDrawfinal = []
            for point in self.pointstoDraw:
                qgspoint = xform.transform(QgsPointXY(point[0], point[1]), QgsCoordinateTransform.ReverseTransform)
                pointstoDrawfinal.append([qgspoint.x(), qgspoint.y()])
            # launch analyses
            self.launchThread([pointstoDrawfinal])
            # Reset
            self.lastFreeHandPoints = self.pointstoDraw
            self.pointstoDraw = []
            # temp point to distinct leftclick and dbleclick
            self.dblclktemp = newPoints

    def cleaning(self):  # used on right click
        self.meshlayer.canvas.setMapTool(self.propertiesdialog.maptooloriginal)
        iface.mainWindow().statusBar().showMessage("")


class FlowMapTool(QgsMapTool):
    def __init__(self, canvas, button):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.cursor = QCursor(Qt.CrossCursor)
        self.button = button

    def canvasMoveEvent(self, event):
        self.moved.emit({"x": event.pos().x(), "y": event.pos().y()})

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit({"x": event.pos().x(), "y": event.pos().y()})
        else:
            self.leftClicked.emit({"x": event.pos().x(), "y": event.pos().y()})

    def canvasDoubleClickEvent(self, event):
        self.doubleClicked.emit({"x": event.pos().x(), "y": event.pos().y()})

    def activate(self):
        QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)

    def deactivate(self):
        self.desactivate.emit()
        QgsMapTool.deactivate(self)

    def setCursor(self, cursor):
        self.cursor = QCursor(cursor)

    moved = pyqtSignal(dict)
    rightClicked = pyqtSignal(dict)
    leftClicked = pyqtSignal(dict)
    doubleClicked = pyqtSignal(dict)
    desactivate = pyqtSignal()


# *********************************************************************************************
# *************** Thread **********************************************************
# ********************************************************************************************


class computeFlow(QObject):
    def __init__(self, selafin, method, line):
        QObject.__init__(self)
        self.selafinlayer = selafin
        self.polyline = line
        self.fig = matplotlib.pyplot.figure(self.selafinlayer.instancecount + 4)
        self.method = method
        self.DEBUG = False

    def computeFlowMain(self):
        """
        Main method

        """

        list1 = []
        list2 = []
        list3 = []

        METHOD = self.method

        if self.DEBUG:
            self.status.emit("polyline raw " + str(self.polyline))

        try:
            for lineelement in self.polyline:
                temp3 = self.getLines(lineelement, METHOD)
                result = []
                parameterh = self.selafinlayer.hydrauparser.parametreh
                parameteruv = self.selafinlayer.hydrauparser.parametrevx
                parametervv = self.selafinlayer.hydrauparser.parametrevy

                if METHOD == 0:  # Method0 : shortest path and vector computation
                    if self.selafinlayer.hydrauparser.networkxgraph == None:
                        self.selafinlayer.hydrauparser.createNetworkxGraph()

                    shortests = []

                    for line in temp3:
                        linetemp = line
                        resulttemp = []
                        # find shortests path
                        for points in range(len(linetemp) - 1):
                            try:
                                triangle = self.selafinlayer.hydrauparser.triangulation.get_trifinder().__call__(
                                    linetemp[points][0], linetemp[points][1]
                                )
                                if triangle != -1:
                                    enumpointdebut = self.getNearestPointEdge(
                                        linetemp[points][0], linetemp[points][1], triangle
                                    )
                                triangle = self.selafinlayer.hydrauparser.triangulation.get_trifinder().__call__(
                                    linetemp[points + 1][0], linetemp[points + 1][1]
                                )
                                if triangle != -1:
                                    enumpointfin = self.getNearestPointEdge(
                                        linetemp[points + 1][0], linetemp[points + 1][1], triangle
                                    )
                                shortests.append(
                                    self.selafinlayer.hydrauparser.getShortestPath(enumpointdebut, enumpointfin)
                                )

                            except Exception as e:
                                self.status.emit("method 0 : " + str(e))

                    totalpointsonshortest = len(sum(shortests, []))
                    compteur1 = 0

                    for shortest in shortests:
                        for i, elem in enumerate(shortest):
                            self.emitprogressbar.emit(float(compteur1 + i) / float(totalpointsonshortest - 1) * 100.0)
                            try:
                                if i == 0:  # init
                                    try:
                                        h2 = np.array(
                                            self.selafinlayer.hydrauparser.getTimeSerie(
                                                [elem], [parameterh], self.selafinlayer.hydrauparser.parametres
                                            )[0][0]
                                        )
                                    except Exception as e:
                                        self.status.emit("method 011 : " + str(e))
                                    uv2 = np.array(
                                        self.selafinlayer.hydrauparser.getTimeSerie(
                                            [elem], [parameteruv], self.selafinlayer.hydrauparser.parametres
                                        )[0][0]
                                    )
                                    uv2 = np.array([[value, 0.0] for value in uv2])
                                    vv2 = np.array(
                                        self.selafinlayer.hydrauparser.getTimeSerie(
                                            [elem], [parametervv], self.selafinlayer.hydrauparser.parametres
                                        )[0][0]
                                    )
                                    vv2 = np.array([[0.0, value] for value in vv2])
                                    v2vect = uv2 + vv2
                                    xy2 = list(self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0])
                                else:
                                    h1 = h2
                                    v1vect = v2vect
                                    xy1 = xy2
                                    h2 = np.array(
                                        self.selafinlayer.hydrauparser.getTimeSerie(
                                            [elem], [parameterh], self.selafinlayer.hydrauparser.parametres
                                        )[0][0]
                                    )
                                    uv2 = np.array(
                                        self.selafinlayer.hydrauparser.getTimeSerie(
                                            [elem], [parameteruv], self.selafinlayer.hydrauparser.parametres
                                        )[0][0]
                                    )
                                    uv2 = np.array([[value, 0.0] for value in uv2])
                                    vv2 = np.array(
                                        self.selafinlayer.hydrauparser.getTimeSerie(
                                            [elem], [parametervv], self.selafinlayer.hydrauparser.parametres
                                        )[0][0]
                                    )
                                    vv2 = np.array([[0.0, value] for value in vv2])
                                    v2vect = uv2 + vv2
                                    xy2 = list(self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0])
                                    if "flow" in locals():
                                        flow = flow + self.computeFlowBetweenPoints(xy1, h1, v1vect, xy2, h2, v2vect)
                                    else:
                                        flow = self.computeFlowBetweenPoints(xy1, h1, v1vect, xy2, h2, v2vect)

                            except Exception as e:
                                self.status.emit("method 01 : " + str(e))

                            x, y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([elem])[0]
                            self.emitpoint.emit(x, y)

                        compteur1 += len(shortest)
                        result.append([None, flow])

                elif METHOD == 1:
                    for line in temp3:
                        linetemp = np.array([[point[0], point[1]] for point in line.coords])
                        resulttemp = []
                        flow = None
                        temp_edges, temp_points, temp_bary = self.getCalcPointsSlice(line)
                        for i in range(len(temp_points)):
                            if i == 0:
                                h2 = self.valuebetweenEdges(temp_points[i], temp_edges[i], parameterh)
                                uv2 = self.valuebetweenEdges(temp_points[i], temp_edges[i], parameteruv)
                                uv2 = np.array([[value, 0.0] for value in uv2])
                                vv2 = self.valuebetweenEdges(temp_points[i], temp_edges[i], parametervv)
                                vv2 = np.array([[0.0, value] for value in vv2])
                                v2vect = uv2 + vv2
                                xy2 = temp_points[i]
                                self.emitpoint.emit(temp_points[i][0], temp_points[i][1])
                                x, y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][0]])[0]
                                self.emitpoint.emit(x, y)
                                x, y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][1]])[0]
                                self.emitpoint.emit(x, y)

                            else:
                                h1 = h2
                                v1vect = v2vect
                                xy1 = xy2
                                h2 = self.valuebetweenEdges(temp_points[i], temp_edges[i], parameterh)
                                uv2 = self.valuebetweenEdges(temp_points[i], temp_edges[i], parameteruv)
                                uv2 = np.array([[value, 0.0] for value in uv2])
                                vv2 = self.valuebetweenEdges(temp_points[i], temp_edges[i], parametervv)
                                vv2 = np.array([[0.0, value] for value in vv2])
                                v2vect = uv2 + vv2
                                xy2 = temp_points[i]
                                lenght = np.linalg.norm(np.array([xy2[0] - xy1[0], xy2[1] - xy1[1]]))
                                if lenght > 0:
                                    if "flow" in locals():
                                        flow = flow + self.computeFlowBetweenPoints(xy1, h1, v1vect, xy2, h2, v2vect)
                                    else:
                                        flow = self.computeFlowBetweenPoints(xy1, h1, v1vect, xy2, h2, v2vect)
                                    self.emitpoint.emit(temp_points[i][0], temp_points[i][1])
                                    x, y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][0]])[
                                        0
                                    ]
                                    self.emitpoint.emit(x, y)
                                    x, y = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([temp_edges[i][1]])[
                                        0
                                    ]
                                    self.emitpoint.emit(x, y)

                        result.append([line, flow])

                flow = None
                for i in range(len(result)):
                    if i == 0:
                        flow = result[i][1]
                    else:
                        flow = flow + result[i][1]

                list1.append(self.selafinlayer.hydrauparser.getTimes().tolist())
                list2.append(flow.tolist())
                list3.append(result)

        except Exception as e:
            self.error.emit("flow calculation error : " + str(e))

        self.finished.emit(list1, list2, list3)

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    killed = pyqtSignal()
    finished = pyqtSignal(list, list, list)
    emitpoint = pyqtSignal(float, float)
    emitprogressbar = pyqtSignal(float)

    def getLines(self, polyline1, METHOD):
        """
        Line input traitment in order to be only in the area of the modelisation
        Method0 : line slighlty inside the area of modelisation
        Method1 : line slighlty outside
        """

        templine2 = QgsGeometry.fromPolylineXY([QgsPointXY(i[0], i[1]) for i in polyline1[:-1]])

        if self.DEBUG:
            self.status.emit("templine2" + str(templine2.asPolyline()))

        temp3_in = []
        temp3_out = []

        meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        triplotcontourf = self.fig.gca().tricontourf(meshx, meshy, ikle, self.selafinlayer.value, [-1.0e20, 1.0e20])

        if METHOD == 0:
            buffervalue = 0.05
        elif METHOD == 1:
            buffervalue = -0.05

        for collection in triplotcontourf.collections:
            for path in collection.get_paths():
                for polygon in path.to_polygons():
                    polygons2 = QgsGeometry.fromPolygonXY([[QgsPointXY(i[0], i[1]) for i in polygon]])

                    if templine2.intersects(polygons2):
                        if np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 > 0:  # outer polygon
                            inter = templine2.intersection(polygons2.buffer(-buffervalue, 12))
                            if inter.type() == 1:
                                if not inter.isMultipart():
                                    temp3_out.append(inter)
                                else:
                                    for line3 in inter.asMultiPolyline():
                                        temp3_out.append(
                                            QgsGeometry.fromPolylineXY([QgsPointXY(i[0], i[1]) for i in line3])
                                        )

                        else:  # inner polygon
                            inter = templine2.intersection(polygons2.buffer(buffervalue, 12))
                            if self.DEBUG:
                                self.status.emit("inter" + str(inter.asMultiPolyline()))
                                self.status.emit("inter" + str(inter.asPolyline()))
                                self.status.emit("inter" + str(inter.type()))
                            if inter.type() == 1:
                                if len(inter.asMultiPolyline()) == 0:
                                    temp3_out.append(inter)
                                else:
                                    for line3 in inter.asMultiPolyline():
                                        temp3_out.append(
                                            QgsGeometry.fromPolyline([QgsPoint(i[0], i[1]) for i in line3])
                                        )

        temp3out_line = temp3_out
        temp3in_line = temp3_in

        if self.DEBUG:
            self.status.emit("temp3out_line" + str([line.asPolyline() for line in temp3out_line]))
            self.status.emit("temp3in_line" + str([line.asPolyline() for line in temp3in_line]))

        linefinal2 = []

        for lineout in temp3out_line:
            templine = lineout
            for linein in temp3in_line:
                linein = linein
                if lineout.length() > linein.length() and lineout.intersects(linein.buffer(0.01, 12)):
                    templine = templine.difference(linein.buffer(0.02, 12))
            if templine.type() == 1:
                if not templine.isMultipart():
                    linefinal2.append(templine)
                else:
                    for line3 in templine.asMultiPolyline():
                        linefinal2.append(QgsGeometry.fromPolylineXY([QgsPointXY(i[0], i[1]) for i in line3]))

        if self.DEBUG:
            self.status.emit("linefinal2" + str([line.asPolyline() for line in linefinal2]))

        # to keep line direction qgis
        geomtemp = [[QgsPointXY(i[0], i[1]) for i in line.asPolyline()] for line in linefinal2]
        multitemp = QgsGeometry.fromMultiPolylineXY(geomtemp)
        multidef2 = templine2.intersection(multitemp.buffer(0.01, 12))

        if self.DEBUG:
            self.status.emit("multidef2" + str(multidef2))

        # qgis
        if not multidef2.isMultipart():
            result = np.array([multidef2.asPolyline()])
        else:
            result = np.array(multidef2.asMultiPolyline())

        return result

    def getLines2(self, polyline1, METHOD):
        """
        Line input traitment in order to be only in the area of the modelisation
        Method0 : line slighlty inside the area of modelisation
        Method1 : line slighlty outside
        """

        if self.DEBUG:
            self.status.emit("getLines - polylin : " + str(polyline1))

        templine1 = shapely.geometry.linestring.LineString([(i[0], i[1]) for i in polyline1[:-1]])
        templine2 = QgsGeometry.fromPolylineXY([QgsPointXY(i[0], i[1]) for i in polyline1[:-1]])

        temp2_in = []
        temp2_out = []
        temp3_in = []
        temp3_out = []

        meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        triplotcontourf = self.fig.gca().tricontourf(meshx, meshy, ikle, self.selafinlayer.value, [-1.0e20, 1.0e20])

        if METHOD == 0:
            buffervalue = 0.05
        elif METHOD == 1:
            buffervalue = -0.05

        for collection in triplotcontourf.collections:
            for path in collection.get_paths():
                for polygon in path.to_polygons():
                    tuplepoly = [(i[0], i[1]) for i in polygon]
                    polygons = shapely.geometry.polygon.Polygon(tuplepoly)
                    polygons2 = QgsGeometry.fromPolygonXY([[QgsPointXY(i[0], i[1]) for i in polygon]])
                    # shapely
                    if templine1.intersects(polygons):
                        if np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 > 0:  # outer polygon
                            inter = templine1.intersection(polygons.buffer(-buffervalue))
                            if isinstance(inter, shapely.geometry.linestring.LineString):
                                temp2_out.append(inter)
                            else:
                                for line3 in inter:
                                    temp2_out.append(line3)
                        else:  # inner polygon
                            inter = templine1.intersection(polygons.buffer(buffervalue))
                            if isinstance(inter, shapely.geometry.linestring.LineString):
                                temp2_in.append(inter)
                            else:
                                for line3 in inter:
                                    temp2_in.append(line3)

                    # qgis
                    if templine2.intersects(polygons2):
                        if np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 > 0:  # outer polygon
                            inter = templine2.intersection(polygons2.buffer(-buffervalue, 12))
                            if inter.type() == 1:
                                if len(inter.asMultiPolyline()) == 1:
                                    temp3_out.append(inter)
                                else:
                                    for line3 in inter.asMultiPolyline():
                                        temp3_out.append(line3)
                        else:  # inner polygon
                            inter = templine2.intersection(polygons2.buffer(buffervalue, 12))
                            if inter.type() == 1:
                                if len(inter.asMultiPolyline()) == 1:
                                    temp3_in.append(inter)
                                else:
                                    for line3 in inter.asMultiPolyline():
                                        temp3_in.append(line3)

        temp2out_line = shapely.geometry.multilinestring.MultiLineString(temp2_out)
        temp2in_line = shapely.geometry.multilinestring.MultiLineString(temp2_in)

        temp3out_line = [
            QgsGeometry.fromMultiPolylineXY([[QgsPointXY(i[0], i[1]) for i in line]]) for line in temp3_out
        ]
        temp3in_line = [QgsGeometry.fromMultiPolylineXY([[QgsPointXY(i[0], i[1]) for i in line]]) for line in temp3_in]
        linefinal = []
        linefinal2 = []

        # shapely
        for lineout in temp2out_line:
            templine = lineout
            for linein in temp2in_line:
                if lineout.length > linein.length and lineout.intersects(linein.buffer(0.01)):
                    templine = templine.difference(linein.buffer(0.02))
            if isinstance(templine, shapely.geometry.linestring.LineString):
                linefinal.append(templine)
            else:
                for line3 in templine:
                    linefinal.append(line3)

        # qgis
        for lineout in temp3out_line:
            templine = lineout
            for linein in temp3in_line:
                linein = linein
                if lineout.length() > linein.length() and lineout.intersects(linein.buffer(0.01, 12)):
                    templine = templine.difference(linein.buffer(0.02, 12))
            if templine.type() == 1:
                if len(templine.asMultiPolyline()) == 1:
                    linefinal2.append(templine)
                else:
                    for line3 in templine.asMultiPolyline():
                        linefinal2.append(line3)

        if self.DEBUG:
            self.status.emit("linefinal : " + str(linefinal))
            self.status.emit("linefinal2 : " + str([line.asMultiPolyline() for line in linefinal2]))

        # to keep line direction shapely
        multitemp = shapely.geometry.multilinestring.MultiLineString(linefinal)
        multidef = templine1.intersection(multitemp.buffer(0.01))

        # to keep line direction qgis
        geomtemp = []
        for multiline in linefinal2:
            for line in multiline.asMultiPolyline():
                geomtemp.append([QgsPointXY(i[0], i[1]) for i in line])

        multitemp = QgsGeometry.fromMultiPolylineXY(geomtemp)
        multidef2 = templine2.intersection(multitemp.buffer(0.01, 12))

        if self.DEBUG:
            self.status.emit(str(multidef))
            self.status.emit(str(multidef2.asMultiPolyline()))

        # shapely
        if isinstance(multidef, shapely.geometry.linestring.LineString):
            multidef = [multidef]

        result = []
        for line in multidef:
            result.append(np.array([[point[0], point[1]] for point in line.coords]))
        result = np.array(result)

        # qgis
        result2 = np.array(multidef2.asMultiPolyline())

        if self.DEBUG:
            self.status.emit("result " + str(result))
            self.status.emit("result2 " + str(result2))

        return result

    def getCalcPointsSlice(self, line):
        linetemp = np.array([[point[0], point[1]] for point in line.coords])
        temp_points_final = []
        temp_edges_final = []
        temp_bary_final = []
        for i in range(len(linetemp) - 1):
            resulttemp = []
            lintemp1 = np.array([[linetemp[i][0], linetemp[i][1]], [linetemp[i + 1][0], linetemp[i + 1][1]]])
            lintemp1shapely = shapely.geometry.linestring.LineString(
                [(linetemp[i][0], linetemp[i][1]), (linetemp[i + 1][0], linetemp[i + 1][1])]
            )
            meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
            ikle = self.selafinlayer.hydrauparser.getElemFaces()
            quoi = sliceMesh(lintemp1, np.asarray(ikle), np.asarray(meshx), np.asarray(meshy))

            temp_points = []
            temp_edges = []
            temp_bary = []

            for i, edgestemp in enumerate(quoi[0][1]):  # slicemesh - quoi[0][1] is list of egdes intersected by line
                x1, y1 = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edgestemp[0]])[0]
                x2, y2 = self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edgestemp[1]])[0]

                line4 = shapely.geometry.linestring.LineString([(x1, y1), (x2, y2)])
                if line4.crosses(lintemp1shapely):
                    temp_edges.append(edgestemp)
                    temp_point.append([quoi[0][0][i][0], quoi[0][0][i][1]])
                    temp_bary.append(quoi[0][2][i])

            # check direction
            dir1 = lintemp1shapely.coords[1][0] - lintemp1shapely.coords[0][0]
            dir2 = temp_points[1][0] - temp_points[0][0]

            if dir1 > 0 and dir2 > 0:
                pass
            elif dir1 < 0 and dir2 < 0:
                pass
            else:
                temp_edges = temp_edges[::-1]
                temp_points = temp_points[::-1]
                temp_bary = temp_bary[::-1]

            temp_points_final += temp_points
            temp_edges_final += temp_edges
            temp_bary_final += temp_bary

        return temp_edges_final, temp_points_final, temp_bary_final

    def computeFlowBetweenPoints(self, xy1, h1, v1vect, xy2, h2, v2vect):
        vectorface = np.array([xy2[0] - xy1[0], xy2[1] - xy1[1]])
        lenght = np.linalg.norm(vectorface)
        if lenght == 0.0:
            return None
        vectorfacenorm = vectorface / np.linalg.norm(vectorface)
        perp = np.array([0, 0, -1.0])
        vectorfacenormcrosstemp = np.cross(vectorfacenorm, perp)
        vectorfacenormcross = np.array([vectorfacenormcrosstemp[0], vectorfacenormcrosstemp[1]])

        v1 = np.array([np.dot(vectorfacenormcross, temp) for temp in v1vect])
        v2 = np.array([np.dot(vectorfacenormcross, temp) for temp in v2vect])

        deltah = h2 - h1
        ah = deltah / lenght
        bh = h1
        deltav = v2 - v1
        av = deltav / lenght
        bv = v1

        flow = (
            1.0 / 3.0 * (ah * av) * math.pow(lenght, 3)
            + 1.0 / 2.0 * (ah * bv + av * bh) * math.pow(lenght, 2)
            + (bh * bv) * lenght
        )
        # if np.isnan(flow).any():
        # self.status.emit(
        # " vecor "
        # + str(vectorface)
        # + "lenght "
        # + str(np.linalg.norm(vectorface))
        # + " norm "
        # + str(vectorfacenormcross)
        # )

        return flow

    def valuebetweenEdges(self, xy, edges, param):
        xytemp = np.array(xy)
        h11 = np.array(
            self.selafinlayer.hydrauparser.getTimeSerie(
                [edges[0] + 1], [param], self.selafinlayer.hydrauparser.parametres
            )[0][0]
        )  # getseries begins at  1
        h12 = np.array(
            self.selafinlayer.hydrauparser.getTimeSerie(
                [edges[1] + 1], [param], self.selafinlayer.hydrauparser.parametres
            )[0][0]
        )

        e1 = np.array(self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edges[0]]))
        e2 = np.array(self.selafinlayer.hydrauparser.getFaceNodeXYFromNumPoint([edges[1]]))
        rap = np.linalg.norm(xytemp - e1) / np.linalg.norm(e2 - e1)

        return (1.0 - rap) * h11 + (rap) * h12

    def getNearest(self, x, y, triangle):
        numfinal = None
        distfinal = None
        meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        for num in np.array(ikle)[triangle]:
            dist = math.pow(math.pow(float(meshx[num]) - float(x), 2) + math.pow(float(meshy[num]) - float(y), 2), 0.5)
            if distfinal:
                if dist < distfinal:
                    distfinal = dist
                    numfinal = num
            else:
                distfinal = dist
                numfinal = num
        return numfinal

    def getNearestPointEdge(self, x, y, triangle):
        numfinal1 = None
        trianglepoints = []
        point = np.array([x, y])
        distedge = None
        meshx, meshy = self.selafinlayer.hydrauparser.getFacesNodes()
        ikle = self.selafinlayer.hydrauparser.getElemFaces()
        for num in np.array(ikle)[triangle]:
            trianglepoints.append(np.array([np.array([meshx[num], meshy[num]], dtype=object), num], dtype=object))
        num1 = np.array(ikle)[triangle][0]
        trianglepoints.append(np.array([np.array([meshx[num1], meshy[num1]], dtype=object), num1], dtype=object))

        for i in range(len(trianglepoints) - 1):
            dist = np.linalg.norm(
                np.cross(trianglepoints[i + 1][0] - trianglepoints[i][0], trianglepoints[i][0] - point)
            ) / np.linalg.norm(trianglepoints[i + 1][0] - trianglepoints[i][0])
            if distedge:
                if dist < distedge:
                    distedge = dist
                    numfinal1 = [trianglepoints[i][1], trianglepoints[i + 1][1]]
            else:
                distedge = dist
                numfinal1 = [trianglepoints[i][1], trianglepoints[i + 1][1]]
        numfinal2 = None
        distfinal = None

        for num in numfinal1:
            distpoint = math.pow(
                math.pow(float(meshx[num]) - float(x), 2) + math.pow(float(meshy[num]) - float(y), 2), 0.5
            )
            if distfinal:
                if distpoint < distfinal:
                    distfinal = distpoint
                    numfinal2 = num
            else:
                distfinal = distpoint
                numfinal2 = num
        return numfinal2


# *********************************************************************************************
# *************** Classe de lancement du thread **********************************************************
# ********************************************************************************************


class InitComputeFlow(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = QThread()
        self.worker = None
        self.processtype = 0

    def start(self, selafin, method, line):
        # Launch worker
        self.worker = computeFlow(selafin, method, line)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.computeFlowMain)
        self.worker.status.connect(self.writeOutput)
        self.worker.emitpoint.connect(self.emitPoint)
        self.worker.error.connect(self.raiseError)
        self.worker.emitprogressbar.connect(self.updateProgressBar)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def raiseError(self, str):
        if self.processtype == 0:
            self.error.emit(str)
        elif self.processtype in [1, 2, 3]:
            raise GeoAlgorithmExecutionException(str)
        elif self.processtype == 4:
            print(str)
            sys.exit(0)

    def writeOutput(self, str1):
        self.status.emit(str(str1))

    def workerFinished(self, list1, list2, list3):
        self.finished1.emit(list1, list2, list3)

    def emitPoint(self, x, y):
        self.emitpoint.emit(x, y)

    def updateProgressBar(self, float1):
        self.emitprogressbar.emit(float1)

    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished1 = pyqtSignal(list, list, list)
    emitpoint = pyqtSignal(float, float)
    emitprogressbar = pyqtSignal(float)
