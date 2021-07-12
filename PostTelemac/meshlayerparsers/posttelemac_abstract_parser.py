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
 Propertiy dialog class
 
Versions :
0.0 : debut

 ***************************************************************************/
"""
from __future__ import unicode_literals

from qgis.PyQt.QtCore import QObject, pyqtSignal

from numpy import sin, cos, abs
import numpy as np
import time
import numbers
import os
import sys
import qgis

try:
    from scipy.spatial import cKDTree
    SCIPYOK = True
except:
    SCIPYOK = False
# force desactivate scipy
# SCIPYOK = False

try:
    import matplotlib.tri
    MATPLOTLIBTRIOK = True
except:
    MATPLOTLIBTRIOK = False

if MATPLOTLIBTRIOK:
    from matplotlib.tri import LinearTriInterpolator
    from matplotlib.tri import Triangulation

try:
    import networkx as nx
    NETWORKXOK = True
except:
    NETWORKXOK = False


class PostTelemacAbstractParser(QObject):

    emitMessage = pyqtSignal(str)
    updateinterplator = pyqtSignal(int)

    def __init__(self, virtualparamtoloadoninit=None):
        super(QObject, self).__init__()
        self.virtualparamtoloadoninit = virtualparamtoloadoninit
        self.path = None
        self.hydraufile = None
        self.elemcount = None
        self.facesnodescount = None
        self.facescount = None
        self.itertimecount = None
        self.skdtreeelemnode = None
        self.skdtreefacenode = None
        self.facesindex = None
        self.elemfacesindex = None
        self.triangulation = None
        self.triangulationisvalid = [False, None]
        self.interpolator = None
        self.trifind = None
        self.parametres = None  # [...,[0 : index, 1 : name, 2 : parametertype, 3 : rawindex, 4 : formula or None, 5 : index od compared param], ...]   - typevar (0 : elem, 1 : facenode, 2 : face)]
        self.parametrev = None
        self.parametrevx = None  # specific num for velolity x parameter
        self.parametrevy = None
        self.parametreh = None
        self.paramfreesurface = None
        self.parambottom = None
        self.networkxgraph = None
        self.translatex = 0
        self.translatey = 0

        # connexion
        self.updateinterplator.connect(self.updateInterpolator)

    # ****************************************************************************************
    # ******************  functions to be completed      *************************************
    # ****************************************************************************************

    def setXYTranslation(self, xtransl, ytransl):
        self.translatex = xtransl
        self.translatey = ytransl

        if SCIPYOK:
            self.initCkdTree()

    def initPathDependantVariablesWhenLoading(self):
        """
        Define at least :
            self.hydraufile
        """
        pass

    def getTimes(self):
        """
        return array of times computed
        """
        return np.array([None])

    # ****************************************************************************************
    # ****************************************************************************************
    # ****************************************************************************************

    def getVarNames(self):
        """
        return np.array[varname, typevar (0 : elem, 1 : facenode, 2 : face)]
        """
        return np.array([])

    # *********** Elems

    def getElemNodes(self):
        """
        xyz
        3T : /
        hec : Cells_Center_Coordinate

        return (np.array(x), np.array(y) )
        """
        return (np.array([]), np.array([]))

    def getElemRawValue(self, time1):
        """
        3T : /
        hec : value

        return np.array[param number][node value for param number]

        """
        return np.array([])

    def getElemRawTimeSerie(self, arraynumelemnode, arrayparam, layerparametres=None):
        """

        return np.array[param][numelem][value for time t]

        """
        return np.array([])

    # *********** Face Node

    def getFacesNodes(self):
        """
        3T : xyz
        hec : FacePoints_Coordinate

        return (np.array(x), np.array(y) )

        """
        return (np.array([]), np.array([]))

    def getElemFaces(self):
        """
        It's the mesh
        3T : ikle
        hec : Faces_FacePoint_Indexes

        return np.array([facenodeindex linked with the elem ])
        """
        return np.array([])

    def getFacesNodesRawValues(self, time1):
        """
        3T : getvalues

        return np.array[param number][node value for param number]

        """
        return np.array([])

    def getFacesNodesRawTimeSeries(self, arraynumelemnode, arrayparam, layerparametres=None):
        """
        3T : getvalues

        return np.array[param][numelem][value for time t]

        """
        return np.array([])

    # *********** Face

    def getFaces(self):
        """
        return np.array([facenodeindex linked with the face ])
        """
        return np.array([])

    def getFacesRawValues(self, time1):
        """
        3T : /
        hec : velocity
        return np.array[param number][node value for param number]

        """
        return np.array([])

    def getFacesRawTimeSeries(self, arraynumelemnode, arrayparam, layerparametres=None):
        """
        3T : /
        hec : velocity

        return np.array[param][numelem][value for time t]

        """
        return np.array([])

    def extent(self):
        x1, y1 = self.getElemNodes()
        x2, y2 = self.getFacesNodes()

        if len(x1) > 0:
            rect1 = qgis.core.QgsRectangle(float(min(x1)), float(min(y1)), float(max(x1)), float(max(y1)))
        else:
            rect1 = None

        if len(x2) > 0:
            rect2 = qgis.core.QgsRectangle(float(min(x2)), float(min(y2)), float(max(x2)), float(max(y2)))
        else:
            rect2 = None

        if rect1 and rect2:
            rect = rect1.union(rect2).boundingBox()

        else:
            if rect1:
                rect = rect1
            else:
                rect = rect2

        return rect

    def loadHydrauFile(self, path1):
        """
        Called when a mesh file is loaded
        """
        self.path = path1
        self.initPathDependantVariablesWhenLoading()
        self.initClassicThingsAndCkdTreeAndMatplotLib()

    def initClassicThingsAndCkdTreeAndMatplotLib(self):
        self.elemcount = len(self.getElemFaces())
        self.facesnodescount = len(self.getFacesNodes()[0])
        self.facescount = len(self.getFaces())
        self.itertimecount = len(self.getTimes()) - 1

        if SCIPYOK:
            self.initCkdTree()

        self.initSelafinParameters()

        if MATPLOTLIBTRIOK:
            self.createInterpolator()

    def initCkdTree(self):
        """
        xx
        self.skdtreeelemnode = None
        self.skdtreefacenode = None
        """

        if len(self.getElemNodes()[0]) > 0:
            x, y = self.getElemNodes()
            arraymesh = np.array([[x[i], y[i]] for i in range(self.elemcount)])
            self.skdtreeelemnode = cKDTree(arraymesh, leafsize=100)

        if len(self.getFacesNodes()[0]) > 0:
            x, y = self.getFacesNodes()
            arraymesh = np.array([[x[i], y[i]] for i in range(self.facesnodescount)])
            self.skdtreefacenode = cKDTree(arraymesh, leafsize=100)

    def createInterpolator(self):
        elemfaces = self.getElemFaces()

        # interpolator for triangle mesh
        if len(elemfaces) > 0 and len(elemfaces.shape) > 1 and elemfaces.shape[1] == 3:
            meshx, meshy = self.getFacesNodes()
            ikle = self.getElemFaces()
            self.triangulation = Triangulation(meshx, meshy, np.array(ikle))
            bool1, error = self.checkTriangul()

            if bool1:
                self.triangulationisvalid = [True, None]

            else:
                self.triangulationisvalid = [False, error]
                self.emitMessage.emit(
                    "Duplicated points : "
                    + str((self.triangulationisvalid[1] + 1).tolist())
                    + " - Triangulation is invalid"
                )

    def checkTriangul(self):
        import collections

        d = collections.OrderedDict()
        indexfinal = []
        x, y = self.getFacesNodes()

        p = [[x[i], y[i]] for i in range(len(x))]
        p1 = np.array(p)
        for i, a in enumerate(p1):
            t = tuple(a)
            if t in d:
                d[t] += 1
                index1 = d.keys().index(t)
                index2 = i
                indexfinal += [[index1, index2]]
            else:
                d[t] = 1

        result = []
        for (key, value) in d.items():
            result.append(list(key) + [value])

        B = np.asarray(result)
        c = np.where(B[:, 2] > 1)

        if len(c[0]) > 0:
            return False, np.array(indexfinal)
        else:
            return True, None

    def updateInterpolatorEmit(self, time1):
        self.updateinterplator.emit(time1)

    def updateInterpolator(self, time1):
        if self.triangulationisvalid[0]:
            values = self.getValues(time1)
            self.interpolator = [
                LinearTriInterpolator(self.triangulation, values[i]) for i in range(len(self.parametres))
            ]
            return True
        else:
            return False

    def initSelafinParameters(self):
        """
        Called load_selafin by when changing selafin file
        Set selafin variables
        """
        self.parametres = []

        elemparcount = 0
        facenodeparcount = 0
        faceparcount = 0
        for i, name in enumerate(self.getVarNames()):
            if int(name[1]) == 0:
                self.parametres.append([i, name[0].strip(), int(name[1]), elemparcount, None, None])
                elemparcount += 1
            elif int(name[1]) == 1:
                self.parametres.append([i, name[0].strip(), int(name[1]), facenodeparcount, None, None])
                facenodeparcount += 1
            elif int(name[1]) == 2:
                self.parametres.append([i, name[0].strip(), int(name[1]), faceparcount, None, None])
                faceparcount += 1

        if self.virtualparamtoloadoninit != None:
            # case of virtual parameters when loadin a selafin layer
            if len(self.virtualparamtoloadoninit["virtual_parameters"]) > 0:
                for param in self.virtualparamtoloadoninit["virtual_parameters"]:
                    self.parametres.append([len(self.parametres), param[1], param[2], None, param[3], None])

            if self.virtualparamtoloadoninit["xtranslation"] != 0 or self.virtualparamtoloadoninit["ytranslation"] != 0:
                self.setXYTranslation(
                    self.virtualparamtoloadoninit["xtranslation"], self.virtualparamtoloadoninit["ytranslation"]
                )

        self.identifyKeysParameters()

    def initSelafinParameters2(self):
        """
        Called load_selafin by when changing selafin file
        Set selafin variables
        """
        self.parametres = []
        for i, name in enumerate(self.getVarnames()):
            self.parametres.append([i, name.strip(), None, i])

        if self.virtualparamtoloadoninit != None:
            # case of virtual parameters when loadin a selafin layer
            if len(self.virtualparamtoloadoninit["virtual_parameters"]) > 0:
                for param in self.virtualparamtoloadoninit["virtual_parameters"]:
                    self.parametres.append([len(self.parametres), param[1], param[2], len(self.parametres)])
            if self.virtualparamtoloadoninit["xtranslation"] != 0 or self.virtualparamtoloadoninit["ytranslation"] != 0:
                self.setXYTranslation(
                    self.virtualparamtoloadoninit["xtranslation"], self.virtualparamtoloadoninit["ytranslation"]
                )

        self.identifyKeysParameters()

    def identifyKeysParameters(self):
        # load velocity parameters pluginlayer
        if self.paramfreesurface == None and self.parambottom == None:
            if self.getParameterName("SURFACELIBRE") != None:
                self.paramfreesurface = self.getParameterName("SURFACELIBRE")[0]
            if self.getParameterName("BATHYMETRIE") != None:
                self.parambottom = self.getParameterName("BATHYMETRIE")[0]

        if self.parametrevx == None and self.parametrevy == None:
            if not (self.getParameterName("VITESSEU") == None and self.getParameterName("VITESSEV") == None):
                self.parametrevx = self.getParameterName("VITESSEU")[0]
                self.parametrevy = self.getParameterName("VITESSEV")[0]

        # load water depth parameters
        if self.parametreh == None:
            if self.getParameterName("HAUTEUR") == None:
                if self.getParameterName("SURFACELIBRE") != None and self.getParameterName("BATHYMETRIE") != None:
                    paramfreesurface = self.getParameterName("SURFACELIBRE")[0]
                    parambottom = self.getParameterName("BATHYMETRIE")[0]
                    self.parametreh = len(self.parametres)
                    self.parametres.append(
                        [
                            len(self.parametres),
                            "HAUTEUR D'EAU",
                            self.parametres[paramfreesurface][2],
                            None,
                            "V" + str(paramfreesurface) + " - V" + str(parambottom),
                            None,
                        ]
                    )
            else:
                self.parametreh = self.getParameterName("HAUTEUR")[0]

        if self.parametrev == None:
            if self.getParameterName("VITESSE") == None:
                if self.getParameterName("VITESSEU") != None and self.getParameterName("VITESSEV") != None:
                    paramvx = self.getParameterName("VITESSEU")[0]
                    paramvy = self.getParameterName("VITESSEV")[0]
                    self.parametrev = len(self.parametres)
                    self.parametres.append(
                        [
                            len(self.parametres),
                            "VITESSE",
                            self.parametres[paramvx][2],
                            None,
                            "(V" + str(paramvx) + "**2 + V" + str(paramvy) + "**2)**0.5",
                            None,
                        ]
                    )
            else:
                self.parametrev = self.getParameterName("VITESSE")[0]

    # ****************************************************************************************
    # ******************  Parameters and else functions  *************************************

    def getValues(self, time):
        """
        Get the values of paameters for time time

        getElemRawValue
        getFacesNodesRawValues

        typevar (0 : elem, 1 : facenode, 2 : face)]

        """
        values = []

        try:
            elemvalue = self.getElemRawValue(time)
            facenodevalues = self.getFacesNodesRawValues(time)
            facevalue = self.getFacesRawValues(time)

            for param in self.parametres:
                if param[4]:  # for virtual parameter - compute it
                    if param[2] == 0:  # elem value
                        self.dico = self.getDico(param[4], self.parametres, values, "values")
                        val = eval(param[4], {"__builtins__": None}, self.dico)
                        # elemvalue = np.vstack((elemvalue,val))
                        values.append(val)
                    elif param[2] == 1:  # face node value
                        self.dico = self.getDico(param[4], self.parametres, values, "values")
                        val = eval(param[4], {"__builtins__": None}, self.dico)
                        # facenodevalues = np.vstack((facenodevalues,val))
                        values.append(val)
                    elif param[2] == 2:  # face node value
                        self.dico = self.getDico(param[4], self.parametres, values, "values")
                        val = eval(param[4], {"__builtins__": None}, self.dico)
                        # facenodevalues = np.vstack((facenodevalues,val))
                        values.append(val)
                else:
                    if param[2] == 0:  # elem value
                        values.append(elemvalue[param[3]])
                    elif param[2] == 1:  # face node value
                        values.append(facenodevalues[param[3]])
                    elif param[2] == 2:  # face  value
                        values.append(facevalue[param[3]])
        except Exception as e:
            self.emitMessage.emit("Abstractparser - getValues : " + str(e) + str(elemvalue) + str(facenodevalues) + str(facevalue))
        return values

    def getValues2(self, time):
        """
        Get the values of paameters for time time
        """
        values = self.getRawValues(time)

        for param in self.parametres:
            if param[2]:  # for virtual parameter - compute it
                self.dico = self.getDico(param[2], self.parametres, values, "values")
                val = eval(param[2], {"__builtins__": None}, self.dico)
                values = np.vstack((values, val))
        return values

    def getTimeSerie(self, arraynumpoint, arrayparam, layerparametres=None):
        """
        Warning : point index begin at 1
        """
        DEBUG = False
        result = []
        try:
            for param in arrayparam:
                if layerparametres != None and layerparametres[param][4]:
                    dico = self.getDico(layerparametres[param][4], layerparametres, arraynumpoint, "timeseries")
                    tempordonees = eval(layerparametres[param][4], {}, dico)
                    result.append(tempordonees[0])
                else:
                    if self.parametres[param][2] == 0:  # elem value
                        if DEBUG:
                            print("getTimeSerie getElemRawTimeSerie  " + str(arraynumpoint))
                        tempordonees = self.getElemRawTimeSerie(arraynumpoint, [self.parametres[param][3]], False)
                        result.append(tempordonees[0])
                    elif self.parametres[param][2] == 1:  # face node value
                        if DEBUG:
                            print("getTimeSerie getFacesNodesRawTimeSeries")
                        tempordonees = self.getFacesNodesRawTimeSeries(
                            arraynumpoint, [self.parametres[param][3]], False
                        )
                        result.append(tempordonees[0])
                    elif self.parametres[param][2] == 2:  # face  value
                        if DEBUG:
                            print("getTimeSerie getFacesRawTimeSeries")
                        tempordonees = self.getFacesRawTimeSeries(arraynumpoint, [self.parametres[param][3]], False)
                        result.append(tempordonees[0])

        except Exception as e:
            self.emitMessage.emit("Abstractparser - getTimeSerie : " + str(e))
        return np.array(result)

    def getDico(self, expr, parametres, enumpointorvalues, type):
        dico = {}
        try:
            dico["sin"] = sin
            dico["cos"] = cos
            dico["abs"] = abs
            dico["int"] = int
            dico["if_then_else"] = self.if_then_else
            a = "V{}"
            nb_var = len(self.getElemRawValue(0)) + len(self.getFacesNodesRawValues(0))
            i = 0
            num_var = 0
            while num_var < nb_var:
                if not parametres[i][4]:
                    rawindex = parametres
                    if type == "values":
                        dico[a.format(i)] = enumpointorvalues[i]
                    elif type == "timeseries":
                        if parametres[i][2] == 0:  # elem value
                            dico[a.format(i)] = self.getElemRawTimeSerie(enumpointorvalues, [parametres[i][3]])
                        elif parametres[i][2] == 1:  # face node value
                            dico[a.format(i)] = self.getFacesNodesRawTimeSeries(enumpointorvalues, [parametres[i][3]])
                        elif parametres[i][2] == 2:  # face  value
                            dico[a.format(i)] = self.getFacesRawTimeSeries(enumpointorvalues, [parametres[i][3]])

                num_var += 1
                i += 1
        except Exception as e:
            self.emitMessage.emit("Abstractparser - getDico : " + str(e))
        return dico

    def getDico2(self, expr, parametres, enumpointorvalues, type):
        dico = {}
        try:
            dico["sin"] = sin
            dico["cos"] = cos
            dico["abs"] = abs
            dico["int"] = int
            dico["if_then_else"] = self.if_then_else
            a = "V{}"
            nb_var = len(self.getRawValues(0))
            i = 0
            num_var = 0
            while num_var < nb_var:
                if not parametres[i][2]:
                    if type == "values":
                        dico[a.format(i)] = enumpointorvalues[i]
                    elif type == "timeseries":
                        dico[a.format(i)] = self.getRawTimeSerie(enumpointorvalues, [i])
                num_var += 1
                i += 1
        except Exception as e:
            print("getdico " + str(e))
        return dico

    def if_then_else(self, ifstat, true1, false1):
        """
        Used for calculation of virtual parameters
        """
        # condition
        if isinstance(ifstat, np.ndarray):
            var2 = np.zeros(ifstat.shape)
            temp1 = np.where(ifstat)
        elif isinstance(ifstat, unicode) or isinstance(ifstat, str):
            val = eval(ifstat, {"__builtins__": None}, self.dico)
            var2 = np.zeros(val.shape)
            temp1 = np.where(val)
        # True
        if isinstance(true1, np.ndarray):
            var2[temp1] = true1[temp1]
        elif isinstance(true1, numbers.Number):
            var2[temp1] = float(true1)
        else:
            pass
        # False
        mask = np.ones(var2.shape, np.bool)
        mask[temp1] = 0
        if isinstance(false1, np.ndarray):
            var2[mask] = false1[mask]
        elif isinstance(false1, numbers.Number):
            var2[mask] = float(false1)
        else:
            pass
        return var2

    # ****************************************************************************************
    # ******************  Spatials functions  ************************************************

    def getFaceNodeXYFromNumPoint(self, arraynumpoint):
        meshx, meshy = self.getFacesNodes()
        return [[meshx[i], meshy[i]] for i in arraynumpoint]

    def getElemXYFromNumElem(self, arraynumelem):
        meshx, meshy = self.getFacesNodes()
        arrayelem = self.getElemFaces()
        result = []
        for numelem in arraynumelem:
            result.append([(meshx[i], meshy[i]) for i in arrayelem[numelem]])

        return result

    def getFaceXYFromNumFace(self, arraynumelem):
        meshx, meshy = self.getFacesNodes()
        arrayelem = self.getFaces()
        result = []
        for numelem in arraynumelem:
            result.append([(meshx[i], meshy[i]) for i in arrayelem[numelem]])
        return result

    def getNearestFaceNode(self, x, y):
        """
        Get the nearest point in selafin mesh
        point is an array [x,y]
        return num of selafin MESH point
        """
        # self.skdtreeelemnode = None
        # self.skdtreefacenode = None
        if SCIPYOK:
            point1 = [[x, y]]
            numfinal = self.skdtreefacenode.query(point1, k=1)[1][0]
            return numfinal
        else:
            meshx, meshy = self.getFacesNodes()
            diffx = np.array(meshx) - x
            diffy = np.array(meshy) - y
            dist = np.square(diffx) + np.square(diffy)
            return np.argmin(dist)

    def getNearestElemNode(self, x, y):
        """
        Get the nearest point in selafin mesh
        point is an array [x,y]
        return num of selafin MESH point
        """
        # self.skdtreeelemnode = None
        # self.skdtreefacenode = None

        point1 = [[x, y]]

        meshx, meshy = self.getFacesNodes()
        # nearestfacenodenum = self.skdtreefacenode.query(point1,k=1)[1][0]
        nearestfacenodenum = self.getNearestFaceNode(x, y)
        if len(self.getElemFaces().shape) == 1:
            faces = []
            elemfaces = self.getElemFaces()
            # face1 = [np.array(a) for a in elemfaces]
            for i, elem in enumerate(elemfaces):
                if len(np.where(np.array(elem) == nearestfacenodenum)[0]) > 0:
                    faces.append(i)
        else:
            faces = np.where(np.array(self.getElemFaces()) == nearestfacenodenum)[0]
        qgspoint = qgis.core.QgsGeometry.fromPointXY(qgis.core.QgsPointXY(x, y))

        for face in faces:
            geom = qgis.core.QgsGeometry.fromPolygonXY(
                [[qgis.core.QgsPointXY(meshx[facenode], meshy[facenode]) for facenode in self.getElemFaces()[face]]]
            )
            if qgspoint.intersects(geom):
                numfinal = face
                return numfinal
        return 0

    def getNearestFace(self, x, y):
        """
        Get the nearest point in selafin mesh
        point is an array [x,y]
        return num of selafin MESH point
        """
        # self.skdtreeelemnode = None
        # self.skdtreefacenode = None

        point1 = [[x, y]]

        meshx, meshy = self.getFacesNodes()
        # nearestfacenodenum = self.skdtreefacenode.query(point1,k=1)[1][0]
        nearestfacenodenum = self.getNearestFaceNode(x, y)
        # print self.getElemFaces().shape
        faces = np.where(np.array(self.getFaces()) == nearestfacenodenum)[0]

        qgspoint = qgis.core.QgsGeometry.fromPointXY(qgis.core.QgsPointXY(x, y))

        mindist = None
        for face in faces:
            geom = qgis.core.QgsGeometry.fromPolylineXY(
                [qgis.core.QgsPointXY(meshx[facenode], meshy[facenode]) for facenode in self.getFaces()[face]]
            )
            # distance
            if mindist == None:
                mindist = geom.distance(qgspoint)
                facefinal = face
            else:
                disttemp = geom.distance(qgspoint)
                if disttemp < mindist:
                    mindist = disttemp
                    facefinal = face
        return facefinal

    def getInterpFactorInTriangleFromPoint(self, x, y):
        """
        get interpolator factors factors form points
        x,y : array of x, y points
        return
        triangle : triangle in wich points are
        numpointsfinal : associated num point of triangle
        pointsfinal : associated point of triangle
        coef : interpolation coefficients
        """
        numpointsfinal = []
        pointsfinal = []
        coef = []
        meshx, meshy = self.getMesh()
        ikle = self.getIkle()
        triangles = self.trifind.__call__(x, y)
        for i, triangle in enumerate(triangles):
            inputpoint = np.array([x[i], y[i]])
            numpoints = ikle[triangle]
            numpointsfinal.append(numpoints)
            points = np.array(self.getXYFromNumPoint(numpoints))
            pointsfinal.append(points)
            # caculate vectors - triangle is ABC and point is P
            vab = points[1] - points[0]
            vac = points[2] - points[0]
            vpa = points[0] - inputpoint
            vpb = points[1] - inputpoint
            vpc = points[2] - inputpoint

            a = np.linalg.norm(np.cross(vab, vac))  # ABC area
            aa = np.linalg.norm(np.cross(vpb, vpc)) / a  # PBC relative area
            ab = np.linalg.norm(np.cross(vpa, vpc)) / a  # PAC relative area
            ac = np.linalg.norm(np.cross(vpa, vpb)) / a  # PAB relative area
            coef.append([aa, ab, ac])

        return triangles, numpointsfinal, pointsfinal, coef

    def createNetworkxGraph(self):
        if NETWORKXOK:
            G = nx.Graph()
            G.add_edges_from([(edge[0], edge[1]) for edge in self.getFaces()])
            self.networkxgraph = G
            return True
        else:
            return False

    def getShortestPath(self, enumpointdebut, enumpointfin):
        if NETWORKXOK and self.networkxgraph != None:
            return nx.shortest_path(self.networkxgraph, enumpointdebut, enumpointfin)
        else:
            return None

    def getBoundary(self):
        elems = self.getElemFaces()
        meshx, meshy = self.getFacesNodes()
        geoms = []
        for elem in elems:
            if len(elem) > 2:
                geoms.append([qgis.core.QgsPoint(meshx[facenode], meshy[facenode]) for facenode in elem])

        finalgeom = qgis.core.QgsGeometry.fromPolygon(geoms)
        return finalgeom

    def getParameterName(self, param):
        trouve = False
        f = open(os.path.join(os.path.dirname(__file__), "..", "config", "parametres.txt"), "r")
        for line in f:
            if param == line.split("=")[0]:
                tabtemp = []
                for txt in line.split("=")[1].split("\n")[0].split(";"):
                    tabtemp.append(str(txt))

                for paramtemp in self.parametres:
                    if paramtemp[1] in tabtemp:
                        trouve = True
                        f.close()
                        return paramtemp
                if not trouve:
                    f.close()
                    return None
        if not trouve:
            f.close()
            return None
