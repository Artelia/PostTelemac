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
import time
import numpy as np
from osgeo import gdal

import subprocess

from .posttelemac_abstract_parser import PostTelemacAbstractParser

MESHX = "x"
MESHY = "y"
IKLE = "volumes"
TIME = "time"
BATHY = "elevation"

TYPENDVAR = 1  # 0 for 1d array 1 for ReadAsArray


class PostTelemacHDFParser(PostTelemacAbstractParser):

    SOFTWARE = "HECRAS"
    EXTENSION = ["hdf"]

    def __init__(self, layer1=None):
        super(PostTelemacHDFParser, self).__init__(layer1)
        self.varnames = None
        self.ikle = None
        self.time = None
        self.onedvar = {}
        self.bottomvalue = None
        self.rawvaluetotal = None
        self.facenodes = None
        self.facesrawvalues = []

        try:
            from . import h5py
        except Exception as e:
            self.emitMessage.emit("h5py error : " + str(e))

    def initPathDependantVariablesWhenLoading(self):
        pass

    def getTimes(self):
        """
        return array of times computed
        """
        # return np.array(range(100))

        if self.time is None:
            hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
            # print hdf_ds.GetSubDatasets()
            lensubdataset = len(hdf_ds.GetSubDatasets())
            hdf_ds = None

            for i in range(1, lensubdataset):
                hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(":")[-1])
                param = str1.split("//")[1].split("/")
                if "Unsteady_Time_Series" in param:
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()
                    band_ds = None

                    self.time = np.array(range(array.shape[0]))

                    break

        return self.time

    # ****************************************************************************************
    # ****************************************************************************************
    # ****************************************************************************************

    def getVarNames(self):
        """

        var 0 : bottom

        self.varnames : [..., [ varname, type : 0 : elem 1 : facenode 2 : face , varnameinhdffile ], ...]

        return np.array[varname, typevar (0 : elem, 1 : facenode, 2 : face)]
        """
        # return np.array([['test',0]])

        """
        hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
        #print hdf_ds.GetSubDatasets() 
        lensubdataset = len(hdf_ds.GetSubDatasets() )
        hdf_ds = None
        
        
        self.varnames = []
        self.varnames.append(['Botttom', 0, None])
        
        if False:
            for i in range(1,lensubdataset):

                hdf_ds = gdal.Open(path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(':')[-1])
                paramid = str1.split('//')[1].split('/')
                if paramid[-1] == 'Cells_Volume_Elevation_Info':
                    finalbottomvalue[0] = True
                    
                if paramid[-1] == 'Cells_Volume_Elevation_Values':
                    finalbottomvalue[1] = True
                    
        
                
        return  [[var[0], var[1]] for var in self.varnames]
        """
        """
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        #path =  os.path.normpath('C://00_Bureau//data2//test3.hdf')
        parser = PostTelemacHDFParser()
        parser.loadHydrauFile(path)
        """
        """
        self.elemcount = len(   self.getElemFaces() )
        self.facesnodescount = len(self.getFacesNodes()[0]   )
        self.facescount = len(   self.getFaces() )
        self.itertimecount = len(self.getTimes())-1
        """
        """
        print parser.elemcount
        print parser.facesnodescount
        print parser.facescount
        print parser.itertimecount
        """

        if self.varnames is None:

            hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
            # print hdf_ds.GetSubDatasets()
            lensubdataset = len(hdf_ds.GetSubDatasets())
            hdf_ds = None

            params = [["Bottom", -1, [2, self.elemcount], None]]

            for i in range(1, lensubdataset):
                hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(":")[-1])
                param = str1.split("//")[1].split("/")
                if "Results" in param and "2D_Flow_Areas" in param:
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()
                    band_ds = None
                    if param[-1] in np.array(params)[:, 0].tolist():
                        index = np.array(params)[:, 0].tolist().index(param[-1])
                        params[index][2][1] += np.array(array).shape[1]
                        params[index][3].append(var)
                    else:
                        params.append([param[-1], None, list(np.array(array).shape), [var]])

            paramsdef = []
            # paramsdef.append(['Bottom', -1, [2,self.elemcount], None])
            for param in params:
                if param[2][1] == self.elemcount:
                    param[1] = 0
                    paramsdef.append(param)
                elif param[2][1] == self.facesnodescount:
                    param[1] = 1
                    paramsdef.append(param)
                elif param[2][1] == self.facescount:
                    param[1] = 2
                    paramsdef.append(param)

            self.varnames = paramsdef

        return [[var[0], var[1]] for var in self.varnames]

    # *********** Elems

    def getElemNodes(self):
        """
        xyz
        3T : /
        hec : Cells_Center_Coordinate

        return (np.array(x), np.array(y) )
        """
        return (np.array([]), np.array([]))

    def getElemRawValue(self, time1):
        """
        3T : /
        hec : value

        return np.array[param number][node value for param number]

        """
        # first : bottom

        DEBUGTIME = False
        timestart = time.clock()

        rawvalue = []

        if self.bottomvalue is None:

            hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
            # print hdf_ds.GetSubDatasets()
            lensubdataset = len(hdf_ds.GetSubDatasets())
            hdf_ds = None

            bottomid = []
            bottomvalue = []
            finalbottomvalue = []

            if DEBUGTIME:
                print("file subdata read : " + str(round(time.clock() - timestart, 3)))

            for i in range(1, lensubdataset):
                hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(":")[-1])
                paramid = str1.split("//")[1].split("/")
                if paramid[-1] == "Cells_Volume_Elevation_Info":
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()
                    bottomid.append(array)
                    band_ds = None

                if paramid[-1] == "Cells_Volume_Elevation_Values":
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()
                    bottomvalue.append(array)
                    band_ds = None

            for i, bottid in enumerate(bottomid):
                # print np.array(bottomvalue[i]).shape
                # print np.array(bottid)[:,0].shape
                temp1 = np.array(bottid)[:, 0]
                # print len(temp1)
                temp1[temp1 == len(bottomvalue[i])] = -1

                tempbotvalue = np.array(bottomvalue[i])[temp1][:, 0]
                finalbottomvalue += tempbotvalue.tolist()
            # self.bottomvalue = np.array(finalbottomvalue)
            self.bottomvalue = np.transpose(
                np.repeat(np.array(finalbottomvalue), (self.itertimecount + 1)).reshape((-1, (self.itertimecount + 1)))
            )

        """
        else:
            rawvalue.append(self.bottomvalue )
        """

        if DEBUGTIME:
            print("fbottom value : " + str(round(time.clock() - timestart, 3)))

        if False:
            if self.rawvaluetotal is None:

                for param in self.varnames:
                    if param[1] == 0:
                        tempval = np.array([])
                        if param[3] != None:
                            for name in param[3]:
                                if False:
                                    if DEBUGTIME:
                                        print(
                                            "param : "
                                            + str(param[0])
                                            + " begin "
                                            + str(round(time.clock() - timestart, 3))
                                        )
                                    band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                                    array = band_ds.ReadAsArray()
                                    band_ds = None
                                    if DEBUGTIME:
                                        print(
                                            "param : "
                                            + str(param[0])
                                            + " array read "
                                            + str(round(time.clock() - timestart, 3))
                                        )
                                    if np.array(array).shape[0] == 2:
                                        tempval = np.concatenate((tempval, array[0]))
                                    else:
                                        tempval = np.concatenate((tempval, array[time1]))
                                    if DEBUGTIME:
                                        print(
                                            "param : "
                                            + str(param[0])
                                            + " concatenate "
                                            + str(round(time.clock() - timestart, 3))
                                        )

                                if True:
                                    if DEBUGTIME:
                                        print(
                                            "param : "
                                            + str(param[0])
                                            + " begin "
                                            + str(round(time.clock() - timestart, 3))
                                        )
                                    band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                                    array = band_ds.ReadAsArray()
                                    band_ds = None
                                    if DEBUGTIME:
                                        print(
                                            "param : "
                                            + str(param[0])
                                            + " array read "
                                            + str(round(time.clock() - timestart, 3))
                                        )
                                    if array.shape[0] == 2:
                                        tempval = np.concatenate((tempval, array[0]))
                                    else:
                                        tempval = np.concatenate((tempval, array[time1]))
                                    if DEBUGTIME:
                                        print(
                                            "param : "
                                            + str(param[0])
                                            + " concatenate "
                                            + str(round(time.clock() - timestart, 3))
                                        )
                            rawvalue.append(np.array(tempval))
                            if DEBUGTIME:
                                print(
                                    "param : "
                                    + str(param[0])
                                    + " append raw value "
                                    + str(round(time.clock() - timestart, 3))
                                )

                if DEBUGTIME:
                    print("done : " + str(round(time.clock() - timestart, 3)))

                return rawvalue

        if self.rawvaluetotal == []:

            self.rawvaluetotal.append(self.bottomvalue)

            for param in self.varnames:
                if param[1] == 0:
                    # self.rawvaluetotal.append(np.array([]))
                    tempval = None
                    if param[3] != None:
                        for name in param[3]:
                            if False:
                                if DEBUGTIME:
                                    print(
                                        "param : " + str(param[0]) + " begin " + str(round(time.clock() - timestart, 3))
                                    )
                                band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                                array = band_ds.ReadAsArray()
                                band_ds = None
                                if DEBUGTIME:
                                    print(
                                        "param : "
                                        + str(param[0])
                                        + " array read "
                                        + str(round(time.clock() - timestart, 3))
                                    )
                                if np.array(array).shape[0] == 2:
                                    tempval = np.concatenate((tempval, array[0]))
                                else:
                                    tempval = np.concatenate((tempval, array[time1]))
                                if DEBUGTIME:
                                    print(
                                        "param : "
                                        + str(param[0])
                                        + " concatenate "
                                        + str(round(time.clock() - timestart, 3))
                                    )

                            if True:
                                band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                                array = band_ds.ReadAsArray()
                                band_ds = None
                                if array.shape[0] == 2:
                                    if tempval == None:
                                        # np.transpose(np.repeat(np.array(finalbottomvalue), self.itertimecount).reshape((-1,self.itertimecount)) )
                                        # tempval = array[0]
                                        tempval = np.transpose(
                                            np.repeat(np.array(array[0]), (self.itertimecount + 1)).reshape(
                                                (-1, (self.itertimecount + 1))
                                            )
                                        )

                                    else:
                                        temp1 = np.transpose(
                                            np.repeat(np.array(array[0]), (self.itertimecount + 1)).reshape(
                                                (-1, (self.itertimecount + 1))
                                            )
                                        )
                                        # tempval = np.concatenate((tempval,array[0]))
                                        tempval = np.concatenate((tempval, temp1), axis=1)
                                else:
                                    if tempval == None:
                                        tempval = array
                                    else:
                                        tempval = np.concatenate((tempval, array), axis=1)
                        self.rawvaluetotal.append(np.array(tempval))
                        # print str(param[0]) + ' ' +str(self.rawvaluetotal[-1].shape)

            self.rawvaluetotal = np.array(self.rawvaluetotal)

        rawvalue = []

        for param in self.rawvaluetotal:
            """
            if len(param.shape) == 1 :
                rawvalue.append(param)
            else:
                rawvalue.append(param[time1])
            """
            rawvalue.append(param[time1])

        return rawvalue

    def getElemRawTimeSerie(self, arraynumelemnode, arrayparam, layerparametres=None):
        """

        return np.array[param][numelem][value for time t]

        """
        # print 'getElemRawTimeSerie'

        if self.rawvaluetotal is None:
            self.getElemRawValue(0)

        result = []

        for param in arrayparam:
            temp1 = np.transpose(self.rawvaluetotal[param])
            result.append(temp1[arraynumelemnode])

        """
        for numelem in arraynumelemnode:
            print self.rawvaluetotal.shape
            print np.transpose(self.rawvaluetotal).shape
            
            value = np.transpose(self.rawvaluetotal)[arrayparam]
            if value.shape[0]==1:
                value = np.array(value.tolist()*itertimecount)
            print 'value ' + str(value.shape)
            #result.append(value)
        """

        return np.array(result)

    # *********** Face Node

    def getFacesNodes(self):
        """
        3T : xyz
        hec : FacePoints_Coordinate

        return (np.array(x), np.array(y) )

        """
        if self.facenodes is None:
            FacePoints_Coordinate = []

            hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
            # print hdf_ds.GetSubDatasets()
            lensubdataset = len(hdf_ds.GetSubDatasets())
            hdf_ds = None

            for i in range(lensubdataset):
                hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(":")[-1])
                param = str1.split("/")[-1]
                if param == "FacePoints_Coordinate":
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray().tolist()
                    FacePoints_Coordinate += array
                    band_ds = None

            arraytemp = np.array(FacePoints_Coordinate)

            self.facenodes = (arraytemp[:, 0], arraytemp[:, 1])

        return self.facenodes

    def getElemFaces(self):
        """
        It's the mesh
        3T : ikle
        hec : Faces_FacePoint_Indexes

        return np.array([facenodeindex linked with the elem ])
        """
        if self.elemfacesindex is None:
            Cells_FacePoint_Indexes = []
            hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
            # print hdf_ds.GetSubDatasets()
            lensubdataset = len(hdf_ds.GetSubDatasets())
            hdf_ds = None

            for i in range(lensubdataset):
                hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(":")[-1])
                param = str1.split("/")[-1]
                if param == "Cells_FacePoint_Indexes":
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()

                    if len(Cells_FacePoint_Indexes) > 0:
                        maxidx = np.max(Cells_FacePoint_Indexes)
                    else:
                        maxidx = -1

                    arraytranslated = np.array(array) + (maxidx + 1)
                    arraytranslated[arraytranslated < maxidx + 1] = -1

                    Cells_FacePoint_Indexes += arraytranslated.tolist()
                    band_ds = None

            Cells_FacePoint_Indexes = [[idx for idx in idxface if idx != -1] for idxface in Cells_FacePoint_Indexes]

            self.elemfacesindex = np.array(Cells_FacePoint_Indexes)
            return self.elemfacesindex
        else:
            return self.elemfacesindex

    def getFacesNodesRawValues(self, time1):
        """
        3T : getvalues

        return np.array[param number][node value for param number]

        """
        """
        temp =  np.array( [np.array([0.0]*self.facesnodescount)] )
        return temp
        """
        rawvalue = []

        for param in self.varnames:
            if param[1] == 1:
                tempval = np.array([])
                if param[3] != None:
                    for name in param[3]:

                        band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                        array = band_ds.ReadAsArray()
                        band_ds = None
                        if array.shape[0] == 2:
                            """
                            if tempval == None:
                                tempval = array[0]
                            else:
                                tempval = np.concatenate((tempval,array[0]))
                            """
                            if tempval == None:
                                # np.transpose(np.repeat(np.array(finalbottomvalue), self.itertimecount).reshape((-1,self.itertimecount)) )
                                # tempval = array[0]
                                tempval = np.transpose(
                                    np.repeat(np.array(array[0]), (self.itertimecount + 1)).reshape(
                                        (-1, (self.itertimecount + 1))
                                    )
                                )

                            else:
                                temp1 = np.transpose(
                                    np.repeat(np.array(array[0]), (self.itertimecount + 1)).reshape(
                                        (-1, (self.itertimecount + 1))
                                    )
                                )
                                # tempval = np.concatenate((tempval,array[0]))
                                tempval = np.concatenate((tempval, temp1), axis=1)

                        else:
                            if tempval == None:
                                tempval = array
                            else:
                                tempval = np.concatenate((tempval, array), axis=1)
                rawvalue.append(np.array(tempval))
                # print str(param[0]) + ' ' +str(self.rawvaluetotal[-1].shape)

        rawvalue = np.array(rawvalue)

        return rawvalue

    def getFacesNodesRawTimeSeries(self, arraynumelemnode, arrayparam, layerparametres=None):
        """
        3T : getvalues

        return np.array[param][numelem][value for time t]

        """
        return np.array([])

    # *********** Face

    def getFaces(self):
        """
        return np.array([facenodeindex linked with the face ])
        """
        if self.facesindex is None:
            Faces_FacePoint_Indexes = []

            hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
            # print hdf_ds.GetSubDatasets()
            lensubdataset = len(hdf_ds.GetSubDatasets())
            hdf_ds = None

            for i in range(lensubdataset):
                hdf_ds = gdal.Open(self.path, gdal.GA_ReadOnly)
                var = hdf_ds.GetSubDatasets()[i][0]
                hdf_ds = None
                str1 = str(var.split(":")[-1])
                param = str1.split("/")[-1]
                if param == "Faces_FacePoint_Indexes":
                    band_ds = gdal.Open(var, gdal.GA_ReadOnly)
                    array = band_ds.ReadAsArray()

                    if len(Faces_FacePoint_Indexes) > 0:
                        # maxidx = max (max(np.array(Faces_FacePoint_Indexes)[:,0]),max(np.array(Faces_FacePoint_Indexes)[:,1]) )
                        maxidx = np.max(Faces_FacePoint_Indexes)
                    else:
                        maxidx = -1

                    arraytranslated = np.array(array) + (maxidx + 1)
                    Faces_FacePoint_Indexes += arraytranslated.tolist()
                    """
                    if len(Faces_FacePoint_Indexes) == 0:
                        Faces_FacePoint_Indexes = arraytranslated
                    else:
                        print Faces_FacePoint_Indexes.shape
                        print arraytranslated.shape
                        np.append(Faces_FacePoint_Indexes, arraytranslated, axis = 0)
                    """
                    band_ds = None

            self.facesindex = np.array(Faces_FacePoint_Indexes)
            return self.facesindex
        else:
            return self.facesindex

    def getFacesRawValues(self, time1):
        """
        3T : /
        hec : velocity
        return np.array[param number][node value for param number]

        """
        # return np.array([])
        if False:
            rawvalue = []

            for param in self.varnames:
                if param[1] == 2:
                    tempval = np.array([])
                    if param[3] != None:
                        for name in param[3]:
                            band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                            array = band_ds.ReadAsArray()
                            band_ds = None
                            if np.array(array).shape[0] == 2:
                                tempval = np.concatenate((tempval, array[0]))
                            else:
                                tempval = np.concatenate((tempval, array[time1]))
                        rawvalue.append(np.array(tempval))

            return rawvalue

        if True:
            DEBUGTIME = False
            timestart = time.clock()

            rawvalue = []

            if self.facesrawvalues == []:

                for param in self.varnames:
                    if param[1] == 2:
                        # self.rawvaluetotal.append(np.array([]))
                        tempval = None
                        if param[3] != None:
                            for name in param[3]:
                                if True:
                                    band_ds = gdal.Open(name, gdal.GA_ReadOnly)
                                    array = band_ds.ReadAsArray()
                                    band_ds = None
                                    if array.shape[0] == 2:
                                        """
                                        if tempval == None:
                                            tempval = array[0]
                                        else:
                                            tempval = np.concatenate((tempval,array[0]))
                                        """
                                        if tempval == None:
                                            # np.transpose(np.repeat(np.array(finalbottomvalue), self.itertimecount).reshape((-1,self.itertimecount)) )
                                            # tempval = array[0]
                                            tempval = np.transpose(
                                                np.repeat(np.array(array[0]), (self.itertimecount + 1)).reshape(
                                                    (-1, (self.itertimecount + 1))
                                                )
                                            )

                                        else:
                                            temp1 = np.transpose(
                                                np.repeat(np.array(array[0]), (self.itertimecount + 1)).reshape(
                                                    (-1, (self.itertimecount + 1))
                                                )
                                            )
                                            # tempval = np.concatenate((tempval,array[0]))
                                            tempval = np.concatenate((tempval, temp1), axis=1)

                                    else:
                                        if tempval == None:
                                            tempval = array
                                        else:
                                            tempval = np.concatenate((tempval, array), axis=1)
                            self.facesrawvalues.append(np.array(tempval))
                            # print str(param[0]) + ' ' +str(self.rawvaluetotal[-1].shape)

                self.facesrawvalues = np.array(self.facesrawvalues)

            rawvalue = []

            for param in self.facesrawvalues:
                """
                if len(param.shape) == 1 :
                    rawvalue.append(param)
                else:
                    rawvalue.append(param[time1])
                """
                rawvalue.append(param[time1])

            return rawvalue

    def getFacesRawTimeSeries(self, arraynumelemnode, arrayparam, layerparametres=None):
        """
        3T : /
        hec : velocity

        return np.array[param][numelem][value for time t]

        """
        # print 'getElemRawTimeSerie'

        if self.facesrawvalues is None:
            self.getElemRawValue(0)

        result = []

        for param in arrayparam:
            temp1 = np.transpose(self.facesrawvalues[param])
            result.append(temp1[arraynumelemnode])

        """
        for numelem in arraynumelemnode:
            print self.rawvaluetotal.shape
            print np.transpose(self.rawvaluetotal).shape
            
            value = np.transpose(self.rawvaluetotal)[arrayparam]
            if value.shape[0]==1:
                value = np.array(value.tolist()*itertimecount)
            print 'value ' + str(value.shape)
            #result.append(value)
        """

        return np.array(result)
