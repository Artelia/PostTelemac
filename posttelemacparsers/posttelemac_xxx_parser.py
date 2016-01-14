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

class PostTelemacXXXParser():

    def __init__(self,layer = None):
        self.layer = None
        self.path = None
        self.hydraufile = None
        self.pointcount = None
        self.meshcount = None
        self.itertimecount = None
        
    def loadHydrauFile(self,path):
        self.path = path
        self.hydraufile = SELAFIN(self.path)
        self.pointcount = len(self.hydraufile.MESHX)
        self.meshcount = len(self.hydraufile.IKLE3)
        self.itertimecount = len(self.hydraufile.tags["times"]) - 1

        
    def getValues(self,time):
        """
        return array : 
        array[param number][node value for param number]
        """
        return self.hydraufile.getVALUES(time)
        
        
    def getTimeSerie(self,arraynumpoint,arrayparam):
        return self.hydraufile.getSERIES(arraynumpoint,arrayparam,False)
        
    def getMesh(self):
        return (self.hydraufile.MESHX, self.hydraufile.MESHY)
        
    def getXYFromNumPoint(self,arraynumpoint):
        return [(self.hydraufile.MESHX[i], self.hydraufile.MESHY[i]) for i in arraynumpoint]
        
        
    def getVarnames(self):
        return self.hydraufile.VARNAMES
    
    def getIkle(self):
        return self.hydraufile.IKLE3
        
    def getTimes(self):
        return self.hydraufile.tags["times"]
        

        
        
    