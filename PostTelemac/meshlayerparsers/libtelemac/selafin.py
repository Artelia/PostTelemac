"""
Contains the class Selafin
"""
# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
from struct import unpack, pack, error
import numpy as np

from scipy.spatial import cKDTree
from matplotlib.tri import Triangulation


def get_endian_from_char(f, nchar):
    """
    Returns endianess of the file by trying to read a value in the file and
    comparing it to nchar

    @param f (file descriptor) File descriptor
    @param nchar (string) String to compare to

    @returns (string) String for endianess ("<" for little ">" for big)
    """
    pointer = f.tell()
    endian = ">"  # "<" means little-endian, ">" means big-endian
    ll, _, chk = unpack(endian+'i'+str(nchar)+'si', f.read(4+nchar+4))
    if chk != nchar:
        endian = "<"
        f.seek(pointer)
        ll, _, chk = unpack(endian+'i'+str(nchar)+'si', f.read(4+nchar+4))
    if ll != chk:
        raise TelemacException(
                '... Cannot read {} characters from your binary file'
                '    +> Maybe it is the wrong file format ?'
                ''.format(str(nchar)))
    f.seek(pointer)
    return endian
    
def get_float_type_from_float(f, endian, nfloat):
    """
    Identifies float precision from the file (single or double)

    @param f (file descriptor) File descriptor
    @param endian (string) Endianess type ("<" for little ">" for big)
    @param nfloat (float) Float to compare to

    @return (string, integer) Returns the string to be used for readinf ans the
    number of byte on which the float is encoded ('f', 4) for single ('d',8)
    for double precision

    """
    pointer = f.tell()
    ifloat = 4
    cfloat = 'f'
    ll = unpack(endian+'i', f.read(4))
    if ll[0] != ifloat*nfloat:
        ifloat = 8
        cfloat = 'd'
    _ = unpack(endian+str(nfloat)+cfloat, f.read(ifloat*nfloat))
    chk = unpack(endian+'i', f.read(4))
    if ll != chk:
        raise TelemacException(
                '... Cannot read {} floats from your binary file'
                '     +> Maybe it is the wrong file format ?'
                ''.format(str(nfloat)))
    f.seek(pointer)
    return cfloat, ifloat

