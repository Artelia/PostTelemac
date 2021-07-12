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
)

import processing

import os


class PostTelemacControlSections(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                'Fichier TELEMAC des sections de contrôle',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='Fichier texte (*.txt)',
                defaultValue=None,
            )
        )
        
    def processAlgorithm(self, parameters, context, feedback):
        
        SCFilePath = self.parameterAsString(parameters, self.INPUT, context)
        
        input_file = os.path.normpath(SCFilePath)
        
        output_file = os.path.join(
            os.path.dirname(input_file),
            "post_" + os.path.basename(input_file).split(".")[0] + ".txt",
        )
        
        finput_file = open(input_file, "r")
        foutput_file = open(output_file, "w")
        
        finput_file.readline()  # First line is useless
        
        # Read, format and write to the output file all variables
        HEADERS = finput_file.readline()[13:].split(" ")
        head = ""
        for h in HEADERS[:-1]:
            head += h + "\t"
        foutput_file.write(head + HEADERS[-1])
        
        IGNORE = ["", "\n"]
        i = 0
        VALUES = []
        for line in finput_file.readlines():
            VALUES += [e for e in line.split(" ") if e not in IGNORE]
        
        for v in VALUES:
            if v[-1] == "\n" and v[-5] == "-":
                v = 0
            if i == len(HEADERS) - 1:
                foutput_file.write("{}\n".format(float(v)))
                i = 0
            else:
                foutput_file.write("{}\t".format(float(v)))
                i += 1
        
        finput_file.close()
        foutput_file.close()
        
        return {
            self.OUTPUT: output_file,
        }
        
    def name(self):
        return 'postFormatSC'

    def displayName(self):
        return "Post-traitement du fichier TELEMAC des sections de contrôle"

    def group(self):
        return 'Post-traitement'

    def groupId(self):
        return 'Post-traitement'
        
    def shortHelpString(self):
        return """
        Formate le fichier de sortie TELEMAC des sections de contrôle pour un usage simplifier sous Excel. 
        """

    def createInstance(self):
        return PostTelemacControlSections()

