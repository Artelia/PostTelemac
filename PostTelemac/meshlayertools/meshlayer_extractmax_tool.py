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
from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal

from qgis.core import QgsApplication, QgsProject
from qgis.utils import iface

from .meshlayer_abstract_tool import *
from ..meshlayerparsers.libtelemac.selafin_io_pp import ppSELAFIN

import sys
import numpy as np
import math

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "ExtractMaxTool.ui"))


class ExtractMaxTool(AbstractMeshLayerTool, FORM_CLASS):

    NAME = "EXTRACTMACTOOL"
    SOFTWARE = ["TELEMAC"]

    def __init__(self, meshlayer, dialog):
        AbstractMeshLayerTool.__init__(self, meshlayer, dialog)
        self.pushButton_max_res.clicked.connect(self.calculMaxRes)

    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__), "..", "icons", "tools", "Wizard_48x48.png")

    def onActivation(self):
        maxiter = self.meshlayer.hydrauparser.itertimecount
        self.spinBox_max_start.setMaximum(maxiter)
        self.spinBox_max_end.setMaximum(maxiter)
        self.spinBox_max_end.setValue(maxiter)

    def onDesactivation(self):
        pass

    def calculMaxRes(self):

        self.initclass = initRunGetMax()
        self.initclass.status.connect(self.propertiesdialog.logMessage)

        self.initclass.finished1.connect(self.chargerSelafin)
        self.propertiesdialog.normalMessage(self.tr("ExtractMax launched - watch progress on log tab"))

        self.initclass.start(
            self.meshlayer,
            self,
            self.checkBox_11.isChecked(),
            self.checkBox_11.isChecked(),
            self.doubleSpinBox_4.value() if self.checkBox_9.isChecked() else -1,
            self.doubleSpinBox_5.value() if self.checkBox_10.isChecked() else -1,
        )

    def chargerSelafin(self, path):
        if path and self.checkBox_8.isChecked():
            if iface is not None:
                slf = QgsApplication.instance().pluginLayerRegistry().pluginLayerType("selafin_viewer").createLayer()
                slf.setRealCrs(self.meshlayer.crs())
                slf.load_selafin(path, "TELEMAC")
                QgsProject.instance().addMapLayer(slf)


