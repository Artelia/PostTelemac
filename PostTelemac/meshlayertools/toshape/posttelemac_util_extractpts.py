"""
Versions :
0.0 premier script
0.2 : un seul script pour modeleur ou non

"""

# unicode behaviour
from __future__ import unicode_literals

from qgis.PyQt.QtCore import QObject, QThread, QVariant, pyqtSignal

from qgis.core import (
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

import time
import os
import sys
import math
import numpy as np

import matplotlib.pyplot as plt

from ...meshlayerparsers.posttelemac_selafin_parser import *


def isFileLocked(file, readLockCheck=False):
    """
    Checks to see if a file is locked. Performs three checks
        1. Checks if the file even exists
        2. Attempts to open the file for reading. This will determine if the file has a write lock.
            Write locks occur when the file is being edited or copied to, e.g. a file copy destination
        3. If the readLockCheck parameter is True, attempts to rename the file. If this fails the
            file is open by some other process for reading. The file can be read, but not written to
            or deleted.
    @param file:
    @param readLockCheck:
    """
    if not (os.path.exists(file)):
        return False
    try:
        f = open(file, "r")
        f.close()
    except IOError:
        return True

    if readLockCheck:
        lockFile = file + ".lckchk"
        if os.path.exists(lockFile):
            os.remove(lockFile)
        try:
            os.rename(file, lockFile)
            time.sleep(1)
            os.rename(lockFile, file)
        except WindowsError:
            return True

    return False


# *************************************************************************


class SelafinContour2Pts(QObject):

    # def __init__(self, donnees_d_entree):
    def __init__(
        self,
        processtype,  # 0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
        meshlayer,
        time,  # time to process (selafin time in interation if int, or second if str)
        spacestep,  # space step
        computevelocity,  # bool for comuting velocity
        paramvx,
        paramvy,
        ztri,  # tab of values
        selafincrs,  # selafin crs
        translatex=0,
        translatey=0,
        selafintransformedcrs=None,  # if no none, specify crs of output file
        outputshpname=None,  # change generic outputname to specific one
        outputshppath=None,  # if not none, create shp in this directory
        outputprocessing=None,
    ):  # needed for toolbox processing

        QObject.__init__(self)

        self.traitementarriereplan = processtype

        # données delafin
        self.meshlayer = meshlayer
        self.parserhydrau = self.meshlayer.hydrauparser
        slf = self.parserhydrau.hydraufile
        self.x, self.y = self.parserhydrau.getFacesNodes()
        #self.x = self.x + translatex
        #self.y = self.y + translatey
        self.mesh = np.array(self.parserhydrau.getElemFaces())

        self.time = time
        self.pasespace = spacestep
        self.computevelocity = computevelocity
        self.paramvalueX = paramvx
        self.paramvalueY = paramvy
        self.ztri = ztri

        self.crs = selafincrs

        # donnees shp - outside qgis
        if not outputshpname:
            outputshpname = os.path.basename(os.path.normpath(self.meshlayer.hydraufilepath)).split(".")[0] + "_point" + str(".shp")
        else:
            outputshpname = (
                os.path.basename(os.path.normpath(self.meshlayer.hydraufilepath)).split(".")[0]
                + "_"
                + str(outputshpname)
                + str(".shp")
            )

        if not outputshppath:
            outputshppath = os.path.dirname(os.path.normpath(self.meshlayer.hydraufilepath))

        self.pathshp = os.path.join(outputshppath, outputshpname)

        # Fields creation
        tabparam = []
        fields = QgsFields()
        paramsname = [param[0] for param in self.parserhydrau.getVarNames()]
        for i, name in enumerate(paramsname):
            self.writeOutput("Initialisation - Variable dans le fichier res : " + name.strip())
            tabparam.append([i, name.strip()])
            fields.append(QgsField(str(name.strip()), QVariant.Double))
        self.vlayer = ""
        self.vitesse = "0"

        if self.computevelocity:
            fields.append(QgsField("UV", QVariant.Double))
            fields.append(QgsField("VV", QVariant.Double))
            fields.append(QgsField("norme", QVariant.Double))
            fields.append(QgsField("angle", QVariant.Double))
            self.vitesse = "1"

        if self.traitementarriereplan == 0 or self.traitementarriereplan == 2:
            # writer for shapefile
            self.writerw1 = None
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "utf-8"
            self.writerw1 = QgsVectorFileWriter.create(
                fileName=self.pathshp,
                fields=fields,
                geometryType=QgsWkbTypes.Point,
                srs=QgsCoordinateReferenceSystem(str(self.crs)),
                transformContext=QgsCoordinateTransformContext(),
                options=options,
            )

    def run(self):
        strtxt = (
            "Thread - repertoire : " + os.path.dirname(self.pathshp) + " - fichier : " + os.path.basename(self.pathshp)
        )
        self.writeOutput(strtxt)

        fet = QgsFeature()

        try:
            if self.paramvalueX == None:
                boolvitesse = False
            else:
                boolvitesse = True

            if self.pasespace == 0:
                noeudcount = len(self.x)

                strtxt = str("Thread - Traitement des points - " + str(noeudcount) + " noeuds")
                self.writeOutput(strtxt)

                for k in range(len(self.x)):
                    if k % 5000 == 0:
                        strtxt = str("Thread - noeud n " + str(k) + "/" + str(noeudcount))
                        self.writeOutput(strtxt)
                    
                    fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(self.x[k]), float(self.y[k]))))

                    tabattr = []

                    if len(self.ztri) > 0:
                        for l in range(len(self.ztri)):
                            tabattr.append(float(self.ztri[l][k]))

                    if boolvitesse:
                        norme = (
                            (float(self.ztri[self.paramvalueX][k])) ** 2.0
                            + (float(self.ztri[self.paramvalueY][k])) ** 2.0
                        ) ** (0.5)
                        atanUVVV = math.atan2(
                            float(self.ztri[self.paramvalueY][k]), float(self.ztri[self.paramvalueX][k])
                        )

                        angle = atanUVVV / math.pi * 180.0
                        if angle < 0:
                            angle = angle + 360

                        tabattr.append(float(self.ztri[self.paramvalueX][k]))
                        tabattr.append(float(self.ztri[self.paramvalueY][k]))
                        tabattr.append(norme)
                        tabattr.append(angle)

                    fet.setAttributes(tabattr)

                    if self.traitementarriereplan == 0 or self.traitementarriereplan == 2:
                        self.writerw1.addFeature(fet)
                    if self.traitementarriereplan == 1 or self.traitementarriereplan == 2:
                        self.writerw2.addFeature(fet)

        except Exception as e:
            strtxt = str("************ PROBLEME CALCUL DES VITESSES : " + str(e))
            self.writeOutput(strtxt)

        if self.traitementarriereplan == 0 or self.traitementarriereplan == 2:
            del self.writerw1
        if self.traitementarriereplan == 1 or self.traitementarriereplan == 2:
            del self.writerw2

        strtxt = str("Thread - fichier " + self.pathshp + " crée")
        self.writeOutput(strtxt)

        if self.traitementarriereplan == 0:
            self.finished.emit(self.pathshp)
        if self.traitementarriereplan == 2:
            t = workerFinished(self.pathshp)

    def writeOutput(self, str1):
        if self.traitementarriereplan in [0, 1, 2, 3]:
            self.status.emit(str(str1))
        elif self.traitementarriereplan == 4:
            print(str1)

    def raiseError(self, str1):
        self.error.emit(str(str1))

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    killed = pyqtSignal()
    finished = pyqtSignal(str)


