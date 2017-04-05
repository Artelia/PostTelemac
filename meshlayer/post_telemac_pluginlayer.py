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
 

 ***************************************************************************/
"""
#unicode behaviour
from __future__ import unicode_literals
#Standart import
import qgis.core
import qgis.utils
#Qt
from  qgis.PyQt import QtCore, QtGui
try:        #qt4
    from qgis.PyQt.QtGui import QApplication
except:     #qt5
    from qgis.PyQt.QtWidgets import  QApplication

# other import
import collections
import time
import gc
import os
#local import 
from ..meshlayerdialogs.posttelemacpropertiesdialog import PostTelemacPropertiesDialog
from ..meshlayerrenderer.meshlayer_rubberband import MeshLayerRubberband
from ..meshlayerrenderer.post_telemac_pluginlayer_renderer import PostTelemacPluginLayerRenderer

#from ..meshlayerlibs.tri import LinearTriInterpolator

"""
Global variable for making new graphs (matplotlib)  with maplotlib 
fig 0 : ??
fig 1 : ??
Concept : when creating new SelafinPluginLayer, use 
selafininstancecount for pluginlayer-draw, 
selafininstancecount + 1 for graph temp util,
 selafininstancecount + 2 for flow util
  selafininstancecount + 3 for volume util
"""
selafininstancecount = 2

debug = False


class SelafinPluginLayer(qgis.core.QgsPluginLayer):
    """
    QgsPluginLayer implmentation for drawing selafin file results
    
    """
    CRS = qgis.core.QgsCoordinateReferenceSystem()
    LAYER_TYPE = "selafin_viewer"
    timechanged = QtCore.pyqtSignal(int)
    updatevalue = QtCore.pyqtSignal(int) 
    
    
    def __init__(self,nom1 = None):
        """
        Init method : 
            initialize variables, connect qgis signals
            load PostTelemacPropertiesDialog class related to this SelafinPluginLayer
            load Selafin2QImage class wich is called to create the qimage needed to draw
        """
        qgis.core.QgsPluginLayer.__init__(self, SelafinPluginLayer.LAYER_TYPE,nom1)
        
        #global variable init
        global selafininstancecount
        self.instancecount = int(selafininstancecount)

        self.meshrenderer = None                        #the class used to get qimage for canvas or composer
        self.renderer = None                            #the qgis renderer class
        self.setValid(True)
        self.realCRS = qgis.core.QgsCoordinateReferenceSystem()
        self.xform = None       #transformation class for reprojection


        #selafin file - properties
        self.hydraufilepath = None               # selafin file name
        self.parametrestoload = {'virtual_parameters' : [],
                                 'xtranslation' : 0.0,
                                 'ytranslation' : 0.0}    #virtual parameters to load with projet
        
        self.param_displayed=None        #temp parameter of selafin file
        self.time_displayed=None           #time for displaying of selafin file
        self.values=None                #Values of params for time t
        self.value=None                 #Values of param_gachette for time t
        
        #managers
        self.hydrauparser = None                        #The dataprovider
        self.rubberband = MeshLayerRubberband(self)     #class used for rubberband
        
        #properties dialog
        self.canvas = qgis.utils.iface.mapCanvas()
        self.propertiesdialog = PostTelemacPropertiesDialog(self)


        #viewer parameters
        self.propertiesdialog.tabWidget_lvl_vel.setCurrentIndex(0)
        self.propertiesdialog.color_palette_changed(0,type = 'contour')
        self.propertiesdialog.color_palette_changed(0,type = 'velocity')
        
        self.affichagevitesse = False
        self.forcerefresh = False
        self.showmesh = False
        self.showvelocityparams =  {'show' : False,
                                    'type' : None,
                                    'step' : None,
                                    'norm' : None}
                
        self.propertiesdialog.tabWidget_lvl_vel.setCurrentIndex(0)
        self.propertiesdialog.color_palette_changed(0)
        self.propertiesdialog.tabWidget_lvl_vel.setCurrentIndex(1)
        self.propertiesdialog.color_palette_changed(0)
        self.propertiesdialog.tabWidget_lvl_vel.setCurrentIndex(0)
        
        #levels
        self.levels=[self.propertiesdialog.predeflevels[i][1] for i in range(len(self.propertiesdialog.predeflevels))]
        """
        #Add 4 to global variable : 
            figure (selafininstancecount) used for get_image, 
            figure(selafininstancecount + 1) for graphtemp, 
            figure(selafininstancecount +2) for graph flow
            figure(selafininstancecount +3) for graph volume
            figure(selafininstancecount +4) for flow computation
        """
        selafininstancecount = selafininstancecount + 5
        
        self.draw = True
        
        #Connectors
        self.canvas.destinationCrsChanged.connect(self.changecrs)
        try:    #qgis2
            qgis.core.QgsMapLayerRegistry.instance().layersWillBeRemoved["QStringList"].connect(self.RemoveScenario)  #to close properties dialog when layer deleted
        except: #qgis3
            qgis.core.QgsProject.instance().layersWillBeRemoved["QStringList"].connect(self.RemoveScenario)  #to close properties dialog when layer deleted
            
        self.updatevalue.connect(self.updateSelafinValues1)
        
        #load parsers
        self.parsers=[]     #list of parser classes
        self.loadParsers()
        

    #****************************************************************************************************
    #************* Typical plugin layer methods***********************************************************
    #****************************************************************************************************
        
    def createMapRenderer(self, rendererContext):
        self.renderer = PostTelemacPluginLayerRenderer(self, rendererContext)
        return self.renderer
    
    
    
    def loadParsers(self):
        import glob
        import sys, inspect
        import importlib
        self.parsers=[]
        path = os.path.join(os.path.dirname(__file__),'..','meshlayerparsers')
        modules = glob.glob(path+"/*.py")
        __all__ = [ os.path.basename(f)[:-3] for f in modules if os.path.isfile(f)]
        import PostTelemac.meshlayerparsers
        for x in __all__:
            module = importlib.import_module('.'+ str(x), 'PostTelemac.meshlayerparsers' )
            for name, obj in inspect.getmembers(module, inspect.isclass):
                try: 
                    self.parsers.append([obj,obj.SOFTWARE, obj.EXTENSION])
                except Exception as e:
                    pass
        

    def extent(self):
        """ 
        implementation of method from QgsMapLayer to compute the extent of the layer 
        return QgsRectangle()
        """
        if self.hydrauparser != None and self.hydrauparser.path != None :
            rect = self.hydrauparser.extent()
            return self.xform.transformBoundingBox(rect)
        else:
            return qgis.core.QgsRectangle()
            
            
            
    def legendSymbologyItems(self, iconSize):
        """ 
        implementation of method from QgsPluginLayer to show legend entries (in QGIS >= 2.1) 
        return an array with [name of symbology, qpixmap]
        """
        if self.meshrenderer != None:
            lst = self.meshrenderer.colormanager.generateSymbologyItems(iconSize)
            return lst
        else :
            return []
            
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

    def load_selafin(self,hydraufilepath=None,fileype = None):
        """
        Handler called when 'choose file' is clicked
        Load Selafin file and initialize properties dialog
        """
        try:
            self.hydrauparser.emitMessage.disconnect(self.propertiesdialog.errorMessage)
        except Exception as e:
            pass
        
        self.hydraufilepath = hydraufilepath
        #Update name in symbology
        filenametemp = os.path.basename(self.hydraufilepath)
        nom,extension = os.path.splitext(filenametemp)
        try:    #qgis2
            self.setLayerName(nom)
        except: #qgis3
            self.setName(nom)
        
        #Set parser
        for i, elem in enumerate(self.parsers):
            if elem[1] == fileype:
                self.hydrauparser = elem[0](self.parametrestoload)
                break
        self.hydrauparser.loadHydrauFile(self.hydraufilepath)
        
        self.propertiesdialog.updateWithParserParamsIdentified()
        self.hydrauparser.emitMessage.connect(self.propertiesdialog.errorMessage)
        #create renderer
        if QtCore.QSettings().value("posttelemac/renderlib") != None :
            if QtCore.QSettings().value("posttelemac/renderlib") == 'OpenGL':
                if int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 4 :
                    from ..meshlayerrenderer.post_telemac_opengl_get_qimage import MeshRenderer
                elif int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 5 :
                    from ..meshlayerrenderer.post_telemac_opengl_get_qimage_qt5 import MeshRenderer
                    
            elif QtCore.QSettings().value("posttelemac/renderlib") == 'MatPlotLib':
                from ..meshlayerrenderer.post_telemac_matplotlib_get_qimage import MeshRenderer
        else:
            from ..meshlayerrenderer.post_telemac_opengl_get_qimage import MeshRenderer
        self.meshrenderer = MeshRenderer(self,self.instancecount)
        
        #reinitialize layer's parameters
        if not self.param_displayed : self.param_displayed = 0
        if not self.meshrenderer.lvl_contour : self.meshrenderer.lvl_contour = self.levels[0]
        if not self.meshrenderer.lvl_vel : self.meshrenderer.lvl_vel = self.levels[0]
        if not self.time_displayed : self.time_displayed = 0
        if not self.meshrenderer.alpha_displayed : self.meshrenderer.alpha_displayed = self.parametrestoload['renderer_alpha']

        self.propertiesdialog.color_palette_changed( type = 'contour')  #initialize colors in renderer
        self.propertiesdialog.color_palette_changed( type = 'velocity') #initialize colors in renderer
        
        #initialize parameters
        #self.triinterp = None
        #change levels
        self.meshrenderer.change_lvl_contour(self.meshrenderer.lvl_contour)
        self.meshrenderer.change_lvl_vel(self.meshrenderer.lvl_vel)
        
        #initialise selafin crs
        if  self.crs().authid() == u'':
            #self.setRealCrs(qgis.utils.iface.mapCanvas().mapRenderer().destinationCrs())
            self.setRealCrs( qgis.utils.iface.mapCanvas().mapSettings().destinationCrs() )
            
        self.xform = qgis.core.QgsCoordinateTransform(self.realCRS, qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
        self.meshrenderer.changeTriangulationCRS()
        #update selafin values
        self.updateSelafinValues()
        #Update propertiesdialog
        self.propertiesdialog.update()
        #final update
        self.triggerRepaint()
        try:    #qgis2
            qgis.utils.iface.legendInterface().refreshLayerSymbology(self)
        except: #qgis3
            qgis.utils.iface.layerTreeView().refreshLayerSymbology(self.id())
            
        qgis.utils.iface.mapCanvas().setExtent(self.extent())
        
    
    
    def clearParameters(self):
        self.param_displayed = None
        
        self.time_displayed = None
        if self.meshrenderer != None:
            self.meshrenderer.alpha_displayed = 100.0
            self.meshrenderer.lvl_contour = None
    
            

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
        self.hydrauparser.identifyKeysParameters()
        self.updatevalue.emit(onlyparamtimeunchanged)
        
    
            
    def updateSelafinValues1(self, onlyparamtimeunchanged = -1):
        """
        Updates the values stored in self.values and self.value
        called when loading selfin file, or when selafin's time is changed
        """
        
        DEBUG = False
        
        if DEBUG :
            self.debugtext = []
            self.timestart = time.clock()
        
        
        if  onlyparamtimeunchanged < 0 :
            #self.triinterp = None
            self.hydrauparser.interpolator = None
            self.values = self.hydrauparser.getValues(self.time_displayed)
            if DEBUG : self.debugtext += ['values : ' + str(round(time.clock()-self.timestart,3))  ]
            self.value = self.values[self.param_displayed]
        else:
            self.value = self.values[self.param_displayed]
            

        if DEBUG : self.debugtext += ['value : ' + str(round(time.clock()-self.timestart,3))  ]
        if DEBUG : self.propertiesdialog.textBrowser_2.append(str(self.debugtext))
            
            
    #****************************************************************************************************
    #Change variables                                                  *********************************
    #****************************************************************************************************
                    
        
    def changeTime(self,nb):
        """When changing time value to display"""
        self.time_displayed = nb
        self.updateSelafinValues()
        #self.triinterp = None
        self.hydrauparser.interpolator = None
        self.timechanged.emit(nb)
        if self.draw:
            self.triggerRepaint()
            
            
    def changeParam(self,int1):
        """When changing parameter value for display"""
        self.param_displayed = int1
        self.updateSelafinValues(int1)
        try:    #qgis2
            qgis.utils.iface.legendInterface().refreshLayerSymbology(self)
        except: #qgis3
            qgis.utils.iface.layerTreeView().refreshLayerSymbology(self.id())
        self.forcerefresh = True
        self.triggerRepaint()
        
    def setRealCrs(self,qgscoordinatereferencesystem):
        """
        The real crs of layer is saved in realCRS variable.
        Otherwise (if real crs is saved in CRS variable), reprojection of the qimage is not fully working. 
        So the layer.crs is the same as the canvas.crs, and reprojection is done in meshrenderer using layer.realCRS
        """
        self.realCRS = qgscoordinatereferencesystem
        self.setCrs(qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
        self.xform  = qgis.core.QgsCoordinateTransform(self.realCRS, qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
        if self.meshrenderer != None :
            self.meshrenderer.changeTriangulationCRS() 
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
            self.setCrs(qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
            self.xform  = qgis.core.QgsCoordinateTransform(self.realCRS, qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
            self.meshrenderer.changeTriangulationCRS()
            self.forcerefresh = True
            self.triggerRepaint()
        except Exception as e:
            pass
        
    #****************************************************************************************************
    #show velocity, mesh  *********************************
    #****************************************************************************************************
        
    def showVelocity(self):
        """
        Called when PostTelemacPropertiesDialog 's "plot velocity" checkbox is checked
        """
        self.forcerefresh = True
        try:    #qgis2
            qgis.utils.iface.legendInterface().refreshLayerSymbology(self)
        except: #qgis3
            #self.propertiesdialog.errorMessage('plugin layer - legend failed')
            qgis.utils.iface.layerTreeView().refreshLayerSymbology(self.id())
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
        if self.hydraufilepath != None:
            return os.path.basename(self.hydraufilepath).split('.')[0]
        else:
            return 'Empty PostTelemac pluginlayer'
        
    def bandCount(self):
        return len(self.hydrauparser.parametres)
        
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
        qgspointfromcanvas= self.xform.transform(qgspointfromcanvas,qgis.core.QgsCoordinateTransform.ReverseTransform)
        if  self.hydrauparser.interpolator == None :
            success = self.hydrauparser.updateInterpolator(self.time_displayed)
        else:
            success = True
            
        #getvalues
        d = collections.OrderedDict()
        if success:
            try:
                #v= [float(self.triinterp[i].__call__([qgspointfromcanvas.x()],[qgspointfromcanvas.y()])) for i in range(len(self.hydrauparser.parametres))]
                v= [float(self.hydrauparser.interpolator[i].__call__([qgspointfromcanvas.x()],[qgspointfromcanvas.y()])) for i in range(len(self.hydrauparser.parametres))]
            except Exception as e :
                v = None
            #send results
            for param in self.hydrauparser.parametres:
                try:
                    d[ QString(param[1]) ] = v[param[0]]
                except:
                    d[ param[1] ] = v[param[0]]
            return (True,d)
        else:
            return (False,d)

        
    #****************************************************************************************************
    #************Method for saving/loading project with selafinlayer file***********************************
    #****************************************************************************************************
    
    def readXml(self, node):
        """
        implementation of method from QgsMapLayer to load layer from qgsproject
        return True ifsuccessful
        """
        element = node.toElement()
        prj = qgis.core.QgsProject.instance()
        hydraufilepath=prj.readPath( element.attribute('meshfile') )
        
        if os.path.isfile(hydraufilepath) :
            self.setRealCrs(qgis.core.QgsCoordinateReferenceSystem( prj.readPath( element.attribute('crs') ) ) )
            self.param_displayed = int(element.attribute('parametre'))
            #self.meshrenderer.alpha_displayed = int(element.attribute('alpha'))
            self.parametrestoload['renderer_alpha'] = int(element.attribute('alpha'))
            self.time_displayed = int(element.attribute('time'))
            self.showmesh = int(element.attribute('showmesh'))
            self.propertiesdialog.checkBox_showmesh.setChecked(self.showmesh) 
            #levelthings - old - need to reworked
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
            """
            #velocity things
            self.propertiesdialog.comboBox_genericlevels_2.setCurrentIndex(0)
            self.propertiesdialog.comboBox_clrgame_2.setCurrentIndex(0)
            self.propertiesdialog.change_cmchoosergenericlvl_vel()
            """
            #Virtual param things
            strtemp =  element.attribute('virtual_param').split(';')
            count = int((len(strtemp)-1)/3)
            for i in range(count):
                self.parametrestoload['virtual_parameters'].append([i,strtemp[3*i],int( strtemp[3*i+1] ),strtemp[3*i+2] ])
            
            
            try:
                self.parametrestoload['xtranslation'] = float(element.attribute('xtranslation'))
                self.parametrestoload['ytranslation'] = float(element.attribute('ytranslation'))
            except Exception as e:
                pass
            
            self.load_selafin(hydraufilepath,element.attribute('filetype') )
            return True
        else:
            return False
        
        
        
    def writeXml(self, node, doc):
        """
        implementation of method from QgsMapLayer to save layer in  qgsproject
        return True ifsuccessful
        """
        prj = qgis.core.QgsProject.instance()
        element = node.toElement()
        element.setAttribute("filetype", self.hydrauparser.SOFTWARE)
        element.setAttribute("crs", self.realCRS.authid())
        element.setAttribute("type", "plugin")
        element.setAttribute("name", SelafinPluginLayer.LAYER_TYPE)
        element.setAttribute("meshfile", prj.writePath(self.hydraufilepath))
        element.setAttribute("parametre", self.param_displayed)
        element.setAttribute("alpha", self.meshrenderer.alpha_displayed)
        element.setAttribute("time", self.time_displayed)
        element.setAttribute("showmesh", int(self.showmesh))
        #levelthings - old - need to reworked
        self.propertiesdialog.tabWidget_lvl_vel.setCurrentIndex(0)
        element.setAttribute("level_color", self.propertiesdialog.comboBox_clrgame.currentIndex())
        element.setAttribute("level_type", self.propertiesdialog.comboBox_levelstype.currentIndex())
        element.setAttribute("level_value", self.propertiesdialog.comboBox_genericlevels.currentIndex())
        element.setAttribute("level_step", self.propertiesdialog.lineEdit_levelmin.text()+";"+self.propertiesdialog.lineEdit_levelmax.text()+";"+self.propertiesdialog.lineEdit_levelstep.text())
        element.setAttribute("xtranslation", self.hydrauparser.translatex)
        element.setAttribute("ytranslation", self.hydrauparser.translatey)
        #Virtuall param things
        strtrmp = ''
        for param in self.hydrauparser.parametres:
            if param[4]:
                strtrmp += param[1]+';'+str(param[2])+';'+param[4]+';'
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
        
        self.propertiesdialog.tabWidget.setCurrentIndex(0)
        
        
        if str(self.id()) in string1:
            #closing figures
            """
            if self.propertiesdialog.unloadtools :
                try:
                    self.propertiesdialog.figure1.clf()
                    matplotlib.pyplot.close(self.propertiesdialog.figure1)
                except Exception as e :
                    print('fig1 ' + str(e) )
            if self.propertiesdialog.unloadtools :
                try:
                    self.propertiesdialog.figure2.clf()
                    matplotlib.pyplot.close(self.propertiesdialog.figure2) 
                except Exception as e :
                    print('fig2 ' + str(e))
            if self.propertiesdialog.unloadtools :
                try:
                    self.propertiesdialog.figure3.clf()
                    matplotlib.pyplot.close(self.propertiesdialog.figure3) 
                except Exception as e :
                    print('fig3 ' + str(e))
                    
            if not self.propertiesdialog.unloadtools :
                for tool in self.propertiesdialog.tools :
                    try:
                        tool.figure1.clf()
                        matplotlib.pyplot.close(tool.figure1) 
                    except Exception as e :
                        #print 'closing figure ' + str(e)
                        pass
            """
            
            """
            #if self.rendertype == 'Matplotlib' :
            if self.meshrenderer != None and self.meshrenderer.RENDERER_TYPE == 'MatPlotLib' :
                try:
                    self.meshrenderer.fig.clf()
                    matplotlib.pyplot.close(self.meshrenderer.fig)
                except Exception as e :
                    print('fig ' + str(e))
            """
                    
            if self.hydrauparser != None:
                try:
                    self.hydrauparser.emitMessage.disconnect(self.propertiesdialog.errorMessage)
                except Exception as e:
                    pass
                self.hydrauparser.hydraufile = None
                del self.hydrauparser
            
            if QtCore.QSettings().value("posttelemac/renderlib") == None :
                self.propertiesdialog.changeMeshLayerRenderer(self.propertiesdialog.comboBox_rendertype.currentIndex())
            #self.propertiesdialog.postutils.rubberband.reset()
            #self.propertiesdialog.postutils.rubberbandpoint.reset()
            #closing properties dialog
            self.propertiesdialog.close()
            del self.propertiesdialog
            #closing some stuff - do not succeed in retrieving what does not release memory...
            del self.values
            del self.value
            del self.meshrenderer

            #end : garbage collector 
            gc.collect()
            #close connexions
            #qgis.core.QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.RemoveScenario)
            try:
                qgis.core.QgsMapLayerRegistry.instance().layersWillBeRemoved.disconnect(self.RemoveScenario)  #to close properties dialog when layer deleted
            except:
                qgis.core.QgsProject.instance().layersWillBeRemoved.disconnect(self.RemoveScenario)  #to close properties dialog when layer deleted
            self.canvas.destinationCrsChanged.disconnect(self.changecrs)

    #****************************************************************************************************
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        try:
            return QtCore.QCoreApplication.translate('SelafinPluginLayer', message, None, QApplication.UnicodeUTF8)
        except Exception as e:
            return message
        
        
        
    
