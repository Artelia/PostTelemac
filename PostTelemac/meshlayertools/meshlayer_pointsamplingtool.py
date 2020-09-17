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


# import Qt
from qgis.PyQt import uic, QtCore, QtGui

try:
    from qgis.PyQt.QtGui import QMessageBox
except:
    from qgis.PyQt.QtWidgets import QMessageBox

import qgis
import numpy as np
import os
import sys

# local import
from .meshlayer_abstract_tool import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "PointSamplingTool.ui"))


class PointSamplingTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "POINTSAMPLINGTOOL"
    SOFTWARE = ["TELEMAC", "ANUGA"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)

    # *********************************************************************************************
    # ***************Imlemented functions  **********************************************************
    # ********************************************************************************************

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Line_Graph_48x48_time.png")
        self.propertiesdialog.updateparamsignal.connect(self.updateParams)

        self.pushButton_calc.clicked.connect(self.computeSamplingPoints)

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""
        pass

    def onDesactivation(self):
        pass

    # *********************************************************************************************
    # ***************Behaviour functions  **********************************************************
    # ********************************************************************************************

    def updateParams(self):

        self.comboBox_parametreschooser.clear()
        self.comboBox_parametreschooser.addItems(["All parameters"])
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

    def computeSamplingPoints(self):
        parentlayer = qgis.utils.iface.activeLayer()
        if not (parentlayer.type() == 0 and parentlayer.geometryType() == 0):
            QMessageBox.warning(qgis.utils.iface.mainWindow(), "PostTelemac", self.tr("Select a point vector layer"))
        else:
            # name
            nameresult = (
                parentlayer.name()
                + "_"
                + self.meshlayer.name()
                + "_T_"
                + str(self.meshlayer.time_displayed)
                + "_sample.shp"
            )
            pathresult = os.path.join(os.path.dirname(parentlayer.source()), nameresult)
            # fields
            fields = qgis.core.QgsFields(parentlayer.fields())
            paramindex = []
            if self.comboBox_parametreschooser.currentText() == "All parameters":
                for param in self.meshlayer.hydrauparser.parametres:
                    fields.append(qgis.core.QgsField(param[1], QtCore.QVariant.Double))
                    paramindex.append(param[0])
            else:
                paramindex.append(int(self.comboBox_parametreschooser.currentText().split(":")[0]))
                paramname = self.meshlayer.hydrauparser.parametres[paramindex[0]][1]
                fields.append(qgis.core.QgsField(paramname, QtCore.QVariant.Double))
            # writer for shapefile
            writer = qgis.core.QgsVectorFileWriter(
                pathresult, "UTF8", fields, qgis.core.QgsWkbTypes.Point, self.meshlayer.realCRS, "ESRI Shapefile"
            )
            # for projection
            if sys.version_info.major == 2:
                xformutil = qgis.core.QgsCoordinateTransform(parentlayer.crs(), self.meshlayer.realCRS)
            elif sys.version_info.major == 3:
                xformutil = qgis.core.QgsCoordinateTransform(
                    parentlayer.crs(), self.meshlayer.realCRS, qgis.core.QgsProject.instance()
                )

            # check interpolator
            if self.meshlayer.hydrauparser.interpolator is None:
                self.meshlayer.hydrauparser.createInterpolator()
            success = self.meshlayer.hydrauparser.updateInterpolatorEmit(self.meshlayer.time_displayed)

            for feat in parentlayer.getFeatures():
                fet = qgis.core.QgsFeature(fields)
                pointsource = feat.geometry().asPoint()
                pointinmeshcrs = xformutil.transform(pointsource)
                fet.setGeometry(qgis.core.QgsGeometry.fromPointXY(pointinmeshcrs))
                attrs = feat.attributes()
                for paramidx in paramindex:
                    value = self.meshlayer.hydrauparser.interpolator[paramidx](pointinmeshcrs.x(), pointinmeshcrs.y())
                    # print('value',value,type(value))
                    attrs.append(float(value.data))
                # print('pointinmeshcrs',pointinmeshcrs.x(),pointinmeshcrs.y() )
                # print('attrs',attrs,[field.name() for field in fields])
                fet.setAttributes(attrs)
                writer.addFeature(fet)

            del writer
            vlayer = qgis.core.QgsVectorLayer(pathresult, os.path.basename(pathresult).split(".")[0], "ogr")
            if sys.version_info.major == 2:
                qgis.core.QgsMapLayerRegistry.instance().addMapLayer(vlayer)
            elif sys.version_info.major == 3:
                qgis.core.QgsProject.instance().addMapLayer(vlayer)
            self.meshlayer.propertiesdialog.normalMessage(
                str(os.path.basename(pathresult).split(".")[0]) + self.tr(" created")
            )

    def updateProgressBar(self, float1):
        self.propertiesdialog.progressBar.setValue(int(float1))
