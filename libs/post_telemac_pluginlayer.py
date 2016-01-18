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
#import scipy
#from scipy.spatial import cKDTree
#import matplotlib
#from matplotlib import tri
from matplotlib import colors
#import PyQT
from PyQt4.QtCore import *
from PyQt4.QtGui import *
# other import
from collections import OrderedDict #for identify
import gc
import os.path
import time
import numbers
#local import 
from ..dialogs.posttelemacpropertiesdialog import PostTelemacPropertiesDialog
from post_telemac_pluginlayer_get_qimage import *
from post_telemac_pluginlayer_colormanager import *
from ..posttelemacparsers.posttelemac_selafin_parser import *

"""
Global variable for making new graphs (matplotlib)  with maplotlib 
Concept : when creating new SelafinPluginLayer, use 
selafininstancecount for pluginlayer-draw, 
selafininstancecount + 1 for graph temp util,
 selafininstancecount + 2 for flow util
"""
selafininstancecount = 2

debug = False
DEBUGTIME = False

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
        self.realCRS = QgsCoordinateReferenceSystem()
        self.xform = None       #transformation for reprojection
        #global variable init
        global selafininstancecount
        self.instancecount = int(selafininstancecount)
        #selafin file - properties
        self.hydraufilepath = None               # selafin file name
        self.parametres=[]              #Parameters of selafin file [[rank,name,None or formula for virtual parameter,identify corresponding value],...]
        self.parametrevx = None         #specific num for velolity x parameter
        self.parametrevy = None
        self.parametreh = None
        self.parametrestoload = []    #virtual parameters to load with projet
        self.dico = {}                  #dico for eval for virtual parametre
        self.param_displayed=None        #temp parameter of selafin file
        self.lvl_contour=[]            #level for contour of selafin file 
        self.lvl_vel = []             #Level for velocity 
        self.time_displayed=None           #time for displaying of selafin file
        self.alpha_displayed = 100       #transparency  of the layer
        self.values=None                #Values of params for time t
        self.value=None                 #Values of param_gachette for time t
        #managers
        self.colormanager = PostTelemacColorManager(self)
        self.hydrauparser = None
        #properties dialog
        self.canvas = iface.mapCanvas()
        self.propertiesdialog = PostTelemacPropertiesDialog(self)
        #matplotlib things and others
        #self.triangulation = None       #matplotlib triangulation of the mesh
        self.triinterp = None           #triinterp for plotting tools
        #self.trifind = None
        #viewer parameters
        self.selafinqimage = Selafin2QImage(self,self.instancecount)
        self.affichagevitesse = False
        self.forcerefresh = False
        self.showmesh = False
        self.showvelocityparams =  {'show' : False,
                                    'type' : None,
                                    'step' : None,
                                    'norm' : None}
        #color ramp
        #for contour
        self.cmap_mpl_contour_raw = None    #original cmap, unchanged with levels
        self.cmap_mpl_contour = None        #cmap modified to correspond levels values
        self.norm_mpl_contour = None        
        self.color_mpl_contour = None       
        self.propertiesdialog.color_palette_changed_contour(0)
        #for velocity
        self.cmap_mpl_vel_raw = None
        self.cmap_mpl_vel = None
        self.norm_mpl_vel = None
        self.color_mpl_vel = None
        self.propertiesdialog.color_palette_changed_vel(0)
        #levels
        self.levels=[self.propertiesdialog.predeflevels[i][1] for i in range(len(self.propertiesdialog.predeflevels))]
        #networkx - to draw path with the mesh 
        self.networkxgraph =  None
        """
        #Add 3 to global variable : 
            figure (selafininstancecount) used for get_image, 
            figure(selafininstancecount + 1) for graphtemp, 
            figure(selafininstancecount +2) for graph flow
        """
        selafininstancecount = selafininstancecount + 3
        
        #Connectors
        self.canvas.destinationCrsChanged.connect(self.changecrs)
        QgsMapLayerRegistry.instance().layersWillBeRemoved["QStringList"].connect(self.RemoveScenario)  #to close properties dialog when layer deleted
        self.updatevalue.connect(self.updateSelafinValues1)

    #****************************************************************************************************
    #************* Typical plugin layer methods***********************************************************
    #****************************************************************************************************
            
    def draw(self, rendererContext):
        """ 
        implementation of method from QgsPluginLayer to draw on he mapcanvas 
        return True if successful
        image 2 is used to display only mesh (make the render faster)
        """
        if self.hydrauparser !=None and self.hydrauparser.hydraufile !=None :
            bool1,image1,image2 = self.selafinqimage.getimage(self,rendererContext)
        else:
            image1 = QImage()
            image2 = None
            bool1=True
        painter = rendererContext.painter()
        painter.save()
        painter.drawImage(0,0,image1)
        if image2:
            painter.drawImage(0,0,image2)
        painter.restore()
        return bool1

    def extent(self):
        """ 
        implementation of method from QgsMapLayer to compute the extent of the layer 
        return QgsRectangle()
        """
        if self.hydrauparser != None and self.hydrauparser.hydraufile != None :
            meshx,meshy = self.hydrauparser.getMesh()
            rect = QgsRectangle(float(min(meshx)), float(min(meshy)), float(max(meshx)),  float(max(meshy)))
            return self.xform.transformBoundingBox(rect)
        else:
            return QgsRectangle()
            
    def legendSymbologyItems(self, iconSize):
        """ 
        implementation of method from QgsPluginLayer to show legend entries (in QGIS >= 2.1) 
        return an array with [name of symbology, qpixmap]
        """
        lst = self.colormanager.generateSymbologyItems(iconSize)
        return lst
            
    #Not used yet
    def readSymbology(self, node, err):
        """ Called when copy symbology is activated"""
        return False
    def writeSymbology(self, node, doc, err):
        """ Called when past symbology is activated"""
        return False
            
    #****************************************************************************************************
    #Initialise methods *********************************************************************
    #****************************************************************************************************

    def load_selafin(self,hydraufilepath=None):
        """
        Handler called when 'choose file' is clicked
        Load Selafin file and initialize properties dialog
        """
        self.hydraufilepath = hydraufilepath
        #Update name in symbology
        nom = os.path.basename(self.hydraufilepath).split('.')[0]
        self.setLayerName(nom)
        #Set selafin
        self.hydrauparser = PostTelemacSelafinParser(self)
        self.hydrauparser.loadHydrauFile(self.hydraufilepath)
        #nitialize layer's parameters
        if not self.param_displayed : self.param_displayed = 0
        if not self.lvl_contour : self.lvl_contour=self.levels[0]
        if not self.time_displayed : self.time_displayed = 0
        self.initSelafinParameters()
        self.triinterp = None
        #change levels
        self.change_lvl_contour(self.lvl_contour)
        self.change_lvl_vel(self.lvl_vel)
        #initialise selafin crs
        if  self.crs().authid() == u'':
            self.setRealCrs(iface.mapCanvas().mapRenderer().destinationCrs())
        self.xform = QgsCoordinateTransform(self.realCRS, iface.mapCanvas().mapSettings().destinationCrs())
        self.selafinqimage.changeTriangulationCRS()
        #update selafin values
        self.updateSelafinValues()
        #Update propertiesdialog
        self.propertiesdialog.update()
        #final update
        self.triggerRepaint()
        iface.legendInterface().refreshLayerSymbology(self)
        iface.mapCanvas().setExtent(self.extent())

    def initSelafinParameters(self):
        """
        Called load_selafin by when changing selafin file
        Set selafin variables
        """
        #self.initTriangul()
        self.parametres = []
        #load  parametres in self.parametres
        for i,name in enumerate(self.hydrauparser.getVarnames()):
            self.parametres.append([i,name.strip(),None,i])
        if len(self.parametrestoload)>0:    #case of virtual parameters when loadin a selafin layer
            for param in self.parametrestoload:
                self.parametres.append([len(self.parametres),param[1],param[2],len(self.parametres)])
        try:    #load velocity parameters
            self.parametrevx = self.propertiesdialog.postutils.getParameterName("VITESSEU")[0]
            self.parametrevy = self.propertiesdialog.postutils.getParameterName("VITESSEV")[0]
            self.propertiesdialog.tab_velocity.setEnabled(True)
            for widget in self.propertiesdialog.tab_velocity.children():
                widget.setEnabled(True)
            for widget in self.propertiesdialog.groupBox_schowvel.children():
                widget.setEnabled(True)
            self.propertiesdialog.groupBox_schowvel.setChecked(True)
            self.propertiesdialog.groupBox_schowvel.setChecked(False)
        except Exception, e:
            self.propertiesdialog.tab_velocity.setEnabled(False)
            #TODO : disable utils dependant on velocity (flow, show velocity)
        try:    #load water depth parameters
            self.parametreh = self.propertiesdialog.postutils.getParameterName("HAUTEUR")[0]
        except Exception, e:
            pass
            #TODO : disable utils dependant on velocity (flow, show velocity)
            
    def clearParameters(self):
        self.param_displayed = None
        self.lvl_contour = None
        self.time_displayed = None
        self.alpha_displayed = 100.0
    
    """
    def initTriangul(self,ct=None):
        if ct:
            pass
        if self.hydrauparser.hydraufile:
            meshx, meshy = self.hydrauparser.getMesh()
            ikle = self.hydrauparser.getIkle()
            self.triangulation = matplotlib.tri.Triangulation(meshx,meshy,np.array(ikle))
            try:
                self.trifind = self.triangulation.get_trifinder()
            except Exception, e:
                print 'bug with trifinder ' + str(e)
                print 'regenerate selafin file please'
                #TODO : disable utils dependant trifind (valeurs,?)
    """
            

    #****************************************************************************************************
    #Update method - selafin value - used with compare util  *********************************
    #****************************************************************************************************
            
    def updateSelafinValues(self, onlyparamtimeunchanged = -1 ):
        """
        Updates the values stored in self.values and self.value
        called when loading selafin file, or when selafin's time is changed
        It emits a signal, because this method is redirected to a different method in comparetool  
        when tool "compare" is activated
        """
        self.updatevalue.emit(onlyparamtimeunchanged)
        
    updatevalue = pyqtSignal(int)
            
    def updateSelafinValues1(self, onlyparamtimeunchanged = -1):
        """
        Updates the values stored in self.values and self.value
        called when loading selfin file, or when selafin's time is changed
        """
        if  onlyparamtimeunchanged < 0 :
            self.values = self.getValues(self.time_displayed)
            self.value = self.values[self.param_displayed]
        else:
            self.value = self.values[self.param_displayed]

            
    def getValues(self,time):
        """
        Get the values of paameters for time time
        """
        values = self.hydrauparser.getValues(time)
        for param in self.parametres:
            if param[2]:        #for virtual parameter - compute it
                self.dico = self.getDico(param[2], self.parametres, values)
                val = eval(param[2],{"__builtins__":None}, self.dico)
                values = np.vstack((values,val))
        return values


    
    def getDico(self,expr, parametres, values):
        """
        Used for calculation of virtual parameters
        """
        dico = {}
        dico['sin'] = sin
        dico['cos'] = cos
        dico['abs'] = abs
        dico['int'] = int
        dico['if_then_else'] = self.if_then_else
        a = 'V{}'
        nb_var = len(values)
        i = 0
        num_var = 0
        while num_var < nb_var:
            dico[a.format(i)] = values[i]
            num_var += 1
            i += 1
        return dico
        
    def if_then_else(self,ifstat,true1,false1):
        """
        Used for calculation of virtual parameters
        """
        #condition
        if isinstance(ifstat,np.ndarray):
            var2 = np.zeros(ifstat.shape)
            temp1 = np.where(ifstat)
        elif isinstance(ifstat,str):
            val = eval(ifstat,{"__builtins__":None}, self.dico)
            var2 = np.zeros(val.shape)
            temp1 = np.where(val)
        #True
        if isinstance(true1,np.ndarray):
            var2[temp1] = true1[temp1]
        elif isinstance(true1, numbers.Number):
            var2[temp1] = float(true1)
        else:
            pass
        #False
        mask = np.ones(var2.shape, np.bool)
        mask[temp1] = 0
        if isinstance(false1,np.ndarray):
            var2[mask] = false1[mask]
        elif isinstance(false1, numbers.Number):
            var2[mask] = float(false1)
        else:
            pass
        return var2
        
    #****************************************************************************************************
    #Change variables                                                  *********************************
    #****************************************************************************************************
                    
    def change_cm_contour(self,cm):
        """
        change the color map and layer symbology
        """
        if len(self.lvl_contour)>=2:
            lvls=self.lvl_contour
            tab1 = []
            max1=256
            if len(lvls) == 2 :
                tab1=[1.0]
            else:
                tab1 = [int(max1*i/(len(lvls)-2)) for i in range(len(lvls)-1)]
            self.color_mpl_contour = cm(tab1)
            self.cmap_mpl_contour,self.norm_mpl_contour = matplotlib.colors.from_levels_and_colors(lvls,self.color_mpl_contour)
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
            self.color_mpl_vel = cm(tab1)
            self.cmap_mpl_vel,self.norm_mpl_vel = matplotlib.colors.from_levels_and_colors(lvls,self.color_mpl_vel)
        iface.legendInterface().refreshLayerSymbology(self)
        self.triggerRepaint()
        
    def change_lvl_contour(self,tab):
        """
        change the levels, update color map and layer symbology
        """
        self.lvl_contour = tab
        self.change_cm_contour(self.cmap_mpl_contour_raw)
        iface.legendInterface().refreshLayerSymbology(self)
        self.propertiesdialog.lineEdit_levelschoosen.setText(str(self.lvl_contour))
        self.triggerRepaint()
        
    def change_lvl_vel(self,tab):
        """
        change the levels, update color map and layer symbology
        """
        self.lvl_vel = tab
        self.change_cm_vel( self.cmap_mpl_vel_raw)
        iface.legendInterface().refreshLayerSymbology(self)
        self.propertiesdialog.lineEdit_levelschoosen_2.setText(str(self.lvl_vel))
        self.triggerRepaint()
        
    def changeTime(self,nb):
        """When changing time value to display"""
        self.time_displayed = nb
        self.updateSelafinValues()
        self.triinterp = None
        if self.draw:
            self.triggerRepaint()
            
    def changeAlpha(self,nb):
        """When changing alpha value for display"""
        self.alpha_displayed = float(nb)
        if self.draw:
            self.triggerRepaint()
            
    def changeParam(self,int1):
        """When changing parameter value for display"""
        self.param_displayed = int1
        self.updateSelafinValues(int1)
        iface.legendInterface().refreshLayerSymbology(self)
        self.forcerefresh = True
        self.triggerRepaint()
        
    def setRealCrs(self,qgscoordinatereferencesystem):
        """
        The real crs of layer is saved in realCRS variable.
        Otherwise (if real crs is saved in CRS variable), reprojection of the qimage is not fully working. 
        So the layer.crs is the same as the canvas.crs, and reprojection is done in selafinqimage using layer.realCRS
        """
        self.realCRS = qgscoordinatereferencesystem
        self.setCrs(iface.mapCanvas().mapSettings().destinationCrs())
        self.xform  = QgsCoordinateTransform(self.realCRS, iface.mapCanvas().mapSettings().destinationCrs())
        self.selafinqimage.changeTriangulationCRS() 
        self.forcerefresh = True
        self.triggerRepaint()
        
    def crs(self):
        """
        implement crs method to get the real CRS
        """
        return self.realCRS
            
    def changecrs(self):
        """Associated with mapcanvascrschaned slot and changing layer crs in property dialog"""
        try:
            self.setCrs(iface.mapCanvas().mapSettings().destinationCrs())
            self.xform  = QgsCoordinateTransform(self.realCRS, iface.mapCanvas().mapSettings().destinationCrs())
            self.selafinqimage.changeTriangulationCRS()
            self.forcerefresh = True
            self.triggerRepaint()
        except Exception, e:
            pass
        
    #****************************************************************************************************
    #show velocity, mesh  *********************************
    #****************************************************************************************************
        
    def showVelocity(self):
        """
        Called when PostTelemacPropertiesDialog 's "plot velocity" checkbox is checked
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
        

    #****************************************************************************************************
    #method for profile tool  *********************************
    #****************************************************************************************************

    def name(self):
        return os.path.basename(self.hydraufilepath).split('.')[0]
        
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
    #****************************************************************************************************

    
    def identify(self,qgspointfromcanvas,multiparam = False):
        """
        Called by profile tool plugin
        compute value of selafin parameters at point qgspoint
        return tuple with (success,  dictionnary with {parameter : value} )
        """
        qgspointfromcanvas= self.xform.transform(qgspointfromcanvas,QgsCoordinateTransform.ReverseTransform)
        if  self.triinterp:
            pass
        else:
            self.initTriinterpolator()
        #getvalues
        try:
            v= [float(self.triinterp[i].__call__([qgspointfromcanvas.x()],[qgspointfromcanvas.y()])) for i in range(len(self.parametres))]
        except Exception, e :
            v = None
        #send results
        d = OrderedDict()
        for param in self.parametres:
            try:
                d[ QString(param[1]) ] = v[param[0]]
            except:
                d[ param[1] ] = v[param[0]]
        return (True,d)
        
    def initTriinterpolator(self):
        self.triinterp = [tri.LinearTriInterpolator(self.hydrauparser.triangulation, self.values[i]) for i in range(len(self.parametres))]
        
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
        hydraufilepath=prj.readPath( element.attribute('meshfile') )
        self.setRealCrs(QgsCoordinateReferenceSystem( prj.readPath( element.attribute('crs') ) ) )
        self.param_displayed = int(element.attribute('parametre'))
        self.alpha_displayed = int(element.attribute('alpha'))
        self.time_displayed = int(element.attribute('time'))
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
            self.parametrestoload.append([i,strtemp[2*i],strtemp[2*i+1]])
        self.load_selafin(hydraufilepath)
        return True
        
        
        
    def writeXml(self, node, doc):
        """
        implementation of method from QgsMapLayer to save layer in  qgsproject
        return True ifsuccessful
        """
        prj = QgsProject.instance()
        element = node.toElement()
        element.setAttribute("crs", self.realCRS.authid())
        element.setAttribute("type", "plugin")
        element.setAttribute("name", SelafinPluginLayer.LAYER_TYPE)
        element.setAttribute("meshfile", prj.writePath(self.hydraufilepath))
        element.setAttribute("parametre", self.param_displayed)
        element.setAttribute("alpha", self.alpha_displayed)
        element.setAttribute("time", self.time_displayed)
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
            #closing some stuff - do not succeed in retrieving what does not release memory...
            del self.values
            del self.value
            del self.selafinqimage
            del self.networkxgraph
            del self.hydrauparser
            #end : garbage collector 
            gc.collect()
            #close connexions
            QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.RemoveScenario)
            self.canvas.destinationCrsChanged.disconnect(self.changecrs)

    #****************************************************************************************************
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('SelafinPluginLayer', message, None, QApplication.UnicodeUTF8)
    
