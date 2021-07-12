# unicode behaviour
from __future__ import unicode_literals

# import PyQT
from qgis.PyQt.QtCore import QObject, QThread, QVariant, pyqtSignal

# Qgis
from qgis.core import (
    QgsFields,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsProject,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)

# imports divers
import time
import threading
import numpy as np
import math
import os
import sys


from ...meshlayerparsers.posttelemac_selafin_parser import *

debug = False

# *************************************************************************


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


# def workerFinished(str1):
#    vlayer = QgsVectorLayer(str1, os.path.basename(str1).split(".")[0], "ogr")
#    QgsMapLayerRegistry.instance().addMapLayer(vlayer)


# *********************************************************************************************
# *************** Classe de traitement **********************************************************
# ********************************************************************************************


class SelafinContour2Shp(QObject):
    def __init__(
        self,
        processtype,  # 0 : thread inside qgis plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
        meshlayer,
        time,  # time to process (selafin time in iteration)
        parameter,  # parameter to process name (string) or id (int)
        facteurz=None,  # z amplify
        azimuth=None,  # azimuth for hillshade
        zenith=None,  # zenith for hillshade
        selafincrs="EPSG:2154",  # selafin crs
        translatex=0,
        translatey=0,
        selafintransformedcrs=None,  # if no none, specify crs of output file
        outputshpname=None,  # change generic outputname to specific one
        outputshppath=None,  # if not none, create shp in this directory
        outputprocessing=None,
    ):  # case of use in modeler

        QObject.__init__(self)
        # donnees process
        self.processtype = processtype
        # données delafin
        self.meshlayer = meshlayer
        self.parserhydrau = self.meshlayer.hydrauparser
        slf = self.parserhydrau.hydraufile
        self.slf_x, self.slf_y = self.parserhydrau.getFacesNodes()
        #self.slf_x = self.slf_x + translatex
        #self.slf_y = self.slf_y + translatey

        self.slf_mesh = np.array(self.parserhydrau.getElemFaces())
        slf_time = [time, self.parserhydrau.getTimes()[time]]

        if parameter is not None:
            self.slf_param = [parameter, self.parserhydrau.getVarNames()[parameter]]
            self.slf_value = slf.getVALUES(slf_time[0])[self.slf_param[0]]
        else:
            self.slf_value = None

        # donnees shp
        champs = QgsFields()
        if self.slf_value is not None:
            self.facteurz_si_hillshade = facteurz
            self.azimuth_rad = float(azimuth) / 180.0 * math.pi
            self.zenith_rad = float(zenith) / 180.0 * math.pi
            champs.append(QgsField("slope", QVariant.Double))
            champs.append(QgsField("aspect", QVariant.Double))
            champs.append(QgsField("hillshade", QVariant.Double))

        # donnees shp - outside qgis
        if not outputshpname:
            outputshpname = os.path.basename(os.path.normpath(self.meshlayer.hydraufilepath)).split(".")[0] + "_mesh" + str(".shp")
        else:
            outputshpname = (
                os.path.basename(os.path.normpath(self.meshlayer.hydraufilepath)).split(".")[0]
                + "_"
                + str(outputshpname)
                + str(".shp")
            )
        if not outputshppath:
            outputshppath = os.path.dirname(os.path.normpath(self.meshlayer.hydraufilepath))
        self.outputshpfile = os.path.join(outputshppath, outputshpname)

        if isFileLocked(self.outputshpfile, True):
            self.raiseError("Initialisation - Erreur : Fichier shape deja charge !!")

        self.slf_crs = selafincrs
        if selafintransformedcrs:
            self.slf_shpcrs = selafintransformedcrs
            self.xform = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(str(self.slf_crs)),
                QgsCoordinateReferenceSystem(str(self.slf_shpcrs)),
                QgsProject.instance(),
            )
        else:
            self.slf_shpcrs = self.slf_crs
            self.xform = None

        if self.processtype in [0, 1, 3, 4]:
            # writer for shapefile
            self.writerw_shp = None
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "utf-8"
            self.writerw_shp = QgsVectorFileWriter.create(
                fileName=self.outputshpfile,
                fields=champs,
                geometryType=QgsWkbTypes.MultiPolygon,
                srs=QgsCoordinateReferenceSystem(self.slf_shpcrs),
                transformContext=QgsCoordinateTransformContext(),
                options=options,
            )

        # donnees shp - processing result
        try:
            if self.processtype in [2, 3]:
                self.writerw_process = VectorWriter(
                    outputprocessing,
                    None,
                    champs,
                    QGis.WKBMultiPolygon,
                    QgsCoordinateReferenceSystem(str(self.slf_shpcrs)),
                    "ESRI Shapefile",
                )
        except Exception as e:
            pass

    def get_slope_azi(self, geom, z1, z2, z3, facteurz_si_hillshade):
        zfactor = facteurz_si_hillshade
        p = []
        p.append([geom.asPolygon()[0][0][0], geom.asPolygon()[0][0][1], z1])
        p.append([geom.asPolygon()[0][1][0], geom.asPolygon()[0][1][1], z2])
        p.append([geom.asPolygon()[0][2][0], geom.asPolygon()[0][2][1], z3])

        a = [p[1][0] - p[0][0], p[1][1] - p[0][1], zfactor * (p[1][2] - p[0][2])]
        b = [p[2][0] - p[0][0], p[2][1] - p[0][1], zfactor * (p[2][2] - p[0][2])]

        norm = np.cross(a, b)

        slope = math.acos(norm[2] / np.linalg.norm(norm))

        if slope != 0:
            asptemp = math.atan2(norm[1], norm[0])
            if asptemp < 0:
                asptemp = asptemp + 2.0 * math.pi
        else:
            asptemp = math.pi / 2.0

        return [slope, asptemp]

    def createShp(self):
        # ******** Informations de lancement de la tache  *****************************************************
        fet = QgsFeature()
        strtxt = str("Création shapefile :" + "\n" + str(self.outputshpfile))
        self.writeOutput(strtxt)
        nombre = len(self.slf_mesh)

        for i in range(len(self.slf_mesh)):
            if i % 5000 == 0:
                strtxt = str("Thread element n " + str(i) + "/" + str(nombre))
                self.writeOutput(strtxt)

            geom = []

            geom.append(QgsPointXY(self.slf_x[self.slf_mesh[i][0]], self.slf_y[self.slf_mesh[i][0]]))
            geom.append(QgsPointXY(self.slf_x[self.slf_mesh[i][1]], self.slf_y[self.slf_mesh[i][1]]))
            geom.append(QgsPointXY(self.slf_x[self.slf_mesh[i][2]], self.slf_y[self.slf_mesh[i][2]]))
            f1geom = QgsGeometry.fromPolygonXY([geom])
            if self.xform:
                f1geom.transform(self.xform)
            fet.setGeometry(f1geom)

            if self.slf_value is not None:
                z1 = float(self.slf_value[self.slf_mesh[i][0]])
                z2 = float(self.slf_value[self.slf_mesh[i][1]])
                z3 = float(self.slf_value[self.slf_mesh[i][2]])

                tab = self.get_slope_azi(f1geom, z1, z2, z3, self.facteurz_si_hillshade)
                Hillshade = max(
                    0,
                    255.0
                    * (
                        (math.cos(self.zenith_rad) * math.cos(tab[0]))
                        + (math.sin(self.zenith_rad) * math.sin(tab[0]) * math.cos(self.azimuth_rad - tab[1]))
                    ),
                )

                fet.setAttributes([z1, z2, z3, tab[0], tab[1], Hillshade])
                if self.slf_value is not None:
                    fet.setAttributes([tab[0], tab[1], Hillshade])

            if self.processtype in [0, 1, 3, 4]:
                self.writerw_shp.addFeature(fet)
            if self.processtype in [2, 3]:
                self.writerw_process.addFeature(fet)

        if self.processtype in [0, 1, 3, 4]:
            del self.writerw_shp
        if self.processtype in [2, 3]:
            del self.writerw_process

        # Emit finish
        if self.processtype in [0, 1]:
            self.finished.emit(self.outputshpfile)
        if self.processtype in [2, 3]:
            t = workerFinished(self.outputshpfile)
        if self.processtype in [4]:
            self.writeOutput("Process finished - " + str(self.outputshpfile))

    def verboseOutput(self, param, lvl, geomelem=None, geomtot=None, ileelem=None, iletot=None):
        strtxt = str(param) + " - lvl : " + str(lvl)
        if geomelem:
            strtxt = strtxt + " - geom : " + str(geomelem) + "/" + str(geomtot)
        if ileelem:
            strtxt = strtxt + " - ring : " + str(ileelem) + "/" + str(iletot)
        self.writeOutput(strtxt)

    def writeOutput(self, str1):
        if self.processtype in [0, 1, 2, 3]:
            self.status.emit(str(str1))
        elif self.processtype == 4:
            print(str1)

    def raiseError(self, str1):
        self.error.emit(str(str1))

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    killed = pyqtSignal()
    finished = pyqtSignal(str)


