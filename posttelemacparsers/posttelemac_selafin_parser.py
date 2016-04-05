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
from numpy import *
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
        
        
    def getTimeSerie(self,arraynumpoint,arrayparam,layerparametres = None):
        """
        Warning : point index begin at 1
        """
        if False:
            return self.hydraufile.getSERIES(arraynumpoint,arrayparam,False)
        else:
            #print 'arraypoint ' + str(arraynumpoint)
            result = []
            try:
                for param in arrayparam:
                    if layerparametres != None and layerparametres[param][2]:
                        dico = self.getDico(layerparametres[param][2], layerparametres,arraynumpoint)
                        tempordonees = eval(layerparametres[param][2],{}, dico)
                        result.append(tempordonees[0])
                    else:
                        tempordonees = self.hydraufile.getSERIES(arraynumpoint,[param],False)
                        result.append(tempordonees[0])
            except Exception, e:
                print 'getserie ' + str(e)
            return np.array(result)
        
    def getMesh(self):
        return (self.hydraufile.MESHX, self.hydraufile.MESHY)
        
        
    def getVarnames(self):
        return self.hydraufile.VARNAMES
    
    def getIkle(self):
        return self.hydraufile.IKLE3
        
    def getTimes(self):
        return self.hydraufile.tags["times"]
        
    
        
    #Others method - don't touch it 
    
    def getDico(self,expr, parametres,enumpoint):
        dico = {}
        try:
            dico['sin'] = sin
            dico['cos'] = cos
            dico['abs'] = abs
            dico['int'] = int
            dico['if_then_else'] = self.if_then_else
            a = 'V{}'
            #nb_var = len(values)
            nb_var = len( self.getValues(0) )
            i = 0
            num_var = 0
            while num_var < nb_var:
                if not parametres[i][2]:
                    dico[a.format(i)] = self.getTimeSerie(enumpoint,[i])
                num_var += 1
                i += 1
        except Exception, e:
            print 'getdico ' + str(e)
        return dico
    
    def if_then_else(self,ifstat,true1,false1):
        """
        Used for calculation of virtual parameters
        """
        #condition
        if isinstance(ifstat,np.ndarray):
            var2 = np.zeros(ifstat.shape)
            temp1 = np.where(ifstat)
        elif isinstance(ifstat,str):
            val = eval(ifstat,{"__builtins__":None}, self.dico)
            var2 = np.zeros(val.shape)
            temp1 = np.where(val)
        #True
        if isinstance(true1,np.ndarray):
            var2[temp1] = true1[temp1]
        elif isinstance(true1, numbers.Number):
            var2[temp1] = float(true1)
        else:
            pass
        #False
        mask = np.ones(var2.shape, np.bool)
        mask[temp1] = 0
        if isinstance(false1,np.ndarray):
            var2[mask] = false1[mask]
        elif isinstance(false1, numbers.Number):
            var2[mask] = float(false1)
        else:
            pass
        return var2
    """
    def getGraphTempSeries(self,num,param):
        if self.compare :
            x,y = self.getXYFromNumPoint(num)[0]
            triangles,numpointsfinal,pointsfinal,coef = self.getInterpFactorInTriangleFromPoint([x],[y])
            layer2serie = 0
            for i, numpoint in enumerate(numpointsfinal[0]):
                layer2serie += float(coef[0][i]) * self.selafinlayer.propertiesdialog.postutils.compareprocess.hydrauparsercompared.getTimeSerie([numpoint],[self.selafinlayer.parametres[param[0]][3]])
            layer1serie = self.selafinlayer.hydrauparser.getTimeSerie(num,param)
            return layer2serie  - layer1serie
        else:
            return self.selafinlayer.hydrauparser.getTimeSerie(num,param)
    """
    
        
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
        
    
    