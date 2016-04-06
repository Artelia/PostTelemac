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


from ..libs_telemac.parsers.parserSELAFIN import SELAFIN

class PostTelemacSelafinParser():

    def __init__(self,selafinlayer = None):
        self.selafinlayer = None
        self.path = None
        self.selafin = None
        self.pointcount = None
        self.meshcount = None
        self.itertimecount = None
        
    def loadSelafin(self,path):
        self.path = path
        self.selafin = SELAFIN(self.path)
        self.pointcount = len(self.selafin.MESHX)
        self.meshcount = len(self.selafin.IKLE3)
        self.itertimecount = len(self.selafin.tags["times"]) - 1

        
    def getValues(self,time):
        """
        return array : 
        array[param number][node value for param number]
        """
        return self.selafin.getVALUES(time)
        
        
    def getTimeSerie(self,arraynumpoint,arrayparam):
        return self.selafin.getSERIES(arraynumpoint,arrayparam,False)
        
    def getMesh(self):
        return (self.selafin.MESHX, self.selafin.MESHY)
        
    def getXYFromNumPoint(self,arraynumpoint):
        return [(self.selafin.MESHX[i], self.selafin.MESHY[i]) for i in arraynumpoint]
        
        
    def getVarnames(self):
        return self.selafin.VARNAMES
    
    def getIkle(self):
        return self.selafin.IKLE3
        
    def getTimes(self):
        return self.selafin.tags["times"]
        

        
        
    