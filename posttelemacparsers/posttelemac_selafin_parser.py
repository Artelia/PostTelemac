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
import matplotlib
from matplotlib import tri
import numpy as np
from scipy.spatial import cKDTree
from ..libs_telemac.parsers.parserSELAFIN import SELAFIN

class PostTelemacSelafinParser():

    def __init__(self,layer = None):
        self.layer = None
        self.path = None
        self.hydraufile = None
        self.pointcount = None
        self.meshcount = None
        self.itertimecount = None
        self.skdtree = None
        self.triangulation = None
        self.trifind = None
        
    #Real Parser part to be modified
        
    def loadHydrauFile(self,path):
        self.path = path
        self.hydraufile = SELAFIN(self.path)
        self.pointcount = len(self.hydraufile.MESHX)
        self.meshcount = len(self.hydraufile.IKLE3)
        self.itertimecount = len(self.hydraufile.tags["times"]) - 1
        #ckdtree
        self.initCkdTree()
        self.initMplTriangulation()

        
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
        
        
    def getVarnames(self):
        return self.hydraufile.VARNAMES
    
    def getIkle(self):
        return self.hydraufile.IKLE3
        
    def getTimes(self):
        return self.hydraufile.tags["times"]
        
    #Others method - don't touch it 
        
    def getXYFromNumPoint(self,arraynumpoint):
        meshx,meshy = self.getMesh()
        #return [(self.hydraufile.MESHX[i], self.hydraufile.MESHY[i]) for i in arraynumpoint]
        return [(meshx[i], meshy[i]) for i in arraynumpoint]
        
    def initCkdTree(self):
        meshx, meshy = self.getMesh()
        arraymesh = np.array([[meshx[i], meshy[i] ] for i in range(self.pointcount) ])
        self.skdtree = cKDTree(arraymesh,leafsize=100)
        
    def initMplTriangulation(self):
        meshx, meshy = self.getMesh()
        ikle = self.getIkle()
        self.triangulation = matplotlib.tri.Triangulation(meshx,meshy,np.array(ikle))
        try:
            self.trifind = self.triangulation.get_trifinder()
        except Exception, e:
            print 'bug with trifinder ' + str(e)
            print 'regenerate selafin file please'
            #TODO : disable utils dependant trifind (valeurs,?)
        
    def getNearestPoint(self,x,y):
        """
        Get the nearest point in selafin mesh
        point is an array [x,y]
        return num of selafin MESH point
        """
        point1 = [[x,y]]
        numfinal = self.skdtree.query(point1,k=1)[1][0]
        return numfinal
        
    def getInterpFactorInTriangleFromPoint(self,x,y):
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
        coef=[]
        meshx,meshy = self.getMesh()
        ikle = self.getIkle()
        triangles = self.trifind.__call__(x,y)
        for i, triangle in enumerate(triangles):
            inputpoint = np.array([x[i],y[i]])
            numpoints = ikle[triangle]
            numpointsfinal.append(numpoints)
            points = np.array( self.getXYFromNumPoint(numpoints) )
            pointsfinal.append(points)
            #caculate vectors - triangle is ABC and point is P
            vab = points[1] - points[0]
            vac = points[2] - points[0]
            vpa = points[0] -  inputpoint
            vpb = points[1] -  inputpoint
            vpc = points[2] -  inputpoint
           
            a = np.linalg.norm( np.cross(vab,vac) ) #ABC area
            aa = np.linalg.norm( np.cross(vpb,vpc) ) / a  #PBC relative area
            ab = np.linalg.norm( np.cross(vpa,vpc) ) / a  #PAC relative area
            ac = np.linalg.norm( np.cross(vpa,vpb) ) / a  #PAB relative area
            coef.append([aa,ab,ac])
        
        return triangles,numpointsfinal,pointsfinal,coef
        
    
    