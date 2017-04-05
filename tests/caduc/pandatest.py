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
import pandas as pd
import os



def doThings():
    try:
        print 'DEBUT'
        
        path = os.path.normpath('C://00_Bureau//data2//baldeagle_multi2d.hdf')
        
        pd.read_hdf(path)
        
        
        
        print 'END'
    except Exception, e:
        print str(e)
    
        

doThings()
    
