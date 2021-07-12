# -*- coding: utf-8 -*-

"""
***************************************************************************
    __init__.py
    ---------------------
    Date                 : July 2013
    Copyright            : (C) 2013 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFeatureSink,
    QgsFields,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
)
from qgis.PyQt.QtCore import QVariant

import processing

import os
import numpy as np
from math import atan2, pi

from ..meshlayerparsers.libtelemac.selafin_io_pp import ppSELAFIN
from ..meshlayerparsers.posttelemac_selafin_parser import PostTelemacSelafinParser


class PostTelemacPointsShapeTool(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    ITER = "ITER"
    TRANSLATE_X = "TRANSLATE_X"
    TRANSLATE_Y = "TRANSLATE_Y"
    OUTPUT_SCR = "OUTPUT_SCR"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                "Fichier résultat TELEMAC",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="Fichiers résultats TELEMAC (*.res)",
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.ITER,
                "Itération à extraire",
                multiLine=False,
                defaultValue="0",
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TRANSLATE_X,
                "Translation du maillage X",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TRANSLATE_Y,
                "Translation du maillage Y",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                "Fichier résultat TELEMAC",
                QgsProcessing.TypeVectorPoint,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.OUTPUT_SCR, "Système de coordonnées du fichier à générer", defaultValue="EPSG:2154"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        selafinFilePath = os.path.normpath(self.parameterAsString(parameters, self.INPUT, context))
        time = self.parameterAsString(parameters, self.ITER, context)
        translatex = self.parameterAsDouble(parameters, self.TRANSLATE_X, context)
        translatey = self.parameterAsDouble(parameters, self.TRANSLATE_Y, context)
        outputShpScr = self.parameterAsCrs(parameters, self.OUTPUT_SCR, context)

        feedback.setProgressText("Initialisation du parser SELAFIN...")

        ## Initialisation du parser SELAFIN
        hydrauparser = PostTelemacSelafinParser()
        hydrauparser.loadHydrauFile(selafinFilePath)

        x, y = hydrauparser.getFacesNodes()
        x = x + translatex
        y = y + translatey

        times = len(hydrauparser.getTimes())
        if time == "dernier":
            time = times - 1
        elif int(time) in range(times):
            time = int(time)
        else:
            feedback.reportError(
                "Itération '{}' non trouvée dans le fichier SELAFIN {}".format(time, os.path.basename(selafinFilePath))
            )
            return {}

        ztri = [hydrauparser.getValues(time)[i] for i in range(len([param for param in hydrauparser.parametres]))]

        feedback.setProgressText("OK\n")

        total = 100.0 / len(x)

        fields = QgsFields()
        paramsName = [param[0] for param in hydrauparser.getVarNames()]
        for i, name in enumerate(paramsName):
            fields.append(QgsField(str(name.strip()), QVariant.Double))
        fields.append(QgsField("UV", QVariant.Double))
        fields.append(QgsField("VV", QVariant.Double))
        fields.append(QgsField("norme", QVariant.Double))
        fields.append(QgsField("angle", QVariant.Double))
        
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            fields,
            QgsWkbTypes.Point,
            outputShpScr,
        )

        for k in range(len(x)):
            if feedback.isCanceled():
                break

            feedback.setProgress(int(k * total))

            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(x[k]), float(y[k]))))

            tabattr = []
            for l in range(len(ztri)):
                tabattr.append(float(ztri[l][k]))

            norme = (
                (float(ztri[hydrauparser.parametrevx][k])) ** 2.0 + (float(ztri[hydrauparser.parametrevy][k])) ** 2.0
            ) ** (0.5)
            atanUVVV = atan2(float(ztri[hydrauparser.parametrevy][k]), float(ztri[hydrauparser.parametrevx][k]))
            angle = atanUVVV / pi * 180.0
            if angle < 0:
                angle = angle + 360

            tabattr.append(float(ztri[hydrauparser.parametrevx][k]))
            tabattr.append(float(ztri[hydrauparser.parametrevy][k]))
            tabattr.append(norme)
            tabattr.append(angle)

            fet.setAttributes(tabattr)

            sink.addFeature(fet)

        return {
            self.OUTPUT: dest_id,
        }

    def name(self):
        return "res2pts"

    def displayName(self):
        return "Extraction des noeuds"

    def group(self):
        return "ShapeTools"

    def groupId(self):
        return "ShapeTools"

    def shortHelpString(self):
        return """
        Extrait les noeuds de calcul du fichier résultats TELEMAC d'entrée.
 
        """

    def createInstance(self):
        return PostTelemacPointsShapeTool()
