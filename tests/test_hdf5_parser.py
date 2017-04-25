import qgis
from ctypes import *
import os
#import h5py
from pandas import read_hdf

def testhdf5_2():
     path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
     dset = "/Geometry/Connections/Polyline_Info"
     read_hdf(path, dset)
     

def testhdf5():
    path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')

    
#    hdf5Lib=r'C://OSGeo4W64//bin//hdf5.dll'
#    lib=cdll.LoadLibrary(hdf5Lib)
    lib=cdll.LoadLibrary('hdf5.dll')
    
    

#    lib=cdll.LoadLibrary('toto.dll')
    if False:
        major = c_uint()
        minor = c_uint()
        release = c_uint()
        print(   lib.H5get_libversion(byref(major), byref(minor), byref(release)) )
    
    
    """
    lib.H5Fopen.restype = c_int
    lib.H5Fopen.argtypes = (c_char_p, c_uint, c_int)
    """
    cpath = c_char_p(path)
#    herr_t = lib.H5Fopen(cpath, c_uint(0), c_int(0))
    herr_t = lib.H5Fopen(cpath, 0, 0)
    print('H5Fopen',herr_t, type(herr_t))
    
    #dset = u'/Results/Unsteady/Output/Output_Blocks/Base_Output/Unsteady_Time_Series/2D_Flow_Areas/lower/Depth'
    dset = "/Geometry/Connections/Polyline_Info"
    cdset = c_char_p(dset)
#    print('cdset',type(cdset))
    cherr_t = c_uint(herr_t)
#    cherr_t = c_int(herr_t)
    """
    lib.H5Dopen2.restype = c_int
    lib.H5Dopen2.argtypes = (c_uint,c_char_p, c_int)
    """
    dataset_id = lib.H5Dopen2(herr_t, dset, 0)
    
    print('H5Dopen2',dataset_id)
    
#   status = lib.H5Dread(c_int(0), H5T_NATIVE_INT, H5S_ALL, H5S_ALL, H5P_DEFAULT, dset_data);
    dset_data = None
    status = lib.H5Dread(0, 0, 0, 0, 0,dset_data)
    print('H5Dread',status, dset_data)
    
    
    result =  lib.H5Fclose(herr_t)
    print('H5Fclose',result)       #0 on success
    
    print('done')



testhdf5_2()