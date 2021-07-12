r"""@author Christopher J. Cawthorn and Sebastien E. Bourban

    @brief Tools for handling SELAFIN files and
        TELEMAC binary related in python

    @details Contains read/write functions for
        binary (big-endian) SELAFIN files

"""
from __future__ import print_function
# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
from struct import unpack
import numpy as np
# ~~> dependencies towards other modules
# ~~> dependencies towards other pytel/modules
from utils.progressbar import ProgressBar
from utils.exceptions import TelemacException

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#


def subset_variables_slf(vrs, all_vars):
    """
    Take a string in the format "var1:object;var2:object;var3;var4" and returns
    two list one of index and one of values of all the variables in all_vars
    that match var.

    @param vrs (string) String contain ; separated var:object values
    @param all_vars (list) List of the variables to match with

    @return (list) list of index of the matching variables
    @return (list) list of names of the matching variables
    """
    ids = []
    names = []
    # vrs has the form "var1:object;var2:object;var3;var4"
    # /!\ the ; separator might be a problem for command line action
    variable = vrs.replace(',', ';').split(';')
    for var in variable:
        var_name = var.split(':')[0]
        # Loop on variables in file
        for jvar in range(len(all_vars)):
            # Filling varname with spaces
            full_var_name = all_vars[jvar].lower() + \
                            " "*(16-len(all_vars[jvar]))
            # if varnme is in the variable name adding it
            if var_name.lower() in full_var_name:
                ids.append(jvar)
                names.append(all_vars[jvar].strip())
    if len(ids) < len(variable):
        raise TelemacException(
                "... Could not find {} in {}"
                "   +> may be you forgot to switch name spaces into "
                "underscores in your command ?"
                "".format(variable, str(all_vars)))
    return ids, names


