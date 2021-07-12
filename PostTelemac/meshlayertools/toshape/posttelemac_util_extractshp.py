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
    QgsVectorLayer,
    QgsSpatialIndex,
)

# import numpy
import numpy as np

# import matplotlib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


# imports divers
import time
import math
import sys
import os

# shapely
try:
    from shapely import *
    from shapely.geometry import Polygon
    from shapely.wkb import loads
except Exception as e:
    print(e)

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
        levels,  # levels to create
        selafincrs="EPSG:2154",  # selafin crs
        translatex=0,
        translatey=0,
        selafintransformedcrs=None,  # if no none, specify crs of output file
        quickprocessing=False,  # quickprocess option - don't make ring
        outputshpname=None,  # change generic outputname to specific one
        outputshppath=None,  # if not none, create shp in this directory
        forcedvalue=None,  # force value for plugin
        outputprocessing=None,
    ):  # case of use in modeler

        QObject.__init__(self)
        # données process
        self.processtype = processtype
        self.quickprocessing = quickprocessing
        # données delafin
        self.meshlayer = meshlayer
        self.parserhydrau = self.meshlayer.hydrauparser
        slf = self.parserhydrau.hydraufile
        self.slf_x, self.slf_y = self.parserhydrau.getFacesNodes()
        # self.slf_x = self.slf_x + translatex
        # self.slf_y = self.slf_y + translatey

        self.slf_mesh = np.array(self.parserhydrau.getElemFaces())

        if self.processtype == 0:
            self.slf_param = [parameter, parameter]
        else:
            self.slf_param = [parameter, self.parserhydrau.getVarNames()[parameter].strip()]

        slf_time = [time, self.parserhydrau.getTimes()[time]]

        if forcedvalue is None:
            self.slf_value = self.parserhydrau.getValues(slf_time[0])[self.slf_param[0]]
        else:
            self.slf_value = forcedvalue

        # donnees shp
        champs = QgsFields()
        champs.append(QgsField("min", QVariant.Double))
        champs.append(QgsField("max", QVariant.Double))
        if self.quickprocessing:
            champs.append(QgsField("int", QVariant.String))

        # donnees shp - outside qgis
        if not outputshpname:
            outputshpname = (
                os.path.basename(os.path.normpath(self.meshlayer.hydraufilepath)).split(".")[0]
                + "_"
                + str(self.slf_param[1]).translate(None, "?,!.;")
                + "_t_"
                + str(slf_time[1])
                + str(".shp")
            )
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
                QgsCoordinateReferenceSystem(str(self.slf_crs)), QgsCoordinateReferenceSystem(str(self.slf_shpcrs))
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

        self.levels = levels

    def createShp(self):

        # ******** Informations de lancement de la tache  *****************************************************
        fet = QgsFeature()

        self.writeOutput("Creation shapefile : " + str(self.outputshpfile))

        # ******** Iteration sur les  niveaux *******************************************************************
        for lvl in range(len(self.levels) - 1):
            level = [self.levels[lvl], self.levels[lvl + 1]]

            self.writeOutput(str(self.slf_param[1]) + " - level : " + str(level) + " - Matplotlib integration")

            # l'outil de matplotlib qui cree la triangulation
            triplotcontourf = plt.tricontourf(
                self.slf_x,
                self.slf_y,
                self.slf_mesh,
                self.slf_value,
                level,
            )

            # Iteration sur les contours fournis par triplotcontourf  et inclusion des outers et inners dans une table temporaire
            vlOuterTemp, vlInnerTemp, vlInnerTempIndex = self.createInnerOutertempLayer(triplotcontourf)

            # Debut du traitement des iles
            self.writeOutput(str(self.slf_param[1]) + " - level : " + str(level) + " - Ring process")

            FeatsInnerTemp = {feature.id(): feature for (feature) in vlInnerTemp.getFeatures()}
            # creation d'un index spatial des inners pour aller plus vite
            map(vlInnerTempIndex.insertFeature, FeatsInnerTemp.values())

            if self.quickprocessing:
                for inner in vlInnerTemp.getFeatures():
                    fet.setGeometry(inner.geometry())
                    fet.setAttributes([level[0], level[1], "False"])

                    if self.processtype in [0, 2]:
                        self.writerw_shp.addFeature(fet)
                    if self.processtype in [1, 2]:
                        self.writerw_process.addFeature(fet)

                for outer in vlOuterTemp.getFeatures():
                    fet.setGeometry(outer.geometry())
                    fet.setAttributes([level[0], level[1], "True"])

                    if self.processtype in [0, 2]:
                        self.writerw_shp.addFeature(fet)
                    if self.processtype in [1, 2]:
                        self.writerw_process.addFeature(fet)

            else:
                counttotal = int(vlOuterTemp.featureCount())
                # Iteration sur tous les outer
                for outer in vlOuterTemp.getFeatures():
                    if int(outer.id()) % 50 == 0:
                        self.verboseOutput(self.slf_param[1], level, outer.id(), counttotal)

                    fet = self.InsertRinginFeature(outer, FeatsInnerTemp, vlInnerTempIndex, level, counttotal)

                    if self.processtype in [0, 1, 3, 4]:
                        self.writerw_shp.addFeature(fet)
                    if self.processtype in [2, 3]:
                        self.writerw_process.addFeature(fet)

        # Clear things
        vlInnerTemp = None
        vlOuterTemp = None
        vlInnerTempIndex = None
        pr1 = None
        pr2 = None

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

    def verboseOutput(self, param, level, geomelem=None, geomtot=None, ileelem=None, iletot=None):
        strtxt = str(param) + " - level : " + str(level)
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

    def createInnerOutertempLayer(self, triplotcontourf):
        fet = QgsFeature()

        for collection in triplotcontourf.collections:
            vl1temp1 = QgsVectorLayer("Multipolygon?crs=" + str(self.slf_crs), "temporary_poly_outer ", "memory")
            pr1 = vl1temp1.dataProvider()
            vl1temp1.startEditing()

            vl2temp1 = QgsVectorLayer("Multipolygon?crs=" + str(self.slf_crs), "temporary_poly_inner ", "memory")
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

    def InsertRinginFeature(self, outer, FeatsInnerTemp, vlInnerTempIndex, lvltemp1, counttotal):
        # Correction des erreurs de geometrie des outers
        if len(outer.geometry().validateGeometry()) != 0:
            outergeom = outer.geometry().buffer(0.01, 5)

            if outergeom.area() < outer.geometry().area():
                outergeom = outer.geometry()
                self.writeOutput("Warning : geometry " + str(outer.id()) + " not valid before inserting rings")
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
                f2geom = f2geom.buffer(0.01, 5)
            tab.append([f2geom.area(), f2geom])

        if len(tab) > 0:
            tab.sort(reverse=True, key=lambda area: area[0])
            # Iteration pour enlever les inner des outers - coeur du script
            for k in range(len(tab)):
                try:
                    if int(k) % 100 == 0 and k != 0:
                        self.verboseOutput(self.slf_param[1], lvltemp1, outer.id(), counttotal, k, len(ids))
                    if tab[k][0] >= fet1surface:
                        continue
                    else:
                        ring = self.do_ring(tab[k][1])
                        tt1 = outergeom.addRing(ring)
                        if tt1 == 5 and outergeom.intersects(tab[k][1]):
                            outergeom = outergeom.difference(tab[k][1])
                except Exception as e:
                    self.writeOutput("Erreur creation ring : " + str(e))
                    return outer

        if len(outergeom.validateGeometry()) != 0:
            outergeomtemp = outergeom.buffer(0.01, 5)
            if outergeomtemp.area() > outergeom.area():
                outergeom = outergeomtemp
            else:
                self.writeOutput("Warning : geometry " + str(outer.id()) + " not valid after inserting rings")

        if self.xform:
            outergeom.transform(self.xform)

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

    def repairPolygon(self, geometry):
        buffer_worker = True
        try:
            geometry = geometry.buffer(0)
        except:
            buffer_worker = False

        if buffer_worker:
            return geometry

        polygons = []
        if geometry.geom_type == "Polygon":
            polygons.append(geometry)
        elif geometry.geom_type == "MultiPolygon":
            polygons.extend(geometry.geoms)

        fixed_polygons = []
        for n, polygon in enumerate(polygons):
            if not self.linear_ring_is_valid(polygon.exterior):
                continue  # "unable to fix"

            interiors = []
            for ring in polygon.interiors:
                if self.linear_ring_is_valid(ring):
                    interiors.append(ring)

            fixed_polygon = shapely.geometry.Polygon(polygon.exterior, interiors)

            try:
                fixed_polygon = fixed_polygon.buffer(0)
            except:
                continue

            if fixed_polygon.geom_type == "Polygon":
                fixed_polygons.append(fixed_polygon)
            elif fixed_polygon.geom_type == "MultiPolygon":
                fixed_polygons.extend(fixed_polygon.geoms)

        if len(fixed_polygons) > 0:
            return shapely.geometry.MultiPolygon(fixed_polygons)
        else:
            return None

    def linear_ring_is_valid(self, ring):
        points = set()
        for x, y in ring.coords:
            points.add((x, y))
        if len(points) < 3:
            return False
        else:
            return True

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    killed = pyqtSignal()
    finished = pyqtSignal(str)


