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
import numpy as np
from .posttelemac_abstract_parser import PostTelemacAbstractParser

# from .libs_telemac.parsers.parserSELAFIN import SELAFIN
from .libtelemac.Class_Serafin import Serafin
import string


class PostTelemacSelafinParser2(PostTelemacAbstractParser):

    SOFTWARE = "TELEMAC2"
    EXTENSION = ["res", "slf", "geo", "init", "*"]

    def __init__(self, layer1=None):
        super(PostTelemacSelafinParser2, self).__init__(layer1)

    def initPathDependantVariablesWhenLoading(self):
        # self.hydraufile = SELAFIN(self.path)
        self.hydraufile = Serafin(name=self.path, mode="rb")
        self.hydraufile.read_header()
        self.hydraufile.get_temps()

        try:
            self.translatex = self.hydraufile.IPARAM[2]
            self.translatey = self.hydraufile.IPARAM[3]
        except Exception as e:
            self.translatex = 0
            self.translatey = 0

    if False:

        def getRawValues(self, time):
            """
            return array : 
            array[param number][node value for param number]
            """
            return self.hydraufile.getVALUES(time)

        def getRawTimeSerie(self, arraynumpoint, arrayparam, layerparametres=None):
            """
            Warning : point index begin at 1 
            """
            result = []
            for param in arrayparam:
                tempordonees = self.hydraufile.getSERIES((np.array(arraynumpoint) + 1).tolist(), [param], False)
                result.append(tempordonees[0])
            return np.array(result)

        def getMesh(self):
            return (self.hydraufile.MESHX + self.translatex, self.hydraufile.MESHY + self.translatey)

        def getVarnames(self):
            paramnamesfinal = []
            remove_punctuation_map = dict((ord(char), ord(u"_")) for char in string.punctuation)

            for name in self.hydraufile.VARNAMES:
                paramnamesfinal.append(unicode(name).translate(remove_punctuation_map))

            return paramnamesfinal

        def getIkle(self):
            return self.hydraufile.IKLE3

    def getTimes(self):
        # return self.hydraufile.tags["times"]

        return self.hydraufile.temps

    # ****************************************************************************************
    # ****************************************************************************************
    # ****************************************************************************************

    def getVarNames(self):
        """
        return np.array[varname, typevar (0 : elem, 1 : facenode, 2 : face)]
        """
        paramnamesfinal = []
        remove_punctuation_map = dict((ord(char), ord(u"_")) for char in string.punctuation)

        for name in self.hydraufile.nomvar:
            paramnamesfinal.append([unicode(name).translate(remove_punctuation_map), 1])

        paramnamesfinal = [[param[0].rstrip(), param[1]] for param in paramnamesfinal]

        return paramnamesfinal

    # *********** Elems

    def getElemNodes(self):
        return (np.array([]), np.array([]))

    def getElemRawValue(self, time1):
        return np.array([])

    def getElemRawTimeSerie(self, arraynumelemnode, arrayparam, layerparametres=None):
        return np.array([])

    # *********** Face Node

    def getFacesNodes(self):
        """
        3T : xyz
        hec : FacePoints_Coordinate
        
        return (np.array(x), np.array(y) )
        
        """
        return (np.array(self.hydraufile.x + self.translatex), np.array(self.hydraufile.y + self.translatey))

    def getElemFaces(self):
        """
        It's the mesh
        3T : ikle
        hec : Faces_FacePoint_Indexes
        
        return np.array([facenodeindex linked with the elem ])
        """
        return np.array(self.hydraufile.ikle).reshape((-1, 3)) - 1

    def getFacesNodesRawValues(self, time1):
        """
        3T : getvalues
        
        return np.array[param number][node value for param number]
        
        """
        return np.array(self.hydraufile.read(time1, is_time=False))
        # return self.hydraufile.getVALUES(time1)

    def getFacesNodesRawTimeSeries(self, arraynumfacenode, arrayparam, layerparametres=None):
        """
        3T : getvalues
        
        return np.array[param][numelem][value for time t]
        
        """
        """
        Warning : point index begin at 1
        """
        result = []
        try:
            for param in arrayparam:
                tempordonees = self.hydraufile.getSERIES((np.array(arraynumfacenode) + 1).tolist(), [param], False)
                result.append(tempordonees[0])
            return np.array(result)
        except:
            return np.array([])

    # *********** Face

    def getFaces(self):
        """
        return np.array([facenodeindex linked with the face ])
        """
        if self.facesindex == None:
            if False:
                try:
                    self.facesindex = np.array([(edge[0], edge[1]) for edge in self.triangulation.edges])
                    return self.facesindex
                except Exception as e:
                    return np.array([])
            if True:
                ikle = self.getElemFaces()
                faceindex = []
                for tri in ikle:
                    faceindex.append([tri[0], tri[1]])
                    faceindex.append([tri[1], tri[2]])
                    faceindex.append([tri[2], tri[0]])
                faceindex = np.array(faceindex)
                self.facesindex = (
                    np.unique(faceindex.view(np.dtype((np.void, faceindex.dtype.itemsize * faceindex.shape[1]))))
                    .view(faceindex.dtype)
                    .reshape(-1, faceindex.shape[1])
                )
                return self.facesindex

        else:
            return self.facesindex

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