def get_value_history(slf, times, support, vrs):
    """
    Extraction of time series at points.
    A point could be:
    (a) A point could be a node 2D associated with one or more plan number
    (b) A pair (x,y) associated with one or more plan number
    Warning: Vertical interpolation has not been implemented yet.

    @param slf (TelemacFile) Serafin file structure
    @param times (list) the discrete list of time frame
        to extract from the time history
    @param support (list) the list of points
    @param vrs (list) the index in the nvar-list to the variable to
                               extract
    """
    (vars_indexes, var_names) = vrs
    # ~~ Total size of support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    lens = 0
    for _, zep in support:
        lens += len(zep)
    # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    z = np.zeros((len(vars_indexes), lens, len(times)), dtype=np.float64)
    for itime, time in enumerate(times):  # it is from 0 to len(time)-1
        for jvar, var_name in enumerate(var_names):  # ivar is from 0 to nvar-1
            varsor = slf.get_data_value(var_name, time)
            # ipt is from 0 to lens-1
            # (= all points extracted and all plans extracted)
            ipt = 0
            for x_y, zep in support:
                # xp is a pair (x,y) and you need interpolation
                if isinstance(x_y, tuple):
                    # /!\ only list of plans is allowed for now
                    for plan in zep:
                        z[jvar][ipt][itime] = 0.
                        l_n, b_n = x_y
                        for inod in range(len(b_n)):
                            ipoin = l_n[inod]+plan*slf.npoin3//slf.nplan
                            z[jvar][ipt][itime] += b_n[inod]*varsor[ipoin]
                        ipt += 1  # ipt advances to keep on track
                else:
                    # /!\ only list of plans is allowed for now
                    for plan in zep:
                        z[jvar][ipt][itime] = \
                            varsor[x_y+plan*slf.npoin3//slf.nplan]
                        ipt += 1  # ipt advances to keep on track

    return z


def get_value_history_slf(hook, tags, time, support, nvar, npoin3, nplan,
                          t1):
    r"""
        Extraction of time series at points.
        A point could be:
        (a) A point could be a node 2D associated with one or more plan number
        (b) A pair (x,y) associated with one or more plan number
/!\   Vertical interpolation has not been implemented yet.
        Arguments:
        - time: the discrete list of time frame to extract
            from the time history
        - support: the list of points
        - vars_indexes: the index in the nvar-list to the variable to extract
    """
    (vars_indexes, _) = t1
    f = hook['hook']
    endian = hook['endian']
    ftype, fsize = hook['float']

    # ~~ Total size of support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    lens = 0
    for _, zep in support:
        lens += len(zep)

    # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    z = np.zeros((len(vars_indexes), lens, len(time)))
    if fsize == 4:
        z = np.zeros((len(vars_indexes), lens, len(time)), dtype=np.float32)
    else:
        z = np.zeros((len(vars_indexes), lens, len(time)), dtype=np.float64)
    for itime in range(len(time)):  # it is from 0 to len(time)-1
        # time[itime] is the frame to be extracted
        f.seek(tags['cores'][time[itime]])
        f.seek(4+fsize+4, 1)  # the file pointer is initialised
        for ivar in range(nvar):  # ivar is from 0 to nvar-1
            # the file pointer advances through all records to keep on track
            f.seek(4, 1)
            if ivar in vars_indexes:  # extraction of a particular variable
                varsor = unpack(endian+str(npoin3)+ftype, f.read(fsize*npoin3))
                jvar = vars_indexes.index(ivar)
                # ipt is from 0 to lens-1
                # (= all points extracted and all plans extracted)
                ipt = 0
                for x_y, zep in support:
                    # xp is a pair (x,y) and you need interpolation
                    t2 = type(())
                    if isinstance(x_y, t2):
                        # /!\ only list of plans is allowed for now
                        for plan in zep:
                            z[jvar][ipt][itime] = 0.
                            l_n, b_n = x_y
                            for inod in range(len(b_n)):
                                z[jvar][ipt][itime] += \
                                  b_n[inod] *\
                                  varsor[l_n[inod]+plan*npoin3//nplan]
                            ipt += 1  # ipt advances to keep on track
                    else:
                        # /!\ only list of plans is allowed for now
                        for plan in zep:
                            z[jvar][ipt][itime] = \
                                varsor[x_y+plan*npoin3//nplan]
                            ipt += 1  # ipt advances to keep on track
            else:
                # the file pointer advances through all
                # records to keep on track
                f.seek(fsize*npoin3, 1)
            f.seek(4, 1)

    return z


def get_edges_slf(ikle, meshx, meshy, showbar=True):
    """
    Returns the list of edges of the mesh

    @param ikle (np.array) Connectivity table
    @param meshx (np.array) X coordinates of the mesh points
    @param meshy (np.array) Y coordinates of the mesh points
    @param showbar (boolean) If True display a progress bar

    @returns (list) The list of edges
    """

    try:
        from matplotlib.tri import Triangulation
        edges = Triangulation(meshx, meshy, ikle).get_cpp_triangulation()\
            .get_edges()
    except ImportError:
        edges = []
        ibar = 0
        if showbar:
            pbar = ProgressBar(maxval=len(ikle)).start()
        for elem in ikle:
            ibar += 1
            if showbar:
                pbar.update(ibar)
            if [elem[0], elem[1]] not in edges:
                edges.append([elem[1], elem[0]])
            if [elem[1], elem[2]] not in edges:
                edges.append([elem[2], elem[1]])
            if [elem[2], elem[0]] not in edges:
                edges.append([elem[0], elem[2]])
        if showbar:
            pbar.finish()

    return edges


def get_neighbours_slf(ikle, meshx, meshy, showbar=True):
    """
    Return a list containing for each element the list of elements that are
    neighbours to that element

    @param ikle (np.array) Connectivity table
    @param meshx (np.array) X coordinates of the mesh points
    @param meshy (np.array) Y coordinates of the mesh points
    @param showbar (boolean) If True display a progress bar

    @returns (list) The list of neighbours
    """

    try:
        from matplotlib.tri import Triangulation
        neighbours = Triangulation(meshx, meshy, ikle).get_cpp_triangulation()\
                                                      .get_neighbors()
    except ImportError:
        insiders = {}
        bounders = {}
        ibar = 0
        if showbar:
            pbar = ProgressBar(maxval=(3*len(ikle))).start()
        for elem, i in zip(ikle, range(len(ikle))):
            n_k = bounders.keys()
            for k in [0, 1, 2]:
                ibar += 1
                if showbar:
                    pbar.update(ibar)
                if (elem[k], elem[(k+1) % 3]) not in n_k:
                    bounders.update({(elem[(k+1) % 3], elem[k]): i})
                else:
                    j = bounders[(elem[k], elem[(k+1) % 3])]
                    insiders.update({(elem[k], elem[(k+1) % 3]): [i, j]})
                    del bounders[(elem[k], elem[(k+1) % 3])]
        ibar = 0
        neighbours = - np.ones((len(ikle), 3), dtype=np.int)
        for elem, i in zip(ikle, range(len(ikle))):
            for k in [0, 1, 2]:
                ibar += 1
                if showbar:
                    pbar.update(ibar)
                if (elem[k], elem[(k+1) % 3]) in insiders:
                    elem_a, elem_b = insiders[(elem[k], elem[(k+1) % 3])]
                    if elem_a == i:
                        neighbours[i][k] = elem_b
                    if elem_b == i:
                        neighbours[i][k] = elem_a
                if (elem[(k+1) % 3], elem[k]) in insiders:
                    elem_a, elem_b = insiders[(elem[(k+1) % 3], elem[k])]
                    if elem_a == i:
                        neighbours[i][k] = elem_b
                    if elem_b == i:
                        neighbours[i][k] = elem_a
        if showbar:
            pbar.finish()

    return neighbours


def get_value_polyline(slf, times, support, vrs):
    """
    Extraction of longitudinal profiles along lines.
    A line is made of points extracted from slice_mesh:
    A point is a pair (x,y) associated with one or more plan number
    Warning: Vertical interpolation has not been implemented yet.

    @param slf (TelemacFile) Telemac file class
    @param times (list) the discrete list of time frame to extract
        from the time
    history
    @param support (list): the list of points intersecting th mesh
    @param vrs (tuple of list): the index, names in the
    nvar-list to the variable to extract
    """
    (vars_indexes, var_names) = vrs
    # ~~ Total size of support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    lens = len(support[0][1])

    # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    z = np.zeros((len(vars_indexes), len(times), lens, len(support)),
                 dtype=np.float64)
    # ~~ Extract data along line ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    for itime, time in enumerate(times):  # it is from 0 to len(time)-1
        # time[itime] is the frame to be extracted
        for jvar, var_name in enumerate(var_names):  # ivar is from 0 to nvar-1
            # the file pointer advances through all records to keep on track
            varsor = slf.get_data_value(var_name, time)
            # ipt is from 0 to lens-1
            # (= all points extracted and all plans extracted)
            for ipt in range(len(support)):
                x_y, zep = support[ipt]
                # /!\ only list of plans is allowed for now
                for ipl in range(len(zep)):
                    z[jvar][itime][ipl][ipt] = 0.
                    l_n, b_n = x_y
                    for inod in range(len(b_n)):
                        ipoin = l_n[inod]+zep[ipl]*slf.npoin3//slf.nplan
                        z[jvar][itime][ipl][ipt] += b_n[inod]*varsor[ipoin]

    return z


def get_value_polyline_slf(hook, tags, time, support, nvar, npoin3, nplan,
                           t1):
    r"""
        Extraction of longitudinal profiles along lines.
        A line is made of points extracted from slice_mesh:
        A point is a pair (x,y) associated with one or more plan number
/!\   Vertical interpolation has not been implemented yet.
        Arguments:
        - time: the discrete list of time frame to extract
            from the time history
        - support: the list of points intersecting th mesh
        - vars_indexes: the index in the nvar-list to the variable to extract
    """
    (vars_indexes, _) = t1
    f = hook['hook']
    endian = hook['endian']
    ftype, fsize = hook['float']

    # ~~ Total size of support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    lens = len(support[0][1])

    # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if fsize == 4:
        z = np.zeros((len(vars_indexes), len(time), lens, len(support)),
                     dtype=np.float32)
    else:
        z = np.zeros((len(vars_indexes), len(time), lens, len(support)),
                     dtype=np.float64)
    # ~~ Extract data along line ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    for itime in range(len(time)):  # it is from 0 to len(time)-1
        # time[itime] is the frame to be extracted
        f.seek(tags['cores'][time[itime]])
        f.read(4+fsize+4)  # the file pointer is initialised
        for ivar in range(nvar):  # ivar is from 0 to nvar-1
            # the file pointer advances through all records to keep on track
            f.read(4)
            if ivar in vars_indexes:  # extraction of a particular variable
                varsor = unpack(endian+str(npoin3)+ftype, f.read(fsize*npoin3))
                # ipt is from 0 to lens-1
                # (= all points extracted and all plans extracted)
                for ipt in range(len(support)):
                    x_y, zep = support[ipt]
                    # /!\ only list of plans is allowed for now
                    for ipl in range(len(zep)):
                        z[vars_indexes.index(ivar)][itime][ipl][ipt] = 0.
                        l_n, b_n = x_y
                        for inod in range(len(b_n)):
                            z[vars_indexes.index(ivar)][itime][ipl][ipt] += \
                              b_n[inod] *\
                              varsor[l_n[inod]+zep[ipl]*npoin3//nplan]
            else:
                # the file pointer advances through
                # all records to keep on track
                f.read(fsize*npoin3)
            f.read(4)

    return z


def get_value_polyplan(slf, times, support, vrs):
    """
    Extraction of variables at a list of times on a list of planes.
    A plane is an integer
    Warning: Vertical interpolation has not been implemented yet.
    Arguments:
    - time: the discrete list of time frame to extract from the time history
    - support: the list of planes
    - vars_indexes: the index in the nvar-list to the variable to extract
    """
    (vars_indexes, var_names) = vrs
    # ~~ Extract time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    z = np.zeros((len(vars_indexes), len(times), len(support),
                  slf.npoin3//slf.nplan),
                 dtype=np.float64)
    # ~~ Extract data along line ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    for itime, time in enumerate(times):  # it is from 0 to len(time)-1
        # time[itime] is the frame to be extracted
        for jvar, var_name in enumerate(var_names):  # ivar is from 0 to nvar-1
            # the file pointer advances through all records to keep on track
            varsor = slf.get_data_value(var_name, time)
            # ipt is from 0 to lens-1
            # (= all points extracted and all plans extracted)
            for ipl in range(len(support)):
                z[jvar][itime][ipl] = \
                  varsor[support[ipl]*slf.npoin3//slf.nplan:
                         (support[ipl]+1)*slf.npoin3//slf.nplan]

    return z


def get_value_polyplan_slf(hook, tags, time, support, nvar, npoin3, nplan,
                           t1):
    r"""
        Extraction of variables at a list of times on a list of planes.
        A plane is an integer
/!\   Vertical interpolation has not been implemented yet.
        Arguments:
        - time: the discrete list of time frame to extract
            from the time history
        - support: the list of planes
        - vars_indexes: the index in the nvar-list to the variable to extract
    """
    (vars_indexes, _) = t1
    f = hook['hook']
    endian = hook['endian']
    ftype, fsize = hook['float']

    # ~~ Extract planes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if fsize == 4:
        z = np.zeros((len(vars_indexes), len(time),
                      len(support), npoin3//nplan),
                     dtype=np.float32)
    else:
        z = np.zeros((len(vars_indexes), len(time),
                      len(support), npoin3//nplan),
                     dtype=np.float64)
    # ~~ Extract data on several planes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    for itime in range(len(time)):  # it is from 0 to len(time)-1
        # time[itime] is the frame to be extracted
        f.seek(tags['cores'][time[itime]])
        f.read(4+fsize+4)  # the file pointer is initialised
        for ivar in range(nvar):  # ivar is from 0 to nvar-1
            # the file pointer advances through all records to keep on track
            f.read(4)
            if ivar in vars_indexes:  # extraction of a particular variable
                varsor = unpack(endian+str(npoin3)+ftype, f.read(fsize*npoin3))
                # ipt is from 0 to len(support) (= all plans extracted)
                for ipl in range(len(support)):
                    z[vars_indexes.index(ivar)][itime][ipl] = \
                      varsor[support[ipl]*npoin3//nplan:
                             (support[ipl]+1)*npoin3//nplan]
            else:
                # the file pointer advances through all
                # records to keep on track
                f.read(fsize*npoin3)
            f.read(4)

    return z


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

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#


__author__ = "Sebastien E. Bourban"
__date__ = "$09-Sep-2011 08:51:29$"