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
import matplotlib
from matplotlib import tri
from numpy import sin, cos, abs, int
import numpy as np
from scipy.spatial import cKDTree
import time
import networkx as nx
import numbers



class PostTelemacAbstractParser(object):

    def __init__(self,layer1 = None):
    
        self.pluginlayer = layer1
        self.path = None
        self.hydraufile = None
        self.pointcount = None
        self.meshcount = None
        self.itertimecount = None
        self.skdtree = None
        self.triangulation = None
        self.triangulationisvalid = [False,None]
        self.trifind = None
        self.parametres = None
        self.parametrev = None
        self.parametrevx = None         #specific num for velolity x parameter
        self.parametrevy = None
        self.parametreh = None
        self.networkxgraph = None
        self.translatex = 0
        self.translatey = 0
        
    #****************************************************************************************
    #******************  functions to be completed      *************************************
    #****************************************************************************************
    
    def setXYTranslation(self,xtransl, ytransl):
        self.translatex = xtransl
        self.translatey = ytransl
        self.initCkdTree()
        self.initMplTriangulation()
        
    def initPathDependantVariablesWhenLoading(self):
        """
        Define at least :
            self.hydraufile 
        """
        pass
        
    def getRawValues(self,time1):
        """
        return array : 
        array[param number][node value for param number]
        """
        return np.array([[None]])
        
    def getRawTimeSerie(self,arraynumpoint,arrayparam,layerparametres = None):
        """
        Warning : point index begin at 1
        [..., param[numpts[values]], ... ]
        """
        return np.array([None])
        
    def getMesh(self):
        """
        return MESHX: np.array[x1,X2,...], MESHY:[y1,y2,...]
        """
        return (np.array([None]), np.array([None]) )
        
    def getVarnames(self):
        """
        return [...[varname, dimension],...]
        """
        return np.array([None])
    
    def getIkle(self):
        """
        return array [...,(meshn:)[point1,point2,point3], ...]
        """
        return np.array([None])
        
    def getTimes(self):
        """
        return array of times computed
        """
        return np.array([None])
        
        
        
        
        
        
    #****************************************************************************************
    #****************** Inherited functions             *************************************
    #****************************************************************************************
    
    #****************************************************************************************
    #******************  Load functions                *************************************
        
    def loadHydrauFile(self,path1):
        """
        Called when a mesh file is loaded
        """
        self.path = path1
        self.initPathDependantVariablesWhenLoading()
        self.initClassicThingsAndCkdTreeAndMatplotLib()
    
    def initClassicThingsAndCkdTreeAndMatplotLib(self):
        self.pointcount = len(self.getMesh()[0])
        self.meshcount = len(self.getIkle())
        self.itertimecount = len(self.getTimes())-1
        self.initCkdTree()
        self.initMplTriangulation()
        self.initSelafinParameters()
        
    def initCkdTree(self):
        meshx, meshy = self.getMesh()
        arraymesh = np.array([[meshx[i], meshy[i] ] for i in range(self.pointcount) ])
        self.skdtree = cKDTree(arraymesh,leafsize=100)
        
    def initMplTriangulation(self):
        meshx, meshy = self.getMesh()
        ikle = self.getIkle()
        self.triangulation = matplotlib.tri.Triangulation(meshx,meshy,np.array(ikle))
        bool1, error = self.checkTriangul()
        if bool1:
            self.trifind = self.triangulation.get_trifinder()
            self.triangulationisvalid = [True,None]
        else:
            self.triangulationisvalid = [False,error]
            if self.pluginlayer != None:
                self.pluginlayer.propertiesdialog.errorMessage('Duplicated points : ' + str( (self.triangulationisvalid[1] + 1).tolist()  ) + ' - Triangulation is invalid')
        
        
    def checkTriangul(self):
        import collections
        d = collections.OrderedDict()
        indexfinal = []
        x,y = self.getMesh()
        p = [[x[i],y[i]] for i in range(len(x))]
        p1 = np.array(p)
        for i, a in enumerate(p1):
            t = tuple(a)
            if t in d:
                d[t] += 1
                index1  = d.keys().index(t)
                index2 = i
                indexfinal += [[index1,index2 ]]
            else:
                d[t] = 1

        result = []
        for (key, value) in d.items():
            result.append(list(key) + [value])

        B = np.asarray(result)
        c = np.where(B[:,2] >1)
        
        if len(c[0])>0:
            return False,np.array(indexfinal)
        else:
            return True,None
            

    def initSelafinParameters(self):
        """
        Called load_selafin by when changing selafin file
        Set selafin variables
        """
        #self.initTriangul()
        self.parametres = []
        #load  parametres in self.parametres
        for i,name in enumerate(self.getVarnames()):
            self.parametres.append([i,name.strip(),None,i])
        if self.pluginlayer != None and len(self.pluginlayer.parametrestoload['virtual_parameters'])>0:    #case of virtual parameters when loadin a selafin layer
            for param in self.pluginlayer.parametrestoload['virtual_parameters']:
                self.parametres.append([len(self.parametres),param[1],param[2],len(self.parametres)])
        if self.pluginlayer != None and (self.pluginlayer.parametrestoload['xtranslation'] != 0 or self.pluginlayer.parametrestoload['ytranslation'] != 0):
            self.setXYTranslation(self.pluginlayer.parametrestoload['xtranslation'],self.pluginlayer.parametrestoload['ytranslation'])
        
        self.identifyKeysParameters()
        
        
    
    def identifyKeysParameters(self):
        #load velocity parameters
        if self.pluginlayer != None :
            if (self.parametrevx == None and self.parametrevy == None) :

                if self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEU") == None and self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEV") == None:
                    self.pluginlayer.propertiesdialog.tab_velocity.setEnabled(False)
                else:
                    self.parametrevx = self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEU")[0]
                    self.parametrevy = self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEV")[0]
                    self.pluginlayer.propertiesdialog.tab_velocity.setEnabled(True)
                    for widget in self.pluginlayer.propertiesdialog.tab_velocity.children():
                        widget.setEnabled(True)
                    for widget in self.pluginlayer.propertiesdialog.groupBox_schowvel.children():
                        widget.setEnabled(True)
                    self.pluginlayer.propertiesdialog.groupBox_schowvel.setChecked(True)
                    self.pluginlayer.propertiesdialog.groupBox_schowvel.setChecked(False)

            #load water depth parameters
            if  self.parametreh == None :
                if self.pluginlayer.propertiesdialog.postutils.getParameterName("HAUTEUR") == None:
                    if self.pluginlayer.propertiesdialog.postutils.getParameterName("SURFACELIBRE") != None and self.pluginlayer.propertiesdialog.postutils.getParameterName("BATHYMETRIE") != None:
                        paramfreesurface = self.pluginlayer.propertiesdialog.postutils.getParameterName("SURFACELIBRE")[0]
                        parambottom = self.pluginlayer.propertiesdialog.postutils.getParameterName("BATHYMETRIE")[0]
                        self.parametreh = len(self.parametres)
                        self.parametres.append([len(self.parametres),"HAUTEUR D'EAU",'V'+str(paramfreesurface)+' - V'+str(parambottom),len(self.parametres)])
                else:
                    self.parametreh = self.pluginlayer.propertiesdialog.postutils.getParameterName("HAUTEUR")[0]
            
            if self.parametrev == None :
                if self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSE") == None:
                    if self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEU") != None and self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEV") != None:
                        paramvx = self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEU")[0]
                        paramvy = self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSEV")[0]
                        self.parametrev = len(self.parametres)
                        self.parametres.append([len(self.parametres),"VITESSE",'(V'+str(paramvx)+'**2 + V'+str(paramvy)+'**2)**0.5',len(self.parametres)])
                else:
                    self.parametrev = self.pluginlayer.propertiesdialog.postutils.getParameterName("VITESSE")[0]
            
            
            

            if self.parametreh != None and self.parametrevx != None and self.parametrevy != None:
                self.pluginlayer.propertiesdialog.page_flow.setEnabled(True)
            else:
                self.pluginlayer.propertiesdialog.page_flow.setEnabled(False)
            
        
        
    #****************************************************************************************
    #******************  Parameters and else functions  *************************************
    
            
    def getValues(self,time):
        """
        Get the values of paameters for time time
        """
        values = self.getRawValues(time)
        #print str(self.parametres)
        for param in self.parametres:
            if param[2]:        #for virtual parameter - compute it
                self.dico = self.getDico(param[2], self.parametres, values,'values')
                val = eval(param[2],{"__builtins__":None}, self.dico)
                values = np.vstack((values,val))
        return values
    
    
    def getTimeSerie(self,arraynumpoint,arrayparam,layerparametres = None):
        """
        Warning : point index begin at 1
        """
        result = []
        try:
            for param in arrayparam:
                if layerparametres != None and layerparametres[param][2]:
                    dico = self.getDico(layerparametres[param][2], layerparametres,arraynumpoint,'timeseries')
                    tempordonees = eval(layerparametres[param][2],{}, dico)
                    result.append(tempordonees[0])
                else:
                    #tempordonees = self.hydraufile.getSERIES(arraynumpoint,[param],False)
                    tempordonees = self.getRawTimeSerie(arraynumpoint,[param],False)
                    result.append(tempordonees[0])
        except Exception, e:
            print 'getserie ' + str(e)
        return np.array(result)
        
        
    def getDico(self,expr, parametres,enumpointorvalues,type):
        dico = {}
        try:
            dico['sin'] = sin
            dico['cos'] = cos
            dico['abs'] = abs
            dico['int'] = int
            dico['if_then_else'] = self.if_then_else
            a = 'V{}'
            #nb_var = len(values)
            nb_var = len( self.getRawValues(0) )
            i = 0
            num_var = 0
            while num_var < nb_var:
                if not parametres[i][2]:
                    if type == 'values':
                        dico[a.format(i)] = enumpointorvalues[i]
                    elif type == 'timeseries':
                        dico[a.format(i)] = self.getRawTimeSerie(enumpointorvalues,[i])
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
        elif isinstance(ifstat,unicode) or isinstance(ifstat,str):
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

    #****************************************************************************************
    #******************  Spatials functions  ************************************************
        
    def getXYFromNumPoint(self,arraynumpoint):
        meshx,meshy = self.getMesh()
        #return [(self.hydraufile.MESHX[i], self.hydraufile.MESHY[i]) for i in arraynumpoint]
        return [(meshx[i], meshy[i]) for i in arraynumpoint]
        
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
        
    def createNetworkxGraph(self):
        G = nx.Graph()
        G.add_edges_from([(edge[0],edge[1]) for edge in self.triangulation.edges])
        self.networkxgraph = G
        
    def getShortestPath(self,enumpointdebut,enumpointfin):
        if self.networkxgraph != None:
            return nx.shortest_path(self.networkxgraph, enumpointdebut, enumpointfin)
        else :
            return None
