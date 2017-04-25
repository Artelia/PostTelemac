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
 get Image class
 Generate a Qimage from selafin file to be displayed in map canvas 
 with tht draw method of posttelemacpluginlayer
 
Versions :
0.0 : debut

 ***************************************************************************/
"""
import sys
import os
from PyQt4 import uic, QtCore, QtGui
import numpy as np

import gdal
import qgis

import time


#sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from PostTelemac.meshlayerparsers.posttelemac_hdf_parser import PostTelemacHDFParser
"""

from meshlayertools.meshlayer_opengl_tool import OpenGLDialog
from meshlayerparsers.posttelemac_anuga_parser import PostTelemacSWWParser
"""

def getParams():
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
#        path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
#        parser = PostTelemacHDFParser()
#        parser.loadHydrauFile(path)
        """
        self.elemcount = len(   self.getElemFaces() )
        self.facesnodescount = len(self.getFacesNodes()[0]   )
        self.facescount = len(   self.getFaces() )
        self.itertimecount = len(self.getTimes())-1
        
        print parser.elemcount
        print parser.facesnodescount
        print parser.facescount
        print parser.itertimecount
        """
        hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
        #print hdf_ds.GetSubDatasets() 
        lensubdataset = len(hdf_ds.GetSubDatasets() )
        hdf_ds = None
        
        params = [['Bottom', 0, [2,parser.elemcount], None]]
        
        for i in range(1,lensubdataset):
                hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(':')[-1])
                print '****************'
                print str1.split('//')
                param = str1.split('//')[1].split('/')
                print param
                #print str1.split('//')[1].split('/')
                if 'Results' in param and '2D_Flow_Areas' in  param :
                    
                    #print param[-1]
                    #print 'ok'
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()
                    #bottomid.append(array)
                    band_ds = None
                    
                    print str(param[-1]) + ' ' +str(   np.array(params)[:,0].tolist()   )
                    
                    if param[-1] in np.array(params)[:,0].tolist():
                            index = np.array(params)[:,0].tolist().index(param[-1] )
                            params[index][2][1] += np.array(array).shape[1]
                            params[index][3].append(var)
                        
                    else:
                        if False:
                            if np.array(array).shape[1] == parser.elemcount :
                                params.append([param[-1], None, list(np.array(array).shape), [var]   ])
                            elif np.array(array).shape[1] == parser.facesnodescount :
                                params.append([param[-1], None,  list(np.array(array).shape ), [var]    ])
                            elif np.array(array).shape[1] == parser.facescount :
                                params.append([param[-1], 2,  list(np.array(array).shape ), [var]    ])
                        else:
                            params.append([param[-1], None,  list(np.array(array).shape ), [var]    ])
                    
        print params
        
        paramsdef = []
        for param in params :
            if param[2][1] == parser.elemcount :
                param[1] = 0
                paramsdef.append(param)
            elif param[2][1] == parser.facesnodescount :
                param[1] = 1
                paramsdef.append(param)
            elif param[2][1]  == parser.facescount :
                param[1] = 2
                paramsdef.append(param)
                
        print paramsdef

def doThings():
    timestart = time.clock()
    debugtext = []
    if False:
        try:
            print 'DEBUT'
            rubberband = qgis.gui.QgsRubberBand(iface.mapCanvas(), qgis.core.QGis.Point)
            path = os.path.normpath('C://00_Bureau//data//baldeagle_multi2d.hdf')
            #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
            #hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
            
            FacePoints_Coordinate = []
            Faces_FacePoint_Indexes = []
            Cells_Center_Coordinate = []
            Faces_Cell_Indexes = []
            #datasets
            
            #print hydraufile.GetSubDatasets()[0]
            
            #print hdf_ds.GetSubDatasets()[1][1].readAsArray()
            hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
            #print hdf_ds.GetSubDatasets() 
            lensubdataset = len(hdf_ds.GetSubDatasets() )
            hdf_ds = None
            print lensubdataset
            
            if True :
            
                for i in range(lensubdataset):
                    try:
                        hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                        var = hdf_ds.GetSubDatasets()[i][0]
                        hdf_ds = None
                        str1 = str(var.split(':')[-1])
                        #print 'variable ' + str(i) + ' ' + str1
                        print str1.split('//')[1].split('/')
                        param = str1.split('/')[-1]
                        
                        
                        if True:
                            band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                            array = np.array(band_ds.ReadAsArray())
                            band_ds = None
                            print array.shape
                            print array[0:5]
                        
                        if False and param == 'FacePoints_Coordinate':
                        
                            band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                            array = np.array(band_ds.ReadAsArray())
                            FacePoints_Coordinate.append(array)
                            band_ds = None
                        
                        if False and param == 'Faces_FacePoint_Indexes':
                            band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                            Faces_FacePoint_Indexes.append(np.array(band_ds.ReadAsArray()) )
                            band_ds = None
                            
                        if False and param == 'Cells_Center_Coordinate':
                            band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                            Cells_Center_Coordinate.append(np.array(band_ds.ReadAsArray()) )
                            band_ds = None
                            
                            
                            
                        if False and param == 'Faces_Cell_Indexes':
                            band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                            Faces_Cell_Indexes.append(np.array(band_ds.ReadAsArray()) )
                            print np.max(np.array(band_ds.ReadAsArray()))
                            print Faces_Cell_Indexes[-1][0:10]
                            band_ds = None
                            
                        
         
                        
                        
                                
                        
                    except Exception, e :
                        print 'error ' + str(e)
            
            #band_ds = None
            #hdf_ds = None
            #rubberband.reset(qgis.core.QGis.Point)
            if False:   #mesh
                print 'rubbreband'
                rubberband = qgis.gui.QgsRubberBand(iface.mapCanvas(), qgis.core.QGis.Point)
                rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
                #print centerppoints
                for centerppoint in Cells_Center_Coordinate :
                    for i, point in enumerate(centerppoint) :
                            print point
                            rubberband.addPoint( qgis.core.QgsPoint(point[0],point[1]) )
            
            if False:   #centercells
                print 'rubbreband'
                rubberband = qgis.gui.QgsRubberBand(iface.mapCanvas(), qgis.core.QGis.Line)
                rubberband.setWidth(2)
                rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
                for i, indexface in enumerate(Faces_FacePoint_Indexes) :
                    for elems in indexface :
                            points = []
                            for elem in elems :
                                if elem != -1 :
                                    points.append( qgis.core.QgsPoint(FacePoints_Coordinate[i][elem][0],FacePoints_Coordinate[i][elem][1]) ) 
                            rubberband.addGeometry(qgis.core.QgsGeometry.fromPolygon([points]), None)
            
            
            if False:    #cells connectivity
                print 'rubbreband'
                rubberband = qgis.gui.QgsRubberBand(iface.mapCanvas(), qgis.core.QGis.Line)
                rubberband.setWidth(2)
                rubberband.setColor(QtGui.QColor(QtCore.Qt.red))
                for i, indexface in enumerate(Faces_Cell_Indexes) :
                    for elems in indexface :
                            points = []
                            for elem in elems :
                                points.append( qgis.core.QgsPoint(Cells_Center_Coordinate[i][elem][0],Cells_Center_Coordinate[i][elem][1]) ) 
                            rubberband.addGeometry(qgis.core.QgsGeometry.fromPolygon([points]), None)
            
            #rubberband.reset(qgis.core.QGis.Point)
            
            if False:
                print 'go'
                hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                #print hdf_ds.GetSubDatasets() 
                lensubdataset = len(hdf_ds.GetSubDatasets() )
                hdf_ds = None
                
                bottomid = []
                bottomvalue = []
                finalbottomvalue = []
                
                for i in range(1,lensubdataset):
                    hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                    var = hdf_ds.GetSubDatasets()[i][0]
                    hdf_ds = None
                    #print var
                    str1 = str(var.split(':')[-1])
                    #print str1
                    paramid = str1.split('//')[1].split('/')
                    
                    #print paramid
                    
                    if paramid[-1] == 'Cells_Volume_Elevation_Info':
                        band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray()
                        bottomid.append(array)
                        band_ds = None
                        
                    if paramid[-1] == 'Cells_Volume_Elevation_Values':
                        band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray().tolist()
                        bottomvalue.append(array)
                        band_ds = None
                        
                print 'ok1'
                            
                for i,bottid in enumerate(bottomid):
                    #print np.array(bottomvalue[i]).shape
                    #print np.array(bottid)[:,0].shape
                    temp1 = np.array(bottid)[:,0]
                    #print len(temp1)
                    temp1[ temp1 == len(bottomvalue[i])] = -1
                    
                    tempbotvalue = np.array(bottomvalue[i])[temp1][:,0]
                    finalbottomvalue +=  tempbotvalue.tolist() 
                print finalbottomvalue
            
            
            
            
           
            if True:
                print 'go'
                hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                #print hdf_ds.GetSubDatasets() 
                lensubdataset = len(hdf_ds.GetSubDatasets() )
                hdf_ds = None
                
                bottomid = []
                bottomvalue = []
                finalbottomvalue = []
                
                for i in range(1,lensubdataset):
                    hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                    var = hdf_ds.GetSubDatasets()[i][0]
                    hdf_ds = None
                    #print var
                    str1 = str(var.split(':')[-1])
                    #print str1
                    paramid = str1.split('//')[1].split('/')
                    
                    #print paramid
                    
                    if paramid[0] == 'Results' and '2D_Flow_Areas' in paramid:
                        print paramid[-1]
                        band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray()
                        print np.array(array).shape
                    
                    if False and paramid[-1] == 'Cells_Volume_Elevation_Info':
                        band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray()
                        bottomid.append(array)
                        band_ds = None
                        
                    if False and paramid[-1] == 'Cells_Volume_Elevation_Values':
                        band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray().tolist()
                        bottomvalue.append(array)
                        band_ds = None
                        
                print 'ok1'
                            

            
            print 'END'
        except Exception, e:
            print str(e)
    
    
    if True:
        print 'DEBUT'
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        parser = PostTelemacHDFParser()
        parser.loadHydrauFile(path)
        
        debugtext += ['parser loaded: ' + str(round(time.clock()-timestart,3))  ]
        
        a = parser.getElemRawValue(0)
        
        debugtext += ['raw val : ' + str(round(time.clock()-timestart,3))  ]
        
        #vtx = self.__vtxfacetodraw[sum(self.__idxfacetodraw,[])]
        idxfacetodraw = parser.getElemFaces()
        debugtext += ['get faces: ' + str(round(time.clock()-timestart,3))  ]
        #test1 = np.ravel(idxfacetodraw)
        test1 = np.concatenate(idxfacetodraw)
        debugtext += ['get faces 1D : ' + str(round(time.clock()-timestart,3))  ]
        
        print test1[0:20]
        print len(test1)
        
        print debugtext
    
        
        print 'Fin'
        
        
        
        


def geValues():
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        parser = PostTelemacHDFParser()
        parser.loadHydrauFile(path)
        params = parser.getVarNames()
        print parser.varnames
        
        rawvalue = []
        time = 0
        for param in parser.varnames:
            if param[1] == 0:
                tempval = np.array([])
                if param[3] != None:
                    for name in param[3]:
                        band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray()
                        band_ds = None
                        print np.array(array).shape
                        if np.array(array).shape[0] == 2:
                            #print '****************************'
                            #print np.array(array)
                            #print array[0] .shape
                            #np.append(tempval,array[0])
                            #np.vstack((tempval,array[0]))
                            tempval = np.concatenate((tempval,array[0]))
                            #tempval.append( array[0] )
                        else:
                            #tempval.append( array[time] )
                            #np.append(tempval,array[time])
                            #np.vstack((tempval,array[time]))
                            tempval = np.concatenate((tempval,array[time]))
                            #print array[time].shape
                        #rawvalue.append(np.array(array[time1]))
                        #print tempval
                    print tempval.shape
                    rawvalue.append(np.array(tempval))
        
        print np.array(rawvalue).shape
        #print np.array(rawvalue)[0]



def getValues2():
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        parser = PostTelemacHDFParser()
        parser.loadHydrauFile(path)
        
        print parser.getVarNames()
        print parser.parametres


def getVars():
        print 'DEBUT'
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        #hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
        
        hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
        lensubdataset = len(hdf_ds.GetSubDatasets() )
        hdf_ds = None
        
        if True :
        
            for i in range(1,lensubdataset):
                hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(':')[-1])
                #print 'variable ' + str(i) + ' ' + str1
                print str1.split('//')[1].split('/')
                param = str1.split('/')[-1]
                
                
                if True:
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = np.array(band_ds.ReadAsArray())
                    band_ds = None
                    print array.shape
                    print array[0:5]
                    
def testimport():
    from os.path import dirname, basename, isfile
    import glob
    path = os.path.dirname('C:\Users\patrice.verchere\Documents\GitHub\PostTelemac\meshlayerparsers\__init__.py')
    print path
    dirname = ''
    #modules = glob.glob(dirname(__file__)+"/*.py")
    modules = glob.glob(path+"/*.py")
    print modules
    __all__ = [ basename(f)[:-3] for f in modules if isfile(f)]
    print __all__
    
    import sys, inspect
    import importlib
    
    

    for x in __all__:
        module = importlib.import_module('.'+ str(x), 'PostTelemac.meshlayerparsers' )
        for name, obj in inspect.getmembers(module, inspect.isclass):
            #print obj
            try: 
                #print obj.TYPE
                obj.EXTENSION
                test = obj()
                print obj
                print test.elemcount
            except Exception, e:
                pass
                #print str(e)
                

    


def getFace():
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        parser = PostTelemacHDFParser()
        parser.loadHydrauFile(path)
        
        face = parser.getElemFaces()
        
        face1 = [np.array(a) for a in face]
        
        print face1[0]
        
        result = []
        print 'ok'
        for i, elem in enumerate(face1):
            if len(np.where(elem ==  3 )[0])>0:
                result.append(i)
        print result
        faces = np.where(np.array(face1) ==  3 )
        print len(faces)
        
        print faces
        
        
def getTimeserie():
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        parser = PostTelemacHDFParser()
        parser.loadHydrauFile(path)
        #getTimeSerie(self, arraynumpoint ,arrayparam,layerparametres = None)
        
        print parser.itertimecount
        
        temp = parser.getElemRawValue(0)
        temp = parser.getTimeSerie([0],[6])
        
        print temp
        
        
        

#if __name__ == '__main__':
#doThings()
getParams()
#geValues()
#getValues2()
#getVars()
#testimport()
#getFace()
#getTimeserie()