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

#import qgis
from qgis.gui import *
from qgis.core import *
#import Qt
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
#import matplotlib
import matplotlib
from matplotlib import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
except :
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
#other import
import os
from time import ctime
import shutil
#local import
from ..libs.posttelemac_util import *
from posttelemacvirtualparameterdialog import *
from posttelemacusercolorrampdialog import *
from ..posttelemacparsers.posttelemac_selafin_parser import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),'..', 'ui', 'properties.ui'))


class PostTelemacPropertiesDialog(QtGui.QDockWidget, FORM_CLASS):

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
        #general variables
        self.layer = layer1                             #the associated selafin layer
        self.qfiledlg = QtGui.QFileDialog(self)         #the filedialog for opening res file
        self.predeflevels=[]                            #the levels in classes.txt
        #self.threadcompare = None                       #The compare file class
        self.canvas = self.layer.canvas
        self.postutils = PostTelemacUtils(layer1)       #the utils class
        self.maptooloriginal = self.canvas.mapTool()        #Initial map tool (ie mouse behaviour)
        self.clickTool = QgsMapToolEmitPoint(self.canvas)   #specific map tool (ie mouse behaviour)
        self.crsselector = QgsGenericProjectionSelector()
        self.loaddirectory = None       #the directory of "load telemac" button
        
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

        #********* ********** ******************************************
        #tab  ************************************************
        #********* ********** ******************************************
        self.tabWidget.currentChanged.connect(self.mapToolChooser)

        #********* ********** ******************************************
        #Display tab  ************************************************
        #********* ********** ******************************************

        #Time
        self.horizontalSlider_time.sliderPressed.connect(self.sliderPressed)
        self.horizontalSlider_time.sliderReleased.connect(self.sliderReleased)
        self.comboBox_time.currentIndexChanged.connect(self.change_timetxt)
        self.horizontalSlider_time.valueChanged.connect(self.change_timetxt)
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
        self.comboBox_levelstype.currentIndexChanged.connect(self.colorRampChooserType)
        self.comboBox_genericlevels.currentIndexChanged.connect(self.change_cmchoosergenericlvl)
        self.InitMapRamp()
        self.comboBox_clrramp_preset.currentIndexChanged.connect(self.loadMapRamp)
        self.pushButton_createsteplevel.clicked.connect(self.createstepclass)
        self.comboBox_clrgame.currentIndexChanged.connect(self.color_palette_changed_contour)
        self.pushButton_editcolorramp.clicked.connect(self.openColorRampDialog)
        #Velocity bpx
        #Velocity
        self.groupBox_schowvel.toggled.connect(self.setVelocityRendererParams)
        self.comboBox_vel_method.currentIndexChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_vel_spatial_step.valueChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_vel_scale.valueChanged.connect(self.setVelocityRendererParams)
        self.spinBox_vel_relative.valueChanged.connect(self.setVelocityRendererParams)
        #colorramp
        self.comboBox_genericlevels_2.currentIndexChanged.connect(self.change_cmchoosergenericlvl_vel)
        self.comboBox_clrgame_2.currentIndexChanged.connect(self.color_palette_changed_vel)
        #Mesh box
        self.checkBox_showmesh.stateChanged.connect(self.layer.showMesh)
        #transparency box
        self.horizontalSlider_transp.valueChanged.connect(self.layer.changeAlpha)
        self.horizontalSlider_transp.sliderPressed.connect(self.sliderPressed)
        self.horizontalSlider_transp.sliderReleased.connect(self.sliderReleased)
        
        #********* ********** ******************************************
        #Tools tab  *****************************************************
        #********* ********** ******************************************
        
        #treewidget behaviour
        self.treeWidget_utils.itemSelectionChanged.connect(self.changepannelutils)
        self.treeWidget_utils.itemClicked.connect(self.mapToolChooser)
        
        #Tools tab - temporal graph
        self.figure1 = plt.figure(self.layer.instancecount+1)
        font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
        rc('font', **font)
        self.canvas1 = FigureCanvas(self.figure1)
        self.ax = self.figure1.add_subplot(111)
        layout = QtGui.QVBoxLayout()
        try:
            self.toolbar = NavigationToolbar(self.canvas1, self.frame,True)
            layout.addWidget(self.toolbar)
        except Exception, e:
            pass
        layout.addWidget(self.canvas1)
        self.canvas1.draw()
        self.frame.setLayout(layout)
        self.comboBox_2.currentIndexChanged.connect(self.mapToolChooser)
        self.pushButton_limni.clicked.connect(self.postutils.computeGraphTemp)
        self.pushButton_graphtemp_pressepapier.clicked.connect(self.postutils.copygraphclipboard)
        
        #Tools tab- flow graph
        self.figure2 = plt.figure(self.layer.instancecount+2)
        self.canvas2 = FigureCanvas(self.figure2)
        self.ax2 = self.figure2.add_subplot(111)
        layout2 = QtGui.QVBoxLayout()
        try:
            self.toolbar2 = NavigationToolbar(self.canvas2, self.frame_2,True)
            layout2.addWidget(self.toolbar2)
        except Exception, e:
            pass
        layout2.addWidget(self.canvas2)
        self.canvas2.draw()
        self.frame_2.setLayout(layout2)
        self.comboBox_3.currentIndexChanged.connect(self.mapToolChooser)
        self.pushButton_4.clicked.connect(self.postutils.copygraphclipboard)
        self.pushButton_flow.clicked.connect(self.postutils.computeFlow)
        
        #Tools tab - compare
        self.pushButton_8.clicked.connect(self.initCompare)
        self.checkBox_6.stateChanged.connect(self.postutils.compare1)
        self.comboBox_compare_method.currentIndexChanged.connect(self.postutils.compare1)
        
        #Tools tab - movie  
        self.pushButton_film.clicked.connect(self.postutils.makeAnimation)
        iface.composerAdded.connect(self.reinitcomposeurlist)
        iface.composerRemoved.connect(self.reinitcomposeurlist)
        self.comboBox_compositions.currentIndexChanged.connect(self.reinitcomposeurimages)
        self.comboBox_8.installEventFilter(self)
        self.spinBox_2.valueChanged.connect(self.postutils.filmEstimateLenght)
        self.spinBox_3.valueChanged.connect(self.postutils.filmEstimateLenght)
        self.spinBox_4.valueChanged.connect(self.postutils.filmEstimateLenght)
        self.spinBox_fps.valueChanged.connect(self.postutils.filmEstimateLenght)
            
        #Tools tab- max  
        self.pushButton_max_res.clicked.connect(self.postutils.calculMaxRes)
        
        #2shape ***************************************************

        #2shape Contour
        self.checkBox_contourcrs.stateChanged.connect(self.enablecheckbox)
        self.pushButton_contourcrs.clicked.connect(self.set_utilcrs)
        self.pushButton_contourcreate.clicked.connect(self.create_shp)
        #2shape mesh
        self.checkBox_3.stateChanged.connect(self.enablecheckbox)
        self.checkBox_2.stateChanged.connect(self.enablecheckbox)
        self.pushButton_7.clicked.connect(self.set_utilcrs)
        self.pushButton_10.clicked.connect(self.create_shp_maillage)
        #2shape  Points
        self.checkBox_4.stateChanged.connect(self.enablecheckbox)
        self.checkBox_5.stateChanged.connect(self.enablecheckbox)
        self.pushButton_9.clicked.connect(self.set_utilcrs)
        self.pushButton_2.clicked.connect(self.create_shp_points)
        
        #raster creation
        self.pushButton_createraster.clicked.connect(self.postutils.rasterCreation)
        
        #final action
        self.initTreewidgettoolsindextab()
        self.treeWidget_utils.expandAll()



        
    #*********************************************************************************
    #update properties dialog with selafin layer modification *************************
    #*********************************************************************************
    def update(self):
        """
        update dialog when selafin layer changes
        """
        if self.layer.hydraufilepath is not None:
            paramtemp = self.layer.param_displayed   #param_gachete deleted with clear - so save it
            tempstemp = self.layer.time_displayed
            alphatemp = self.layer.alpha_displayed
            #name
            self.label_loadslf.setText(os.path.basename(self.layer.hydraufilepath).split('.')[0])
            self.loaddirectory = os.path.dirname(self.layer.hydraufilepath)
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
            self.horizontalSlider_time.setMaximum(self.layer.hydrauparser.itertimecount)
            self.horizontalSlider_time.setPageStep(min(10,int(self.layer.hydrauparser.itertimecount/20)))
            self.populatecombobox_time()
            self.change_timetxt(tempstemp)
            self.horizontalSlider_time.setValue(tempstemp)
            self.comboBox_time.setCurrentIndex(tempstemp)
            #transparency
            self.horizontalSlider_transp.setEnabled(True)
            self.horizontalSlider_transp.setValue(alphatemp)
            #crs
            if self.layer.crs().authid():
                self.label_selafin_crs.setText(self.layer.crs().authid())
            self.pushButton_crs.setEnabled(True)
            #utils
            self.textBrowser_2.clear()
            #compare
            self.writeSelafinCaracteristics(self.textEdit_2,self.layer.hydrauparser)
            if self.postutils.compareprocess is not None:
                self.reset_dialog()
                self.postutils.compareprocess = None
            #movie
            self.reinitcomposeurlist()
            self.reinitcomposeurimages(0)
            self.populateMinMaxSpinBox()

    #*********************************************************************************
    #Standart output ****************************************************************
    #*********************************************************************************

    def errorMessage(self,str):
        """
        Show message str in main textbrowser
        """
        self.textBrowser_main.setTextColor(QColor("red"))
        self.textBrowser_main.setFontWeight(QFont.Bold)
        self.textBrowser_main.append(ctime() + ' - '+ str)
        self.textBrowser_main.setTextColor(QColor("black"))
        self.textBrowser_main.setFontWeight(QFont.Normal)
        self.textBrowser_main.verticalScrollBar().setValue(self.textBrowser_main.verticalScrollBar().maximum())
        
    def normalMessage(self,str):
        """
        Show message error str in main textbrowser
        """
        self.textBrowser_main.append(ctime() + ' - '+ str)
        self.textBrowser_main.setTextColor(QColor("black"))
        self.textBrowser_main.setFontWeight(QFont.Normal)
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
        str3 = self.tr("All files")     
        tempname = self.qfiledlg.getOpenFileName(None,str1,self.loaddirectory, str2 + " (*.res *.geo *.init *.slf);;" + str3 + " (*)")
        if tempname:
            self.loaddirectory = os.path.dirname(tempname)
            self.layer.clearParameters()
            self.layer.load_selafin(tempname)
            nom = os.path.basename(tempname).split('.')[0]
            self.normalMessage(self.tr('File ') +  str(nom) +  self.tr(" loaded"))
        else:
            if not self.layer.hydraufilepath:
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
        self.layer.setRealCrs(QgsCoordinateReferenceSystem(crs))
        
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
        self.layer.changeTime(intitmetireation)
        time2 = time.strftime("%j:%H:%M:%S", time.gmtime(self.layer.hydrauparser.getTimes()[intitmetireation]))
        
        self.label_time.setText(self.tr("time (hours)") + " : " + str(time2) +"\n"+ 
                                self.tr("time (iteration)") + " : "+ str(intitmetireation)+"\n"+
                                self.tr("time (seconds)") + " : " + str(self.layer.hydrauparser.getTimes()[intitmetireation]))
            
    def sliderReleased(self):
        """Associated with time slider behaviour"""
        self.layer.draw=True
        self.layer.triggerRepaint()
        
    def sliderPressed(self):
        """Associated with time slider behaviour"""
        self.layer.draw=False
        
    #*********************************************************************************
    #Display tools - contour  ***********************************************
    #*********************************************************************************
    
    #Display tools - contour -  parameter ***********************************************
        
    def change_param(self,int1=None):
        """When changing parameter value"""
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)
        self.layer.changeParam(position[1])
        if self.layer.parametres[position[1]][2]:
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
            if self.layer.parametres[index][2]:
                lst_param = [self.layer.parametres[index][1], self.layer.parametres[index][2], ""]
            else:
                return False
        
        lst_var = [param for param in self.layer.parametres if not param[2]]
        #launch dialog
        self.dlg_dv = DefVariablesDialog(lst_param, lst_var)
        self.dlg_dv.setWindowModality(2)
    
        r = self.dlg_dv.exec_()
        
        #Process new/edited param
        if r == 1:
            itms = []
            new_var = self.dlg_dv.dialogIsFinished()
            if source == self.pushButton_param_add:
                self.layer.parametres.append([len(self.layer.parametres),new_var[0],new_var[1]])
                self.populatecombobox_param()
                self.layer.updateSelafinValues()
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,len(self.layer.parametres)-1)
            elif source == self.pushButton_param_edit:
                self.layer.parametres[index] = [index,new_var[0],new_var[1]]
                self.populatecombobox_param()
                self.layer.updateSelafinValues()
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,index)
                
            
    def delete_def_variables(self):
        """
        Delete virtual parameter
        When clicking on delete virtual parameter
        """
        index = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)[1]
        if self.layer.parametres[index][2]:
            self.layer.param_displayed = index-1
            self.layer.parametres[index:index+1] = []
            self.populatecombobox_param()
            self.setTreeWidgetIndex(self.treeWidget_parameters,0,index-1)
            #checkkeysparameter
            self.layer.parametreh = None
            self.layer.parametrevx = None
            self.layer.parametrevy = None
            
            self.layer.updateSelafinValues()
        
    #Display tools - contour - color ramp things ***********************************************

    def colorRampChooserType(self,item):
        """
        main chooser of color ramp type (predef, step, user defined)
        """
        if item == 0:
            self.color_palette_changed_contour(0)
            self.layer.change_lvl_contour(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
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
        self.layer.change_lvl_contour(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
            
            
    def createstepclass(self):
        """
        create steps classes and change levels of selafin layer when steps classes are changed
        """
        if self.lineEdit_levelmin.text()=="" : 
            zmin=min(self.layer.hydrauparser.getValues(self.layer.time_displayed)[self.layer.param_displayed] )
            self.lineEdit_levelmin.setText(str(round(float(zmin),3)))
        else : 
            zmin = float(self.lineEdit_levelmin.text())
        if self.lineEdit_levelmax.text()=="" : 
            zmax=max(self.layer.hydrauparser.getValues(self.layer.time_displayed)[self.layer.param_displayed] )
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
        self.layer.change_lvl_contour(levels)
        
    def color_palette_changed_contour(self,int):
        """
        change color map of selafin layer (matplotlib's style) when color palette combobox is changed
        """
        temp1 = QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
        self.layer.cmap_mpl_contour_raw = self.layer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
        self.layer.change_cm_contour(self.layer.cmap_mpl_contour_raw)


    def openColorRampDialog(self):
        """
        open dialog for user defined color ramp and update color ramp
        """

        self.dlg_color = UserColorRampDialog(self.layer)
        
        self.dlg_color.setWindowModality(2)

        r = self.dlg_color.exec_()
        
        colors,levels = self.dlg_color.dialogIsFinished()
        if colors and levels:
            self.layer.cmap_mpl_contour_raw = self.layer.colormanager.arrayStepRGBAToCmap(colors)
            self.layer.change_lvl_contour(levels)

    def saveMapRamp(self):
        """
        Save user defined color ramp on /config/"name"".clr
        """
        colors, levels = self.dlg_color.returnColorsLevels()
        self.layer.colormanager.saveClrColorRamp(self.dlg_color.lineEdit_name.text(),colors,levels)
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
        if isinstance(name,int):
            name = self.comboBox_clrramp_preset.currentText()
            
        if fullpath:
            path = name
        else:
            #path = os.path.join(os.path.dirname(__file__),'..', 'config',str(name)+'.clr')
            path = os.path.join(self.posttelemacdir,str(name)+'.clr')
        if name : 
            cmap, levels = self.layer.colormanager.readClrColorRamp(path)
            if cmap and levels:
                #self.layer.cmap = cmap
                self.layer.cmap_mpl_contour_raw = cmap
                self.layer.change_lvl_contour(levels)

            
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
        if self.comboBox_vel_method.currentIndex() == 0 :
            self.layer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                            'type' : self.comboBox_vel_method.currentIndex(),
                                            'step' : self.spinBox_vel_relative.value(),
                                            'norm' : 1/self.doubleSpinBox_vel_scale.value()}
        elif self.comboBox_vel_method.currentIndex() == 1 :
            self.layer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                            'type' : self.comboBox_vel_method.currentIndex(),
                                            'step' : self.doubleSpinBox_vel_spatial_step.value(),
                                            'norm' :1/self.doubleSpinBox_vel_scale.value()}
        elif  self.comboBox_vel_method.currentIndex() == 2 :
            self.layer.showvelocityparams = {'show' : self.groupBox_schowvel.isChecked(),
                                            'type' : self.comboBox_vel_method.currentIndex(),
                                            'step' : None,
                                            'norm' : 1/self.doubleSpinBox_vel_scale.value()}
        self.layer.showVelocity()
            
    def color_palette_changed_vel(self,int):
        """
        change color map of selafin layer (matplotlib's style) when color palette combobox is changed
        """
        temp1 = QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame_2.currentText())
        self.layer.cmap_mpl_vel_raw = self.layer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
        #cmap_vel = self.layer.colormanager.qgsvectorgradientcolorrampv2ToCmap(temp1)
        self.layer.change_cm_vel(self.layer.cmap_mpl_vel_raw)
        
    def change_cmchoosergenericlvl_vel(self):
        """
        change levels of selafin layer when generics levels are changed
        """
        self.layer.change_lvl_vel(self.predeflevels[self.comboBox_genericlevels_2.currentIndex()][1])
        
        

    #*********************************************************************************
    #Display tab - Init things                          ******************************************
    #*********************************************************************************

    def enablecheckbox(self,int1):
        """
        Enable checkboxes for activating buttons when another buttons are activated
        """
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
                
    def populateMinMaxSpinBox(self):
        """
        Populate time  min/max spin box on dialog creation
        """
        maxiter = self.layer.hydrauparser.itertimecount
        #movie
        self.spinBox_3.setMaximum(maxiter)
        self.spinBox_2.setMaximum(maxiter)
        self.spinBox_3.setValue(maxiter)
        #max
        self.spinBox_max_start.setMaximum(maxiter)
        self.spinBox_max_end.setMaximum(maxiter)
        self.spinBox_max_end.setValue(maxiter)
        
                

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
            self.comboBox_genericlevels_2.addItem(self.predeflevels[i][0])

    def populatecombobox_time(self):
        """
        Populate time combobox on dialog update
        """
        self.comboBox_time.clear()
        for i in range(self.layer.hydrauparser.itertimecount + 1):
            self.comboBox_time.addItems([str(self.layer.hydrauparser.getTimes()[i])])
            
    def populatecombobox_param(self):
        """
        Populate parameters comboboxes on dialog update
        """
        self.comboBox_parametreschooser.clear()
        self.comboBox_parametreschooser_2.clear()
        for i in range(len(self.layer.parametres)):
            temp1 = [str(self.layer.parametres[i][0])+" : "+str(self.layer.parametres[i][1])]
            self.comboBox_parametreschooser.addItems(temp1)
            self.comboBox_parametreschooser_2.addItems(temp1)
        
        self.treeWidget_parameters.clear()
        itms = []
        for i in range(len(self.layer.parametres)):
            itm = QTreeWidgetItem()
            itm.setText(0, str(self.layer.parametres[i][0]))
            itm.setText(1, str(self.layer.parametres[i][1]))
            if self.layer.parametres[i][2]:
                itm.setText(2, str(self.layer.parametres[i][2]))
            else:
                itm.setText(2, self.tr('Raw data'))
            itms.append(itm)
        self.treeWidget_parameters.addTopLevelItems(itms)
        self.tableWidget_values.clearContents()
        self.tableWidget_values.setRowCount(len(self.layer.parametres))
        for i, param in enumerate(self.layer.parametres):
            self.tableWidget_values.setItem(i, 0, QtGui.QTableWidgetItem(param[1]))
        self.tableWidget_values.setFixedHeight((self.tableWidget_values.rowHeight(0) - 1)*(len(self.layer.parametres) + 1) + 1)
 

    def populatecombobox_colorpalette(self):
        """
        Populate colorpalette combobox on dialog creation
        """
        style = QgsStyleV2.defaultStyle()
        rampIconSize = QSize(50,20)
        for rampName in style.colorRampNames():
            ramp = style.colorRamp(rampName)
            icon = QgsSymbolLayerV2Utils.colorRampPreviewIcon(ramp, rampIconSize)
            self.comboBox_clrgame.addItem(icon, rampName)
            self.comboBox_clrgame_2.addItem(icon, rampName)
            self.comboBox_clrgame2.addItem(icon, rampName)
            
            
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
    
    
    def initTreewidgettoolsindextab(self):
        """
        create array used to create the tree in the utilities tab
        """
        # treewidgettoolsindextab : [ [parent node row index, node row index],stacked widget index to show, name  ]
        self.treewidgettoolsindextab = [[[-1,0],1, 'Values'],
                                        [[-1,1],2,'Temporal graph'],
                                        [[-1,2],3,'Spatial graph'],
                                        [[-1,3],4, 'Flow graph'],
                                        [[-1,4],5, 'Compare'],
                                        [[-1,5],6, 'Movie'],
                                        [[-1,6],7, 'Max res' ] ,
                                        [[7,0],8,'2shape contour' ],
                                        [[7,1],9,'2shape mesh' ],
                                        [[7,2],10,'2shape point' ],
                                        [[8,0],11,'Raster creation']]

    
    def changepannelutils(self):
        """
        Method to choose the stackedwidget page linked mith the tree item
        """
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_utils)
        indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
        try:
            self.stackedWidget.setCurrentIndex(self.treewidgettoolsindextab[indextabtemp.index(position)][1])
        except Exception, e:
            self.stackedWidget.setCurrentIndex(0)
        

            
    #*********************************************************************************
    #Tab / tool treewidget map tool activator ****************************************
    #*********************************************************************************
        
    def mapToolChooser(self,int=None):
        """
        Activate maptool (specific mouse behaviour) when specifics items in the utilities tree is clicked
        """
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_utils)
        indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
        if position :
            itemname = self.treewidgettoolsindextab[indextabtemp.index(position)][2]
        else:
            itemname = None
        
        if (len(self.treeWidget_utils.selectedItems())>0 
            and itemname == 'Values' 
            and self.tabWidget.currentIndex() == 1):
            """Click on value tool item"""
            self.canvas.setMapTool(self.clickTool)
            try:self.clickTool.canvasClicked.disconnect()
            except Exception: pass
            self.clickTool.canvasClicked.connect(self.postutils.valeurs_click)
            self.postutils.valeurs_click(QgsPoint(0.0,0.0))
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
              and itemname == 'Temporal graph' 
              and self.tabWidget.currentIndex() == 1
              and self.comboBox_2.currentIndex() == 0):
            """Click on temopral graph + temporary point selection method"""
            if self.postutils.rubberband:
                self.postutils.rubberband.reset(QGis.Point)
            try : self.clickTool.canvasClicked.disconnect()
            except Exception, e : pass
            self.pushButton_limni.setEnabled(False)
            self.canvas.setMapTool(self.clickTool)
            self.clickTool.canvasClicked.connect(self.postutils.computeGraphTemp)
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
                  and itemname == 'Flow graph' 
                  and self.tabWidget.currentIndex() == 1
                  and (self.comboBox_3.currentIndex() in [0] )):
            """Click on flow computation - temporary polyline"""
            if self.postutils.rubberband:
                self.postutils.rubberband.reset(QGis.Point)
            try : self.clickTool.canvasClicked.disconnect()
            except Exception, e :  pass
            self.pushButton_flow.setEnabled(False)
            self.postutils.computeFlow()
        else:
            """else..."""
            self.pushButton_limni.setEnabled(True)
            self.pushButton_flow.setEnabled(True)
            try: self.canvas.setMapTool(self.maptooloriginal)
            except Exception, e : pass

        #All the time : rubberband reset when the treewidget item changes
        try:
            source = self.sender()
            if source == self.treeWidget_utils and self.postutils.rubberband:
                self.postutils.rubberband.reset(QGis.Line)
        except Exception, e :
            self.textBrowser_2.append(str(e))

            
    #*********************************************************************************
    #Tools activation  *****************************************************
    #*********************************************************************************
    
    #*********************************************************************************
    #*******************************2shape **************************************

    def create_shp_maillage(self):
        """
        Called when Shape / create mesh is activated
        """
        self.postutils.create_shp_maillage()

    def create_shp(self):
        """
        Called when Shape / create contour is activated
        """
        self.postutils.create_shp()
        
    def create_shp_points(self):
        """
        Called when Shape / create points is activated
        """
        self.postutils.create_points()
        
        

    #Display tools - CRS things ***********************************************

    def set_utilcrs(self):
        self.crsselector.exec_()
        crs = self.crsselector.selectedAuthId()
        source = self.sender()
        #print str(source.name())
        if source == self.pushButton_crs:
            self.label_selafin_crs.setText(crs)
        else:
            source.setText(crs)
        
    
    #*********************************************************************************
    #*******************************Compare **************************************
    def initCompare(self):
        self.checkBox_6.setCheckState(0)
        #file to compare choice
        str1 = self.tr("Selafin file chooser")
        str2 = self.tr("Telemac files")
        str3 = self.tr("All files")  
        fname = self.qfiledlg.getOpenFileName(None,str1,self.loaddirectory, str2 + " (*.res *.geo *.init *.slf);;" + str3 + " (*)")
        #Things
        if fname:
            self.reset_dialog()
            self.lineEdit_5.setText(fname)
            hydrauparser = PostTelemacSelafinParser()
            hydrauparser.loadHydrauFile(fname)
            self.writeSelafinCaracteristics(self.textEdit_3,hydrauparser)
            #Launch thread
            self.checkBox_6.setEnabled(False)
            self.postutils.compareselafin()
        
    def reset_dialog(self):
        #self.textEdit_2.clear()
        self.textEdit_3.clear()
        self.lineEdit_5.clear()
        self.lineEdit.clear()
        self.checkBox_6.setCheckState(0)
        self.checkBox_6.setEnabled(False)

        
    def writeSelafinCaracteristics(self,textedit,hydrauparser):
        textedit.setText('')
        for var in hydrauparser.getVarnames():
            textedit.append(var)
        textedit.append("nombre d elements : "+str(len(hydrauparser.getValues(0)[0])))
        
        


    #*********************************************************************************
    #Tools - movie *******************************************
            
    def reinitcomposeurlist(self,composeurview1=None):
        """
        update composer list in movie page when a new composer is added
        """
        try:
            self.comboBox_compositions.clear()
            for composeurview in iface.activeComposers():
                name = composeurview.composerWindow().windowTitle()
                self.comboBox_compositions.addItems([str(name)])
        except Exception , e :
            self.comboBox_compositions.addItems([self.tr("no composer")])
        

    def reinitcomposeurimages(self,int1=None):
        """
        update image list in movie page when images' combobox is clicked
        """
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
            
            
    #****************************************************************************************************
    #************translation  / general method                                      ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('PostTelemacPropertiesDialog', message, None, QApplication.UnicodeUTF8)

            
    def eventFilter(self,target,event):
        """
        event for specific actions
        Used only for movie utilities - update images in composer
        """
        #Action to update images in composer with movie tool
        try:
            if target == self.comboBox_8 and event.type() == QtCore.QEvent.MouseButtonPress:
                self.reinitcomposeurimages()
            return False
        except Exception, e:
            #print 'Property dialog eventFilter ' + str(e)
            return False
            
            
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
        
        
