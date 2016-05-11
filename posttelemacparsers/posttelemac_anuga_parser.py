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
#from ..libs_telemac.parsers.parserSELAFIN import SELAFIN
import gdal
import subprocess
#from subprocess import Popen, PIPE
import time

MESHX = 'x'
MESHY = 'y'
IKLE = 'volumes'
TIME = 'time'
BATHY = 'elevation'


class PostTelemacSWWParser():

    def __init__(self,layer = None):
        self.layer = None
        self.path = None
        self.hydraufile = None
        self.pointcount = None
        self.meshcount = None
        self.itertimecount = None
        self.skdtree = None
        self.triangulation = None
        self.triangulationisvalid = [False,None]
        self.trifind = None
        self.varnames=None
        self.ikle = None
        self.time = None
        self.translatex = 0.0
        self.translatey = 0.0
        self.onedvar = {}
        
    #Real Parser part to be modified
        
    def loadHydrauFile(self,path):
        self.path = path
        #self.hydraufile = SELAFIN(self.path)
        #self.hydraufile = 'OK'
        self.hydraufile = gdal.Open('NETCDF:"'+self.path+'"')
        self.pointcount = len(self.get1DVar(MESHX))
        self.meshcount = len(self.get1DVar(IKLE))
        self.itertimecount = len(self.get1DVar(TIME))-1
        #x y tranlsation
        dump = self.getNcDumpVar()[4]
        names = [tt1[0] for tt1 in dump]
        indexxllcorner = names.index('xllcorner')
        indexyllcorner = names.index('yllcorner')
        self.translatex = float( dump[indexxllcorner][1] )
        self.translatey = float( dump[indexyllcorner][1] )
        #ckdtree
        self.initCkdTree()
        self.initMplTriangulation()

        
        
    def getValues(self,time1):
        """
        return array : 
        array[param number][node value for param number]
        """
        #return self.hydraufile.getVALUES(time)
        #timestart = time.clock()
        result=[]
        for var in self.varnames:
            if var[1] == 1 :
                result.append( self.get1DVar(var[0]) )
            elif var[1] == 2 :
                #result.append( self.getNDVar(var[0])[time1] )
                #result.append( np.array( self.hydraufile.GetSubDatasets()[var[2]].ReadAsArray() )[::-1,:][time1] )
                result.append(np.array( var[2].ReadAsArray() )[::-1,:][time1])
        #print 'time ' + str( time.clock() - timestart)
        return np.array(result)
        
        
        
        
    def getTimeSerie(self,arraynumpoint,arrayparam,layerparametres = None):
        """
        Warning : point index begin at 1
        [..., param[numpts[values]], ... ]
        """
        #timestart = time.clock()
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
                        if self.varnames[param][1] == 1 :
                            tt1 =  np.array( self.get1DVar(self.varnames[param][0]) )
                            #print str(tt1)
                            tt2 = tt1[np.array(arraynumpoint)-1]
                            #tt3 = list( tt2 ) * self.itertimecount
                            tt3 = [[ [tt4] * (self.itertimecount +1) ] for tt4 in tt2 ]
                            result.append(tt3[0])
                            
                        elif self.varnames[param][1] == 2 :
                            tt1 = np.array(self.getNDVar(self.varnames[param][0]))
                            #print str(tt1)
                            tt1 = np.transpose(tt1)
                            tt2 = tt1[np.array(arraynumpoint)-1]
                            result.append(tt2[::-1,:])
                        
                        """
                        tempordonees = self.hydraufile.getSERIES(arraynumpoint,[param],False)
                        result.append(tempordonees[0])
                        """
            except Exception, e:
                print 'getserie ' + str(e)
            #print 'time ' + str( time.clock() - timestart)
            return np.array(result)
        
    def getMesh(self):
        #tranlsation info        
        return (np.array(self.get1DVar(MESHX)) + self.translatex , np.array(self.get1DVar(MESHY)) + self.translatey )
        
        
    def getVarnames(self):
        """
        return [...[varname, dimension],...]
        """
        if self.varnames == None:
            dump = self.getNcDumpVar()[2]
            varnames=[]
            for str1 in dump:
                if len(str1[2]) == 1:
                    if str1[1] != MESHX and str1[1] != MESHY and str1[1] != TIME:
                        if len( self.get1DVar(str1[1]) ) == self.pointcount:
                            varnames.append([str1[1],1,None])
                            #self.onedvar[str1[1]] = None
                
                elif len(str1[2]) == 2:
                    if str1[1] != IKLE:
                        if len( self.getNDVar(str1[1])[0] ) == self.pointcount:
                            varnames.append([str1[1],2])
                            if True:
                                u = self.hydraufile.GetSubDatasets()
                                int1 = 0
                                for i, arr in enumerate(u):
                                    layer1 = arr[0].split(':')[-1]
                                    if layer1 == str1[1]:
                                        file1 = gdal.Open(arr[0])
                                        break
                                varnames[-1].append(file1)
                            
            self.varnames = varnames
        
        #return self.hydraufile.VARNAMES
        return [var[0] for var in self.varnames]
    
    def getIkle(self):
        #return self.hydraufile.IKLE3
        if self.ikle == None:
            self.ikle = self.getNDVar(IKLE)
        
        return self.ikle
        
    def getTimes(self):
        #return self.hydraufile.tags["times"]
        if self.time == None:
            self.time = np.array( self.get1DVar(TIME) )
        
        return self.time
    
        
    #Others method - don't touch it 
    
    def getNcDumpVar(self):
        str1 = "ncdump -h "+ self.path
        p = subprocess.Popen(str1, shell = True, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        temp = p.stdout.readlines()
        
        result=[]
        for str1 in temp:
            if str1[0:1]=='\t' or str1[0:2]=='\t\t' :
                if str1[0:1]=='\t' :
                    result[-1] += [[str1.replace(' ;','').replace('\r\n','').replace('\t','')]]
                elif str1[0:2]=='\t\t' :
                    result[-1] += [[str1.replace(' ;','').replace('\r\n','').replace('\t\t','')]]
            else:
                result.append([str1.replace(' ;','').replace('\r\n','')])
        
        #dimension process
        resultaray=[]
        for str1 in  result[1][1:]:
            tt1=str1[0].split('=')
            tt2 = [tt3.strip() for tt3 in tt1]
            resultaray += [tt2]
        result[1] = resultaray
        
        #var process
        resultaray=[]
        for str1 in  result[2][1:]:
                temparray=[]
                #vartype
                tt1 = str1[0].split()
                temparray += [tt1[0]]
                #print 'tt1 ' + str(tt1)
                #varname
                tt2 = tt1[1].split('(')[0]
                temparray += [tt2]
                #print 'tt2 ' + str(tt2)
                #dimensions
                tt2 = str1[0].replace(' ','').replace('(',';').replace(')',';')
                tt3 = tt2.split(';')
                #print 'tt3 ' + str(tt3)
                tt4 = [tt5 for tt5 in tt3[1:] if tt5 != '']
                temparray += [tt4[0].split(',')]
                resultaray.append(temparray)
        result[2] = resultaray
        
        #Global process
        resultaray=[]
        for str1 in  result[4][1:]:
            tt1=str1[0].split('=')
            tt2 = [tt3.strip().replace(':','') for tt3 in tt1]
            resultaray += [tt2]
        result[4] = resultaray
        
        return result
        
    def get1DVar(self,varname):
    
        if varname not in self.onedvar.keys() or self.onedvar[varname] == None:
                str1 = "ncdump -v "+varname+' ' +self.path
                p = subprocess.Popen(str1, shell = True, stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                temp = p.stdout.readlines()
                
                temp1 = [str2.replace("\r\n", "") for str2 in temp]
                
                int2 = temp1.index('data:')
                temp3 = temp1[int2+2:]
                temp4=[]
                
                for test in temp3 :
                    temp5 = test.split(',')
                    temp5 = [a.split('=')[-1] for a in temp5]
                    temp5 = [a.split(';')[0] for a in temp5]
                    temp4+=temp5

                temp5=[]
                for test in temp4:
                    try:
                        tt1 = float(test.strip())
                        temp5 += [tt1]
                    except:
                        pass
                
                self.onedvar[varname] = temp5
            
        return self.onedvar[varname]
        
    
    def getNDVar(self,varname):
        str2 = 'NETCDF:"'+self.path+'":'+varname
        v = gdal.Open(str2)
        temp1 = np.array( v.ReadAsArray() )
        return temp1[::-1,:]
        
    
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
        bool1, error = self.checkTriangul()
        if bool1:
            self.trifind = self.triangulation.get_trifinder()
            self.triangulationisvalid = [True,None]
        else:
            self.triangulationisvalid = [False,error]
        
        
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
        
        if len(c)>0:
            return False,np.array(indexfinal)
        else:
            return True,None
        
        
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
        
    
    