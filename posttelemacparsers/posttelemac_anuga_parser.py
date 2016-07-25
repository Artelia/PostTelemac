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
import gdal
import subprocess
from posttelemac_abstract_parser import PostTelemacAbstractParser


MESHX = 'x'
MESHY = 'y'
IKLE = 'volumes'
TIME = 'time'
BATHY = 'elevation'


class PostTelemacSWWParser(PostTelemacAbstractParser):

    def __init__(self,layer1 = None):
        super(PostTelemacSWWParser, self).__init__(layer1)
        self.varnames=None
        self.ikle = None
        self.time = None
        self.onedvar = {}

    
    def initPathDependantVariablesWhenLoading(self):
        self.hydraufile = gdal.Open('NETCDF:"'+self.path+'"')
        #x y tranlsation
        dump = self.getNcDumpVar()[4]
        names = [tt1[0] for tt1 in dump]
        indexxllcorner = names.index('xllcorner')
        indexyllcorner = names.index('yllcorner')
        self.translatex = float( dump[indexxllcorner][1] )
        self.translatey = float( dump[indexyllcorner][1] )
        
    def getRawValues(self,time1):
        """
        return array : 
        array[param number][node value for param number]
        """
        result=[]
        for var in self.varnames:
            if var[1] == 1 :
                result.append( self.get1DVar(var[0]) )
            elif var[1] == 2 :
                result.append(np.array( var[2].ReadAsArray() )[::-1,:][time1])
        return np.array(result)
        
        
    def getRawTimeSerie(self,arraynumpoint,arrayparam,layerparametres = None):
        """
        Warning : point index begin at 1
        [..., param[numpts[values]], ... ]
        """
        result = []
        for param in arrayparam:
            if self.varnames[param][1] == 1 :
                tt1 =  np.array( self.get1DVar(self.varnames[param][0]) )
                tt2 = tt1[np.array(arraynumpoint)-1]
                tt3 = [[ [tt4] * (self.itertimecount +1) ] for tt4 in tt2 ]
                result.append(np.array(tt3[0]))
            elif self.varnames[param][1] == 2 :
                tt1 = np.array(self.getNDVar(self.varnames[param][0]))
                tt1 = np.transpose(tt1)
                tt2 = tt1[np.array(arraynumpoint)-1]
                result.append(tt2[::-1,:])
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
        
        return [var[0] for var in self.varnames]
    
    def getIkle(self):
        if self.ikle == None:
            self.ikle = self.getNDVar(IKLE)
        
        return self.ikle
        
    def getTimes(self):
        if self.time == None:
            self.time = np.array( self.get1DVar(TIME) )
        
        return self.time
    
    
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
                #varname
                tt2 = tt1[1].split('(')[0]
                temparray += [tt2]
                #dimensions
                tt2 = str1[0].replace(' ','').replace('(',';').replace(')',';')
                tt3 = tt2.split(';')
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
        