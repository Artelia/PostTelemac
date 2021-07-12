#
# +!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#                                                                       #
#                                 selafin_io_pp.py                      #
#                                                                       #
# +!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#
# Author: Pat Prodanovic, Ph.D., P.Eng.
#
# Date: Feb 13, 2016
#
# Purpose: Class that reads and writes TELEMAC's SELAFIN files. Based on
# HRW's class under the same name. Made it so that it works under Python 2
# and Python 3.
#
# Revised: Apr 30, 2016
# Added ability to read 3d *.slf files.
# Can not write 3d *.slf files yet, but this could be added in the future.
#
# Revised: Jun 21, 2016
# Added a method readVariablesAtNode() that works super fast at extracting
# values from *.slf files
#
# Revised: Jun 23, 2016
# Made sure that title, precision, variable names and units are padded with
# spaces. This change is made in the writeHeader() method.
#
# Revised: Jul 06, 2016
# Made sure that title, precision, variable names and units are padded with
# spaces. This change is made in the readHeader() method. Paraview legacy
# reader for *.vtk files did not like junk after variable names.
#
# Revised: Nov 24, 2019
# Made the change recommended by Qilong Bi to work in writing 3d files.
#
# Uses: Python 2 or 3, Numpy
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Global Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from struct import unpack, pack
import sys
import numpy as np

