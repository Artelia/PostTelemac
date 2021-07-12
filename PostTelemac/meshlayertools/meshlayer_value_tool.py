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
from qgis.PyQt.QtWidgets import QTableWidgetItem

from qgis.core import QgsPointXY, QgsCoordinateTransform
from qgis.gui import QgsMapToolEmitPoint

from .meshlayer_abstract_tool import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ValueTool.ui"))


class ValueTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "VALUETOOL"

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)

    def initTool(self):
        self.setupUi(self)
        self.clickTool = QgsMapToolEmitPoint(self.propertiesdialog.canvas)
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Information_48x48.png")

    def onActivation(self):
        if self.meshlayer.hydrauparser != None:
            self.propertiesdialog.canvas.setMapTool(self.clickTool)
            try:
                self.clickTool.canvasClicked.disconnect()
            except Exception as e:
                pass
            self.clickTool.canvasClicked.connect(self.valeurs_click)
            self.valeurs_click(QgsPointXY(0.0, 0.0))

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
        if self.comboBox_values_method.currentIndex() == 0:
            qgspoint = self.meshlayer.xform.transform(
                QgsPointXY(qgspointfromcanvas[0], qgspointfromcanvas[1]),
                QgsCoordinateTransform.ReverseTransform,
            )
            point1 = [[qgspoint.x(), qgspoint.y()]]
            numnearestfacenode = self.meshlayer.hydrauparser.getNearestFaceNode(point1[0][0], point1[0][1])
            numnearestelem = self.meshlayer.hydrauparser.getNearestElemNode(point1[0][0], point1[0][1])
            numnearestface = self.meshlayer.hydrauparser.getNearestFace(point1[0][0], point1[0][1])

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
            self.tableWidget_values.item(i, 0).setForeground(color)

        self.tableWidget_values.setFixedHeight(
            (self.tableWidget_values.rowHeight(0) - 1) * (len(self.meshlayer.hydrauparser.parametres) + 1) + 1
        )
