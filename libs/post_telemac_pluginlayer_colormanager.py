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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from matplotlib.colors import LinearSegmentedColormap
import os


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
            cmap = LinearSegmentedColormap('temp', dict)
            return cmap
        else:
            return None
            
    #*********************** layer symbology generator ******************************************************
        
    def generateSymbologyItems(self,iconSize):
        if self.selafinlayer.selafinparser.selafin != None and self.selafinlayer.color_mpl_contour != None:
            lst = [(  (str(self.selafinlayer.parametres[self.selafinlayer.param_displayed][1]), QPixmap())  )]
            for i in range(len(self.selafinlayer.lvl_contour)-1):
                pix = QPixmap(iconSize)
                r,g,b,a = self.selafinlayer.color_mpl_contour[i][0]*255,self.selafinlayer.color_mpl_contour[i][1]*255,self.selafinlayer.color_mpl_contour[i][2]*255,self.selafinlayer.color_mpl_contour[i][3]*255
                pix.fill(QColor(r,g,b))
                lst.append( (str(self.selafinlayer.lvl_contour[i])+"/"+str(self.selafinlayer.lvl_contour[i+1]), pix))
            
            if self.selafinlayer.propertiesdialog.groupBox_schowvel.isChecked() :
                lst.append((self.tr('VELOCITY'),QPixmap()))
                for i in range(len(self.selafinlayer.lvl_vel)-1):
                    pix = QPixmap(iconSize)
                    r,g,b,a = self.selafinlayer.color_mpl_vel[i][0]*255,self.selafinlayer.color_mpl_vel[i][1]*255,self.selafinlayer.color_mpl_vel[i][2]*255,self.selafinlayer.color_mpl_vel[i][3]*255
                    pix.fill(QColor(r,g,b))
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
        path = os.path.join(os.path.dirname(__file__),'..', 'config', str(name) +'.clr')
        f = open(path, 'w')
        f.write(str(name)+"\n")
        f.write("colors\n")
        for color in colors:
            f.write(str(';'.join(str(col) for col in color))+"\n")
        f.write("levels\n")
        f.write(str(';'.join(str(lvl) for lvl in levels))+"\n")
        f.close()
        
    #****************************************************************************************************
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('PostTelemacColorManager', message, None, QApplication.UnicodeUTF8)