class runGetMax(QObject):
    def __init__(self, selafinlayer, tool, intensite=False, direction=False, submersion=-1, duree=-1):
        QObject.__init__(self)
        self.selafinlayer = selafinlayer
        self.tool = tool
        self.name_res = self.selafinlayer.hydraufilepath
        self.name_res_out = self.selafinlayer.hydraufilepath.rsplit(".", maxsplit=1)[0] + "_Max.res"
        self.intensite = intensite
        self.direction = direction
        self.submersion = submersion
        self.duree = duree

    def run(self):
        """
        Fonction permettant de recuperer la valeur max d'un resultat (avec en plus
        l'ecriture de l'intensite et de la direction)
        Parametre d'entree:
        - name_res (str) : nom du fichier resultat telemac
        - name_res_out (str) : nom du fichier a creer (au format Serafin)
        - intensite (bool) : si vrai alors on recalcule l'intensite max
        - direction (bool) : si vrai alors on recalcule la direction des intensites max
        Parametre de sortie:
        - aucun
        fonctions appelees:
        - aucunes

        """

        ## Creation de la variable au format Serafin
        resIn = ppSELAFIN(self.name_res)
        resOut = ppSELAFIN(self.name_res_out)

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

        for param in self.selafinlayer.hydrauparser.parametres:
            if param[4]:  # for virtual parameter
                variables.append(str(param[1]))
                units.append("")

        if self.intensite:
            variables.append("intensite")
            units.append("M/S")
        if self.direction:
            variables.append("direction")
            units.append("")
        if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
            variables.append("submersion")
            units.append("S")
        if self.duree > -1 and self.selafinlayer.hydrauparser.parametreh != None:
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

        ## Boucle sur tous les temps et récuperation des variables
        itermin = self.tool.spinBox_max_start.value()
        iterfin = self.tool.spinBox_max_end.value()

        try:
            initialisation = True
            for timeslf in self.selafinlayer.hydrauparser.getTimes()[itermin:iterfin]:
                num_time = np.where(self.selafinlayer.hydrauparser.getTimes() == timeslf)[0][0]

                if (num_time - itermin) % 10 == 0:
                    self.status.emit("Maximum creation - time " + str(timeslf))

                if initialisation:  ## Ce else permet de d'initialiser notre variable max avec le premier pas de temps
                    var_max = self.selafinlayer.hydrauparser.getValues(num_time)

                    if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                        var_sub = np.array([np.nan] * self.selafinlayer.hydrauparser.facesnodescount)
                        pos_sub = np.where(var_max[self.selafinlayer.hydrauparser.parametreh] >= self.submersion)[0]
                        var_sub[pos_sub] = timeslf

                    if self.duree > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                        var_dur = np.array([0.0] * self.selafinlayer.hydrauparser.facesnodescount)
                        previoustime = timeslf

                    initialisation = False
                else:
                    var = self.selafinlayer.hydrauparser.getValues(num_time)

                    for num_var, val_var in enumerate(var):
                        if (
                            self.selafinlayer.hydrauparser.parametrevx != None
                            and self.selafinlayer.hydrauparser.parametrevy != None
                            and (
                                num_var == self.selafinlayer.hydrauparser.parametrevx
                                or num_var == self.selafinlayer.hydrauparser.parametrevy
                            )
                        ):
                            # On recherche tous les indicides du tableau ou les nouvelles valeurs sont supérieurs aux anciennes
                            pos_max = np.where(var[num_var] > var_max[num_var])[0]
                            var_max[num_var][pos_max] = val_var[pos_max]

                        else:
                            if (
                                (self.submersion > -1 or self.duree > -1)
                                and self.selafinlayer.hydrauparser.parametreh != None
                                and num_var == self.selafinlayer.hydrauparser.parametreh
                            ):
                                if self.duree > -1:
                                    pos_dur = np.where(var[num_var] >= self.duree)[0]
                                    var_dur[pos_dur] += timeslf - previoustime
                                    previoustime = timeslf
                                if self.submersion > -1:
                                    pos_sub = np.where(var[num_var] >= self.submersion)[0]
                                    possubpreced = np.where(np.isnan(var_sub))[0]  # on cherche les valeurs encore a nan
                                    goodnum = np.intersect1d(pos_sub, possubpreced)  # on intersecte les deux
                                    var_sub[goodnum] = timeslf

                            # On recherche tous les indices du tableau ou les nouvelles valeurs sont supérieures aux anciennes
                            pos_max = np.where(var[num_var] > var_max[num_var])[0]
                            var_max[num_var][pos_max] = val_var[pos_max]

                    ## Maintenant on s'occuppe du cas particulier des vitesses
                    if (
                        self.selafinlayer.hydrauparser.parametrevx != None
                        and self.selafinlayer.hydrauparser.parametrevy != None
                    ):
                        vit = np.power(
                            np.power(var[self.selafinlayer.hydrauparser.parametrevx], 2)
                            + np.power(var[self.selafinlayer.hydrauparser.parametrevy], 2),
                            0.5,
                        )
                        vit_max = np.power(
                            np.power(var_max[self.selafinlayer.hydrauparser.parametrevx], 2)
                            + np.power(var_max[self.selafinlayer.hydrauparser.parametrevy], 2),
                            0.5,
                        )

                        pos_vmax = np.where(vit > vit_max)[0]
                        var_max[self.selafinlayer.hydrauparser.parametrevx][pos_vmax] = var[
                            self.selafinlayer.hydrauparser.parametrevx
                        ][pos_vmax]
                        var_max[self.selafinlayer.hydrauparser.parametrevy][pos_vmax] = var[
                            self.selafinlayer.hydrauparser.parametrevy
                        ][pos_vmax]

            if (
                self.selafinlayer.hydrauparser.parametrevx != None
                and self.selafinlayer.hydrauparser.parametrevy != None
                and (self.intensite or self.direction)
            ):
                u = var_max[self.selafinlayer.hydrauparser.parametrevx]
                v = var_max[self.selafinlayer.hydrauparser.parametrevy]
                if self.intensite:
                    val_intensite = np.power(np.power(u, 2) + np.power(v, 2), 0.5)
                    var_max = np.vstack((var_max, val_intensite))

                if self.direction:
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

            if self.submersion > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                var_sub = np.nan_to_num(var_sub)
                var_max = np.vstack((var_max, var_sub))
            if self.duree > -1 and self.selafinlayer.hydrauparser.parametreh != None:
                var_max = np.vstack((var_max, var_dur))

            ## Ecriture des valeurs max dans le fichier de sortie (on met un temps à 0 dans le fichier)
            resOut.writeVariables(0.0, var_max)

            resOut.close()

            self.finished.emit(self.name_res_out)

        except Exception as e:
            self.status.emit("getmax error : " + str(e))
            resIn.close()
            resOut.close()

    status = pyqtSignal(str)
    finished = pyqtSignal(str)


class initRunGetMax(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = QThread()
        self.worker = None

    def start(self, selafinlayer, tool, intensite, direction, submersion, duree):
        # Launch worker
        self.worker = runGetMax(selafinlayer, tool, intensite, direction, submersion, duree)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.writeOutput)
        self.worker.finished.connect(self.workerFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def writeOutput(self, str1):
        self.status.emit(str(str1))

    def workerFinished(self, str1):
        self.finished1.emit(str1)

    status = pyqtSignal(str)
    finished1 = pyqtSignal(str)
