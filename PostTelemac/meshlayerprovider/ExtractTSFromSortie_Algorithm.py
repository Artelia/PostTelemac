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
    QgsProcessingParameterEnum,
)

import processing

import os
import re
import collections


class ExtractTSFromSortie(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    TIMESERIE = "TIMESERIE"
    OUTPUT = "OUTPUT"

    _OPTIONS = [
        "Buses",
        "Siphons",
    ]
    _KEYWORD = {
        "Buses": ["BUSE", "CULVERT"],
        "Siphons": ["SIPHON"],
    }

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                "Fichier sortie TELEMAC",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="Fichier sortie (*.sortie)",
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TIMESERIE,
                "Série temporelle à extraire",
                options=self._OPTIONS,
                allowMultiple=False,
                defaultValue=[],
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        SortieFilePath = self.parameterAsString(parameters, self.INPUT, context)
        serie = self._OPTIONS[self.parameterAsEnum(parameters, self.TIMESERIE, context)]

        input_file = os.path.normpath(SortieFilePath)

        output_file = os.path.join(
            os.path.dirname(input_file),
            os.path.basename(input_file).split(".")[0] + "_{}".format(serie) + ".txt",
        )

        finput_file = open(input_file, "r")

        culvert_list = {}

        ## Je suppose que si le script est lancé c'est qu'il y au moins une buse --> Toi !
        culvert_list[1] = Culvert(1)

        all_time = []

        for line in finput_file.readlines():
            elements = re.sub(r"\s\s+", " ", line[1:]).split(" ")
            if ("ITERATION" in elements) and ("TEMPS" in elements):
                time = float(elements[-2])
                all_time.append(time)
                continue
            elif elements[0] in self._KEYWORD[serie]:
                numero = int(elements[1])
                debit = float(elements[4])
            else:
                continue

            try:
                culvert = culvert_list[numero]
            except KeyError:
                culvert = Culvert(numero)
                culvert_list[numero] = culvert
            culvert.add(time, debit)

        finput_file.close()

        od = collections.OrderedDict(sorted(culvert_list.items()))

        foutput_file = open(output_file, "w")

        ## Ecriture de l'en-tete et extraction des séries
        culvert_serie = []
        culvert_number = len(od)
        lineToWrite = "Temps\t"
        for i, (numero, culvert) in enumerate(od.items()):
            culvert_serie.append(culvert.getSerie())

            if i == culvert_number - 1:
                lineToWrite += "OH{}".format(culvert.numero)
            else:
                lineToWrite += "OH{}\t".format(culvert.numero)

        foutput_file.write("{}\n".format(lineToWrite))

        for time in all_time:
            lineToWrite = "{}\t".format(time)

            for i in range(culvert_number):
                try:
                    pos = culvert_serie[i][0].index(time)
                    debit = culvert_serie[i][1][pos]
                except ValueError:
                    debit = 0.0

                if i == culvert_number - 1:
                    lineToWrite += "{}".format(debit)
                else:
                    lineToWrite += "{}\t".format(debit)

            foutput_file.write("{}\n".format(lineToWrite))

        foutput_file.close()

        return {
            self.OUTPUT: output_file,
        }

    def name(self):
        return "extractTSFromSortie"

    def displayName(self):
        return "Extraction des séries temporelles du fichier de sortie"

    def group(self):
        return "Post-traitement"

    def groupId(self):
        return "Post-traitement"

    def shortHelpString(self):
        return """
        Extrait du fichier de sortie TELEMAC les séries temporelles telles que les débits des buses.

        Pour obtenir le fichier de sortie, lancer le calcul TELEMAC avec l'option "-s" : telemac2d.py -s fichier.cas
        
        Séries temporelles supportées :
            - Débit des buses "BUSE" ou "CULVERT"
            - Débit des siphons "SIPHON"
        """

    def createInstance(self):
        return ExtractTSFromSortie()


class Culvert:
    def __init__(self, numero):
        self.numero = numero
        self._timeList = []
        self._debitList = []

    def add(self, time, debit):
        self._timeList.append(time)
        self._debitList.append(debit)

    def getSerie(self):
        return [self._timeList, self._debitList]
