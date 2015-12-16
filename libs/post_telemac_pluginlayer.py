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
 Implementation of QgsPluginLayer class, used to show selafin res
 
Versions :
Impl
0.0 : debut

 ***************************************************************************/
"""


#import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
#import numpy
from numpy import *
import numpy as np
#import matplotlib
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib import tri
from matplotlib import colors
import matplotlib.tri as tri
from matplotlib.mlab import griddata
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
#import telemac python
from ..libs_telemac.parsers.parserSELAFIN import SELAFIN
#imports divers
#from math import *
from time import ctime
import os.path
from ..Post_Telemac_properties_dialog import PostTelemacPropertiesDialog
import post_telemac_get_qimage
# import calculator
from collections import OrderedDict #for identify
import gc

"""
Global variable for making new graphs (matplotlib)  with maplotlib 
Concept : when creating new SelafinPluginLayer, use 
selafininstancecount for pluginlayer-draw, 
selafininstancecount + 1 for graph temp util,
 selafininstancecount + 2 for flow util
"""
selafininstancecount = 2

debug = False

class SelafinPluginLayer(QgsPluginLayer):
    """
    QgsPluginLayer implmentation for drawing selafin file results
    
    """
    CRS=QgsCoordinateReferenceSystem()
    LAYER_TYPE="selafin_viewer"
    
    def __init__(self,nom1 = None):
        """
        Init method : 
            initialize variables, connect qgis signals
            load PostTelemacPropertiesDialog class related to this SelafinPluginLayer
            load Selafin2QImage class wich is called to create the qimage needed to draw
        """
        QgsPluginLayer.__init__(self, SelafinPluginLayer.LAYER_TYPE,nom1)
        self.setValid(True)
        #global varaible init
        global selafininstancecount
        self.instancecount = int(selafininstancecount)
        #Fichier selafin - properties
        self.fname = None               # selafin file name
        self.slf = None                 # selafin class
        self.tempsmax=0                 #Max time of selafin file
        self.parametres=[]              #Parameters of selafin file [rank,name]
        self.parametrestoload = []    #virtual parameters to load with projet
        self.dico = {}                  #dico for eval for virtual parametre
        self.param_gachette=None        #temp parameter of selafin file
        self.param_memoire=None         #parameter choosen of selafin file
        self.param_identify = None      #temp parameter of selafin file for identify method
        self.lvl_gachette=[]            #temp level for traitment of selafin file
        self.lvl_memoire=[]             #level for traitment of selafin file
        self.lvl_vel = []             #Level for velocity
        self.temps_gachette=None           #time for traitment of selafin file
        self.temps_memoire=None            #time  choosen of selafin file
        self.temps_identify = None      #temp time of selafin file for identify method
        self.alpha = 100                #transparency choosen of the layer
        self.alpha_gachette = 100       #temp transparency  of the layer
        self.values=None                #Values of params for time t
        self.value=None                 #Values of param_gachette for time t
        #properties dialog
        self.canvas = iface.mapCanvas()
        self.loaddirectory = None       #the directory of "load telemac" button
        self.propertiesdialog = PostTelemacPropertiesDialog(self)
        
        #Connectors
        self.layerCrsChanged.connect(self.changecrs)                             #crs check because reprojection is not effective
        self.canvas.destinationCrsChanged.connect(self.changecrs)
        QgsMapLayerRegistry.instance().layersWillBeRemoved["QStringList"].connect(self.RemoveScenario)  #to close properties dialog when layer deleted
        #iface.projectRead.connect(self.projectreadfinished)
        #viewer parameters
        self.renderersizepx=None
        self.rendererrect=None
        self.selafinqimage = post_telemac_get_qimage.Selafin2QImage(self.instancecount)
        self.affichagevitesse = False
        self.parametrevx = None
        self.parametrevy = None
        self.parametreh = None
        self.forcerefresh = False
        self.showmesh = False
        #matplotlib thongs and others
        self.triangulation = None
        self.triinterp = None           #triinterp for plotting tools
        self.compare = False
        self.compare_identify = False
        self.trifind = None
        #color ramp
        self.cmap = None
        self.cmap_vel = None
        self.propertiesdialog.color_palette_changed(0)
        self.propertiesdialog.color_palette_changed_vel(0)
        self.cmap_gachette = None
        self.cmap3 = None
        self.norm3 = None
        self.colors3 = None
        self.cmap3_vel = None
        self.norm3_vel = None
        self.colors3_vel = None
        self.levels=[self.propertiesdialog.predeflevels[i][1] for i in range(len(self.propertiesdialog.predeflevels))]
        #networkx
        self.networkxgraph =  None
        """
        #Add 3 to global variable : 
            figure (selafininstancecount) used for get_image, 
            figure(selafininstancecount + 1) for graphtemp, 
            figure(selafininstancecount +2) for graph flow
        """
        selafininstancecount = selafininstancecount + 3




        
    #****************************************************************************************************
    #************* Typical plugin layer methods***********************************************************
    #****************************************************************************************************
    
    def legendSymbologyItems(self, iconSize):
        """ 
        implementation of method from QgsPluginLayer to show legend entries (in QGIS >= 2.1) 
        return an array with [name of symbology, qpixmap]
        """
        if self.slf != None :
            lst = [(  (str(self.parametres[self.param_gachette][1]), QPixmap())  )]
            for i in range(len(self.lvl_gachette)-1):
                pix = QPixmap(iconSize)
                r,g,b,a = self.colors3[i][0]*255,self.colors3[i][1]*255,self.colors3[i][2]*255,self.colors3[i][3]*255
                pix.fill(QColor(r,g,b))
                lst.append( (str(self.lvl_gachette[i])+"/"+str(self.lvl_gachette[i+1]), pix))
            
            if self.propertiesdialog.groupBox_schowvel.isChecked() :
                lst.append((self.tr('VELOCITY'),QPixmap()))
                for i in range(len(self.lvl_vel)-1):
                    pix = QPixmap(iconSize)
                    r,g,b,a = self.colors3_vel[i][0]*255,self.colors3_vel[i][1]*255,self.colors3_vel[i][2]*255,self.colors3_vel[i][3]*255
                    pix.fill(QColor(r,g,b))
                    lst.append( (str(self.lvl_vel[i])+"/"+str(self.lvl_vel[i+1]), pix))
                
            return lst
        else:
            return []

            
    #Not used yet
    def readSymbology(self, node, err):
        """ Called when copy symbology is activated"""
        return False
    def writeSymbology(self, node, doc, err):
        """ Called when past symbology is activated"""
        return False
            
        
    def draw(self, rendererContext):
        """ 
        implementation of method from QgsPluginLayer to draw on he mapcanvas 
        return True if successful
        """
        starttime2 = time.clock()
        if self.slf !=None:
            bool1,image1 = self.selafinqimage.getimage(self,rendererContext)
        else:
            image1 = QImage()
            bool1=True
        painter = rendererContext.painter()
        painter.save()
        painter.drawImage(0,0,image1)
        painter.restore()
        txt=str(round(time.clock()-starttime2,3))
        return bool1

    def extent(self):
        """ 
        implementation of method from QgsMapLayer to compute the extent of the layer 
        return QgsRectangle()
        """
        if self.slf != None:
            return QgsRectangle(float(min(self.slf.MESHX)), float(min(self.slf.MESHY)), float(max(self.slf.MESHX)),  float(max(self.slf.MESHY)))
        else:
            return QgsRectangle()
            
    #****************************************************************************************************
    #Initialise methods *********************************************************************
    #****************************************************************************************************

    def load_selafin(self,fname=None):
        """
        Handler called when 'choose file' is clicked
        Load Selafin file and initialize properties dialog
        """

        if not fname:
            str1 = self.tr("Result file chooser")
            str2 = self.tr("Telemac files")
            str3 = self.tr("All files")     
            #tempname = self.propertiesdialog.qfiledlg.getOpenFileName(None,"Choix du fichier res",self.loaddirectory, "Fichiers Telemac (*.res *.geo *.init);;Tous les fichiers (*)")
            tempname = self.propertiesdialog.qfiledlg.getOpenFileName(None,str1,self.loaddirectory, str2 + " (*.res *.geo *.init *.slf);;" + str3 + " (*)")
            if tempname:
                self.fname = tempname
                self.param_gachette = None
                self.lvl_gachette = None
                self.temps_gachette = None
                self.alpha_gachette = 100.0
        else:
            self.fname = fname  #cas du chargement d'un projet qgis 

        if self.fname:
            #repertoire de recherche
            self.loaddirectory = os.path.dirname(self.fname)
            #Update name in symbology
            nom = os.path.basename(self.fname).split('.')[0]
            self.setLayerName(nom)
            #Set selafin
            self.set_selafin(SELAFIN(self.fname) )
            #nitialize layer's parameters
            if not self.param_gachette : self.param_gachette=0
            if not self.lvl_gachette : self.lvl_gachette=self.levels[0]
            if not self.temps_gachette : self.temps_gachette=0
            self.compare = False
            self.compare_identify = False
            self.triinterp = None
            #change levels
            self.change_lvl(self.lvl_gachette)
            self.change_lvl_vel(self.lvl_vel)
            #initialise sleafin crs
            if  self.crs().authid() == u'':
                self.setCrs(iface.mapCanvas().mapRenderer().destinationCrs())
            #update selafin values
            self.updateSelafinValues()
            #Update propertiesdialog
            self.propertiesdialog.update()
            #final update
            self.triggerRepaint()
            iface.legendInterface().refreshLayerSymbology(self)
            #self.propertiesdialog.textBrowser_main.append(str(ctime())+" - " + self.tr('File ') +  str(nom) +  self.tr(" loaded"))
            self.propertiesdialog.normalMessage(self.tr('File ') +  str(nom) +  self.tr(" loaded"))
            iface.mapCanvas().setExtent(self.extent())
        else:
            self.propertiesdialog.label_loadslf.setText(self.tr('No file selected'))
            
            
    def set_selafin(self,slf1):
        """
        Called load_selafin by when changing selafin file
        Set selafin variables
        """
        self.slf = slf1
        self.set_triangul(self.slf)
        self.tempsmax=len(self.slf.tags["times"])-1
        self.parametres = []
        #Charge les parametres dans self.parametres
        for i,name in enumerate(self.slf.VARNAMES):
            self.parametres.append([i,name.strip(),None])
        if len(self.parametrestoload)>0:
            for param in self.parametrestoload:
                self.parametres.append([len(self.parametres),param[1],param[2]])
        try:
            self.parametrevx = self.propertiesdialog.postutils.getParameterName("VITESSEU")[0]
            self.parametrevy = self.propertiesdialog.postutils.getParameterName("VITESSEV")[0]
            self.propertiesdialog.groupBox_vel.setEnabled(True)
        except Exception, e:
            #self.propertiesdialog.groupBox_8.setEnabled(False)
            self.propertiesdialog.groupBox_schowvel.setEnabled(False)
            #TODO : disable utils dependant on velocity (flow, show velocity)
        try:
            self.parametreh = self.propertiesdialog.postutils.getParameterName("HAUTEUR")[0]
        except Exception, e:
            pass
            #TODO : disable utils dependant on velocity (flow, show velocity)
            

                    
    def set_triangul(self,slf1,ct=None):
        """
        Called set_selafin by when changing selafin file
        set matplotlib's triangulation variables
        """
        if ct:
            pass
        if slf1:
            self.triangulation = tri.Triangulation(slf1.MESHX,slf1.MESHY,np.array(slf1.IKLE3))
            try:
                self.trifind = self.triangulation.get_trifinder()
            except Exception, e:
                print 'bug with trifinder ' + str(e)
                print 'regenerate selafin file please'
                #TODO : disable utils dependant trifind (valeurs,?)

            

    #****************************************************************************************************
    #Update method - selafin value - used with compare util  *********************************
    #****************************************************************************************************
            
    def updateSelafinValues(self,force = False):
        """
        Updates the values stored in self.values and self.value
        called when loading selfin file, or when selafin's time is changed
        """
        if not self.compare:
            if self.param_memoire == self.param_gachette and self.temps_memoire == self.temps_gachette and not force:
                pass
            else:
                values = self.slf.getVALUES(self.temps_gachette)
                for param in self.parametres:
                    if param[2]:
                        self.dico = self.getDico(param[2], self.parametres, values)
                        val = eval(param[2],{}, self.dico)
                        values = np.vstack((values,val))
                self.values = values
                self.value = self.values[self.param_gachette]
                    
        else:
            self.updatevalue.emit()
            
    updatevalue = pyqtSignal()
    
    def getDico(self,expr, parametres, values):
        dico = {}
        dico['sin'] = sin
        dico['cos'] = cos
        dico['abs'] = abs
        dico['int'] = int
    
        a = 'V{}'
        nb_var = len(values)
        i = 0
        num_var = 0
        while num_var < nb_var:
            dico[a.format(i)] = values[i]
            num_var += 1
            i += 1
        return dico
        

    #****************************************************************************************************
    #Update method - Color map and level update  *********************************
    #****************************************************************************************************
                    
    def change_cm(self,cm):
        """
        change the color map and layer symbology
        """
        if len(self.lvl_gachette)>=2:
            lvls=self.lvl_gachette
            tab1 = []
            max1=256
            for i in range(len(lvls)-1):
                if len(lvls)==2:
                    tab1.append(1.0)
                else:
                    tab1.append(int(max1*i/(len(lvls)-2)))
            self.colors3 = cm(tab1)
            self.cmap3,self.norm3 = colors.from_levels_and_colors(lvls,self.colors3)
        iface.legendInterface().refreshLayerSymbology(self)
        self.triggerRepaint()
        
    def change_cm_vel(self,cm):
        """
        change the color map and layer symbology
        """
        if len(self.lvl_vel)>=2:
            lvls=self.lvl_vel
            tab1 = []
            max1=256
            for i in range(len(lvls)-1):
                if len(lvls)==2:
                    tab1.append(1.0)
                else:
                    tab1.append(int(max1*i/(len(lvls)-2)))
            self.colors3_vel = cm(tab1)
            self.cmap3_vel,self.norm3_vel = colors.from_levels_and_colors(lvls,self.colors3_vel)
        iface.legendInterface().refreshLayerSymbology(self)
        self.triggerRepaint()
        
    def changeAffichageVitesse(self,int1):
        """
        Called when PostTelemacPropertiesDialog 's "plot velocity" checkbox is checked
        
        """
        self.parametrevx = self.propertiesdialog.postutils.getParameterName("VITESSEU")[0]
        self.parametrevy = self.propertiesdialog.postutils.getParameterName("VITESSEV")[0]
        #self.propertiesdialog.textBrowser_main.append(str(ctime())+" - paramX : "+str(self.parametrevx)+" paramY : "+str(self.parametrevy))
        """
        if int1 == 2:
            self.affichagevitesse = True
        elif int1 == 0:
            self.affichagevitesse = False
        """
        self.forcerefresh = True
        iface.legendInterface().refreshLayerSymbology(self)
        self.triggerRepaint()
    
    def showMesh(self,int1):
        """
        Called when PostTelemacPropertiesDialog 's "plot mesh" checkbox is checked
        """
        if int1 == 2:
            self.showmesh = True
        elif int1 == 0:
            self.showmesh = False
        self.triggerRepaint()
        
        self.forcerefresh = True
        self.triggerRepaint()

    
    def change_lvl(self,tab):
        """
        change the levels, update color map and layer symbology
        """
        self.lvl_gachette = tab
        self.change_cm( self.cmap)
        iface.legendInterface().refreshLayerSymbology(self)
        self.propertiesdialog.lineEdit_levelschoosen.setText(str(self.lvl_gachette))
        self.triggerRepaint()
        
    def change_lvl_vel(self,tab):
        """
        change the levels, update color map and layer symbology
        """
        self.lvl_vel = tab
        self.change_cm_vel( self.cmap_vel)
        iface.legendInterface().refreshLayerSymbology(self)
        self.propertiesdialog.lineEdit_levelschoosen_2.setText(str(self.lvl_vel))
        self.triggerRepaint()
    
    
    #****************************************************************************************************
    #Update method - transaprency, param, time,crs  *********************************
    #****************************************************************************************************
            
    def changeAlpha(self,nb):
        """When changing alpha value"""
        self.alpha_gachette = float(nb)
        if self.draw:
            self.triggerRepaint()
            
            
    def change_param(self,int1):
        """When changing parameter value"""
        self.param_gachette = int1
        self.value = self.values[self.param_gachette]
        iface.legendInterface().refreshLayerSymbology(self)
        self.triggerRepaint()
        
    def change_param2(self,int1=None):
        """When changing parameter value"""
        getSelected = self.propertiesdialog.treeWidget_parameters.selectedItems()
        try:
            baseNode = getSelected[0]
            position = [self.propertiesdialog.treeWidget_parameters.indexFromItem(baseNode).parent().row(),self.propertiesdialog.treeWidget_parameters.indexFromItem(baseNode).row()]
            """
            indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
            itemname = self.treewidgettoolsindextab[indextabtemp.index(position)][2]
            """
            self.param_gachette = position[1]
            if self.parametres[position[1]][2]:
                self.propertiesdialog.pushButton_param_edit.setEnabled(True)
                self.propertiesdialog.pushButton_param_delete.setEnabled(True)
            else:
                self.propertiesdialog.pushButton_param_edit.setEnabled(False)
                self.propertiesdialog.pushButton_param_delete.setEnabled(False)
                
            
        except Exception, e:
            itemname = None

        self.updateSelafinValues()
        #self.value = self.values[self.param_gachette]
        iface.legendInterface().refreshLayerSymbology(self)
        self.triggerRepaint()
        

    def change_timetxt(self,nb):
        """Associated with time modification"""
        self.temps_gachette=nb
        self.updateSelafinValues()
        time2 = time.strftime("%j:%H:%M:%S", time.gmtime(self.slf.tags["times"][self.temps_gachette]))
        
        self.propertiesdialog.label_time.setText(self.tr("time (hours)") + " : " + str(time2) +"\n"+ 
                                              self.tr("time (iteration)") + " : "+ str(self.temps_gachette)+"\n"+
                                              self.tr("time (seconds)") + " : " + str(self.slf.tags["times"][self.temps_gachette]))
        if self.draw:
            self.triggerRepaint()
            

    def changecrs(self):
        """Associated with layercrschaned slot"""
        try:
            #self.propertiesdialog.pushButton_crs.setText(self.crs().authid())
            self.propertiesdialog.label_selafin_crs.setText(self.crs().authid())
            if iface.mapCanvas().mapSettings().destinationCrs() != self.crs():
                """
                self.propertiesdialog.textBrowser_main.setTextColor(QColor("red"))
                self.propertiesdialog.textBrowser_main.setFontWeight(QFont.Bold)
                self.propertiesdialog.textBrowser_main.append(ctime() + self.tr(" - Beware : qgis project's crs is not the same as selafin's crs - reprojection is not implemented")
                                                              + self.tr(" - Project's CRS : ") +str(iface.mapCanvas().mapSettings().destinationCrs().authid()) + self.tr(" / Selafin's CRS : ")   
                                                              + str(self.crs().authid()))
                self.propertiesdialog.textBrowser_main.setTextColor(QColor("black"))
                self.propertiesdialog.textBrowser_main.setFontWeight(QFont.Normal)
                """
                self.propertiesdialog.errorMessage(self.tr(" - Beware : qgis project's crs is not the same as selafin's crs - reprojection is not implemented")
                                                  + self.tr(" - Project's CRS : ") +str(iface.mapCanvas().mapSettings().destinationCrs().authid()) + self.tr(" / Selafin's CRS : ")   
                                                  + str(self.crs().authid()))
        except Exception, e:
            pass
        
    #****************************************************************************************************
    #Update method - wait for slider to be released  *********************************
    #****************************************************************************************************
    
    def change2(self):
        """Associated with slider behaviour"""
        self.draw=True
        self.triggerRepaint()
        
    def change1(self):
        """Associated with slider behaviour"""
        self.draw=False
 
    #****************************************************************************************************
    #method for profile tool  *********************************

    def name(self):
        return os.path.basename(self.fname).split('.')[0]
        
    def bandCount(self):
        return len(self.parametres)
        
    def rasterUnitsPerPixel(self):
        # Only required so far for the profile tool
        # There's probably a better way of doing this
        return float(0.5)
    
    def rasterUnitsPerPixelX(self):
        # Only required so far for the profile tool
        return self.rasterUnitsPerPixel()
    
    def rasterUnitsPerPixelY(self):
        # Only required so far for the profile tool
        return self.rasterUnitsPerPixel()
        


    #****************************************************************************************************
    #method for identifying value  *********************************


    
    def identify(self,qgspoint,multiparam = False):
        """
        Called by profile tool plugin
        compute value of selafin parameters at point qgspoint
        return tuple with (success,  dictionnary with {parameter : value} )
        """
        #triinterp creation
        self.updateSelafinValues()
        if self.temps_identify == self.temps_memoire and self.compare_identify == self.compare and self.triinterp:
            pass
        else:
            self.triinterp = [tri.LinearTriInterpolator(self.triangulation, self.values[i]) for i in range(len(self.parametres))]
            self.temps_identify = self.temps_memoire
            self.compare_identify = self.compare
        #getvalues
        try:
            v= [float(self.triinterp[i].__call__(qgspoint.x(),qgspoint.y())) for i in range(len(self.parametres))]
        except Exception, e :
            v = None
        #send results
        if multiparam:
            strident = ''
            try:
                for i in range(len(self.parametres)):
                    strident = strident + str(self.parametres[i][1])+" : "+str(v[i])+"\n"
            except Exception,e:
                print str(e)
            return strident
        else:
            d = OrderedDict()
            #d = dict()
            for param in self.parametres:
                try:
                    d[ QString(param[1]) ] = v[param[0]]
                except:
                    d[ param[1] ] = v[param[0]]
            
            """
            d = []
            for param in self.parametres:
                d.append([param[1], v[param[0]]])
            """
            return (True,d)
        
    #****************************************************************************************************
    #************Method for saving/loading project with selafinlayer file***********************************
    #****************************************************************************************************
    
    def readXml(self, node):
        """
        implementation of method from QgsMapLayer to load layer from qgsproject
        return True ifsuccessful
        """
        element = node.toElement()
        prj = QgsProject.instance()
        fname=prj.readPath( element.attribute('meshfile') )
        self.param_gachette = int(element.attribute('parametre'))
        self.alpha_gachette = int(element.attribute('alpha'))
        self.temps_gachette = int(element.attribute('time'))
        self.showmesh = int(element.attribute('showmesh'))
        self.propertiesdialog.checkBox_showmesh.setChecked(self.showmesh) 
        
        #levelthings
        self.propertiesdialog.comboBox_genericlevels.setCurrentIndex(int(element.attribute('level_value')))
        lvlstep = [element.attribute('level_step').split(";")[i] for i in range(len(element.attribute('level_step').split(";")))]
        self.propertiesdialog.lineEdit_levelmin.setText(lvlstep[0])
        self.propertiesdialog.lineEdit_levelmax.setText(lvlstep[1])
        self.propertiesdialog.lineEdit_levelstep.setText(lvlstep[2])
        self.propertiesdialog.comboBox_clrgame.setCurrentIndex(int(element.attribute('level_color')))

        self.propertiesdialog.comboBox_levelstype.setCurrentIndex(int(element.attribute('level_type')))
        if int(element.attribute('level_type'))==0:
            self.propertiesdialog.change_cmchoosergenericlvl()
        elif int(element.attribute('level_type'))==1:
            self.propertiesdialog.createstepclass()

        
        #velocity things
        self.propertiesdialog.comboBox_genericlevels_2.setCurrentIndex(0)
        self.propertiesdialog.comboBox_clrgame_2.setCurrentIndex(0)
        self.propertiesdialog.change_cmchoosergenericlvl_vel()
        
        #Virtual param things
        strtemp =  element.attribute('virtual_param').split(';')
        count = int((len(strtemp)-1)/2)
        for i in range(count):
            self.parametrestoload.append([i,strtemp[i],strtemp[i+1]])
        
        self.load_selafin(fname)

        return True
        
        
        
    def writeXml(self, node, doc):
        """
        implementation of method from QgsMapLayer to save layer in  qgsproject
        return True ifsuccessful
        """
        prj = QgsProject.instance()
        element = node.toElement()
        element.setAttribute("type", "plugin")
        element.setAttribute("name", SelafinPluginLayer.LAYER_TYPE)
        element.setAttribute("meshfile", prj.writePath(self.fname))
        element.setAttribute("parametre", self.param_gachette)
        element.setAttribute("alpha", self.alpha_gachette)
        element.setAttribute("time", self.temps_gachette)
        element.setAttribute("showmesh", int(self.showmesh))
        #levelthings
        element.setAttribute("level_color", self.propertiesdialog.comboBox_clrgame.currentIndex())
        element.setAttribute("level_type", self.propertiesdialog.comboBox_levelstype.currentIndex())
        element.setAttribute("level_value", self.propertiesdialog.comboBox_genericlevels.currentIndex())
        element.setAttribute("level_step", self.propertiesdialog.lineEdit_levelmin.text()+";"+self.propertiesdialog.lineEdit_levelmax.text()+";"+self.propertiesdialog.lineEdit_levelstep.text())
        #Virtuall param things
        strtrmp = ''
        for param in self.parametres:
            if param[2]:
                strtrmp += param[1]+';'+param[2]+';'
        element.setAttribute("virtual_param", strtrmp)
        
        return True

    #****************************************************************************************************
    #************Called when the layer is deleted from qgis canvas ***********************************
    #****************************************************************************************************
    """
    def projectreadfinished(self):
        QgsMapLayerRegistry.instance().layersWillBeRemoved["QStringList"].connect(self.RemoveScenario)  #to close properties dialog when layer deleted
    """
    def RemoveScenario(self,string1): 
        """
        When deleting a selafin layer - remove : 
            matplotlib ' s figures
            propertiesdialog 
            and other things
        """
        if str(self.id()) in string1:
            #closing figures
            try:
                self.propertiesdialog.figure1.clf()
                plt.close(self.propertiesdialog.figure1)
            except Exception, e :
                print 'fig1 ' + str(e)
            try:
                self.propertiesdialog.figure2.clf()
                plt.close(self.propertiesdialog.figure2)
            except Exception, e :
                print 'fig2 ' + str(e)
            try:
                self.selafinqimage.fig.clf()
                plt.close(self.selafinqimage.fig)
            except Exception, e :
                print 'fig ' + str(e)
            self.propertiesdialog.postutils.rubberband.reset()
            #closing properties dialog
            self.propertiesdialog.close()
            del self.propertiesdialog
            #closing some stuff
            del self.values
            del self.value
            del self.selafinqimage
            del self.networkxgraph
            #end : garbage collector 
            gc.collect()
            #close connecxions
            QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.RemoveScenario)

    #****************************************************************************************************
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('SelafinPluginLayer', message, None, QApplication.UnicodeUTF8)
    
