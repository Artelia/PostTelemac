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
from .libtelemac.parserSELAFIN import SELAFIN
import string

try:
    import pyfive
except:
    print("no pyfive")


class PostTelemacSelafinParser(PostTelemacAbstractParser):

    SOFTWARE = "TELEMAC"
    EXTENSION = ["res", "slf", "geo", "init"]
    # TOOLS = ['VALUETOOL', 'TEMPORALGRAPHTOOL', 'FLOWTOOL', 'VOLUMETOOL', 'ANIMATIONTOOL', 'COMPARETOOL',  'EXTRACTMACTOOL', 'OPENGLTOOL', 'PROFILETOOL', 'RASTERTOOL', 'TOSHAPETOOL']

    def __init__(self, layer1=None):
        super(PostTelemacSelafinParser, self).__init__(layer1)

    def initPathDependantVariablesWhenLoading(self):
        self.hydraufile = SELAFIN(self.path)
        try:
            self.translatex = self.hydraufile.IPARAM[2]
            self.translatey = self.hydraufile.IPARAM[3]
        except Exception as e:
            self.translatex = 0
            self.translatey = 0

    # ****************************************************************************************
    # ****************************************************************************************
    # ****************************************************************************************

    def getTimes(self):
        return self.hydraufile.tags["times"]

    def getVarNames(self):
        """
        return np.array[varname, typevar (0 : elem, 1 : facenode, 2 : face)]
        """
        paramnamesfinal = []

        if False:
            remove_punctuation_map = dict((ord(char), ord(u"_")) for char in string.punctuation)

            for name in self.hydraufile.VARNAMES:
                paramnamesfinal.append([unicode(name).translate(remove_punctuation_map), 1])

        if True:

            if isinstance(self.hydraufile.VARNAMES[0], str):
                remove_punctuation_map = dict((ord(char), ord(u"_")) for char in string.punctuation)

                for name in self.hydraufile.VARNAMES:
                    paramnamesfinal.append([unicode(name).translate(remove_punctuation_map), 1])

            elif isinstance(self.hydraufile.VARNAMES[0], bytes):
                for name in self.hydraufile.VARNAMES:
                    paramnamesfinal.append([name.strip().decode("utf-8"), 1])

        paramnamesfinal = [[param[0].rstrip(), param[1]] for param in paramnamesfinal]

        return paramnamesfinal

    # *********** Face Node

    def getFacesNodes(self):
        """
        3T : xyz
        hec : FacePoints_Coordinate
        
        return (np.array(x), np.array(y) )
        
        """
        return (self.hydraufile.MESHX + self.translatex, self.hydraufile.MESHY + self.translatey)

    def getElemFaces(self):
        """
        It's the mesh
        3T : ikle
        hec : Faces_FacePoint_Indexes
        
        return np.array([facenodeindex linked with the elem ])
        """
        return self.hydraufile.IKLE3

    def getFacesNodesRawValues(self, time1):
        """
        3T : getvalues
        
        return np.array[param number][node value for param number]
        
        """
        return self.hydraufile.getVALUES(time1)

    def getFacesNodesRawTimeSeries(self, arraynumfacenode, arrayparam, layerparametres=None):
        """
        3T : getvalues
        
        return np.array[param][numelem][value for time t]
        
        """
        """
        Warning : point index begin at 1
        """
        result = []
        for param in arrayparam:
            tempordonees = self.hydraufile.getSERIES((np.array(arraynumfacenode) + 1).tolist(), [param], False)
            result.append(tempordonees[0])
        return np.array(result)

    # *********** Face

    def getFaces(self):
        """
        return np.array([facenodeindex linked with the face ])
        """
        if not isinstance(self.facesindex, np.ndarray) and self.facesindex == None:
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