# *********************************************************************************************
# *************** Classe de lancement du thread **********************************************************
# ********************************************************************************************


class InitSelafinContour2Shp(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.thread = QThread()
        self.worker = None

    def start(
        self,
        processtype,  # 0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
        meshlayer,
        time,  # time to process (selafin time in seconds if exist else iteration number)
        parameter,  # parameter to process name (string) or id (int)
        levels,  # levels to create
        selafincrs="EPSG:2154",  # selafin crs
        translatex=0,
        translatey=0,
        selafintransformedcrs=None,  # if no none, specify crs of output file
        quickprocessing=False,  # quickprocess option - don't make ring
        outputshpname=None,  # change generic outputname to specific one
        outputshppath=None,  # if not none, create shp in this directory
        forcedvalue=None,  # force value for plugin
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

        parameters = [str(parserhydrau.getVarNames()[i]).strip() for i in range(len(parserhydrau.getVarNames()))]
        if not parameter.isdigit():
            if parameter in parameters:
                parameter = parameters.index(parameter)
            else:
                if not self.processtype == 0:
                    self.raiseError(str(parameter) + " parameter pas trouve dans " + str(parameters))

        # Launch worker
        self.worker = SelafinContour2Shp(
            processtype,
            meshlayer,
            time,
            parameter,
            levels,
            selafincrs,
            translatex=translatex,
            translatey=translatey,
            selafintransformedcrs=selafintransformedcrs,
            quickprocessing=quickprocessing,
            outputshpname=outputshpname,
            outputshppath=outputshppath,
            forcedvalue=forcedvalue,
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