# *********************************************************************************************
# *************** Classe de lancement du thread **********************************************************
# ********************************************************************************************


class InitSelafinMesh2Shp(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = QThread()
        self.worker = None

    def start(
        self,
        processtype,  # 0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
        meshlayer,
        time,  # time to process (selafin time in interation if int, or second if str)
        parameter=None,  # parameter to process name (string) or id (int) for hillsahde, none if not hillshade
        facteurz=None,  # z amplify
        azimuth=None,  # azimuth for hillshade
        zenith=None,  # zenith for hillshade
        selafincrs="EPSG:2154",  # selafin crs
        translatex=0,
        translatey=0,
        selafintransformedcrs=None,  # if no none, specify crs of output file
        outputshpname=None,  # change generic outputname to specific one
        outputshppath=None,  # if not none, create shp in this directory
        outputprocessing=None,
    ):  # needed for toolbox processing

        # Check validity
        self.processtype = processtype
        self.meshlayer = meshlayer
        parserhydrau = self.meshlayer.hydrauparser
        times = parserhydrau.getTimes()
        if isinstance(time, int):  # cas des plugins et scripts
            if not time in range(len(times)):
                self.raiseError("Time non trouve dans  " + str(times))
        elif isinstance(time, str):  # cas de la ligne de commande python - utilise time en s
            if time in times:
                time = list(times).index(int(time))
            else:
                self.raiseError("Time non trouve dans  " + str(times))

        if parameter is not None:
            parameters = [param[0] for param in parserhydrau.getVarNames()]
            if not parameter.isdigit():
                if parameter in parameters:
                    parameter = parameters.index(parameter)
                else:
                    self.raiseError(str(parameter) + " parameter pas trouve dans " + str(parameters))
            else:
                parameter = int(parameter)

        self.worker = SelafinContour2Shp(
            processtype,
            meshlayer,
            time,
            parameter,
            facteurz=facteurz,
            azimuth=azimuth,
            zenith=zenith,
            selafincrs=selafincrs,
            translatex=translatex,
            translatey=translatey,
            selafintransformedcrs=selafintransformedcrs,
            outputshpname=outputshpname,
            outputshppath=outputshppath,
            outputprocessing=outputprocessing,
        )

        if processtype in [0, 1]:
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.createShp)
            self.worker.status.connect(self.writeOutput)
            self.worker.error.connect(self.raiseError)
            self.worker.finished.connect(self.workerFinished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.finished.connect(self.thread.quit)
            champ = QgsFields()
            if processtype in [1]:
                writercontour = VectorWriter(
                    outputprocessing, None, champ, QGis.WKBMultiPolygon, QgsCoordinateReferenceSystem(str(selafincrs))
                )
            self.thread.start()
        else:
            self.worker.createShp()

    def raiseError(self, str):
        if self.processtype == 0:
            self.error.emit(str)
        elif self.processtype in [1, 2, 3]:
            if sys.version_info.major == 2:
                raise GeoAlgorithmExecutionException(str)
            elif sys.version_info.major == 3:
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


if __name__ == "__main__":
    qgishome = os.environ["QGIS_PREFIX_PATH"]
    app = QgsApplication([], True)
    QgsApplication.setPrefixPath(qgishome, True)
    QgsApplication.initQgis()
    print(len(sys.argv[1:]))

    initclass = InitSelafinContour2Shp()

    if len(sys.argv[1:]) == 3:
        traitement = initclass.start(
            4,  # type de traitement
            sys.argv[1],  # path to selafin file
            sys.argv[2],  # time of selafin file
            str(sys.argv[3]),
        )  # name or id of the parametre if hillshade else None

    if len(sys.argv[1:]) == 4:
        traitement = initclass.start(
            4,  # type de traitement
            sys.argv[1],  # path to selafin file
            sys.argv[2],  # time of selafin file
            str(sys.argv[3]),  # name or id of the parametre if hillshade else None
            5,
            0,
            30,
            str(sys.argv[4]),
        )  # selafin crs

    if len(sys.argv[1:]) == 5:
        traitement = initclass.start(
            4,  # type de traitement
            sys.argv[1],  # path to selafin file
            sys.argv[2],  # time of selafin file
            str(sys.argv[3]),  # name or id of the parametre if hillshade else None
            5,
            0,
            30,
            str(sys.argv[4]),  # selafin crs
            str(sys.argv[5]),
        )  # outputshpcrs
