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
import os

class PostTelemacFlo2DParser(PostTelemacAbstractParser):

    def __init__(self,layer1 = None):
        super(PostTelemacSelafinParser, self).__init__(layer1)

    
    def initPathDependantVariablesWhenLoading(self):
        self.hydraufile = self.path
        #Ptsfile
        self.ptsfile = None
        for file in os.listdir(os.path.dirname(self.hydraufile)):
            if file.endswith("CADPTS.dat"):
                self.ptsfile = os.path.join(os.path.dirname(self.hydraufile),file)
                break
        #ikle
        self.iklefile = None
        for file in os.listdir(os.path.dirname(self.hydraufile)):
            if file.endswith("FPLAIN.dat"):
                self.iklefile = os.path.join(os.path.dirname(self.hydraufile),file)
                break
        
        self.translatex = self.hydraufile.IPARAM[2]
        self.translatey = self.hydraufile.IPARAM[3]

        
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
        f = open(self.ptsfile, 'r')
        meshx = []
        meshy = []
        for line in f:
            line1 = line.split()
            meshx.append(line1[1])
            meshy.append(line1[2])
        f.close()
        return (np.array(meshx) + self.translatex, np.array(meshy) + self.translatey)
        
        
    def getVarnames(self):
        return self.hydraufile.VARNAMES
    
    def getIkle(self):
        f = open(self.iklefile, 'r')
        ikle = []
        for line in f:
            line1 = line.split()
            meshx.append(line1[1])
            meshy.append(line1[2])
        f.close()
        return (meshx + self.translatex, meshy + self.translatey)
        
        return self.hydraufile.IKLE3
        
    def getTimes(self):
        return self.hydraufile.tags["times"]
        
