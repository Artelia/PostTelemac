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
    QgsProcessingParameterEnum,
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
    QgsVectorLayer,
    QgsSpatialIndex,
)
from qgis.PyQt.QtCore import QVariant

import processing

import os
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..meshlayerparsers.libtelemac.selafin_io_pp import ppSELAFIN
from ..meshlayerparsers.posttelemac_selafin_parser import PostTelemacSelafinParser


class PostTelemacContourShapeTool(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    ITER = "ITER"
    PARAMETER = "PARAMETER"
    LEVELS = "LEVELS"
    TRANSLATE_X = "TRANSLATE_X"
    TRANSLATE_Y = "TRANSLATE_Y"
    OUTPUT_SCR = "OUTPUT_SCR"
    OUTPUT = "OUTPUT"

    PARAMETERS_LIST = [
        "VITESSE U",
        "VITESSE V",
        "HAUTEUR D'EAU",
        "SURFACE LIBRE",
        "FOND",
        "FROTTEMENT",
        "COTE MAXIMUM",
        "VITESSE",
        "VITESSE MAXIMUM",
        "VITESSE DE MONTE",
        "ALEA",
        "intensite",
        "direction",
        "submersion",
        "duree",
    ]

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
            QgsProcessingParameterString(
                self.LEVELS,
                "Classes de niveau",
                multiLine=False,
                defaultValue="[0.05, 0.5, 1.0, 9999.0]",
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PARAMETER,
                "Paramètre",
                options=self.PARAMETERS_LIST,
                allowMultiple=False,
                defaultValue=["HAUTEUR D'EAU"],
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
        levels = self.parameterAsString(parameters, self.LEVELS, context).strip("][").replace(" ", "").split(",")
        parameter = self.parameterAsInt(parameters, self.PARAMETER, context)
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
        mesh = np.array(hydrauparser.getElemFaces())

        hydrauparser.identifyKeysParameters()

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

        paramList = [str(hydrauparser.getVarNames()[i][0]).strip() for i in range(len(hydrauparser.getVarNames()))]
        if self.PARAMETERS_LIST[parameter] in paramList:
            parameter = paramList.index(self.PARAMETERS_LIST[parameter])
        else:
            feedback.reportError(
                "Paramètre '{}' non trouvée dans la liste de paramètres du fichier SELAFIN {}".format(
                    self.PARAMETERS_LIST[parameter], os.path.basename(selafinFilePath)
                )
            )
            feedback.reportError(
                "La liste de paramètres disponibles dans le fichier SELAFIN {} est :".format(
                    os.path.basename(selafinFilePath)
                )
            )
            for p in paramList:
                feedback.reportError("    - {}".format(p))
            return {}

        values = hydrauparser.getValues(time)[parameter]

        totalLevels = 100.0 / (len(levels) - 1)

        fields = QgsFields()
        fields.append(QgsField("min", QVariant.Double))
        fields.append(QgsField("max", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.MultiPolygon,
            outputShpScr,
        )

        for lvl in range(len(levels) - 1):
            level = [levels[lvl], levels[lvl + 1]]

            feedback.setProgressText("Niveaux {}".format(level))

            if feedback.isCanceled():
                break

            progressLevels = int(lvl * totalLevels)
            feedback.setProgress(progressLevels)

            triplotcontourf = plt.tricontourf(
                x,
                y,
                mesh,
                values,
                level,
            )

            # Iteration sur les contours fournis par triplotcontourf  et inclusion des outers et inners dans une table temporaire
            vlOuterTemp, vlInnerTemp, vlInnerTempIndex = self.createInnerOutertempLayer(triplotcontourf)

            FeatsInnerTemp = {feature.id(): feature for (feature) in vlInnerTemp.getFeatures()}
            # creation d'un index spatial des inners pour aller plus vite
            map(vlInnerTempIndex.insertFeature, FeatsInnerTemp.values())

            counttotal = int(vlOuterTemp.featureCount())
            totalFeats = 100.0 / counttotal

            for i, outer in enumerate(vlOuterTemp.getFeatures()):
                if feedback.isCanceled():
                    return {}

                feedback.setProgressText("Géométrie n°{} - Ring process...".format(i))
                progressOuter = progressLevels + int(i * totalFeats * totalLevels / 100)
                feedback.setProgress(progressOuter)

                fet = self.InsertRinginFeature(outer, FeatsInnerTemp, vlInnerTempIndex, level, feedback)

                if fet == "Cancelled":
                    return {}
                else:
                    sink.addFeature(fet)

        return {
            self.OUTPUT: dest_id,
        }

    def name(self):
        return "res2ctr"

    def displayName(self):
        return "Extraction des contours"

    def group(self):
        return "ShapeTools"

    def groupId(self):
        return "ShapeTools"

    def shortHelpString(self):
        return """
        Extrait les contours d'une des variables du fichier résultats TELEMAC d'entrée suivant les niveaux définis.
        
        Quelques listes de niveaux utiles :
            - ZI : [0.05, 9999.0]
            - 4 classes : [0.05, 0.5, 1.0, 2.0, 9999.0]

        """

    def createInstance(self):
        return PostTelemacContourShapeTool()

    def createInnerOutertempLayer(self, triplotcontourf):
        fet = QgsFeature()

        for collection in triplotcontourf.collections:
            vl1temp1 = QgsVectorLayer("Multipolygon?crs=" + str(self.OUTPUT_SCR), "temporary_poly_outer ", "memory")
            pr1 = vl1temp1.dataProvider()
            vl1temp1.startEditing()

            vl2temp1 = QgsVectorLayer("Multipolygon?crs=" + str(self.OUTPUT_SCR), "temporary_poly_inner ", "memory")
            pr2 = vl2temp1.dataProvider()
            vl2temp1.startEditing()

            for path in collection.get_paths():
                for polygon in path.to_polygons():
                    if len(polygon) >= 3:
                        fet.setGeometry(self.get_outerinner(polygon)[0])
                        fet.setAttributes([])
                        if np.cross(polygon, np.roll(polygon, -1, axis=0)).sum() / 2.0 > 0:
                            pr1.addFeatures([fet])
                            vl1temp1.commitChanges()
                        else:
                            pr2.addFeatures([fet])
                            vl2temp1.commitChanges()

        index2 = QgsSpatialIndex(vl2temp1.getFeatures())

        return (vl1temp1, vl2temp1, index2)

    def get_outerinner(self, geom):
        geomtemp1 = []

        if (
            str(geom.__class__) == "<class 'qgis.core.QgsGeometry'>"
            or str(geom.__class__) == "<class 'qgis._core.QgsGeometry'>"
        ):
            geompolygon = geom.asPolygon()

            for i in range(len(geompolygon)):
                geomtemp2 = []

                for j in range(len(geompolygon[i])):
                    geomtemp2.append(QgsPointXY(geompolygon[i][j][0], geompolygon[i][j][1]))
                geomcheck = QgsGeometry.fromPolygonXY([geomtemp2])

                if len(geomcheck.validateGeometry()) != 0:
                    geomcheck = geomcheck.buffer(0.01, 5)
                geomtemp1.append(geomcheck)
        else:
            geomtemp2 = []

            for i in range(len(geom)):
                geomtemp2.append(QgsPointXY(geom[i][0], geom[i][1]))

            geomcheck = QgsGeometry.fromPolygonXY([geomtemp2])
            if len(geomcheck.validateGeometry()) != 0:
                geomcheck = geomcheck.buffer(0.01, 5)
            geomtemp1.append(geomcheck)

        return geomtemp1

    def InsertRinginFeature(self, outer, FeatsInnerTemp, vlInnerTempIndex, lvltemp1, feedback):
        # Correction des erreurs de geometrie des outers
        if len(outer.geometry().validateGeometry()) != 0:
            outergeom = outer.geometry().buffer(0.01, 5)
            if outergeom.area() < outer.geometry().area():
                outergeom = outer.geometry()
                feedback.pushInfo(
                    "WARNING : géométrie " + str(outer.id()) + " non valide avant l'insertion de l'anneau."
                )
        else:
            outergeom = outer.geometry()

        # requete spatiale pour avoir les inner dans les outers
        ids = vlInnerTempIndex.intersects(outergeom.boundingBox())

        fet1surface = outergeom.area()
        # Iteration sur tous les inners pour les inclures dans les outers
        # creation d'un tableau pour trier les inners par ordre de S decroissant
        tab = []
        for id in ids:
            f2geom = FeatsInnerTemp[id].geometry()
            if len(f2geom.validateGeometry()) != 0:
                f2geom = f2geom.buffer(0.00, 5)
            tab.append([f2geom.area(), f2geom])

        tabLen = len(tab)

        if tabLen > 0:
            totalInner = 100.0 / len(tab)
            tab.sort(reverse=True, key=lambda area: area[0])
            # Iteration pour enlever les inner des outers - coeur du script
            for k in range(tabLen):
                try:
                    if feedback.isCanceled():
                        return "Cancelled"
                    if tab[k][0] >= fet1surface:
                        continue
                    else:
                        ring = self.do_ring(tab[k][1])
                        tt1 = outergeom.addRing(ring)
                        if tt1 == 5 and outergeom.intersects(tab[k][1]):
                            outergeom = outergeom.difference(tab[k][1])
                except Exception as e:
                    feedback.reportError("Erreur creation ring : " + str(e))
                    return outer

        if len(outergeom.validateGeometry()) != 0:
            outergeomtemp = outergeom.buffer(0.01, 5)
            if outergeomtemp.area() > outergeom.area():
                outergeom = outergeomtemp
            else:
                feedback.pushInfo(
                    "WARNING : géométrie " + str(outer.id()) + " non valide avant l'insertion de l'anneau."
                )

        fet = QgsFeature()
        fet.setGeometry(outergeom)
        fet.setAttributes([lvltemp1[0], lvltemp1[1]])

        return fet

    def do_ring(self, geom3):
        ring = []
        try:
            polygon = geom3.asPolygon()[0]
        except TypeError:
            polygon = geom3.asMultiPolygon()[0][0]
        for i in range(len(polygon)):
            ring.append(QgsPointXY(polygon[i][0], polygon[i][1]))
        ring.append(QgsPointXY(polygon[0][0], polygon[0][1]))

        return ring
