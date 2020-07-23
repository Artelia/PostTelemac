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

try:
    from qgis.PyQt.QtGui import QTableWidgetItem
except:
    from qgis.PyQt.QtWidgets import QTableWidgetItem

import qgis

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ValueTool.ui"))


class ValueTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "VALUETOOL"

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)
        # self.setupUi(self)

    def initTool(self):
        self.setupUi(self)
        self.clickTool = qgis.gui.QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        # self.rubberbandfacenode = None
        # self.rubberbandelem = None
        # self.rubberbandface = None
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Information_48x48.png")
        # self.qtreewidgetitem.setIcon(0,QtGui.QIcon(os.path.join(os.path.dirname(__file__),'..','icons','tools','Information_48x48.png' )))
        # self.pointcolor = QtGui.QColor(QtCore.Qt.red)
        # self.elemcolor = QtGui.QColor(QtCore.Qt.blue)
        # self.facecolor = QtGui.QColor(QtCore.Qt.darkGreen)

    def onActivation(self):
        if self.meshlayer.hydrauparser != None:
            self.propertiesdialog.canvas.setMapTool(self.clickTool)
            try:
                self.clickTool.canvasClicked.disconnect()
            except Exception as e:
                pass
            self.clickTool.canvasClicked.connect(self.valeurs_click)
            if int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 4:
                self.valeurs_click(qgis.core.QgsPoint(0.0, 0.0))
            elif int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 5:
                self.valeurs_click(qgis.core.QgsPointXY(0.0, 0.0))

    def onDesactivation(self):
        try:
            self.clickTool.canvasClicked.disconnect()
        except Exception as e:
            pass

        self.meshlayer.rubberband.reset()

    def valeurs_click(self, qgspointfromcanvas):
        """
        Called in PostTelemacPropertiesDialog by value tool
        fill the tablewidget
        """
        # qgspointtransformed = self.selafinlayer.xform.transform(qgspoint,QgsCoordinateTransform.ReverseTransform)
        if self.comboBox_values_method.currentIndex() == 0:
            if int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 4:
                qgspoint = self.meshlayer.xform.transform(
                    qgis.core.QgsPoint(qgspointfromcanvas[0], qgspointfromcanvas[1]),
                    qgis.core.QgsCoordinateTransform.ReverseTransform,
                )
            elif int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 5:
                qgspoint = self.meshlayer.xform.transform(
                    qgis.core.QgsPointXY(qgspointfromcanvas[0], qgspointfromcanvas[1]),
                    qgis.core.QgsCoordinateTransform.ReverseTransform,
                )
            point1 = [[qgspoint.x(), qgspoint.y()]]
            # for facenode
            numnearestfacenode = self.meshlayer.hydrauparser.getNearestFaceNode(point1[0][0], point1[0][1])
            # x,y = self.meshlayer.hydrauparser.getFaceNodeXYFromNumPoint([numnearestfacenode])[0]
            # qgspointfromcanvas = self.meshlayer.xform.transform( qgis.core.QgsPoint(x,y) )
            # for elem
            numnearestelem = self.meshlayer.hydrauparser.getNearestElemNode(point1[0][0], point1[0][1])
            # geomtemp = self.meshlayer.hydrauparser.getElemXYFromNumElem([numnearestelem])[0]
            # elemqgisgeom = QgsGeometry.fromPolygon([[QgsPoint(x1,y1),QgsPoint(x2,y2), QgsPoint(x3,y3)]])
            # elemqgisgeom = qgis.core.QgsGeometry.fromPolygon([[self.meshlayer.xform.transform( qgis.core.QgsPoint(coord[0],coord[1]) ) for coord in geomtemp]])

            numnearestface = self.meshlayer.hydrauparser.getNearestFace(point1[0][0], point1[0][1])
            # geomtemp = self.meshlayer.hydrauparser.getFaceXYFromNumFace([numnearestface])[0]
            # faceqgisgeom = qgis.core.QgsGeometry.fromPolyline([self.meshlayer.xform.transform( qgis.core.QgsPoint(coord[0],coord[1]) ) for coord in geomtemp])

            if True:
                showelem = False
                showfacenode = False
                showface = False

                for i, param in enumerate(self.meshlayer.hydrauparser.parametres):
                    if param[2] == 0:
                        showelem = True
                        self.tableWidget_values.setItem(
                            i, 1, QTableWidgetItem(str(round(self.meshlayer.values[i][numnearestelem], 3)))
                        )
                    elif param[2] == 1:
                        showfacenode = True
                        self.tableWidget_values.setItem(
                            i, 1, QTableWidgetItem(str(round(self.meshlayer.values[i][numnearestfacenode], 3)))
                        )
                    elif param[2] == 2:
                        showface = True
                        self.tableWidget_values.setItem(
                            i, 1, QTableWidgetItem(str(round(self.meshlayer.values[i][numnearestface], 3)))
                        )

            if showelem:
                self.meshlayer.rubberband.drawFromNum([numnearestelem], 0)
            if showfacenode:
                self.meshlayer.rubberband.drawFromNum([numnearestfacenode], 1)
            if showface:
                self.meshlayer.rubberband.drawFromNum([numnearestface], 2)

    def updateParams(self):
        self.tableWidget_values.clearContents()
        self.tableWidget_values.setRowCount(len(self.meshlayer.hydrauparser.parametres))

        for i, param in enumerate(self.meshlayer.hydrauparser.parametres):
            if param[2] == 0:
                color = self.meshlayer.rubberband.elemcolor
            elif param[2] == 1:
                color = self.meshlayer.rubberband.pointcolor
            elif param[2] == 2:
                color = self.meshlayer.rubberband.facecolor

            self.tableWidget_values.setItem(i, 0, QTableWidgetItem(param[1]))
            try:
                self.tableWidget_values.item(i, 0).setTextColor(color)
            except:
                self.tableWidget_values.item(i, 0).setForeground(color)

            # self.tableWidget.item(i, 1).setTextColor(color)
        self.tableWidget_values.setFixedHeight(
            (self.tableWidget_values.rowHeight(0) - 1) * (len(self.meshlayer.hydrauparser.parametres) + 1) + 1
        )
