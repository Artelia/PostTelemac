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
#unicode behaviour
from __future__ import unicode_literals

import matplotlib.colors
import os
from PyQt4 import  QtGui,  QtCore 


class PostTelemacColorManager():

    def __init__(self,selafinlayer):
        self.selafinlayer = selafinlayer
        
    #*********************** color ramp transformation ******************************************************
        
    def qgsvectorgradientcolorrampv2ToCmap(self,temp1):
    
    
        if str(temp1.__class__.__name__) == 'QgsVectorGradientColorRampV2':
        
            firstcol = temp1.properties()['color1']
            lastcol=temp1.properties()['color2']
            
            otherscol = [[0, 
                         int(firstcol.split(',')[0]),
                         int(firstcol.split(',')[1]),
                         int(firstcol.split(',')[2]),
                         int(firstcol.split(',')[3])]]
            
            try:
                otherscoltemp=temp1.properties()['stops'].split(":")
                bool_stops = True
            except Exception, e :
                bool_stops = False
                
            if bool_stops:
                for col in otherscoltemp:
                    otherscol.append([float(col.split(';')[0]),
                                      int(col.split(';')[1].split(',')[0]) ,
                                      int(col.split(';')[1].split(',')[1])  ,
                                      int(col.split(';')[1].split(',')[2]),
                                      int(col.split(';')[1].split(',')[3])])
            otherscol.append([1, 
                             int(lastcol.split(',')[0]) ,
                             int(lastcol.split(',')[1]),
                             int(lastcol.split(',')[2]),
                             int(lastcol.split(',')[3])])
                             
            return self.arrayStepRGBAToCmap(otherscol)
        
        elif str(temp1.__class__.__name__) == 'QgsCptCityColorRampV2':
            temp1 = temp1.cloneGradientRamp()
            firstcol = temp1.properties()['color1']
            lastcol=temp1.properties()['color2']
            
            otherscol = [[0, 
                         int(firstcol.split(',')[0]),
                         int(firstcol.split(',')[1]),
                         int(firstcol.split(',')[2]),
                         int(firstcol.split(',')[3])]]
            
            try:
                otherscoltemp=temp1.properties()['stops'].split(":")
                bool_stops = True
            except Exception, e :
                bool_stops = False
                
            if bool_stops:
                for col in otherscoltemp:
                    otherscol.append([float(col.split(';')[0]),
                                      int(col.split(';')[1].split(',')[0]) ,
                                      int(col.split(';')[1].split(',')[1])  ,
                                      int(col.split(';')[1].split(',')[2]),
                                      int(col.split(';')[1].split(',')[3])])
            otherscol.append([1, 
                             int(lastcol.split(',')[0]) ,
                             int(lastcol.split(',')[1]),
                             int(lastcol.split(',')[2]),
                             int(lastcol.split(',')[3])])
                             
            return self.arrayStepRGBAToCmap(otherscol)
            
        else:
            return None
    
    
    def arrayStepRGBAToCmap(self,temp1):
        if str(temp1.__class__.__name__) == 'list':
            #arrange it to fit dict of matplotlib:
            """
            http://matplotlib.org/examples/pylab_examples/custom_cmap.html
            """
            otherscol = temp1
            dict={}
            identcolors=['red','green','blue','alpha']
            for col in range(len(identcolors)):
                dict[identcolors[col]]=[]
                if True:
                    lendict=len(otherscol)
                    dict[identcolors[col]].append((0,float(otherscol[0][col+1])/255.0,float(otherscol[0][col+1])/255.0))
                    for i in range(1,lendict-1):
                        dict[identcolors[col]].append((float(otherscol[i][0]),float(otherscol[i][col+1])/255.0,float(otherscol[i][col+1])/255.0))
                dict[identcolors[col]].append((1,float(otherscol[lendict-1][col+1])/255.0,float(otherscol[lendict-1][col+1])/255.0))
                dict[identcolors[col]] = tuple(dict[identcolors[col]])
                
            cmap = matplotlib.colors.LinearSegmentedColormap('temp', dict)
            return cmap
        else:
            return None
            
    #*********************** layer symbology generator ******************************************************
        
    def generateSymbologyItems(self,iconSize):
        if self.selafinlayer.hydrauparser != None and self.selafinlayer.hydrauparser.hydraufile != None and self.selafinlayer.color_mpl_contour != None:
            lst = [(  (str(self.selafinlayer.hydrauparser.parametres[self.selafinlayer.param_displayed][1]), QtGui.QPixmap())  )]
            for i in range(len(self.selafinlayer.lvl_contour)-1):
                pix = QtGui.QPixmap(iconSize)
                r,g,b,a = self.selafinlayer.color_mpl_contour[i][0]*255,self.selafinlayer.color_mpl_contour[i][1]*255,self.selafinlayer.color_mpl_contour[i][2]*255,self.selafinlayer.color_mpl_contour[i][3]*255
                pix.fill(QtGui.QColor(r,g,b,a))
                lst.append( (str(self.selafinlayer.lvl_contour[i])+"/"+str(self.selafinlayer.lvl_contour[i+1]), pix))
            
            if self.selafinlayer.propertiesdialog.groupBox_schowvel.isChecked() :
                lst.append((self.tr('VELOCITY'),QtGui.QPixmap()))
                for i in range(len(self.selafinlayer.lvl_vel)-1):
                    pix = QtGui.QPixmap(iconSize)
                    r,g,b,a = self.selafinlayer.color_mpl_vel[i][0]*255,self.selafinlayer.color_mpl_vel[i][1]*255,self.selafinlayer.color_mpl_vel[i][2]*255,self.selafinlayer.color_mpl_vel[i][3]*255
                    pix.fill(QtGui.QColor(r,g,b,a))
                    lst.append( (str(self.selafinlayer.lvl_vel[i])+"/"+str(self.selafinlayer.lvl_vel[i+1]), pix))
            return lst
        else:
            return []
            
    #*********************** .Clr sparser ******************************************************
            
            
    def readClrColorRamp(self,path):
        f = open(path, 'r')
        colors = []
        levels = None
        processtype = 0
        for line in f:
            if 'colors' in line :
                processtype = 1
                continue
            elif 'levels' in line :
                processtype = 2
                continue
            if processtype == 1:
                colors.append([float(elem) for elem in line.split(';')])
                #print 'col ' + str(colors)
            if processtype == 2:
                levels = ([float(elem) for elem in line.split(';')])
        f.close()
        if colors and levels:
            return (self.arrayStepRGBAToCmap(colors),levels)
        else:
            return (None, None)
            
    def saveClrColorRamp(self,name,colors,levels):
        #path = os.path.join(os.path.dirname(__file__),'..', 'config', str(name) +'.clr')
        path = os.path.join(self.selafinlayer.propertiesdialog.posttelemacdir, str(name) +'.clr')
        f = open(path, 'w')
        f.write(str(name)+"\n")
        f.write("colors\n")
        for color in colors:
            f.write(str(';'.join(str(col) for col in color))+"\n")
        f.write("levels\n")
        f.write(str(';'.join(str(lvl) for lvl in levels))+"\n")
        f.close()
        
        
    def changeColorMap(self,cm,levels1):
        if len(levels1)>=2:
            lvls=levels1
            tab1 = []
            max1=256
            if len(lvls) == 2 :
                tab1=[1.0]
            else:
                tab1 = [int(max1*i/(len(lvls)-2)) for i in range(len(lvls)-1)]
            color_mpl_contour = cm(tab1)
            #self.cmap_mpl_contour,self.norm_mpl_contour = matplotlib.colors.from_levels_and_colors(lvls,self.color_mpl_contour)
            cmap_mpl,norm_mpl = matplotlib.colors.from_levels_and_colors(lvls,color_mpl_contour)
            return (cmap_mpl, norm_mpl, color_mpl_contour)
        else :
            return None,None,None
        
    #****************************************************************************************************
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QtCore.QCoreApplication.translate('PostTelemacColorManager', message, None, QtGui.QApplication.UnicodeUTF8)