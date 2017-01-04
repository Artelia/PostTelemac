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
from posttelemac_abstract_parser import PostTelemacAbstractParser
from libs_telemac.parsers.parserSELAFIN import SELAFIN
import string

class PostTelemacSelafinParser(PostTelemacAbstractParser):

    def __init__(self,layer1 = None):
        super(PostTelemacSelafinParser, self).__init__(layer1)

    
    def initPathDependantVariablesWhenLoading(self):
        self.hydraufile = SELAFIN(self.path)
        try:
            self.translatex = self.hydraufile.IPARAM[2]
            self.translatey = self.hydraufile.IPARAM[3]
        except Exception, e:
            self.translatex = 0
            self.translatey = 0

        
    def getRawValues(self,time):
        """
        return array : 
        array[param number][node value for param number]
        """
        return self.hydraufile.getVALUES(time)
        
        
    def getRawTimeSerie(self,arraynumpoint,arrayparam,layerparametres = None):
        """
        Warning : point index begin at 1
        """
        result = []
        for param in arrayparam:
            tempordonees = self.hydraufile.getSERIES(arraynumpoint,[param],False)
            result.append(tempordonees[0])
        return np.array(result)
        
        
    def getMesh(self):
        return (self.hydraufile.MESHX + self.translatex, self.hydraufile.MESHY + self.translatey)
        
        
    def getVarnames(self):
        paramnamesfinal = []
        remove_punctuation_map = dict((ord(char), ord(u'_')) for char in string.punctuation)
        
        for name in self.hydraufile.VARNAMES:
            paramnamesfinal.append(unicode(name).translate(remove_punctuation_map))
            
        return paramnamesfinal
    
    def getIkle(self):
        return self.hydraufile.IKLE3
        
    def getTimes(self):
        return self.hydraufile.tags["times"]
        
