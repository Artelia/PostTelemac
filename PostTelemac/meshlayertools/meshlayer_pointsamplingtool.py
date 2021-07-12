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
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QVariant

from qgis.core import (
    QgsFields,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsProject,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsVectorLayer,
)
from qgis.utils import iface

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
        parentlayer = iface.activeLayer()
        if not (parentlayer.type() == 0 and parentlayer.geometryType() == 0):
            QMessageBox.warning(iface.mainWindow(), "PostTelemac", self.tr("Select a point vector layer"))
        else:
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
            fields = QgsFields(parentlayer.fields())
            paramindex = []
            if self.comboBox_parametreschooser.currentText() == "All parameters":
                for param in self.meshlayer.hydrauparser.parametres:
                    fields.append(QgsField(param[1], QVariant.Double))
                    paramindex.append(param[0])
            else:
                paramindex.append(int(self.comboBox_parametreschooser.currentText().split(":")[0]))
                paramname = self.meshlayer.hydrauparser.parametres[paramindex[0]][1]
                fields.append(QgsField(paramname, QVariant.Double))
            # writer for shapefile
            writer = None
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "utf-8"
            writer = QgsVectorFileWriter.create(
                fileName=pathresult,
                fields=fields,
                geometryType=QgsWkbTypes.Point,
                srs=self.meshlayer.realCRS,
                transformContext=QgsCoordinateTransformContext(),
                options=options,
            )
            # for projection
            xformutil = QgsCoordinateTransform(parentlayer.crs(), self.meshlayer.realCRS, QgsProject.instance())
            # check interpolator
            if self.meshlayer.hydrauparser.interpolator is None:
                self.meshlayer.hydrauparser.createInterpolator()
            success = self.meshlayer.hydrauparser.updateInterpolatorEmit(self.meshlayer.time_displayed)

            for feat in parentlayer.getFeatures():
                fet = QgsFeature(fields)
                pointsource = feat.geometry().asPoint()
                pointinmeshcrs = xformutil.transform(pointsource)
                fet.setGeometry(QgsGeometry.fromPointXY(pointinmeshcrs))
                attrs = feat.attributes()
                for paramidx in paramindex:
                    value = self.meshlayer.hydrauparser.interpolator[paramidx](pointinmeshcrs.x(), pointinmeshcrs.y())
                    attrs.append(float(value.data))
                fet.setAttributes(attrs)
                writer.addFeature(fet)

            del writer

            vlayer = QgsVectorLayer(pathresult, os.path.basename(pathresult).split(".")[0], "ogr")
            QgsProject.instance().addMapLayer(vlayer)
            self.meshlayer.propertiesdialog.normalMessage(
                str(os.path.basename(pathresult).split(".")[0]) + self.tr(" created")
            )

    def updateProgressBar(self, float1):
        self.propertiesdialog.progressBar.setValue(int(float1))