# ****************************************************************************
# *************** Classe de lancement du thread ***********************************
# ****************************************************************************


class InitSelafinMesh2Pts(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = QThread()
        self.worker = None

    def start(
        self,
        processtype,  # 0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
        meshlayer,
        time,  # time to process (selafin time in interation if int, or second if str)
        spacestep,  # space step
        computevelocity,  # bool for comuting velocity
        paramvx,
        paramvy,
        ztri,  # tab of values
        selafincrs,  # selafin crs
        translatex=0,
        translatey=0,
        selafintransformedcrs=None,  # if no none, specify crs of output file
        outputshpname=None,  # change generic outputname to specific one
        outputshppath=None,  # if not none, create shp in this directory
        outputprocessing=None,
    ):  # needed for toolbox processing

        self.processtype = processtype
        self.meshlayer = meshlayer
        self.parserhydrau = self.meshlayer.hydrauparser

        # check time
        times = self.parserhydrau.getTimes()
        if isinstance(time, int):  # cas des plugins et scripts
            if not time in range(len(times)):
                self.raiseError("Time non trouve dans  " + str(times))
        elif isinstance(time, str):  # cas de la ligne de commande python - utilise time en s
            if time in times:
                time = list(times).index(int(time))
            else:
                self.raiseError("Time non trouve dans  " + str(times))

        self.worker = SelafinContour2Pts(
            processtype,
            meshlayer,
            time,
            spacestep,
            computevelocity,
            paramvx,
            paramvy,
            ztri,
            selafincrs,
            translatex=translatex,
            translatey=translatey,
            selafintransformedcrs=selafintransformedcrs,
            outputshpname=outputshpname,
            outputshppath=outputshppath,
            outputprocessing=outputprocessing,
        )

        if processtype in [0, 1]:
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.status.connect(self.writeOutput)
            self.worker.error.connect(self.raiseError)
            self.worker.finished.connect(self.workerFinished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(self.thread.quit)
            self.thread.start()
        else:
            self.worker.createShp()

    def raiseError(self, str):
        if self.processtype == 0:
            self.error.emit(str)
        elif self.processtype in [1, 2, 3]:
            pass
        elif self.processtype == 4:
            print(str)
            sys.exit(0)

    def writeOutput(self, str1):
        self.status.emit(str(str1))

    def workerFinished(self, str1):
        self.finished1.emit(str(str1))

    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished1 = pyqtSignal(str)
