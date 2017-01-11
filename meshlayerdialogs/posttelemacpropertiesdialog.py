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
#import Qt
from PyQt4 import uic, QtCore, QtGui
#import matplotlib
from matplotlib import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
except :
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
#other import
import os
import time
import shutil
#local import
#import ..resources_rc
#from ..libs.posttelemac_util import *
from posttelemacvirtualparameterdialog import *
from posttelemacusercolorrampdialog import *
from posttelemac_xytranslation import *
#from ..posttelemacparsers.posttelemac_selafin_parser import *

from ..meshlayertools.meshlayer_value_tool import ValueTool
from ..meshlayertools.meshlayer_temporalgraph_tool import TemporalGraphTool
from ..meshlayertools.meshlayer_volume_tool import VolumeTool
from ..meshlayertools.meshlayer_flow_tool import FlowTool
from ..meshlayertools.meshlayer_animation_tool import AnimationTool
from ..meshlayertools.meshlayer_raster_tool import RasterTool
from ..meshlayertools.meshlayer_compare_tool import CompareTool
from ..meshlayertools.meshlayer_extractmax_tool import ExtractMaxTool
from ..meshlayertools.meshlayer_profile_tool import ProfileTool
from ..meshlayertools.meshlayer_toshape_tool import ToShapeTool
from ..meshlayertools.meshlayer_opengl_tool import OpenGLTool


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),'..', 'ui', 'properties.ui'))