#
class ppSELAFIN:

    # object's properties
    def __init__(self, slf_file):

        # determine which version of python the user is running
        if sys.version_info > (3, 0):
            self.version = 3
        elif sys.version_info > (2, 7):
            self.version = 2

        self.slf_file = slf_file

        self.endian = ">"  # always assume big endian

        # For C float type use size 4
        # For C double type use size 8
        # defaults are single precision selafin
        # for double precision, use setPrecision, and change it to 'd', 8
        self.float_type = "f"
        self.float_size = 4

        self.title = ""
        self.precision = "SELAFIN "
        self.NBV1 = 0
        self.NBV2 = 0

        # variables and units
        self.vars = []

        self.vnames = []
        self.vunits = []

        self.IPARAM = []

        self.NPLAN = 0  # number of vertical planes; =1 for 2d; >1 for 3d

        # Aug 29, 1997 2:15 am EST (date when skynet became self-aware)
        self.DATE = [1997, 8, 29, 2, 15, 0]

        self.NELEM = 0
        self.NPOIN = 0
        self.NDP = 0

        self.IKLE = np.zeros((self.NELEM, self.NPOIN), dtype=np.int32)

        self.IPOBO = np.zeros(self.NPOIN, dtype=np.int32)

        self.x = np.zeros(self.NPOIN)
        self.y = np.zeros(self.NPOIN)

        self.time = []

        # temporary array that hold results read for a single time step
        # for each variable in the file
        self.temp = np.zeros((self.NBV1, self.NPOIN))

        self.tempAtNode = np.zeros((0, 0))

    # methods start here
    def readHeader(self):
        self.f = open(self.slf_file, "rb")
        garbage = unpack(">i", self.f.read(4))[0]

        if self.version == 2:
            self.title = unpack(">72s", self.f.read(72))[0]
            self.precision = unpack(">8s", self.f.read(8))[0]
        else:
            self.title = unpack(">72s", self.f.read(72))[0].decode()
            self.precision = unpack(">8s", self.f.read(8))[0].decode()
        garbage = unpack(">i", self.f.read(4))[0]

        garbage = unpack(">i", self.f.read(4))[0]
        self.NBV1 = unpack(">i", self.f.read(4))[0]  # variables
        self.NBV2 = unpack(">i", self.f.read(4))[0]  # quad variables, not used
        garbage = unpack(">i", self.f.read(4))[0]

        # each item in the vars list has 32 characters; 16 for name, and 16 for unit
        for i in range(self.NBV1):
            garbage = unpack(">i", self.f.read(4))[0]
            if self.version == 2:
                self.vars.append(unpack(">32s", self.f.read(32))[0])
            else:
                self.vars.append(unpack(">32s", self.f.read(32))[0].decode())
            garbage = unpack(">i", self.f.read(4))[0]

        for i in range(self.NBV1):
            self.vnames.append(self.vars[i][0:15])
            self.vunits.append(self.vars[i][16:31])

        # added on 2016.07.06
        # after reading the variable names, make sure they are padded with spaces!
        # Paraview legacy *.vtk reader doesn't like this junk after variable names!!!

        # make sure title and precision is padded
        self.title = "{:<72}".format(self.title)
        self.precision = "{:<8}".format(self.precision)

        # make sure that variable names and units are paded
        for i in range(self.NBV1):
            # sometimes sisyphe vnames and vunits would have this garbage
            # part of the strings, which have to be removed.
            self.vnames[i] = self.vnames[i].replace("\x00", "")
            self.vunits[i] = self.vunits[i].replace("\x00", "")

            # pad it with spaces
            self.vnames[i] = "{:<16}".format(self.vnames[i])
            self.vunits[i] = "{:<16}".format(self.vunits[i])

        garbage = unpack(">i", self.f.read(4))[0]
        self.IPARAM = unpack(">10i", self.f.read(10 * 4))
        garbage = unpack(">i", self.f.read(4))[0]

        if self.IPARAM[-1] == 1:
            garbage = unpack(">i", self.f.read(4))[0]
            # date is 6 integers stored as a list
            self.DATE = unpack(">6i", self.f.read(6 * 4))
            garbage = unpack(">i", self.f.read(4))[0]

        if self.IPARAM[6] > 1:
            # the *.slf file is 3d
            self.NPLAN = self.IPARAM[6]
        else:
            # the *.slf file is 2d (this is the default)
            self.NPLAN = 1

        # uses python's long instead of integer
        garbage = unpack(">i", self.f.read(4))[0]
        self.NELEM = unpack(">l", self.f.read(4))[0]
        self.NPOIN = unpack(">l", self.f.read(4))[0]
        self.NDP = unpack(">i", self.f.read(4))[0]
        dummy = unpack(">i", self.f.read(4))[0]
        garbage = unpack(">i", self.f.read(4))[0]

        self.IKLE = np.zeros((self.NELEM, self.NDP), dtype=np.int32)

        garbage = unpack(">i", self.f.read(4))[0]
        for i in range(self.NELEM):
            for j in range(self.NDP):
                self.IKLE[i, j] = unpack(">l", self.f.read(4))[0]
        garbage = unpack(">i", self.f.read(4))[0]

        self.IPOBO = np.zeros(self.NPOIN, dtype=np.int32)

        garbage = unpack(">i", self.f.read(4))[0]
        for i in range(self.NPOIN):
            self.IPOBO[i] = unpack(">l", self.f.read(4))[0]
        garbage = unpack(">i", self.f.read(4))[0]

        # reads x
        self.x = np.zeros(self.NPOIN)
        garbage = unpack(">i", self.f.read(4))[0]

        # this is where we decide if it is single of double precision
        # I got this from HRW's getFloatTypeFromFloat method
        # I would have never gotten this on my own!!!
        if garbage != self.float_size * self.NPOIN:
            self.float_type = "d"
            self.float_size = 8

        for i in range(self.NPOIN):
            self.x[i] = unpack(">" + self.float_type, self.f.read(self.float_size))[0]
        garbage = unpack(">i", self.f.read(4))[0]

        # reads y
        self.y = np.zeros(self.NPOIN)
        garbage = unpack(">i", self.f.read(4))[0]
        for i in range(self.NPOIN):
            self.y[i] = unpack(">" + self.float_type, self.f.read(self.float_size))[0]
        garbage = unpack(">i", self.f.read(4))[0]

    def writeHeader(self):
        self.f = open(self.slf_file, "wb")

        # added on 2016.06.23 thanks to Yoann Audouin
        # before writing the variable names, make sure they are padded with spaces!

        # make sure title and precision is padded
        self.title = "{:<72}".format(self.title)
        self.precision = "{:<8}".format(self.precision)

        # make sure that variable names and units are paded
        for i in range(self.NBV1):
            self.vnames[i] = "{:<16}".format(self.vnames[i])
            self.vunits[i] = "{:<16}".format(self.vunits[i])

        # now we are ready to write the data
        self.f.write(pack(">i", 80))
        self.f.write(pack(">72s", self.title.encode()))
        self.f.write(pack(">8s", self.precision.encode()))
        self.f.write(pack(">i", 80))

        self.f.write(pack(">i", 8))
        self.f.write(pack(">i", self.NBV1))
        self.f.write(pack(">i", self.NBV2))
        self.f.write(pack(">i", 8))

        # writeHeader() must only be called after setVarUnits and setVarNames
        for i in range(self.NBV1):
            self.f.write(pack(">i", 32))
            self.f.write(pack(">16s", self.vnames[i].encode()))
            self.f.write(pack(">16s", self.vunits[i].encode()))
            self.f.write(pack(">i", 32))

        self.f.write(pack(">i", 40))
        for i in range(len(self.IPARAM)):
            self.f.write(pack(">i", self.IPARAM[i]))
        self.f.write(pack(">i", 40))

        if self.IPARAM[-1] == 1:
            self.f.write(pack(">i", 24))
            # date is 6 integers stored as a list
            for i in range(len(self.DATE)):
                self.f.write(pack(">i", self.DATE[i]))
            self.f.write(pack(">i", 24))

        self.f.write(pack(">i", 16))
        self.f.write(pack(">i", self.NELEM))
        self.f.write(pack(">i", self.NPOIN))
        self.f.write(pack(">i", self.NDP))
        self.f.write(pack(">i", 1))  # NPLAN???
        self.f.write(pack(">i", 16))

        self.f.write(pack(">i", 4 * self.NELEM * self.NDP))
        for i in range(self.NELEM):
            for j in range(self.NDP):
                self.f.write(pack(">i", self.IKLE[i, j]))
        self.f.write(pack(">i", 4 * self.NELEM * self.NDP))

        self.f.write(pack(">i", 4 * self.NPOIN))
        for i in range(len(self.IPOBO)):
            self.f.write(pack(">i", self.IPOBO[i]))
        self.f.write(pack(">i", 4 * self.NPOIN))

        # this is the garbage record that determines the float size
        # I have no idea why this works, but it does!!!
        self.f.write(pack(">i", self.float_size * self.NPOIN))
        for i in range(len(self.x)):
            self.f.write(pack(">" + self.float_type, self.x[i]))
        self.f.write(pack(">i", self.float_size * self.NPOIN))

        self.f.write(pack(">i", self.float_size * self.NPOIN))
        for i in range(len(self.y)):
            self.f.write(pack(">" + self.float_type, self.y[i]))
        self.f.write(pack(">i", self.float_size * self.NPOIN))

    def writeVariables(self, time, temp):
        # appends object's time
        self.time.append(time)

        # keeps only the current 2d array in object's memory
        self.temp = temp

        # write the time
        self.f.write(pack(">i", 4))
        self.f.write(pack(">" + self.float_type, time))
        self.f.write(pack(">i", 4))

        # writes the rest of the variables
        for j in range(self.NBV1):
            self.f.write(pack(">i", self.float_size * self.NPOIN))
            for k in range(self.NPOIN):
                self.f.write(pack(">" + self.float_type, self.temp[j, k]))
            self.f.write(pack(">i", self.float_size * self.NPOIN))

    def readTimes(self):
        pos_prior_to_time_reading = self.f.tell()

        while True:
            try:
                # get the times
                self.f.seek(4, 1)
                self.time.append(unpack(">" + self.float_type, self.f.read(self.float_size))[0])
                self.f.seek(4, 1)

                # skip through the variables
                self.f.seek(self.NBV1 * (4 + self.float_size * self.NPOIN + 4), 1)

                # skip the variables
                # 4 at begining and end are garbage
                # 4*NPOIN assumes each times step there are NPOIN nodes of
                # size 4 bytes (i.e., single precision)
                # f.seek(NBV1*(4+4*NPOIN+4), 1)
            except:
                break
        self.f.seek(pos_prior_to_time_reading)

    def readVariables(self, t_des):
        # print('Desired time: ' + str(t_des) + '\n')
        pos_prior_to_var_reading = self.f.tell()

        # reads data for all variables in the *.slf file at desired time t_des
        self.temp = np.zeros((self.NBV1, self.NPOIN))

        # it reads the time again, but this it is not used
        time2 = []

        # time index
        t = -1

        while True:
            try:
                self.f.seek(4, 1)
                time2.append(unpack(">" + self.float_type, self.f.read(self.float_size))[0])
                self.f.seek(4, 1)

                t = t + 1

                if t == t_des:
                    # print('slf time: ' + str(t))
                    for i in range(self.NBV1):
                        self.f.seek(4, 1)
                        for j in range(self.NPOIN):
                            self.temp[i, j] = unpack(">" + self.float_type, self.f.read(self.float_size))[0]
                        self.f.seek(4, 1)
                else:
                    self.f.seek(self.NBV1 * (4 + self.float_size * self.NPOIN + 4), 1)
            except:
                break

        # need to re-set in case another variable needs to be read!
        self.f.seek(pos_prior_to_var_reading)

    def readVariablesAtNode(self, node):

        # node is the desired node from which to extract results for
        numTimes = len(self.time)

        pos_prior_to_var_reading = self.f.tell()

        # reads data for all variables in the *.slf file at desired time t_des
        self.tempAtNode = np.zeros((numTimes, self.NBV1))

        # it reads the time again, but this it is not used
        time2 = []

        # time index
        t = -1

        while True:
            try:
                self.f.seek(4, 1)
                time2.append(unpack(">" + self.float_type, self.f.read(self.float_size))[0])
                self.f.seek(4, 1)

                # this is the time step index
                t = t + 1

                for i in range(self.NBV1):
                    self.f.seek(4, 1)

                    self.f.seek((node) * self.float_size, 1)
                    self.tempAtNode[t, i] = unpack(">" + self.float_type, self.f.read(self.float_size))[0]
                    self.f.seek((self.NPOIN - node - 1) * self.float_size, 1)

                    self.f.seek(4, 1)
            except:
                break

        # need to re-set in case another variable needs to be read!
        self.f.seek(pos_prior_to_var_reading)

    # get methods start here
    def getTitle(self):
        return self.title

    def getPrecision(self):
        return self.float_type, self.float_size

    def getNPOIN(self):
        return self.NPOIN

    def getNELEM(self):
        return self.NELEM

    def getTimes(self):
        return self.time

    def getVarNames(self):
        return self.vnames

    def getVarUnits(self):
        return self.vunits

    def getIPARAM(self):
        return self.IPARAM

    def getNPLAN(self):
        return self.NPLAN

    def getIKLE(self):
        return self.IKLE

    def getMeshX(self):
        return self.x

    def getMeshY(self):
        return self.y

    def getVarValues(self):
        return self.temp

    def getVarValuesAtNode(self):
        return self.tempAtNode

    def getIPOBO(self):
        return self.IPOBO

    def getDATE(self):
        return self.DATE

    def getMesh(self):
        return self.NELEM, self.NPOIN, self.NDP, self.IKLE, self.IPOBO, self.x, self.y

    # set methods start here
    def setPrecision(self, ftype, fsize):
        # for single precision use ftype='f', fsize=4
        # for double precision use ftype='d', fsize=8
        self.float_type = ftype
        self.float_size = fsize

        if ftype == "d" and fsize == 8:
            self.precision = "SELAFIND"
        if ftype == "f" and fsize == 4:
            self.precision = "SELAFIN "

    def setTitle(self, title):
        self.title = title

    def setDATE(self, DATE):
        self.DATE = DATE

    def setVarNames(self, vnames):
        self.NBV1 = len(vnames)
        self.vnames = vnames

    def setVarUnits(self, vunits):
        self.vunits = vunits

    def setIPARAM(self, IPARAM):
        self.IPARAM = IPARAM

    def setMesh(self, NELEM, NPOIN, NDP, IKLE, IPOBO, x, y):
        self.NELEM = NELEM
        self.NPOIN = NPOIN
        self.NDP = NDP
        self.IKLE = IKLE
        self.IPOBO = IPOBO
        self.x = x
        self.y = y

    def close(self):
        self.f.close()
