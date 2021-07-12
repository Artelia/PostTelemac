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
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
)

import processing

import os
import numpy as np
import math

from ..meshlayerparsers.libtelemac.selafin_io_pp import ppSELAFIN
from ..meshlayerparsers.posttelemac_selafin_parser import PostTelemacSelafinParser


class PostTelemacExtractMax(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    COMPUTE_REAL_MAX_VELOCITY = 'COMPUTE_REAL_VELOCITY'
    H_WATER_ARRIVAL = 'H_WATER_ARRIVAL'
    H_FLOOD_DURATION = 'H_FLOOD_DURATION'
    OUTPUT = 'OUTPUT'
    # SELAFIN_LVL_STD = 'SELAFIN_LVL_STD'
    # SELAFIN_LVL_SPE = 'SELAFIN_LVL_SPE'
    # SELAFIN_PARAM_STD = 'SELAFIN_PARAM_STD'
    # SELAFIN_PARAM_SPE = 'SELAFIN_PARAM_SPE'
    # QUICK_PROCESS = 'QUICK_PROCESS'
    # SELAFIN_CRS = 'SELAFIN_CRS'
    # TRANS_CRS = 'TRANS_CRS'
    # SHP_CRS = 'SHP_CRS'
    # SHP_NAME = 'SHP_NAME'
    # SHP_PROCESS = 'SHP_PROCESS'
    
    # PROCESS_TYPES = ['En arriere plan', 'Modeler', 'Modeler avec creation de fichier']
    # SELAFIN_LVL_STDS = ['[H_simple : 0.0,0.05,0.5,1.0,2.0,,5.0,9999.0]' , '[H_complet : 0.0,0.01,0.05,0.1,0.25,0.5,1.0,1.5,2.0,5.0,9999.0]' , '[H_AMC]' , '[V_AMC_simple : 0.0,0.5,1.0,2.0,4.0]' , '[V_complet : 0,0.25,0.5,1.0,2.0,4.0,9999.0]' , '[Onde : mn : 0,5,10,15,30,h : 1, 2, 3, 6, 12, 24, >24]' , '[Delta_SL : -9999,0.5,-0.25,-0.10,-0.05,-0.02,-0.01,0.01,0.02,0.10,0.25,0.50,9999]' , '[Duree_AMC]']
    # SELAFIN_PARAM_STDS = ['Hmax','Vmax','SLmax','?SLmax','SUBMERSION']
    
    

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                'Fichier résultat TELEMAC',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='Fichiers résultats TELEMAC (*.res)',
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.COMPUTE_REAL_MAX_VELOCITY,
                'Calculer la vitesse maximale réelle',
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.H_WATER_ARRIVAL,
                "Calculer le pas de temps d'arrivée de l'onde pour une hauteur d'eau supérieure à ...(-1 pour désactiver)",
                type=QgsProcessingParameterNumber.Double,
                minValue=-1,
                defaultValue=0.05,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.H_FLOOD_DURATION,
                "Calculer la durée de l'inondation pour une hauteur d'eau supérieure à ...(-1 pour désactiver)",
                type=QgsProcessingParameterNumber.Double,
                minValue=-1,
                defaultValue=0.05,
            )
        )       
        
    def processAlgorithm(self, parameters, context, feedback):
        
        selafinFilePath = self.parameterAsString(parameters, self.INPUT, context)
        selafinFileOutPath = selafinFilePath.rsplit(".", maxsplit=1)[0] + "_Max.res"
        intensite = self.parameterAsBoolean(parameters, self.COMPUTE_REAL_MAX_VELOCITY, context)
        direction = self.parameterAsBoolean(parameters, self.COMPUTE_REAL_MAX_VELOCITY, context)
        submersion = self.parameterAsDouble(parameters, self.H_WATER_ARRIVAL, context)
        duree = self.parameterAsDouble(parameters, self.H_FLOOD_DURATION, context)
        
        feedback.setProgressText("Initialisation du parser SELAFIN...")
        
        ## Initialisation du parser SELAFIN
        hydrauparser = PostTelemacSelafinParser()
        hydrauparser.loadHydrauFile(os.path.normpath(selafinFilePath))
        
        feedback.setProgressText("OK\n")
        
        total = 100.0 / len(hydrauparser.getTimes())
        
        feedback.setProgressText("Initialisation du fichier de sortie...")
        
        ## Creation de la variable au format Serafin
        resIn = ppSELAFIN(selafinFilePath)
        resOut = ppSELAFIN(selafinFileOutPath)

        ## Lecture de l'entete du fichier d'entree
        resIn.readHeader()

        ## Recuperation de tous les temps
        resIn.readTimes()

        ## On copie toutes les variables de l'entete du fichier d'entree dans
        ## les variables du fichier de sortie
        title = resIn.getTitle()
        times = resIn.getTimes()
        variables = resIn.getVarNames()
        units = resIn.getVarUnits()
        float_type, float_size = resIn.getPrecision()

        # number of variables
        NVAR = len(variables)

        # gets some mesh properties from the *.slf file
        IPARAM = resIn.getIPARAM()
        NELEM, NPOIN, NDP, IKLE, IPOBO, x, y = resIn.getMesh()

        resIn.close()

        ## On ajoute les deux nouvelles variables, pour cela il faut modifier la variable
        ## nbvar et nomvar (le nom de la variable ne doit pas depasser 72 caracteres

        for param in hydrauparser.parametres:
            if param[4]:  # for virtual parameter
                variables.append(str(param[1]))
                units.append("")

        if intensite:
            variables.append("intensite")
            units.append("M/S")
        if direction:
            variables.append("direction")
            units.append("")
        if submersion > -1 and hydrauparser.parametreh != None:
            variables.append("submersion")
            units.append("S")
        if duree > -1 and hydrauparser.parametreh != None:
            variables.append("duree")
            units.append("S")

        ## Ecriture de l'entete dans le fichier de sortie
        resOut.setPrecision(float_type, float_size)
        resOut.setTitle(title)
        resOut.setVarNames(variables)
        resOut.setVarUnits(units)
        resOut.setIPARAM(IPARAM)
        resOut.setMesh(NELEM, NPOIN, NDP, IKLE, IPOBO, x, y)
        resOut.writeHeader()
        
        feedback.setProgressText("OK\n")
        
        feedback.setProgressText("Calcul du max...")
        
        initialisation = True
        for current, timeslf in enumerate(hydrauparser.getTimes()):
            if feedback.isCanceled():
                resOut.close()
                break
        
            num_time = np.where(hydrauparser.getTimes() == timeslf)[0][0]

            feedback.setProgress(int(current * total))

            if initialisation:  ## Ce else permet de d'initialiser notre variable max avec le premier pas de temps
                var_max = hydrauparser.getValues(num_time)

                if submersion > -1 and hydrauparser.parametreh != None:
                    var_sub = np.array([np.nan] * hydrauparser.facesnodescount)
                    pos_sub = np.where(var_max[hydrauparser.parametreh] >= submersion)[0]
                    var_sub[pos_sub] = timeslf

                if duree > -1 and hydrauparser.parametreh != None:
                    var_dur = np.array([0.0] * hydrauparser.facesnodescount)
                    previoustime = timeslf

                initialisation = False
            else:
                var = hydrauparser.getValues(num_time)

                for num_var, val_var in enumerate(var):
                    if (
                        hydrauparser.parametrevx != None
                        and hydrauparser.parametrevy != None
                        and (
                            num_var == hydrauparser.parametrevx
                            or num_var == hydrauparser.parametrevy
                        )
                    ):
                        # On recherche tous les indicides du tableau ou les nouvelles valeurs sont supérieurs aux anciennes
                        pos_max = np.where(var[num_var] > var_max[num_var])[0]
                        var_max[num_var][pos_max] = val_var[pos_max]

                    else:
                        if (
                            (submersion > -1 or duree > -1)
                            and hydrauparser.parametreh != None
                            and num_var == hydrauparser.parametreh
                        ):
                            if duree > -1:
                                pos_dur = np.where(var[num_var] >= duree)[0]
                                var_dur[pos_dur] += timeslf - previoustime
                                previoustime = timeslf
                            if submersion > -1:
                                pos_sub = np.where(var[num_var] >= submersion)[0]
                                possubpreced = np.where(np.isnan(var_sub))[0]  # on cherche les valeurs encore a nan
                                goodnum = np.intersect1d(pos_sub, possubpreced)  # on intersecte les deux
                                var_sub[goodnum] = timeslf

                        # On recherche tous les indices du tableau ou les nouvelles valeurs sont supérieures aux anciennes
                        pos_max = np.where(var[num_var] > var_max[num_var])[0]
                        var_max[num_var][pos_max] = val_var[pos_max]

                ## Maintenant on s'occuppe du cas particulier des vitesses
                if (
                    hydrauparser.parametrevx != None
                    and hydrauparser.parametrevy != None
                ):
                    vit = np.power(
                        np.power(var[hydrauparser.parametrevx], 2)
                        + np.power(var[hydrauparser.parametrevy], 2),
                        0.5,
                    )
                    vit_max = np.power(
                        np.power(var_max[hydrauparser.parametrevx], 2)
                        + np.power(var_max[hydrauparser.parametrevy], 2),
                        0.5,
                    )

                    pos_vmax = np.where(vit > vit_max)[0]
                    var_max[hydrauparser.parametrevx][pos_vmax] = var[
                        hydrauparser.parametrevx
                    ][pos_vmax]
                    var_max[hydrauparser.parametrevy][pos_vmax] = var[
                        hydrauparser.parametrevy
                    ][pos_vmax]
                    
        if (
            hydrauparser.parametrevx != None
            and hydrauparser.parametrevy != None
            and (intensite or direction)
        ):
            u = var_max[hydrauparser.parametrevx]
            v = var_max[hydrauparser.parametrevy]
            if intensite:
                val_intensite = np.power(np.power(u, 2) + np.power(v, 2), 0.5)
                var_max = np.vstack((var_max, val_intensite))

            if direction:
                np.seterr(divide="ignore", invalid="ignore")
                val_direction = (
                    np.arctan2(u, v) * 360.0 / (2.0 * math.pi)
                    + np.minimum(np.arctan2(u, v), 0.0) / np.arctan2(u, v) * 360.0
                )
                np.seterr(divide="warn", invalid="warn")
                ## Dans la creation des directions il peut y avoir des divisions par 0
                ## Ceci entraine la creation de nan (not a number)
                ## On va alors remplacer tous ces nan par 0.
                np.place(val_direction, np.isnan(val_direction), 0.0)
                var_max = np.vstack((var_max, val_direction))

        if submersion > -1 and hydrauparser.parametreh != None:
            var_sub = np.nan_to_num(var_sub)
            var_max = np.vstack((var_max, var_sub))
        if duree > -1 and hydrauparser.parametreh != None:
            var_max = np.vstack((var_max, var_dur))

        ## Ecriture des valeurs max dans le fichier de sortie (on met un temps à 0 dans le fichier)
        resOut.writeVariables(0.0, var_max)

        resOut.close()
        
        return {
            self.OUTPUT: selafinFileOutPath,
        }
        
    def name(self):
        return 'extractMax'

    def displayName(self):
        return "Extraction des maximums"

    def group(self):
        return 'Export'

    def groupId(self):
        return 'Export'
        
    def shortHelpString(self):
        return """
        Extrait le maximum de toutes les variables du fichier résultats TELEMAC d'entrée.
        
        Optionnel :
            - Calcul de la vitesse maximale réelle
            - Calcul du temps d'arrivée de l'onde pour une certaine hauteur d'eau minimale
            - Calcul de la durée de submersion pour une certaine hauteur d'eau minimale
            
        WIP :
            - Variables définies par l'utilisateur non supportées
            - Extraction sur un intervalle d'itérations 
        """

    def createInstance(self):
        return PostTelemacExtractMax()