class PostTelemacPropertiesDialog(QtGui.QDockWidget, FORM_CLASS):

    updateparamsignal = QtCore.pyqtSignal()
    meshlayerschangedsignal = QtCore.pyqtSignal()

    def __init__(self, layer1, parent=None):
        """
        Constructor, inherited from  QDockWidget
        Doing :
            connecting PostTelemacPropertiesDialog ' s signals to methods :
                methods for viewer are set in SelafinPluginLayer class
                methods for utilities are set in PostTelemacUtils class
        """
        super(PostTelemacPropertiesDialog, self).__init__(parent)
        #QtGui.QDockWidget.__init__(self, parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        
        self.unloadtools = False
        
        
        #general variables
        self.meshlayer = layer1                             #the associated selafin layer
        self.qfiledlg = QtGui.QFileDialog(self)         #the filedialog for opening res file
        self.predeflevels=[]                            #the levels in classes.txt
        self.lastscolorparams = None                    #used to save the color ramp state
        #self.threadcompare = None                       #The compare file class
        self.canvas = self.meshlayer.canvas
        #self.postutils = PostTelemacUtils(layer1)       #the utils class
        self.maptooloriginal = self.canvas.mapTool()        #Initial map tool (ie mouse behaviour)
        #self.clickTool = QgsMapToolEmitPoint(self.canvas)   #specific map tool (ie mouse behaviour)
        self.crsselector = qgis.gui.QgsGenericProjectionSelector()
        self.playstep= None
        self.playactive = False
        
        if QtCore.QSettings().value("posttelemac/lastdirectory") != '':
            self.loaddirectory = QtCore.QSettings().value("posttelemac/lastdirectory")       #the directory of "load telemac" button
        else:
            self.loaddirectory = None
            
        
        #setup user dir in home
        homedir = os.path.expanduser("~")
        self.posttelemacdir = os.path.join(homedir,'.PostTelemac')
        if not os.path.isdir(self.posttelemacdir):
            #os.makedirs(self.posttelemacdir)
            shutil.copytree(os.path.join(os.path.dirname(__file__),'..', 'config'), self.posttelemacdir)
            
            
        
        #********* ********** ******************************************
        #********* Connecting ******************************************
        #********* ********** ******************************************
        self.pushButton_loadslf.clicked.connect(self.loadSelafin)
        self.pushButton_crs.clicked.connect(self.set_layercrs)
        self.pushbutton_crstranslation.clicked.connect(self.translateCrs)

        #********* ********** ******************************************
        #tab  ************************************************
        #********* ********** ******************************************
        #self.tabWidget.currentChanged.connect(self.mapToolChooser)

        #********* ********** ******************************************
        #Display tab  ************************************************
        #********* ********** ******************************************

        #Time
        self.horizontalSlider_time.sliderPressed.connect(self.sliderPressed)
        self.horizontalSlider_time.sliderReleased.connect(self.sliderReleased)
        self.comboBox_time.currentIndexChanged.connect(self.change_timetxt)
        self.horizontalSlider_time.valueChanged.connect(self.change_timetxt)
        self.pushButton_Read.clicked.connect(self.readHydrauFile)
        #Contour box
        #parameters
        self.treeWidget_parameters.itemSelectionChanged.connect(self.change_param)
        self.treeWidget_parameters.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.treeWidget_parameters.setColumnWidth(0,40)
        self.treeWidget_parameters.header().setResizeMode(0,QtGui.QHeaderView.Fixed)
        #virtual parameter
        self.pushButton_param_add.clicked.connect(self.open_def_variables)
        self.pushButton_param_edit.clicked.connect(self.open_def_variables)
        self.pushButton_param_delete.clicked.connect(self.delete_def_variables)
        #levels and color ramp
        self.populatecombobox_lvl()
        self.populatecombobox_colorpalette()
        self.InitMapRamp()
        self.checkBox_inverse_clr.setCheckState(0)
        self.checkBox_inverse_clr2.setCheckState(0)
        self.tabWidget_lvl_vel.currentChanged.connect(self.updateColorParams)
        if False:
            self.comboBox_levelstype.currentIndexChanged.connect(self.colorRampChooserType)
            self.comboBox_clrgame.currentIndexChanged.connect(self.color_palette_changed_contour)
            self.comboBox_genericlevels.currentIndexChanged.connect(self.change_cmchoosergenericlvl)
            self.comboBox_clrramp_preset.currentIndexChanged.connect(self.loadMapRamp)
            self.pushButton_createsteplevel.clicked.connect(self.createstepclass)
            self.pushButton_editcolorramp.clicked.connect(self.openColorRampDialog)
        else:
            self.connectColorRampSignals()
        

        #Velocity bpx
        #Velocity
        self.groupBox_schowvel.toggled.connect(self.setVelocityRendererParams)
        self.comboBox_vel_method.currentIndexChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_vel_spatial_step.valueChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_vel_scale.valueChanged.connect(self.setVelocityRendererParams)
        self.spinBox_vel_relative.valueChanged.connect(self.setVelocityRendererParams)
        self.comboBox_viewer_arow.currentIndexChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_uniform_vel_arrow.valueChanged.connect(self.setVelocityRendererParams)
        #colorramp
        #self.comboBox_genericlevels_2.currentIndexChanged.connect(self.change_cmchoosergenericlvl_vel)
        #self.comboBox_clrgame_2.currentIndexChanged.connect(self.color_palette_changed_vel)
        #Mesh box
        self.checkBox_showmesh.stateChanged.connect(self.meshlayer.showMesh)
        #transparency box
        #self.horizontalSlider_transp.valueChanged.connect(self.meshlayer.meshrenderer.changeAlpha)
        self.horizontalSlider_transp.valueChanged.connect(self.changeAlpha)
        self.horizontalSlider_transp.sliderPressed.connect(self.sliderPressed)
        self.horizontalSlider_transp.sliderReleased.connect(self.sliderReleased)
        #progressbar
        self.progressBar.reset()
        
        #rednertype
        self.comboBox_rendertype.currentIndexChanged.connect(self.changeMeshLayerRenderer)
        
        #********* ********** ******************************************
        #Tools tab  *****************************************************
        #********* ********** ******************************************
        

        self.tools = []
        self.tools.append(   ValueTool(self.meshlayer,self)   )
        self.tools.append(   TemporalGraphTool(self.meshlayer,self)   )
        self.tools.append(   VolumeTool(self.meshlayer,self)   )
        self.tools.append(   FlowTool(self.meshlayer,self)   )
        self.tools.append(   ProfileTool(self.meshlayer,self)   )
        self.tools.append(   AnimationTool(self.meshlayer,self)   )
        self.tools.append(   CompareTool(self.meshlayer,self)   )
        self.tools.append(   ExtractMaxTool(self.meshlayer,self)   )
        self.tools.append(   ToShapeTool(self.meshlayer,self)   )
        self.tools.append(   RasterTool(self.meshlayer,self)   )
        self.tools.append(   OpenGLTool(self.meshlayer,self)   )
            
            
        self.treeWidget_utils.expandAll()

        
    #*********************************************************************************
    #update properties dialog with selafin layer modification *************************
    #*********************************************************************************
    def update(self):
        """
        update dialog when selafin layer changes
        """
        if self.meshlayer.hydraufilepath is not None:
            paramtemp = self.meshlayer.param_displayed   #param_gachete deleted with clear - so save it
            tempstemp = self.meshlayer.time_displayed
            alphatemp = self.meshlayer.meshrenderer.alpha_displayed
            #name
            self.label_loadslf.setText(os.path.basename(self.meshlayer.hydraufilepath).split('.')[0])
            
            self.loaddirectory = os.path.dirname(self.meshlayer.hydraufilepath)
            QtCore.QSettings().setValue("posttelemac/lastdirectory", self.loaddirectory)
            #param
            self.populatecombobox_param()
            if paramtemp:
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,paramtemp)
            else:
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,0)
            self.tab_contour.setEnabled(True)
            self.groupBox_param.setEnabled(True)
            self.groupBox_time.setEnabled(True)
            self.treeWidget_parameters.setEnabled(True)
            #time
            self.horizontalSlider_time.setEnabled(True)
            self.comboBox_time.setEnabled(True)
            self.horizontalSlider_time.setMaximum(self.meshlayer.hydrauparser.itertimecount)
            self.horizontalSlider_time.setPageStep(min(10,int(self.meshlayer.hydrauparser.itertimecount/20)))
            self.populatecombobox_time()
            self.change_timetxt(tempstemp)
            self.horizontalSlider_time.setValue(tempstemp)
            self.comboBox_time.setCurrentIndex(tempstemp)
            #transparency
            self.horizontalSlider_transp.setEnabled(True)
            self.horizontalSlider_transp.setValue(alphatemp)
            #crs
            if self.meshlayer.crs().authid():
                self.label_selafin_crs.setText(self.meshlayer.crs().authid())
            self.pushButton_crs.setEnabled(True)
            #utils
            self.textBrowser_2.clear()
            
            
            if self.unloadtools :
                #compare
                self.writeSelafinCaracteristics(self.textEdit_2,self.meshlayer.hydrauparser)
                
                if self.postutils.compareprocess is not None:
                    self.reset_dialog()
                    self.postutils.compareprocess = None
                    
                #movie
                self.reinitcomposeurlist()
                self.reinitcomposeurimages(0)
                
            self.meshlayerschangedsignal.emit()
            #self.populateMinMaxSpinBox()
            
            

    #*********************************************************************************
    #Standart output ****************************************************************
    #*********************************************************************************

    def errorMessage(self,str):
        """
        Show message str in main textbrowser
        """
        self.textBrowser_main.setTextColor(QtGui.QColor("red"))
        self.textBrowser_main.setFontWeight(QtGui.QFont.Bold)
        self.textBrowser_main.append(time.ctime() + ' - '+ str)
        self.textBrowser_main.setTextColor(QtGui.QColor("black"))
        self.textBrowser_main.setFontWeight(QtGui.QFont.Normal)
        self.textBrowser_main.verticalScrollBar().setValue(self.textBrowser_main.verticalScrollBar().maximum())
        
    def normalMessage(self,str):
        """
        Show message error str in main textbrowser
        """
        self.textBrowser_main.append(time.ctime() + ' - '+ str)
        self.textBrowser_main.setTextColor(QtGui.QColor("black"))
        self.textBrowser_main.setFontWeight(QtGui.QFont.Normal)
        self.textBrowser_main.verticalScrollBar().setValue(self.textBrowser_main.verticalScrollBar().maximum())
                
    #*********************************************************************************
    #General tools****************************************************************
    #*********************************************************************************
    
    def loadSelafin(self):
        """
        Called when clicking on load selafin button
        """
        str1 = self.tr("Result file chooser")
        str2 = self.tr("Telemac files")
        str2_1 = self.tr("Anuga files")
        str3 = self.tr("All files")     
        tempname = self.qfiledlg.getOpenFileName(None,str1,self.loaddirectory, str2 + " (*.res *.geo *.init *.slf);;" +str2_1 + " (*.sww);;"+ str3 + " (*)")
        if tempname:
            self.loaddirectory = os.path.dirname(tempname)
            QtCore.QSettings().setValue("posttelemac/lastdirectory", self.loaddirectory)
            self.meshlayer.clearParameters()
            self.meshlayer.load_selafin(tempname)
            nom = os.path.basename(tempname).split('.')[0]
            self.normalMessage(self.tr('File ') +  str(nom) +  self.tr(" loaded"))
        else:
            if not self.meshlayer.hydraufilepath:
                self.label_loadslf.setText(self.tr('No file selected'))

    
    def set_layercrs(self):
        """
        Called when clicking on  selafin'crs button
        """
        source = self.sender()
        self.crsselector.exec_()
        crs = self.crsselector.selectedAuthId()
        if source == self.pushButton_crs:
            self.label_selafin_crs.setText(crs)
        else:
            source.setText(crs)
        self.meshlayer.setRealCrs(qgis.core.QgsCoordinateReferenceSystem(crs))
        
    def translateCrs(self):
        if self.meshlayer.hydrauparser != None:
            self.dlg_xytranslate = xyTranslationDialog()
            self.dlg_xytranslate.setXandY(self.meshlayer.hydrauparser.translatex, self.meshlayer.hydrauparser.translatey )
            self.dlg_xytranslate.setWindowModality(2)
            r = self.dlg_xytranslate.exec_()
            xtranslate,ytranslate = self.dlg_xytranslate.dialogIsFinished()
            if xtranslate != None and ytranslate != None:
                self.meshlayer.hydrauparser.setXYTranslation(xtranslate,ytranslate )
                self.meshlayer.meshrenderer.changeTriangulationCRS()
                self.meshlayer.forcerefresh = True
                self.meshlayer.triggerRepaint()
                qgis.utils.iface.mapCanvas().setExtent(self.meshlayer.extent())
        else:
            QMessageBox.about(self, "My message box", 'Load a file first')
        
    """
    #*********************************************************************************
    #*********************************************************************************
    #Display tools ****************************************************************
    #*********************************************************************************
    #*********************************************************************************
    """
    
    #Display tools - time  ***********************************************
    
    def change_timetxt(self,intitmetireation):
        """Associated with time modification buttons"""
        if self.sender() == self.comboBox_time:
            try:
                self.horizontalSlider_time.valueChanged.disconnect(self.change_timetxt)
            except:
                pass
            self.horizontalSlider_time.setValue(intitmetireation)
            self.horizontalSlider_time.valueChanged.connect(self.change_timetxt)
        elif self.sender() == self.horizontalSlider_time:
            try:
                self.comboBox_time.currentIndexChanged.disconnect(self.change_timetxt)
            except:
                pass
            self.comboBox_time.setCurrentIndex(intitmetireation)
            self.comboBox_time.currentIndexChanged.connect(self.change_timetxt)
        
        self.meshlayer.changeTime(intitmetireation)
        time2 = time.strftime("%j:%H:%M:%S", time.gmtime(self.meshlayer.hydrauparser.getTimes()[intitmetireation]))
        
        self.label_time.setText(self.tr("time (hours)") + " : " + str(time2) +"\n"+ 
                                self.tr("time (iteration)") + " : "+ str(intitmetireation)+"\n"+
                                self.tr("time (seconds)") + " : " + str(self.meshlayer.hydrauparser.getTimes()[intitmetireation]))
                                
            
    def sliderReleased(self):
        """Associated with time slider behaviour"""
        self.meshlayer.draw=True
        self.meshlayer.triggerRepaint()
        
    def sliderPressed(self):
        """Associated with time slider behaviour"""
        self.meshlayer.draw=False
        
    def readHydrauFile(self):
        """Action when play clicked"""
        iconplay  =QtGui.QIcon(':/plugins/PostTelemac/icons/play/play.png')
        iconstop  =QtGui.QIcon(':/plugins/PostTelemac/icons/play/stop.png')
        if not self.playactive :    #action on click when not playing
            self.pushButton_Read.setIcon(iconstop)
            self.playactive = True
            self.meshlayer.canvas.mapCanvasRefreshed.connect(self.readHydrauFile2)
            self.change_timetxt(self.meshlayer.time_displayed)
            self.meshlayer.canvas.refresh()
        else:    #action on click when  playing
            self.pushButton_Read.setIcon(iconplay)
            self.playactive = False
            self.meshlayer.canvas.mapCanvasRefreshed.disconnect(self.readHydrauFile2)
        
    def readHydrauFile2(self):  
        self.playstep = int(self.spinBox_readtimestep.value())
        if self.meshlayer.time_displayed < len(self.meshlayer.hydrauparser.getTimes()) - self.playstep :
            #print str(self.meshlayer.time_displayed + self.playstep) + ' ' + str(len(self.meshlayer.hydrauparser.getTimes() ))
            self.horizontalSlider_time.setValue(self.meshlayer.time_displayed + self.playstep)
            self.meshlayer.canvas.refresh()
        else:   #end of time reached
            iconplay  =QtGui.QIcon(':/plugins/PostTelemac/icons/play/play.png')
            self.pushButton_Read.setIcon(iconplay)
            self.playactive = False
            self.meshlayer.canvas.mapCanvasRefreshed.disconnect(self.readHydrauFile2)
        
    #*********************************************************************************
    #Display tools - contour  ***********************************************
    #*********************************************************************************
    
    #Display tools - contour -  parameter ***********************************************
        
    def change_param(self,int1=None):
        """When changing parameter value"""
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)
        self.meshlayer.changeParam(position[1])
        if self.meshlayer.hydrauparser.parametres[position[1]][2]:
            self.pushButton_param_edit.setEnabled(True)
            self.pushButton_param_delete.setEnabled(True)
        else:
            self.pushButton_param_edit.setEnabled(False)
            self.pushButton_param_delete.setEnabled(False)
                

    #Display tools - contour -  virtual parameter ***********************************************
        
    def open_def_variables(self, lst_param):
        """
        Create or edit virtual parameter, based on raw parameter of selafin file
        appears when clicking on new virtual parameter
        """
        source = self.sender()
        if source == self.pushButton_param_add:
            lst_param = ["", "", ""]
        elif source == self.pushButton_param_edit:
            index = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)[1]
            if self.meshlayer.hydrauparser.parametres[index][2]:
                lst_param = [self.meshlayer.hydrauparser.parametres[index][1], self.meshlayer.hydrauparser.parametres[index][2], ""]
            else:
                return False
        
        lst_var = [param for param in self.meshlayer.hydrauparser.parametres if not param[2]]
        #launch dialog
        self.dlg_dv = DefVariablesDialog(lst_param, lst_var)
        self.dlg_dv.setWindowModality(2)
    
        r = self.dlg_dv.exec_()
        
        #Process new/edited param
        if r == 1:
            itms = []
            new_var = self.dlg_dv.dialogIsFinished()
            if source == self.pushButton_param_add:
                self.meshlayer.hydrauparser.parametres.append([len(self.meshlayer.hydrauparser.parametres),new_var[0],new_var[1]])
                self.populatecombobox_param()
                self.meshlayer.updateSelafinValues()
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,len(self.meshlayer.hydrauparser.parametres)-1)
            elif source == self.pushButton_param_edit:
                self.meshlayer.hydrauparser.parametres[index] = [index,new_var[0],new_var[1]]
                self.populatecombobox_param()
                self.meshlayer.updateSelafinValues()
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,index)
                
            
    def delete_def_variables(self):
        """
        Delete virtual parameter
        When clicking on delete virtual parameter
        """
        index = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)[1]
        if self.meshlayer.hydrauparser.parametres[index][2]:
            self.meshlayer.param_displayed = index-1
            self.meshlayer.hydrauparser.parametres[index:index+1] = []
            #checkkeysparameter
            self.meshlayer.parametreh = None
            self.meshlayer.parametrevx = None
            self.meshlayer.parametrevy = None
            #update all
            self.meshlayer.updateSelafinValues()
            self.populatecombobox_param()
            self.setTreeWidgetIndex(self.treeWidget_parameters,0,index-1)
        
    #Display tools - contour - color ramp things ***********************************************
    
    def updateColorParams(self,int1):
        """
        Remember state of color ramp when changing contour/velocity tabwidget
        """
        #save current color ramp state
        if self.comboBox_levelstype.currentIndex() == 0 :
            lastscolorparamstemp = [0, self.lineEdit_levelschoosen.text(), self.comboBox_clrgame.currentIndex(), self.comboBox_genericlevels.currentIndex()]
        elif self.comboBox_levelstype.currentIndex() == 1 :
            lastscolorparamstemp = [1, self.lineEdit_levelschoosen.text(), self.comboBox_clrgame2.currentIndex(), self.lineEdit_levelmin.text(), self.lineEdit_levelmax.text(),self.lineEdit_levelstep.text()]
        elif self.comboBox_levelstype.currentIndex() == 2 :
            lastscolorparamstemp = [2, self.lineEdit_levelschoosen.text(), self.comboBox_clrramp_preset.currentIndex()]
            
        
        if self.lastscolorparams != None:
            #update color ramp widget
            self.disconnectColorRampSignals()
            self.comboBox_levelstype.setCurrentIndex(self.lastscolorparams[0])
            self.stackedWidget_colorramp.setCurrentIndex(self.lastscolorparams[0])
            if self.lastscolorparams[0] == 0 :
                self.lineEdit_levelschoosen.setText(self.lastscolorparams[1])
                self.comboBox_clrgame.setCurrentIndex(self.lastscolorparams[2])
                self.comboBox_genericlevels.setCurrentIndex(self.lastscolorparams[3])
            elif self.lastscolorparams[0] == 1 :
                self.lineEdit_levelschoosen.setText(self.lastscolorparams[1])
                self.comboBox_clrgame2.setCurrentIndex(self.lastscolorparams[2])
                self.lineEdit_levelmin.setText(self.lastscolorparams[3])
                self.lineEdit_levelmax.setText(self.lastscolorparams[4])
                self.lineEdit_levelstep.setText(self.lastscolorparams[5])
            elif self.lastscolorparams[0] == 2 :
                self.lineEdit_levelschoosen.setText(self.lastscolorparams[1])
                self.comboBox_clrramp_preset.setCurrentIndex(self.lastscolorparams[2])
            self.connectColorRampSignals()
            
        #update name
        if int1 == 0 :
            self.groupBox_colorramp.setTitle("Color ramp - contour")
        elif int1 == 1 :
            self.groupBox_colorramp.setTitle("Color ramp - velocity")
        
        #update lastscolorparams
        #self.lastscolorparams = [classes, text,  #1 : color gradient, generic levels, #2 : color gradient, min, max, step, #3 : preset color ramp]
        self.lastscolorparams = lastscolorparamstemp
        
    
    def connectColorRampSignals(self):
        self.comboBox_levelstype.currentIndexChanged.connect(self.stackedWidget_colorramp.setCurrentIndex)
        self.comboBox_levelstype.currentIndexChanged.connect(self.colorRampChooserType)
        #1
        #self.comboBox_clrgame.currentIndexChanged.connect(self.color_palette_changed_contour)
        self.comboBox_clrgame.currentIndexChanged.connect(self.color_palette_changed)
        self.comboBox_clrgame.currentIndexChanged.connect(self.comboBox_clrgame2.setCurrentIndex)
        self.checkBox_inverse_clr.stateChanged.connect(self.color_palette_changed)
        self.checkBox_inverse_clr.stateChanged.connect(self.checkBox_inverse_clr2.setCheckState)
        self.comboBox_genericlevels.currentIndexChanged.connect(self.change_cmchoosergenericlvl)
        #2
        self.comboBox_clrgame2.currentIndexChanged.connect(self.comboBox_clrgame.setCurrentIndex)
        self.checkBox_inverse_clr2.stateChanged.connect(self.color_palette_changed)
        self.checkBox_inverse_clr2.stateChanged.connect(self.checkBox_inverse_clr.setCheckState)
        self.pushButton_createsteplevel.clicked.connect(self.createstepclass)
        #3
        self.comboBox_clrramp_preset.currentIndexChanged.connect(self.loadMapRamp)
        #all
        self.pushButton_editcolorramp.clicked.connect(self.openColorRampDialog)
        
    def disconnectColorRampSignals(self):
        self.comboBox_levelstype.currentIndexChanged.disconnect(self.stackedWidget_colorramp.setCurrentIndex)
        self.comboBox_levelstype.currentIndexChanged.disconnect(self.colorRampChooserType)
        #1
        #self.comboBox_clrgame.currentIndexChanged.disconnect(self.color_palette_changed_contour)
        self.comboBox_clrgame.currentIndexChanged.disconnect(self.color_palette_changed)
        self.comboBox_clrgame.currentIndexChanged.disconnect(self.comboBox_clrgame2.setCurrentIndex)
        self.checkBox_inverse_clr.stateChanged.disconnect(self.color_palette_changed)
        self.checkBox_inverse_clr2.setCheckState(self.checkBox_inverse_clr.checkState())
        self.comboBox_genericlevels.currentIndexChanged.disconnect(self.change_cmchoosergenericlvl)
        #2
        self.comboBox_clrgame2.currentIndexChanged.disconnect(self.comboBox_clrgame.setCurrentIndex)
        self.checkBox_inverse_clr2.stateChanged.disconnect(self.color_palette_changed)
        self.checkBox_inverse_clr.setCheckState(self.checkBox_inverse_clr2.checkState())
        self.pushButton_createsteplevel.clicked.disconnect(self.createstepclass)
        #3
        self.comboBox_clrramp_preset.currentIndexChanged.disconnect(self.loadMapRamp)
        #all
        self.pushButton_editcolorramp.clicked.disconnect(self.openColorRampDialog)

        
        
    def colorRampChooserType(self,item):
        """
        main chooser of color ramp type (predef, step, user defined)
        """
        if self.meshlayer.meshrenderer != None:
            if item == 0:
                if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                    #self.color_palette_changed_contour(0)
                    self.color_palette_changed(0)
                    self.meshlayer.meshrenderer.change_lvl_contour(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
                elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
                    #self.color_palette_changed_vel(0)
                    self.color_palette_changed(0)
                    self.meshlayer.meshrenderer.change_lvl_vel(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
            elif item == 1:
                pass
                #self.stackedWidget_colorramp.setCurrentIndex(1)
            elif item == 2 :
                self.loadMapRamp(self.comboBox_clrramp_preset.currentText())
            else:
                pass

        
            
    def change_cmchoosergenericlvl(self):
        """
        change levels of selafin layer when generics levels are changed
        """
        if self.meshlayer.meshrenderer != None: 
            if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                self.meshlayer.meshrenderer.change_lvl_contour(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
            elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
                self.meshlayer.meshrenderer.change_lvl_vel(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
            
            
    def createstepclass(self):
        """
        create steps classes and change levels of selafin layer when steps classes are changed
        """
        
        if self.lineEdit_levelmin.text()=="" : 
            zmin=min(self.meshlayer.hydrauparser.getValues(self.meshlayer.time_displayed)[self.meshlayer.param_displayed] )
            self.lineEdit_levelmin.setText(str(round(float(zmin),3)))
        else : 
            zmin = float(self.lineEdit_levelmin.text())
        if self.lineEdit_levelmax.text()=="" : 
            zmax=max(self.meshlayer.hydrauparser.getValues(self.meshlayer.time_displayed)[self.meshlayer.param_displayed] )
            self.lineEdit_levelmax.setText(str(round(float(zmax),3)))
        else : 
            zmax = float(self.lineEdit_levelmax.text())
        precision = len(str(float(self.lineEdit_levelstep.text())).split('.')[1])
        pdn = round(float(self.lineEdit_levelstep.text()) * 10**precision ) / 10**precision
        zmin1 = zmin
        
        while zmin1<=zmin:
            zmin1 = zmin1+  pdn
        zmin1 = zmin1 - pdn
        zmax1=int(zmax)+1
        while zmax1>=zmax:
            zmax1=  zmax1-pdn
        zmax1 = zmax1
        #Remplissage tableau
        temp=zmin1
        levels=[temp]
        while temp<=zmax1:
            temp=round(temp+pdn,precision)
            levels.append(temp)
            
        if self.meshlayer.meshrenderer != None:
            if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                self.meshlayer.meshrenderer.change_lvl_contour(levels)
            elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
                self.meshlayer.meshrenderer.change_lvl_vel(levels)
            
    def color_palette_changed(self,int1 = None,type = None):
        """
        change color map of selafin layer (matplotlib's style) when color palette combobox is changed
        """
        #temp1 = qgis.core.QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
        """
        if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
            #print self.meshlayer.meshrenderer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
            self.meshlayer.meshrenderer.cmap_mpl_contour_raw = self.meshlayer.meshrenderer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
            self.meshlayer.meshrenderer.change_cm_contour(self.meshlayer.meshrenderer.cmap_mpl_contour_raw)
        elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
            self.meshlayer.meshrenderer.cmap_mpl_vel_raw = self.meshlayer.meshrenderer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
            #cmap_vel = self.meshlayer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
            self.meshlayer.meshrenderer.change_cm_vel(self.meshlayer.meshrenderer.cmap_mpl_vel_raw)
        """
        temp1 = qgis.core.QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
        inverse = self.checkBox_inverse_clr.isChecked()
        if self.meshlayer.meshrenderer != None :
            if type == None:
                #temp1 = qgis.core.QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
                if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                    self.meshlayer.meshrenderer.color_palette_changed_contour(temp1,inverse)
                elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
                    self.meshlayer.meshrenderer.color_palette_changed_vel(temp1,inverse)
            else:
                if type == 'contour':
                    #temp1 = qgis.core.QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
                    self.meshlayer.meshrenderer.color_palette_changed_contour(temp1,inverse)
                elif type == 'velocity':
                    #temp1 = qgis.core.QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
                    self.meshlayer.meshrenderer.color_palette_changed_vel(temp1,inverse)
        if False:
            if type == None:
                if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                    self.meshlayer.color_palette_changed_contour(temp1,inverse)
                elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
                    self.meshlayer.color_palette_changed_vel(temp1,inverse)
            else:
                if type == 'contour':
                    self.meshlayer.color_palette_changed_contour(temp1,inverse)
                elif type == 'velocity':
                    self.meshlayer.color_palette_changed_vel(temp1,inverse)
                
    
    def changeAlpha(self,nb):
        """When changing alpha value for display"""
        if self.meshlayer.meshrenderer != None:
            self.meshlayer.meshrenderer.changeAlpha(nb)
    

    
    def openColorRampDialog(self):
        """
        open dialog for user defined color ramp and update color ramp
        """

        self.dlg_color = UserColorRampDialog(self.meshlayer)
        
        self.dlg_color.setWindowModality(2)

        r = self.dlg_color.exec_()
        
        colors,levels = self.dlg_color.dialogIsFinished()
        
        if self.meshlayer.meshrenderer != None:
            if colors and levels:
                if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                    #self.meshlayer.meshrenderer.cmap_mpl_contour_raw = self.meshlayer.meshrenderer.colormanager.arrayStepRGBAToCmap(colors)
                    #self.meshlayer.meshrenderer.cmap_mpl_contour_raw = colors
                    self.meshlayer.meshrenderer.cmap_contour_raw = colors
                    self.meshlayer.meshrenderer.change_lvl_contour(levels)
                elif self.tabWidget_lvl_vel.currentIndex() == 1 :#velocity
                    #self.meshlayer.meshrenderer.cmap_mpl_vel_raw = self.meshlayer.meshrenderer.colormanager.arrayStepRGBAToCmap(colors)
                    #self.meshlayer.meshrenderer.cmap_mpl_vel_raw = colors
                    self.meshlayer.meshrenderer.cmap_vel_raw = colors
                    
                    self.meshlayer.meshrenderer.change_lvl_vel(levels)

    def saveMapRamp(self):
        """
        Save user defined color ramp on /config/"name"".clr
        """
        if self.meshlayer.meshrenderer != None:
            colors, levels = self.dlg_color.returnColorsLevels()
            self.meshlayer.meshrenderer.colormanager.saveClrColorRamp(self.dlg_color.lineEdit_name.text(),colors,levels)
            self.InitMapRamp()
            int2 = self.comboBox_clrramp_preset.findText(self.dlg_color.lineEdit_name.text())
            self.comboBox_clrramp_preset.setCurrentIndex(int2)
        
        
    def deleteMapRamp(self):
        """
        delete user defined color ramp 
        """
        name = self.dlg_color.lineEdit_name.text()
        if self.comboBox_clrramp_preset.findText(name) > -1 :
            #path = os.path.join(os.path.dirname(__file__),'..', 'config',name+'.clr')
            path = os.path.join(self.posttelemacdir,name+'.clr')
            os.remove(path)
            self.dlg_color.close()
            self.InitMapRamp()
            
            
            
    def loadMapRamp(self,name,fullpath = False):
        """
        load clr file and apply it
        """
        
        if self.meshlayer.meshrenderer != None:
        
            if isinstance(name,int):
                name = self.comboBox_clrramp_preset.currentText()
                
            if fullpath:
                path = name
            else:
                #path = os.path.join(os.path.dirname(__file__),'..', 'config',str(name)+'.clr')
                path = os.path.join(self.posttelemacdir,str(name)+'.clr')
            if name : 
                cmap, levels = self.meshlayer.meshrenderer.colormanager.readClrColorRamp(path)
                
                if cmap and levels:
                    #self.meshlayer.cmap = cmap
                    if self.tabWidget_lvl_vel.currentIndex() == 0 :#contour
                        #self.meshlayer.meshrenderer.cmap_mpl_contour_raw = cmap
                        self.meshlayer.meshrenderer.cmap_contour_raw = cmap
                        self.meshlayer.meshrenderer.change_lvl_contour(levels)
                    elif self.tabWidget_lvl_vel.currentIndex() == 1 :#veolicty
                        #self.meshlayer.meshrenderer.cmap_mpl_vel_raw = cmap
                        self.meshlayer.meshrenderer.cmap_vel_raw = cmap
                        self.meshlayer.meshrenderer.change_lvl_vel(levels)
        

            
    def InitMapRamp(self):
        """
        Load user defined color ramp in user defined color ramp combobox
        """
        self.comboBox_clrramp_preset.clear()
        #for file in os.listdir(os.path.join(os.path.dirname(__file__),'..', 'config')):
        for file in os.listdir(self.posttelemacdir):
            if file.endswith(".clr") and file.split('.')[0] :
                self.comboBox_clrramp_preset.addItem(file.split('.')[0])
            

    #Display tools - velocity - user color ramp things ***********************************************
            
            
    def setVelocityRendererParams(self):
        """
        set parameters for velocity rendering in layer.showvelocityparams like this :
            [enabled Bool, type int , poinst step float , lenght of normal velocity float ]
        """
        if self.comboBox_viewer_arow.currentIndex() == 0 :
            if self.comboBox_vel_method.currentIndex() == 0 :
                self.meshlayer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                                'type' : self.comboBox_vel_method.currentIndex(),
                                                'step' : self.spinBox_vel_relative.value(),
                                                'norm' : 1/self.doubleSpinBox_vel_scale.value()}
            elif self.comboBox_vel_method.currentIndex() == 1 :
                self.meshlayer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                                'type' : self.comboBox_vel_method.currentIndex(),
                                                'step' : self.doubleSpinBox_vel_spatial_step.value(),
                                                'norm' :1/self.doubleSpinBox_vel_scale.value()}
            elif  self.comboBox_vel_method.currentIndex() == 2 :
                self.meshlayer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                                'type' : self.comboBox_vel_method.currentIndex(),
                                                'step' : None,
                                                'norm' : 1/self.doubleSpinBox_vel_scale.value()}
        elif self.comboBox_viewer_arow.currentIndex() == 1 :
            if self.comboBox_vel_method.currentIndex() == 0 :
                self.meshlayer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                                'type' : self.comboBox_vel_method.currentIndex(),
                                                'step' : self.spinBox_vel_relative.value(),
                                                'norm' : -self.doubleSpinBox_uniform_vel_arrow.value()}
            elif self.comboBox_vel_method.currentIndex() == 1 :
                self.meshlayer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                                'type' : self.comboBox_vel_method.currentIndex(),
                                                'step' : self.doubleSpinBox_vel_spatial_step.value(),
                                                'norm' :-self.doubleSpinBox_uniform_vel_arrow.value()}
            elif  self.comboBox_vel_method.currentIndex() == 2 :
                self.meshlayer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                                'type' : self.comboBox_vel_method.currentIndex(),
                                                'step' : None,
                                                'norm' : -self.doubleSpinBox_uniform_vel_arrow.value()}
        self.meshlayer.showVelocity()
            

    """
    def change_cmchoosergenericlvl_vel(self):
        
        change levels of selafin layer when generics levels are changed
        
        self.meshlayer.change_lvl_vel(self.predeflevels[self.comboBox_genericlevels_2.currentIndex()][1])
    """
        

    #*********************************************************************************
    #Display tab - Init things                          ******************************************
    #*********************************************************************************
    """
    def enablecheckbox(self,int1):

        source = self.sender()
        if source == self.checkBox_contourcrs:
            if int1 == 2:
                self.pushButton_contourcrs.setEnabled(True)
            elif int1 == 0:
                self.pushButton_contourcrs.setEnabled(False)
        if source == self.checkBox_3:
            if int1 == 2:
                self.doubleSpinBox.setEnabled(True)
                self.doubleSpinBox_2.setEnabled(True)
                self.doubleSpinBox_3.setEnabled(True)
            elif int1 == 0:
                self.doubleSpinBox.setEnabled(False)
                self.doubleSpinBox_2.setEnabled(False)
                self.doubleSpinBox_3.setEnabled(False)
        if source == self.checkBox_2:
            if int1 == 2:
                self.pushButton_7.setEnabled(True)
            elif int1 == 0:
                self.pushButton_7.setEnabled(False)
        if source == self.checkBox_4:
            if int1 == 2:
                self.pushButton_9.setEnabled(True)
            elif int1 == 0:
                self.pushButton_9.setEnabled(False)
    """
    """
    def populateMinMaxSpinBox(self):

        maxiter = self.meshlayer.hydrauparser.itertimecount
        if self.unloadtools :
            #movie
            self.spinBox_3.setMaximum(maxiter)
            self.spinBox_2.setMaximum(maxiter)
            self.spinBox_3.setValue(maxiter)
            #max
            self.spinBox_max_start.setMaximum(maxiter)
            self.spinBox_max_end.setMaximum(maxiter)
            self.spinBox_max_end.setValue(maxiter)
    """
                

    def populatecombobox_lvl(self):
        """
        Populate classes combobox on dialog creation
        """
        #f = open(os.path.join(os.path.dirname(__file__),'..', 'config','classes.txt'), 'r')
        f = open(os.path.join(self.posttelemacdir,'classes.txt'), 'r')
        for line in f:
                tabtemp=[]
                for txt in line.split("=")[1].split("\n")[0].split(";"):
                    tabtemp.append(float(txt))
                self.predeflevels.append([line.split("=")[0],tabtemp])
        for i in range(len(self.predeflevels)):
            self.comboBox_genericlevels.addItem(self.predeflevels[i][0])
            #self.comboBox_genericlevels_2.addItem(self.predeflevels[i][0])

    def populatecombobox_time(self):
        """
        Populate time combobox on dialog update
        """
        self.comboBox_time.clear()
        for i in range(self.meshlayer.hydrauparser.itertimecount + 1):
            self.comboBox_time.addItems([str(self.meshlayer.hydrauparser.getTimes()[i])])
            
    def populatecombobox_param(self):
        """
        Populate parameters comboboxes on dialog update
        """
        #tree widget
        self.treeWidget_parameters.clear()
        itms = []
        for i in range(len(self.meshlayer.hydrauparser.parametres)):
            itm = QtGui.QTreeWidgetItem()
            itm.setText(0, str(self.meshlayer.hydrauparser.parametres[i][0]))
            itm.setText(1, str(self.meshlayer.hydrauparser.parametres[i][1]))
            if self.meshlayer.hydrauparser.parametres[i][2]:
                itm.setText(2, str(self.meshlayer.hydrauparser.parametres[i][2]))
            else:
                itm.setText(2, self.tr('Raw data'))
            itms.append(itm)
        self.treeWidget_parameters.addTopLevelItems(itms)
        
        if self.unloadtools :
            self.tableWidget_values.clearContents()
            self.tableWidget_values.setRowCount(len(self.meshlayer.hydrauparser.parametres))
            for i, param in enumerate(self.meshlayer.hydrauparser.parametres):
                self.tableWidget_values.setItem(i, 0, QtGui.QTableWidgetItem(param[1]))
            self.tableWidget_values.setFixedHeight((self.tableWidget_values.rowHeight(0) - 1)*(len(self.meshlayer.hydrauparser.parametres) + 1) + 1)
        
        self.updateparamsignal.emit()
 

    def populatecombobox_colorpalette(self):
        """
        Populate colorpalette combobox on dialog creation
        """
        style = qgis.core.QgsStyleV2.defaultStyle()
        rampIconSize = QtCore.QSize(50,20)
        for rampName in style.colorRampNames():
            ramp = style.colorRamp(rampName)
            icon = qgis.core.QgsSymbolLayerV2Utils.colorRampPreviewIcon(ramp, rampIconSize)
            self.comboBox_clrgame.addItem(icon, rampName)
            #self.comboBox_clrgame_2.addItem(icon, rampName)
            self.comboBox_clrgame2.addItem(icon, rampName)
            
            
            
    def changeMeshLayerRenderer(self, typerenderer):
        if typerenderer == 0 : #openGL
            QtCore.QSettings().setValue("posttelemac/renderlib", 'OpenGL')
            if self.meshlayer.hydraufilepath != None:
                self.meshlayer.load_selafin(self.meshlayer.hydraufilepath)
        elif  typerenderer == 1 : #matplotlib
            QtCore.QSettings().setValue("posttelemac/renderlib", 'MatPlotLib')
            if self.meshlayer.hydraufilepath != None:
                self.meshlayer.load_selafin(self.meshlayer.hydraufilepath)
            
            
            
    """
    #*********************************************************************************
    #*********************************************************************************
    #Tools tab ****************************************************************
    #*********************************************************************************
    #*********************************************************************************
    """




    #*********************************************************************************
    #General behaviour for utilitites tools *****************************************************
    #Action on click on the Treewidget of tools  *************************************
    #Show the good panel and load the appropriate map tool   *************************
    #*********************************************************************************
    #**** This part need to be updated when adding a tool ***************************
    #*********************************************************************************
    
    """
    def initTreewidgettoolsindextab(self):
        #""
        #create array used to create the tree in the utilities tab
        #""
        # treewidgettoolsindextab : [ [parent node row index, node row index],stacked widget index to show, name  ]
        self.treewidgettoolsindextab = [[[-1,0],1, 'Values'],
                                        [[-1,1],2,'Temporal graph'],
                                        [[-1,2],3,'Spatial graph'],
                                        [[-1,3],4,'Volume graph'],
                                        [[-1,4],5, 'Flow graph'],
                                        [[-1,5],6, 'Compare'],
                                        [[-1,6],7, 'Movie'],
                                        [[-1,7],8, 'Max res' ] ,
                                        [[8,0],9,'2shape contour' ],
                                        [[8,1],10,'2shape mesh' ],
                                        [[8,2],11,'2shape point' ],
                                        [[9,0],12,'Raster creation']]

    
    def changepannelutils(self):
        #""
        #Method to choose the stackedwidget page linked mith the tree item
        #""
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_utils)
        indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
        try:
            self.stackedWidget.setCurrentIndex(self.treewidgettoolsindextab[indextabtemp.index(position)][1])
        except Exception, e:
            self.stackedWidget.setCurrentIndex(0)
        
    """
            
    #*********************************************************************************
    #Tab / tool treewidget map tool activator ****************************************
    #*********************************************************************************
    
    """
    def mapToolChooser(self,int=None):
        ""
        Activate maptool (specific mouse behaviour) when specifics items in the utilities tree is clicked
        ""
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_utils)
        indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
        if position :
            itemname = self.treewidgettoolsindextab[indextabtemp.index(position)][2]
        else:
            itemname = None
        
        if (len(self.treeWidget_utils.selectedItems())>0 
            and itemname == 'Values' 
            and self.tabWidget.currentIndex() == 1):
            #""Click on value tool item""
            if self.unloadtools :
                self.canvas.setMapTool(self.clickTool)
                try:self.clickTool.canvasClicked.disconnect()
                except Exception: pass
                self.clickTool.canvasClicked.connect(self.postutils.valeurs_click)
                self.postutils.valeurs_click(QgsPoint(0.0,0.0))
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
              and itemname == 'Temporal graph' 
              and self.tabWidget.currentIndex() == 1
              and self.comboBox_2.currentIndex() == 0):
            if self.unloadtools :
                #""Click on temopral graph + temporary point selection method""
                if self.postutils.rubberband:
                    self.postutils.rubberband.reset(QGis.Point)
                if self.postutils.rubberbandpoint:
                    self.postutils.rubberbandpoint.reset(QGis.Point)
                try : self.clickTool.canvasClicked.disconnect()
                except Exception, e : pass
                self.pushButton_limni.setEnabled(False)
                self.canvas.setMapTool(self.clickTool)
                self.clickTool.canvasClicked.connect(self.postutils.computeGraphTemp)
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
                  and itemname == 'Volume graph' 
                  and self.tabWidget.currentIndex() == 1
                  and (self.comboBox_4.currentIndex() in [0] )):
            if self.unloadtools :
                #""Click on flow computation - temporary polyline""
                if self.postutils.rubberband:
                    self.postutils.rubberband.reset(QGis.Point)
                if self.postutils.rubberbandpoint:
                    self.postutils.rubberbandpoint.reset(QGis.Point)
                try : self.clickTool.canvasClicked.disconnect()
                except Exception, e :  pass
                self.pushButton_volume.setEnabled(False)
                self.postutils.computeVolume()
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
                  and itemname == 'Flow graph' 
                  and self.tabWidget.currentIndex() == 1
                  and (self.comboBox_3.currentIndex() in [0] )):
            if self.unloadtools :
                #""Click on flow computation - temporary polyline""
                if self.postutils.rubberband:
                    self.postutils.rubberband.reset(QGis.Point)
                if self.postutils.rubberbandpoint:
                    self.postutils.rubberbandpoint.reset(QGis.Point)
                try : self.clickTool.canvasClicked.disconnect()
                except Exception, e :  pass
                self.pushButton_flow.setEnabled(False)
                self.postutils.computeFlow()
        else:
            #""else...""
            self.pushButton_limni.setEnabled(True)
            self.pushButton_flow.setEnabled(True)
            self.pushButton_volume.setEnabled(True)
            try: self.canvas.setMapTool(self.maptooloriginal)
            except Exception, e : pass

        #All the time : rubberband reset when the treewidget item changes
        try:
            source = self.sender()
            if source == self.treeWidget_utils and self.postutils.rubberband and self.postutils.rubberbandpoint:
                self.postutils.rubberband.reset(QGis.Line)
                self.postutils.rubberbandpoint.reset(QGis.Point)
        except Exception, e :
            self.textBrowser_2.append(str(e))

    """
            
    #*********************************************************************************
    #Tools activation  *****************************************************
    #*********************************************************************************
    
    """
    
    def volumemethodchanged(self, int1):
        if int1 in [0,1]:
            self.comboBox_volumeparam.setEnabled(False)
        else:
            self.comboBox_volumeparam.setEnabled(True)
            
    """
    
    #*********************************************************************************
    #*******************************2shape **************************************
    """
    def create_shp_maillage(self):
        self.postutils.create_shp_maillage()

    def create_shp(self):
        self.postutils.create_shp()
        
    def create_shp_points(self):
        self.postutils.create_points()
    """
        

    #Display tools - CRS things ***********************************************

    """
    def set_utilcrs(self):
        self.crsselector.exec_()
        crs = self.crsselector.selectedAuthId()
        source = self.sender()
        #print str(source.name())
        if source == self.pushButton_crs:
            self.label_selafin_crs.setText(crs)
        else:
            source.setText(crs)
        
    """
    
    #*********************************************************************************
    #*******************************Compare **************************************
    """
    
    def initCompare(self):
        self.checkBox_6.setCheckState(0)
        #file to compare choice
        str1 = self.tr("Selafin file chooser")
        str2 = self.tr("Telemac files")
        str3 = self.tr("All files")  
        fname = self.qfiledlg.getOpenFileName(None,str1,self.loaddirectory, str2 + " (*.res *.geo *.init *.slf);;" + str3 + " (*)")
        #Things
        if fname:
            #update dialog
            self.reset_dialog()
            self.lineEdit_5.setText(fname)
            #Launch thread
            self.checkBox_6.setEnabled(False)
            self.postutils.compareselafin()
            self.writeSelafinCaracteristics(self.textEdit_3,self.postutils.compareprocess.hydrauparsercompared)

        
    def reset_dialog(self):
        #self.textEdit_2.clear()
        self.textEdit_3.clear()
        self.lineEdit_5.clear()
        self.lineEdit.clear()
        self.checkBox_6.setCheckState(0)
        self.checkBox_6.setEnabled(False)
        
    

        
    def writeSelafinCaracteristics(self,textedit,hydrauparser):
        textedit.setText('')
        
        for var in hydrauparser.parametres:
            textedit.append(str(var[0]) + ' : ' + str(var[1]))
        
        textedit.append("nombre d elements : "+str(len(hydrauparser.getValues(0)[0])))
        
    """


    #*********************************************************************************
    #Tools - movie *******************************************
    """
    def reinitcomposeurlist(self,composeurview1=None):

        try:
            self.comboBox_compositions.clear()
            for composeurview in iface.activeComposers():
                name = composeurview.composerWindow().windowTitle()
                self.comboBox_compositions.addItems([str(name)])
        except Exception , e :
            self.comboBox_compositions.addItems([self.tr("no composer")])
        

    def reinitcomposeurimages(self,int1=None):

        self.comboBox_8.clear()
        name = self.comboBox_compositions.currentText()
        #print name
        try:
            for composeurview in iface.activeComposers():
                if composeurview.composerWindow().windowTitle() == name:
                    composition = composeurview.composition()
            images = [item.id() for item in composition.items() if item.type() == QgsComposerItem.ComposerPicture and item.scene()] 
            #print 'composeur trouve'
            images=[str(image) for image in images]
            self.comboBox_8.addItems([self.tr('no picture')])
            self.comboBox_8.addItems(images)
        except Exception , e :
            #print str(e)
            self.comboBox_8.addItems([self.tr('no picture')])
            
    """
    #****************************************************************************************************
    #************translation  / general method                                      ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QtCore.QCoreApplication.translate('PostTelemacPropertiesDialog', message, None, QtGui.QApplication.UnicodeUTF8)

    """
    def eventFilter(self,target,event):
    
        #Action to update images in composer with movie tool
        try:
            if target == self.comboBox_8 and event.type() == QtCore.QEvent.MouseButtonPress:
                self.reinitcomposeurimages()
            return False
        except Exception, e:
            #print 'Property dialog eventFilter ' + str(e)
            return False
    """
            
    def getTreeWidgetSelectedIndex(self,widget):
        """
        """
        getSelected = widget.selectedItems()
        if getSelected:
            baseNode = getSelected[0]
            position = [widget.indexFromItem(baseNode).parent().row(),widget.indexFromItem(baseNode).row()]
            return position
        else :
            return [-1,0]
        
    def setTreeWidgetIndex(self,widget,pos0,pos1):
        """
        """
        widget.scrollToItem(widget.topLevelItem(pos1))
        widget.setCurrentItem(widget.topLevelItem(pos1))
        widget.setItemSelected(widget.topLevelItem(pos1), True)
    
    
    
    
    def updateWithParserParamsIdentified(self):
        """
        #enable volume tool if freesurface and bottom are present in parser params
        if (self.meshlayer.hydrauparser.paramfreesurface == None or self.meshlayer.hydrauparser.parambottom == None):
            self.groupBox_volume1.setEnabled(False)
            self.groupBox_volume2.setEnabled(False)
        else:
            self.groupBox_volume1.setEnabled(True)
            self.groupBox_volume2.setEnabled(True) 
        """
        
        #enable veolocity tool if velocity u and v are present in parser params
        if (self.meshlayer.hydrauparser.parametrevx == None or self.meshlayer.hydrauparser.parametrevy == None):
            self.tab_velocity.setEnabled(False)
        else:
            self.tab_velocity.setEnabled(True)
            for widget in self.tab_velocity.children():
                widget.setEnabled(True)
            for widget in self.groupBox_schowvel.children():
                widget.setEnabled(True)
            self.groupBox_schowvel.setChecked(True)
            self.groupBox_schowvel.setChecked(False)
        
            
        """
        #enable  flow if depth, veolocuty are present in parser params 
        if self.meshlayer.hydrauparser.parametreh != None and self.meshlayer.hydrauparser.parametrevx != None and self.meshlayer.hydrauparser.parametrevy != None:
            self.page_flow.setEnabled(True)
        else:
            self.page_flow.setEnabled(False)
        """

        
        
        
        
        