class Selafin(object):
    """(DOXYGEN parsing)
    Class Selafin

    @brief
        Read and create Selafin files with python

    @details
        The idea is to be able to set float_type and float_type_size from
        outside when we start to write a selafinfiles.
        This will make it possible to do some kind of converters

    @history
        - switch between big/little endian
        - switch to double precission only for float

    @TODO
        - changes where only tested for simple reading, writing must still be
          done
        - get_series was not tested
        - all appen and put functions must be tested
        - needs some intensive testing
    """

    datetime = np.asarray([1972, 7, 13, 17, 24, 27])
    # ... needed here because optional in SLF (static)

    def __init__(self, file_name):
        """
        Intialisation of the class

        @param file_name (string) Name of the file
        """
        self.file = {}
        self.file.update({"name": file_name})
        # "<" means little-endian, ">" means big-endian
        self.file.update({"endian": ">"})
        self.file.update({"float": ("f", 4)})  # 'f' size 4, 'd' = size 8
        if file_name != "":
            self.file.update({"hook": open(file_name, "rb")})
            # ~~> checks endian encoding
            self.file["endian"] = get_endian_from_char(self.file["hook"], 80)
            # ~~> header parameters
            self.tags = {"meta": self.file["hook"].tell()}
            self.get_header_metadata_slf()
            # ~~> sizes and connectivity
            self.get_header_integers_slf()
            # ~~> checks float encoding
            self.file["float"] = get_float_type_from_float(self.file["hook"], self.file["endian"], self.npoin3)
            # ~~> xy mesh
            self.get_header_floats_slf()
            # ~~> time series
            self.tags = {"cores": [], "times": []}
            self.get_time_history_slf()
        else:
            self.title = ""
            self.nbv1 = 0
            self.nbv2 = 0
            self.nvar = self.nbv1 + self.nbv2
            self.varindex = range(self.nvar)
            self.iparam = []
            self.nelem3 = 0
            self.npoin3 = 0
            self.ndp3 = 0
            self.nplan = 1
            self.nelem2 = 0
            self.npoin2 = 0
            self.ndp2 = 0
            self.varnames = []
            self.varunits = []
            self.cldnames = []
            self.cldunits = []
            self.ikle3 = None
            self.ikle2 = []
            self.ipob2 = []
            self.ipob3 = []
            self.meshx = []
            self.meshy = []
            self.tags = {"cores": [], "times": []}
            self.datetime = np.asarray([1972, 7, 13, 17, 15, 13])
        self.fole = {}
        self.fole.update({"name": ""})
        self.fole.update({"endian": self.file["endian"]})
        self.fole.update({"float": self.file["float"]})
        self.tree = None
        self.neighbours = None
        self.edges = None
        self.alter_z_names = []
        self.alter_zm = None
        self.alter_zp = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #   Parsing the Big- and Little-Endian binary file
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_header_metadata_slf(self):
        """
        Reads title, variable names and units, date and time
        """
        f = self.file["hook"]
        endian = self.file["endian"]
        # ~~ Read title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        _, tmp, _ = unpack(endian + "i80si", f.read(4 + 80 + 4))
        self.title = tmp.decode("utf-8")
        # ~~ Read nbv(1) and nbv(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        _, self.nbv1, self.nbv2, _ = unpack(endian + "iiii", f.read(4 + 8 + 4))
        self.nvar = self.nbv1 + self.nbv2
        self.varindex = range(self.nvar)
        # ~~ Read variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.varnames = []
        self.varunits = []
        for _ in range(self.nbv1):
            _, name, unit, _ = unpack(endian + "i16s16si", f.read(4 + 16 + 16 + 4))
            self.varnames.append(name.decode("utf8"))
            self.varunits.append(unit.decode("utf8"))
        self.cldnames = []
        self.cldunits = []
        for _ in range(self.nbv2):
            _, name, unit, _ = unpack(endian + "i16s16si", f.read(4 + 16 + 16 + 4))
            self.cldnames.append(name.decode("utf8"))
            self.cldunits.append(unit.decode("utf8"))
        # ~~ Read iparam array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        dummy = unpack(endian + "12i", f.read(4 + 40 + 4))
        self.iparam = np.asarray(dummy[1:11])
        # ~~ Read DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.datetime = np.asarray([1972, 7, 13, 17, 15, 13])
        if self.iparam[9] == 1:
            dummy = unpack(endian + "8i", f.read(4 + 24 + 4))
            self.datetime = np.asarray(dummy[1:9])

    def get_header_integers_slf(self):
        """
        Reads nelem, npoin, ndp3, nplan, ikle and ipobo
        """
        f = self.file["hook"]
        endian = self.file["endian"]
        # ~~ Read nelem3, npoin3, ndp3, nplan ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        _, self.nelem3, self.npoin3, self.ndp3, self.nplan, _ = unpack(endian + "6i", f.read(4 + 16 + 4))
        self.nelem2 = self.nelem3
        self.npoin2 = self.npoin3
        self.ndp2 = self.ndp3
        self.nplan = max(1, self.nplan)
        if self.iparam[6] > 1:
            self.nplan = self.iparam[6]  # /!\ How strange is that ?
            self.nelem2 = self.nelem3 // (self.nplan - 1)
            self.npoin2 = self.npoin3 // self.nplan
            self.ndp2 = self.ndp3 // 2
        # ~~ Read the ikle array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.seek(4, 1)
        self.ikle3 = (
            np.array(unpack(endian + str(self.nelem3 * self.ndp3) + "I", f.read(4 * self.nelem3 * self.ndp3))) - 1
        )
        f.seek(4, 1)
        self.ikle3 = self.ikle3.reshape((self.nelem3, self.ndp3))
        if self.nplan > 1:
            self.ikle2 = np.compress(np.repeat([True, False], self.ndp2), self.ikle3[0 : self.nelem2], axis=1)
        else:
            self.ikle2 = self.ikle3
        # ~~ Read the ipobo array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.seek(4, 1)
        self.ipob3 = np.asarray(unpack(endian + str(self.npoin3) + "i", f.read(4 * self.npoin3)))
        f.seek(4, 1)
        self.ipob2 = self.ipob3[0 : self.npoin2]

    def get_header_floats_slf(self):
        """
        Reads the mesh coordinates
        """
        f = self.file["hook"]
        endian = self.file["endian"]
        # ~~ Read the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
        ftype, fsize = self.file["float"]
        f.seek(4, 1)
        self.meshx = np.asarray(unpack(endian + str(self.npoin3) + ftype, f.read(fsize * self.npoin3))[0 : self.npoin2])
        f.seek(4, 1)
        # ~~ Read the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
        f.seek(4, 1)
        self.meshy = np.asarray(unpack(endian + str(self.npoin3) + ftype, f.read(fsize * self.npoin3))[0 : self.npoin2])
        f.seek(4, 1)

    def get_time_history_slf(self):
        """
        Reads all result values
        """
        f = self.file["hook"]
        endian = self.file["endian"]
        ftype, fsize = self.file["float"]
        ats = []
        att = []
        while True:
            try:
                att.append(f.tell())
                # ~~ Read AT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                f.seek(4, 1)
                ats.append(unpack(endian + ftype, f.read(fsize))[0])
                f.seek(4, 1)
                # ~~ Skip Values ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                f.seek(self.nvar * (4 + fsize * self.npoin3 + 4), 1)
            except error:
                att.pop(len(att) - 1)  # since the last record failed the try
                break
        self.tags.update({"cores": att})
        self.tags.update({"times": np.asarray(ats)})

    def get_variables_at(self, frame, vars_indexes):
        """
        Get values for a given time step and a list of variables

        @param frame (int) Time step to extract
        @param vars_indexes (list) List of variable indices

        @return (np.array) array containg the values for each variable
        """
        f = self.file["hook"]
        endian = self.file["endian"]
        ftype, fsize = self.file["float"]
        if fsize == 4:
            z = np.zeros((len(vars_indexes), self.npoin3), dtype=np.float32)
        else:
            z = np.zeros((len(vars_indexes), self.npoin3), dtype=np.float64)
        # if tags has 31 frames, len(tags)=31 from 0 to 30,
        # then frame should be >= 0 and < len(tags)
        if frame < len(self.tags["cores"]) and frame >= 0:
            f.seek(self.tags["cores"][frame])
            f.seek(4 + fsize + 4, 1)
            for ivar in range(self.nvar):
                f.seek(4, 1)
                if ivar in vars_indexes:
                    z[vars_indexes.index(ivar)] = unpack(endian + str(self.npoin3) + ftype, f.read(fsize * self.npoin3))
                else:
                    f.seek(fsize * self.npoin3, 1)
                f.seek(4, 1)
        return z

    def alter_endian(self):
        """
        Alter Endian for the file
        """
        if self.fole["endian"] == ">":
            self.fole["endian"] = "<"
        else:
            self.fole["endian"] = ">"

    def alter_float(self):
        """
        Alter the precision for float
        """
        if self.fole["float"] == ("f", 4):
            self.fole["float"] = ("d", 8)
        else:
            self.fole["float"] = ("f", 4)

    def alter_values(self, vrs=None, m_z=1, p_z=0):
        """
        Set alter values
        """
        if vrs is not None:
            self.alter_zm = m_z
            self.alter_zp = p_z
            self.alter_z_names = vrs.split(":")

    def append_header_slf(self):
        """
        Write the header part of the file
        """
        f = self.fole["hook"]
        endian = self.fole["endian"]
        ftype, fsize = self.fole["float"]
        # ~~ Write title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "i80si", 80, self.title.encode("utf8"), 80))
        # ~~ Write nbv(1) and nbv(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "iiii", 4 + 4, self.nbv1, self.nbv2, 4 + 4))
        # ~~ Write variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for i in range(self.nbv1):
            f.write(pack(endian + "i", 32))
            f.write(pack(endian + "16s", self.varnames[i].encode("utf8")))
            f.write(pack(endian + "16s", self.varunits[i].encode("utf8")))
            f.write(pack(endian + "i", 32))
        for i in range(self.nbv2):
            f.write(pack(endian + "i", 32))
            f.write(pack(endian + "16s", self.cldnames[i]))
            f.write(pack(endian + "16s", self.cldunits[i]))
            f.write(pack(endian + "i", 32))
        # ~~ Write iparam array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "i", 4 * 10))
        for i in range(len(self.iparam)):
            f.write(pack(endian + "i", self.iparam[i]))
        f.write(pack(endian + "i", 4 * 10))
        # ~~ Write DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if self.iparam[9] == 1:
            f.write(pack(endian + "i", 4 * 6))
            for i in range(6):
                f.write(pack(endian + "i", self.datetime[i]))
            f.write(pack(endian + "i", 4 * 6))
        # ~~ Write nelem3, npoin3, ndp3, nplan ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "6i", 4 * 4, self.nelem3, self.npoin3, self.ndp3, 1, 4 * 4))
        # ~~ Write the ikle array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "I", 4 * self.nelem3 * self.ndp3))
        f.write(pack(endian + str(self.nelem3 * self.ndp3) + "I", *(self.ikle3.ravel() + 1)))
        f.write(pack(endian + "I", 4 * self.nelem3 * self.ndp3))
        # ~~ Write the ipobo array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "i", 4 * self.npoin3))
        f.write(pack(endian + str(self.npoin3) + "i", *(self.ipob3)))
        f.write(pack(endian + "i", 4 * self.npoin3))
        # ~~ Write the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "i", fsize * self.npoin3))
        for i in range(self.nplan):
            f.write(pack(endian + str(self.npoin2) + ftype, *(self.meshx)))
        f.write(pack(endian + "i", fsize * self.npoin3))
        # ~~ Write the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + "i", fsize * self.npoin3))
        for i in range(self.nplan):
            f.write(pack(endian + str(self.npoin2) + ftype, *(self.meshy)))
        f.write(pack(endian + "i", fsize * self.npoin3))

    def append_core_time_slf(self, time):
        """
        Write time value

        @param time (float) Time value
        """
        f = self.fole["hook"]
        endian = self.fole["endian"]
        ftype, fsize = self.fole["float"]
        # Print time record
        if isinstance(time, type(0.0)):
            f.write(pack(endian + "i" + ftype + "i", fsize, time, fsize))
        else:
            f.write(pack(endian + "i" + ftype + "i", fsize, self.tags["times"][time], fsize))

    def append_core_vars_slf(self, varsor):
        """
        Write variable informations

        @param varsor (list) List of value for each variable
        """
        f = self.fole["hook"]
        endian = self.fole["endian"]
        ftype, fsize = self.fole["float"]
        # Print variable records
        for var in varsor:
            f.write(pack(endian + "i", fsize * self.npoin3))
            f.write(pack(endian + str(self.npoin3) + ftype, *(var)))
            f.write(pack(endian + "i", fsize * self.npoin3))

    def put_content(self, file_name, showbar=True):
        """
        Write content of the object into a Serafin file

        @param file_name (string) Name of the serafin file
        @param showbar (boolean) If True displays a showbar
        """
        self.fole.update({"name": file_name})
        self.fole.update({"hook": open(file_name, "wb")})
        self.append_header_slf()
        for time in range(len(self.tags["times"])):
            self.append_core_time_slf(time)
            self.append_core_vars_slf(self.get_values(time))
        self.fole["hook"].close()
        if showbar:
            pbar.finish()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #   Tool Box
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_values(self, time):
        """
        Get values for all variables for a give time step
        If alter_values were set it applies modification
        """
        varsor = self.get_variables_at(time, self.varindex)
        for alter_var in self.alter_z_names:
            for var in range(len(self.varnames)):
                if alter_var.lower() in self.varnames[var].lower():
                    varsor[var] = self.alter_zm * varsor[var] + self.alter_zp
            for var in range(len(self.cldnames)):
                if alter_var.lower() in self.cldnames[var].lower():
                    varsor[var + self.nbv1] = self.alter_zm * varsor[var + self.nbv1] + self.alter_zp
        return varsor

    def get_series(self, nodes, vars_indexes=None, showbar=True):
        """
        Return the value for a list of nodes on variables given in vars_indexes
        for each time step

        @param nodes (list) list of nodes for which to extract data
        @param vars_indexes (list) List of variables to extract data for
        @param showbar (boolean) If True display a showbar for the progress

        """
        f = self.file["hook"]
        endian = self.file["endian"]
        ftype, fsize = self.file["float"]
        if vars_indexes is None:
            vars_indexes = self.varindex
        # ~~ Ordering the nodes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # This assumes that nodes starts at 1
        onodes = np.sort(np.array(zip(range(len(nodes)), nodes), dtype=[("0", int), ("1", int)]), order="1")
        # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if fsize == 4:
            z = np.zeros((len(vars_indexes), len(nodes), len(self.tags["cores"])), dtype=np.float32)
        else:
            z = np.zeros((len(vars_indexes), len(nodes), len(self.tags["cores"])), dtype=np.float64)
        f.seek(self.tags["cores"][0])
        for time in range(len(self.tags["cores"])):
            f.seek(self.tags["cores"][time])
            f.seek(4 + fsize + 4, 1)
            if showbar:
                pbar.update(time)
            for ivar in range(self.nvar):
                f.seek(4, 1)
                if ivar in vars_indexes:
                    jnod = onodes[0]
                    f.seek(fsize * (jnod[1] - 1), 1)
                    z[vars_indexes.index(ivar), jnod[0], time] = unpack(endian + ftype, f.read(fsize))[0]
                    for inod in onodes[1:]:
                        f.seek(fsize * (inod[1] - jnod[1] - 1), 1)
                        z[vars_indexes.index(ivar), inod[0], time] = unpack(endian + ftype, f.read(fsize))[0]
                        jnod = inod
                    f.seek(fsize * self.npoin3 - fsize * jnod[1], 1)
                else:
                    f.seek(fsize * self.npoin3, 1)
                f.seek(4, 1)
        return z

    def set_kd_tree(self, reset=False):
        """
        Builds a KDTree (impoves search of neighbors)

        @param reset (boolean) Force reset of tree
        """
        if reset or self.tree is None:
            isoxy = np.column_stack(
                (np.sum(self.meshx[self.ikle2], axis=1) / 3.0, np.sum(self.meshy[self.ikle2], axis=1) / 3.0)
            )
            self.tree = cKDTree(isoxy)

    def set_mpl_tri(self, reset=False):
        """
        Build neighbours from matplotlib

        @param reset (boolean) Force computing neighbours
        """
        if reset or self.neighbours is None or self.edges is None:
            # from matplotlib.tri import Triangulation
            mpltri = Triangulation(self.meshx, self.meshy, self.ikle2).get_cpp_triangulation()
            self.neighbours = mpltri.get_neighbors()
            self.edges = mpltri.get_edges()

    def __del__(self):
        """
        Deleting the object
        """
        if self.file["name"] != "":
            self.file["hook"].close()
