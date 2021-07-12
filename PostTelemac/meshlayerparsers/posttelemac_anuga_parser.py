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
import osgeo.gdal
import subprocess
from .posttelemac_abstract_parser import PostTelemacAbstractParser


MESHX = "x"
MESHY = "y"
IKLE = "volumes"
TIME = "time"
BATHY = "elevation"

TYPENDVAR = 1  # 0 for 1d array 1 for ReadAsArray


class PostTelemacSWWParser(PostTelemacAbstractParser):

    SOFTWARE = "ANUGA"
    EXTENSION = ["sww"]

    def __init__(self, layer1=None):
        super(PostTelemacSWWParser, self).__init__(layer1)
        self.varnames = None
        self.ikle = None
        self.time = None
        self.facesindex == None
        self.onedvar = {}

    def initPathDependantVariablesWhenLoading(self):
        self.hydraufile = gdal.Open('NETCDF:"' + self.path + '"')
        # x y tranlsation
        dump = self.getNcDumpVar()[4]
        names = [tt1[0] for tt1 in dump]
        indexxllcorner = names.index("xllcorner")
        indexyllcorner = names.index("yllcorner")
        self.translatex = float(dump[indexxllcorner][1])
        self.translatey = float(dump[indexyllcorner][1])

    if False:

        def getRawValues(self, time1):
            """
            return array :
            array[param number][node value for param number]
            """
            result = []
            for var in self.varnames:
                if var[1] == 1:
                    result.append(self.get1DVar(var[0]))
                elif var[1] == 2:
                    if TYPENDVAR:
                        result.append(np.array(var[2].ReadAsArray())[::-1, :][time1])
                    else:
                        result.append(np.array(self.getNDVar(var[0])).reshape((-1, self.pointcount))[time1])

            return np.array(result)

        def getRawTimeSerie(self, arraynumpoint, arrayparam, layerparametres=None):
            """
            Warning : point index begin at 1
            [..., param[numpts[values]], ... ]
            """
            result = []
            for param in arrayparam:
                if self.varnames[param][1] == 1:
                    tt1 = np.array(self.get1DVar(self.varnames[param][0]))
                    tt2 = tt1[np.array(arraynumpoint) - 1]
                    tt3 = [[[tt4] * (self.itertimecount + 1)] for tt4 in tt2]
                    result.append(np.array(tt3[0]))
                elif self.varnames[param][1] == 2:
                    tt1 = np.array(self.getNDVar(self.varnames[param][0]))
                    tt1 = np.transpose(tt1)
                    tt2 = tt1[np.array(arraynumpoint) - 1]
                    result.append(tt2[::-1, :])
            return np.array(result)

        def getMesh(self):
            # tranlsation info
            return (np.array(self.get1DVar(MESHX)) + self.translatex, np.array(self.get1DVar(MESHY)) + self.translatey)

        def getVarnames(self):
            """
            return [...[varname, dimension],...]
            """
            # self.hydraufile = gdal.Open('NETCDF:"'+self.path+'"')

            if self.varnames == None:
                dump = self.getNcDumpVar()[2]
                varnames = []
                for str1 in dump:
                    if len(str1[2]) == 1:
                        if str1[1] != MESHX and str1[1] != MESHY and str1[1] != TIME:
                            if len(self.get1DVar(str1[1])) == self.pointcount:
                                varnames.append([str1[1], 1, None])

                    elif len(str1[2]) == 2:
                        if str1[1] != IKLE:
                            if TYPENDVAR:
                                temp = self.getNDVar(str1[1])[0]
                            else:
                                temp = np.array(self.getNDVar(str1[1])).reshape((self.pointcount, -1))

                            if len(temp) == self.pointcount:
                                varnames.append([str1[1], 2])
                                if True:
                                    u = self.hydraufile.GetSubDatasets()
                                    int1 = 0
                                    for i, arr in enumerate(u):
                                        layer1 = arr[0].split(":")[-1]
                                        if layer1 == str1[1]:
                                            file1 = gdal.Open(arr[0])
                                            break
                                    varnames[-1].append(file1)

                self.varnames = varnames

            # self.hydraufile = None
            return [var[0] for var in self.varnames]

        def getIkle(self):
            if self.ikle == None:
                if TYPENDVAR:
                    self.ikle = self.getNDVar(IKLE)
                else:
                    temp = np.array(self.getNDVar(IKLE))
                    self.ikle = np.reshape(temp, (-1, 3)).astype(int)
            return self.ikle

    def getTimes(self):
        if self.time == None:
            self.time = np.array(self.get1DVar(TIME))

        return self.time

    # ****************************************************************************************
    # ****************************************************************************************
    # ****************************************************************************************

    def getVarNames(self):
        """
        return np.array[varname, typevar (0 : elem, 1 : facenode, 2 : face)]

        self.varnames : array[..[name, timedependant or not, ?, typevar]]

        """
        # self.hydraufile = gdal.Open('NETCDF:"'+self.path+'"')

        if self.varnames == None:
            dump = self.getNcDumpVar()[2]
            varnames = []
            for str1 in dump:
                if len(str1[2]) == 1:
                    if str1[1] != MESHX and str1[1] != MESHY and str1[1] != TIME:
                        if len(self.get1DVar(str1[1])) == self.facesnodescount:
                            varnames.append([str1[1], 1, None, 1])

                elif len(str1[2]) == 2:
                    if str1[1] != IKLE:
                        if TYPENDVAR:
                            temp = self.getNDVar(str1[1])[0]
                        else:
                            temp = np.array(self.getNDVar(str1[1])).reshape((self.facesnodescount, -1))

                        if len(temp) == self.facesnodescount:
                            varnames.append([str1[1], 2])
                            if True:
                                u = self.hydraufile.GetSubDatasets()
                                int1 = 0
                                for i, arr in enumerate(u):
                                    layer1 = arr[0].split(":")[-1]
                                    if layer1 == str1[1]:
                                        file1 = gdal.Open(arr[0])
                                        break
                                varnames[-1].append(file1)
                                varnames[-1].append(1)

            self.varnames = varnames

        # self.hydraufile = None
        return [[var[0], var[3]] for var in self.varnames]

    def getVarNames2(self):
        """
        return np.array[varname, typevar (0 : elem, 1 : facenode, 2 : face)]

        self.varnames : array[..[name, timedependant or not, ?, typevar]]

        """
        # self.hydraufile = gdal.Open('NETCDF:"'+self.path+'"')

        if self.varnames == None:
            dump = self.getNcDumpVar()[2]
            varnames = []
            for str1 in dump:
                if len(str1[2]) == 1:
                    if str1[1] != MESHX and str1[1] != MESHY and str1[1] != TIME:
                        if len(self.get1DVar(str1[1])) == self.pointcount:
                            varnames.append([str1[1], 1, None, 1])

                elif len(str1[2]) == 2:
                    if str1[1] != IKLE:
                        if TYPENDVAR:
                            temp = self.getNDVar(str1[1])[0]
                        else:
                            temp = np.array(self.getNDVar(str1[1])).reshape((self.pointcount, -1))

                        if len(temp) == self.pointcount:
                            varnames.append([str1[1], 2])
                            if True:
                                u = self.hydraufile.GetSubDatasets()
                                int1 = 0
                                for i, arr in enumerate(u):
                                    layer1 = arr[0].split(":")[-1]
                                    if layer1 == str1[1]:
                                        file1 = gdal.Open(arr[0])
                                        break
                                varnames[-1].append(file1)
                                varnames[-1].append(1)

            self.varnames = varnames

        # self.hydraufile = None
        return [[var[0], var[3]] for var in self.varnames]

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
        return np.array([])

    def getElemRawTimeSerie(self, arraynumelemnode, arrayparam, layerparametres=None):
        """

        return np.array[param][numelem][value for time t]

        """
        return np.array([])

    # *********** Face Node

    def getFacesNodes(self):
        """
        3T : xyz
        hec : FacePoints_Coordinate

        return (np.array(x), np.array(y) )

        """
        return (np.array(self.get1DVar(MESHX)) + self.translatex, np.array(self.get1DVar(MESHY)) + self.translatey)

    def getElemFaces(self):
        """
        It's the mesh
        3T : ikle
        hec : Faces_FacePoint_Indexes

        return np.array([facenodeindex linked with the elem ])
        """
        if self.ikle == None:
            if TYPENDVAR:
                self.ikle = self.getNDVar(IKLE)
            else:
                temp = np.array(self.getNDVar(IKLE))
                self.ikle = np.reshape(temp, (-1, 3)).astype(int)
        return self.ikle

    def getFacesNodesRawValues(self, time1):
        """
        3T : getvalues

        return np.array[param number][node value for param number]

        """
        result = []
        for var in self.varnames:
            if var[1] == 1:
                result.append(self.get1DVar(var[0]))
            elif var[1] == 2:
                if TYPENDVAR:
                    result.append(np.array(var[2].ReadAsArray())[::-1, :][time1])
                else:
                    result.append(np.array(self.getNDVar(var[0])).reshape((-1, self.pointcount))[time1])

        return np.array(result)

    def getFacesNodesRawTimeSeries(self, arraynumelemnode, arrayparam, layerparametres=None):
        """
        3T : getvalues

        return np.array[param][numelem][value for time t]

        """
        result = []
        for param in arrayparam:
            if self.varnames[param][1] == 1:
                tt1 = np.array(self.get1DVar(self.varnames[param][0]))
                tt2 = tt1[np.array(arraynumelemnode)]
                tt3 = [[[tt4] * (self.itertimecount + 1)] for tt4 in tt2]
                result.append(np.array(tt3[0]))
            elif self.varnames[param][1] == 2:
                tt1 = np.array(self.getNDVar(self.varnames[param][0]))
                tt1 = np.transpose(tt1)
                tt2 = tt1[np.array(arraynumelemnode)]
                result.append(tt2[::-1, :])
        return np.array(result)

    # *********** Face

    def getFaces(self):
        """
        return np.array([facenodeindex linked with the face ])
        """
        """
        if self.facesindex == None :
            try:
                self.facesindex = np.array([(edge[0],edge[1]) for edge in self.triangulation.edges])
                return self.facesindex
            except Exception as e:
                return np.array([])
        else:
            return self.facesindex
        """
        """
        return np.array([facenodeindex linked with the face ])
        """
        if self.facesindex == None:
            if False:
                try:
                    self.facesindex = np.array([(edge[0], edge[1]) for edge in self.triangulation.edges])
                    return self.facesindex
                except Exception as e:
                    return np.array([])
            if True:
                ikle = self.getElemFaces()
                faceindex = []
                for tri in ikle:
                    faceindex.append([tri[0], tri[1]])
                    faceindex.append([tri[1], tri[2]])
                    faceindex.append([tri[2], tri[0]])
                faceindex = np.array(faceindex)
                self.facesindex = (
                    np.unique(faceindex.view(np.dtype((np.void, faceindex.dtype.itemsize * faceindex.shape[1]))))
                    .view(faceindex.dtype)
                    .reshape(-1, faceindex.shape[1])
                )
                return self.facesindex

        else:
            return self.facesindex

    def getFacesRawValues(self, time1):
        """
        3T : /
        hec : velocity
        return np.array[param number][node value for param number]

        """
        return np.array([])

    def getFacesRawTimeSeries(self, arraynumelemnode, arrayparam, layerparametres=None):
        """
        3T : /
        hec : velocity

        return np.array[param][numelem][value for time t]

        """
        return np.array([])

    def getNcDumpVar(self):
        str1 = "ncdump -h " + self.path
        p = subprocess.Popen(str1, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        temp = p.stdout.readlines()

        result = []
        for str1 in temp:
            if str1[0:1] == "\t" or str1[0:2] == "\t\t":
                if str1[0:1] == "\t":
                    result[-1] += [[str1.replace(" ;", "").replace("\r\n", "").replace("\t", "")]]
                elif str1[0:2] == "\t\t":
                    result[-1] += [[str1.replace(" ;", "").replace("\r\n", "").replace("\t\t", "")]]
            else:
                result.append([str1.replace(" ;", "").replace("\r\n", "")])

        # dimension process
        resultaray = []
        for str1 in result[1][1:]:
            tt1 = str1[0].split("=")
            tt2 = [tt3.strip() for tt3 in tt1]
            resultaray += [tt2]
        result[1] = resultaray

        # var process
        resultaray = []
        for str1 in result[2][1:]:
            temparray = []
            # vartype
            tt1 = str1[0].split()
            temparray += [tt1[0]]
            # varname
            tt2 = tt1[1].split("(")[0]
            temparray += [tt2]
            # dimensions
            tt2 = str1[0].replace(" ", "").replace("(", ";").replace(")", ";")
            tt3 = tt2.split(";")
            tt4 = [tt5 for tt5 in tt3[1:] if tt5 != ""]
            temparray += [tt4[0].split(",")]
            resultaray.append(temparray)
        result[2] = resultaray

        # Global process
        resultaray = []
        for str1 in result[4][1:]:
            tt1 = str1[0].split("=")
            tt2 = [tt3.strip().replace(":", "") for tt3 in tt1]
            resultaray += [tt2]
        result[4] = resultaray

        return result

    def get1DVar(self, varname):
        # print 'get1DVar'
        if varname not in self.onedvar.keys() or self.onedvar[varname] == None:
            str1 = "ncdump -v " + varname + " " + self.path
            p = subprocess.Popen(
                str1, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            temp = p.stdout.readlines()

            temp1 = [str2.replace("\r\n", "") for str2 in temp]
            int2 = temp1.index("data:")
            temp3 = temp1[int2 + 2 :]
            temp4 = []
            i = 0
            for test in temp3:
                temp5 = test.split(",")
                temp5 = [a.split("=")[-1] for a in temp5]
                temp5 = [a.split(";")[0] for a in temp5]
                temp4 += temp5
                i += 1
            temp5 = []
            for test in temp4:
                try:
                    tt1 = float(test.strip())
                    temp5 += [tt1]
                except:
                    pass

            self.onedvar[varname] = temp5

        return self.onedvar[varname]

    def getNDVar(self, varname):
        if TYPENDVAR:
            str2 = 'NETCDF:"' + self.path + '":' + varname
            v = gdal.Open(str2)
            temp1 = np.array(v.ReadAsArray())
            v = None
            return temp1[::-1, :]
        else:
            temp = self.get1DVar(varname)
            return temp
