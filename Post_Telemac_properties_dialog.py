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



import os
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.gui import *
from qgis.core import *
from libs.post_telemac_utils import *
from libs.posttelemac_util_extractshp import *
from libs.posttelemac_util_extractmesh import *
from libs.posttelemac_util_getcomparevalue import *
from libs.def_variable import *

from time import ctime
from matplotlib.colors import LinearSegmentedColormap

#import matplotlib
import matplotlib
from matplotlib import *
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib import tri
from matplotlib import colors
import matplotlib.tri as tri
from matplotlib.mlab import griddata
import matplotlib.pyplot  as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui', 'properties.ui'))



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
        self.layer = layer1                             #the associated selafin layer
        self.qfiledlg = QtGui.QFileDialog(self)         #the filedialog for opening res file
        self.predeflevels=[]                            #the levels in classes.txt
        self.threadcompare = None                       #The compare file class

        self.canvas = self.layer.canvas
        self.postutils = PostTelemacUtils(layer1)       #the utils class
        
        self.maptooloriginal = self.canvas.mapTool()        #Initial map tool (ie mouse behaviour)
        self.clickTool = QgsMapToolEmitPoint(self.canvas)   #specific map tool (ie mouse behaviour)
        
        #********* ********** ******************************************
        #********* Connecting ******************************************
        #********* ********** ******************************************
        
        #********* ********** ******************************************
        #Display tab  ************************************************
        #********* ********** ******************************************
        self.pushButton_loadslf.clicked.connect(lambda: self.layer.load_selafin())
        self.populatecombobox_lvl()
        self.populatecombobox_colorpalette()
        #param
        #self.comboBox_param.currentIndexChanged.connect(self.layer.change_param)
        self.treeWidget_parameters.itemSelectionChanged.connect(self.layer.change_param2)
        self.treeWidget_parameters.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.treeWidget_parameters.setColumnWidth(0,40)
        self.treeWidget_parameters.header().setResizeMode(0,QtGui.QHeaderView.Fixed)
        self.horizontalSlider_time.sliderPressed.connect(self.layer.change1)
        self.horizontalSlider_time.sliderReleased.connect(self.layer.change2)
        #↔self.itmModel_param = QStandardItemModel()
        #self.pushButton_manageParameter.clicked.connect(self.open_def_variables)
        self.pushButton_param_add.clicked.connect(self.open_def_variables)
        self.pushButton_param_edit.clicked.connect(self.open_def_variables)
        self.pushButton_param_delete.clicked.connect(self.delete_def_variables)
        
        #transparency
        self.horizontalSlider_transp.valueChanged.connect(self.layer.changeAlpha)
        self.horizontalSlider_transp.sliderPressed.connect(self.layer.change1)
        self.horizontalSlider_transp.sliderReleased.connect(self.layer.change2)
        #levels and color ramp
        self.comboBox_levelstype.currentIndexChanged.connect(self.change_cmchoosertype)
        self.comboBox_genericlevels.currentIndexChanged.connect(self.change_cmchoosergenericlvl)
        self.comboBox_genericlevels_2.currentIndexChanged.connect(self.change_cmchoosergenericlvl_vel)
        self.doubleSpinBox_levelshift.valueChanged.connect(self.decal_lvl)
        self.pushButton_createsteplevel.clicked.connect(self.createstepclass)
        self.pushButton_crs.clicked.connect(self.set_layercrs)
        #time
        self.comboBox_time.currentIndexChanged.connect(self.layer.change_timetxt)
        self.horizontalSlider_time.valueChanged.connect(self.layer.change_timetxt)
        #color palette
        self.comboBox_clrgame.currentIndexChanged.connect(self.color_palette_changed)
        #Affichage divers
        self.groupBox_schowvel.toggled.connect(self.layer.changeAffichageVitesse)
        self.comboBox_vel_method.currentIndexChanged.connect(self.layer.changeAffichageVitesse)
        self.doubleSpinBox_vel_spatial_step.valueChanged.connect(self.layer.changeAffichageVitesse)
        self.doubleSpinBox_vel_scale.valueChanged.connect(self.layer.changeAffichageVitesse)
        self.spinBox_vel_relative.valueChanged.connect(self.layer.changeAffichageVitesse)
        self.comboBox_clrgame_2.currentIndexChanged.connect(self.color_palette_changed_vel)
        
        self.checkBox_showmesh.stateChanged.connect(self.layer.showMesh)
        
        #********* ********** ******************************************
        #Tools tab  *****************************************************
        #********* ********** ******************************************
        
        self.treeWidget_utils.itemSelectionChanged.connect(self.changepannelutils)
        self.crsselector = QgsGenericProjectionSelector()

        #Tools tab - Extraction .shp Contour
        self.checkBox_contourcrs.stateChanged.connect(self.enablecheckbox)
        self.pushButton_contourcrs.clicked.connect(self.set_utilcrs)
        self.pushButton_contourcreate.clicked.connect(self.create_shp)
        
        #Tools tab - Extraction .shp Maillage
        self.checkBox_3.stateChanged.connect(self.enablecheckbox)
        self.checkBox_2.stateChanged.connect(self.enablecheckbox)
        self.pushButton_7.clicked.connect(self.set_utilcrs)
        self.pushButton_10.clicked.connect(self.create_shp_maillage)
        
        #Tools tab - Extraction .shp Points
        self.checkBox_4.stateChanged.connect(self.enablecheckbox)
        self.checkBox_5.stateChanged.connect(self.enablecheckbox)
        self.pushButton_9.clicked.connect(self.set_utilcrs)
        self.pushButton_2.clicked.connect(self.create_shp_points)
        
        #Tools tab - values
        self.tabWidget.currentChanged.connect(self.mapToolChooser)
        self.treeWidget_utils.itemClicked.connect(self.mapToolChooser)
        
        #Tools tab - temporal graph
        self.figure1 = plt.figure(self.layer.instancecount+1)
        font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
        rc('font', **font)
        self.canvas1 = FigureCanvas(self.figure1)
        self.ax = self.figure1.add_subplot(111)
        self.toolbar = NavigationToolbar(self.canvas1, self.frame,True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas1)
        self.canvas1.draw()
        self.frame.setLayout(layout)
        self.comboBox_2.currentIndexChanged.connect(self.mapToolChooser)
        self.pushButton_limni.clicked.connect(self.postutils.computeGraph)
        self.pushButton_graphtemp_pressepapier.clicked.connect(self.postutils.copygraphclipboard)
        
        #Tools tab- flow graph
        self.figure2 = plt.figure(self.layer.instancecount+2)
        self.canvas2 = FigureCanvas(self.figure2)
        self.ax2 = self.figure2.add_subplot(111)
        self.toolbar2 = NavigationToolbar(self.canvas2, self.frame_2,True)
        layout2 = QtGui.QVBoxLayout()
        layout2.addWidget(self.toolbar2)
        layout2.addWidget(self.canvas2)
        self.canvas2.draw()
        self.frame_2.setLayout(layout2)
        self.comboBox_3.currentIndexChanged.connect(self.mapToolChooser)
        self.pushButton_4.clicked.connect(self.postutils.copygraphclipboard)
        self.pushButton_flow.clicked.connect(self.postutils.computeFlow)
        
        #Tools tab - compare
        self.pushButton_8.clicked.connect(self.initCompare)
        self.checkBox_6.stateChanged.connect(self.compare1)
        
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
            
        #Tools tab- max ppr 
        self.pushButton_max_res.clicked.connect(self.postutils.calculMaxRes)
        

            
            
        
        #final action
        self.initTreewidgettoolsindextab()
        self.treeWidget_utils.expandAll()

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

        
    #*********************************************************************************
    #update properties dialog with selafin layer modification *************************
    #*********************************************************************************
    def update(self):
        """
        update dialog when selafin layer changed
        """
        if self.layer.fname is not None:
            paramtemp = self.layer.param_gachette   #param_gachete deleted with clear - so save it
            tempstemp = self.layer.temps_gachette
            alphatemp = self.layer.alpha_gachette
            #nom
            self.label_loadslf.setText(os.path.basename(self.layer.fname).split('.')[0])
            #param
            self.populatecombobox_param()
            if paramtemp:
                #pass
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,paramtemp)
                #self.comboBox_param.setCurrentIndex(paramtemp)
                #self.treeWidget_parameters.
            else:
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,0)
            #self.comboBox_param.setEnabled(True)
            self.groupBox_contour.setEnabled(True)
            self.groupBox_param.setEnabled(True)
            self.groupBox_time.setEnabled(True)
            self.treeWidget_parameters.setEnabled(True)
            #time
            self.horizontalSlider_time.setEnabled(True)
            self.comboBox_time.setEnabled(True)
            self.horizontalSlider_time.setMaximum(self.layer.tempsmax)
            self.horizontalSlider_time.setPageStep (int(self.layer.tempsmax/20) )
            self.populatecombobox_time()
            self.layer.change_timetxt(tempstemp)
            self.horizontalSlider_time.setValue(tempstemp)
            self.comboBox_time.setCurrentIndex(tempstemp)
            #transparency
            self.horizontalSlider_transp.setEnabled(True)
            self.horizontalSlider_transp.setValue(alphatemp)
            #crs
            if self.layer.crs().authid():
                #self.pushButton_crs.setText(self.layer.crs().authid())
                self.label_selafin_crs.setText(self.layer.crs().authid())
            self.pushButton_crs.setEnabled(True)
            #utils
            self.textBrowser_2.clear()
            #compare
            if self.threadcompare is not None:
                self.threadcompare.compare.reset_dialog()
                self.threadcompare = None
            #film
            self.reinitcomposeurlist()
            self.reinitcomposeurimages(0)
            maxiter = len(self.layer.slf.tags["times"])-1
            self.spinBox_3.setMaximum(maxiter)
            self.spinBox_2.setMaximum(maxiter)
            self.spinBox_3.setValue(maxiter)

    #*********************************************************************************
    #Standart output ****************************************************************
    #*********************************************************************************

    def errorMessage(self,str):
        self.textBrowser_main.setTextColor(QColor("red"))
        self.textBrowser_main.setFontWeight(QFont.Bold)
        self.textBrowser_main.append(ctime() + ' - '+ str)
        self.textBrowser_main.setTextColor(QColor("black"))
        self.textBrowser_main.setFontWeight(QFont.Normal)
        
    def normalMessage(self,str):
        self.textBrowser_main.append(ctime() + ' - '+ str)
        self.textBrowser_main.setTextColor(QColor("black"))
        self.textBrowser_main.setFontWeight(QFont.Normal)
                
    #*********************************************************************************
    #Display tools****************************************************************
    #*********************************************************************************
    

    def decal_lvl(self,int):
        """
        update classes when level offset is changed
        """
        leveltemp = self.predeflevels[self.comboBox_genericlevels.currentIndex()][1]
        lvltemp1=[leveltemp[i]+self.doubleSpinBox_levelshift.value() for i in range(len(leveltemp))]
        self.layer.change_lvl(lvltemp1)
        
    def open_def_variables(self, lst_param):
        source = self.sender()
        if source == self.pushButton_param_add:
            lst_param = ["", "", ""]
        elif source == self.pushButton_param_edit:
            index = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)[1]
            if self.layer.parametres[index][2]:
                lst_param = [self.layer.parametres[index][1], self.layer.parametres[index][2], ""]
            else:
                return False
        
        """
        lst_var = []
        mdl = self.list_variables.model()
        for i in range(mdl.rowCount()):
            itm = mdl.item(i)
            lst_var.append(itm.text())
        """
        lst_var = [param for param in self.layer.parametres if not param[2]]
        
        self.dlg_dv = DefVariablesDialog(lst_param, lst_var)
        self.dlg_dv.setWindowModality(2)
    
        r = self.dlg_dv.exec_()
        
        """
        with open(os.path.dirname(os.path.realpath(__file__)) + '\\classes','rb') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            self.classe_val = mon_depickler.load()
        """
        if r == 1:
            """
            if len(self.tab_variables_creer.selectedItems()) > 0:
                self.supprimer_var()
            """
            itms = []
            new_var = self.dlg_dv.dialogIsFinished()
            #print str(new_var)
            """
            param_name = [param[1] for param in self.layer.parametres]
            if new_var[0] in param_name:
                pass
            else:
            """
            if source == self.pushButton_param_add:
                self.layer.parametres.append([len(self.layer.parametres),new_var[0],new_var[1]])
                self.populatecombobox_param()
                self.layer.param_memoire = None
                self.layer.temps_identify = None
                self.layer.updateSelafinValues(True)
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,len(self.layer.parametres)-1)
            elif source == self.pushButton_param_edit:
                self.layer.parametres[index] = [index,new_var[0],new_var[1]]
                self.populatecombobox_param()
                self.layer.param_memoire = None
                self.layer.temps_identify = None
                self.layer.updateSelafinValues(True)
                self.setTreeWidgetIndex(self.treeWidget_parameters,0,index)
            #self.layer.triggerRepaint()
                
            """
            self.itmModel = QStandardItemModel()
            itm = QTreeWidgetItem()
            itm.setText(0, new_var["nom"])
            itm.setText(1, new_var["formule"])
            itm.setText(2, new_var["classe"])
            itms.append(itm)
            self.tab_variables_creer.addTopLevelItems(itms)

            self.tab_variables_creer.clearSelection()
            """
            
    def delete_def_variables(self):
        index = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)[1]
        if self.layer.parametres[index][2]:
            self.layer.param_gachette = index-1
            self.layer.parametres[index:index+1] = []
            self.populatecombobox_param()
            self.setTreeWidgetIndex(self.treeWidget_parameters,0,index-1)
            self.layer.updateSelafinValues(True)
            #self.layer.triggerRepaint()
        
        

    #Display tools - color ramp things ***********************************************

    def change_cmchoosertype(self,item):
        """
        pass
        """
        if item == 0:
            #self.stackedWidget_colorramp.setCurrentIndex(0)
            self.layer.change_lvl(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
        elif item == 1:
            self.stackedWidget_colorramp.setCurrentIndex(1)
        else:
            pass
            
    def change_cmchoosergenericlvl(self):
        """
        change levels of selafin layer when generics levels are changed
        """
        self.layer.change_lvl(self.predeflevels[self.comboBox_genericlevels.currentIndex()][1])
            
            
    def change_cmchoosergenericlvl_vel(self):
        """
        change levels of selafin layer when generics levels are changed
        """
        self.layer.change_lvl_vel(self.predeflevels[self.comboBox_genericlevels_2.currentIndex()][1])
            
    def createstepclass(self):
        """
        create steps classes and change levels of selafin layer when steps classes are changed
        """
        if self.lineEdit_levelmin.text()=="" : 
            zmin=min(self.layer.slf.getVALUES(self.layer.temps_gachette)[self.layer.param_gachette] )
            self.lineEdit_levelmin.setText(str(round(float(zmin),3)))
        else : 
            zmin = float(self.lineEdit_levelmin.text())
        if self.lineEdit_levelmax.text()=="" : 
            zmax=max(self.layer.slf.getVALUES(self.layer.temps_gachette)[self.layer.param_gachette] )
            self.lineEdit_levelmax.setText(str(round(float(zmax),3)))
        else : 
            zmax = float(self.lineEdit_levelmax.text())

        pdn = float(self.lineEdit_levelstep.text())
        zmin1=int(zmin)
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
            temp=round(temp+pdn,3)
            levels.append(temp)
            
        self.layer.change_lvl(levels)
        

            
    def color_palette_changed(self,int):
        """
        change color map of selafin layer (matplotlib's style) when color palette combobox is changed
        """
        temp1 = QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())
        dict = self.getTupleColors(temp1)
        self.layer.cmap = LinearSegmentedColormap('temp', dict)
        self.layer.change_cm(self.layer.cmap)
            
    def color_palette_changed_vel(self,int):
        """
        change color map of selafin layer (matplotlib's style) when color palette combobox is changed
        """
        temp1 = QgsStyleV2.defaultStyle().colorRamp(self.comboBox_clrgame_2.currentText())
        dict = self.getTupleColors(temp1)
        self.layer.cmap_vel = LinearSegmentedColormap('temp', dict)
        self.layer.change_cm_vel(self.layer.cmap_vel)
            
            
            
    def getTupleColors(self,temp1):
        if str(temp1.__class__.__name__) == 'QgsVectorGradientColorRampV2':
            #first load colormap from qgis
            #print str(temp1.properties())
            firstcol = temp1.properties()['color1']
            lastcol=temp1.properties()['color2']
            try:
                otherscol=temp1.properties()['stops'].split(":")
                bool_stops = True
            except Exception, e :
                bool_stops = False
            
            #arrange it to fit dict of matplotlib:
            """
            http://matplotlib.org/examples/pylab_examples/custom_cmap.html
            """
            dict={}
            identcolors=['red','green','blue','alpha']
            for col in range(len(identcolors)):
                dict[identcolors[col]]=[]
                dict[identcolors[col]].append((0,float(firstcol.split(',')[col])/255.0,float(firstcol.split(',')[col])/255.0))
                if bool_stops:
                    lendict=len(otherscol)
                    for i in range(lendict):
                        dict[identcolors[col]].append((float(otherscol[i].split(';')[0]),float(otherscol[i].split(';')[1].split(',')[col])/255.0,float(otherscol[i].split(';')[1].split(',')[col])/255.0))
                dict[identcolors[col]].append((1,float(lastcol.split(',')[col])/255.0,float(lastcol.split(',')[col])/255.0))
                dict[identcolors[col]] = tuple(dict[identcolors[col]])
        return dict
        
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
        
    def set_layercrs(self):
        source = self.sender()
        self.crsselector.exec_()
        crs = self.crsselector.selectedAuthId()

        #print str(source.name())
        if source == self.pushButton_crs:
            self.label_selafin_crs.setText(crs)
        else:
            source.setText(crs)
        self.layer.setCrs(QgsCoordinateReferenceSystem(crs))
        

    #*********************************************************************************
    #Display - Init things                          ******************************************
    #*********************************************************************************

    def enablecheckbox(self,int1):
        """
        Enable checkboxes for activating buttons when atoher buttons are activated
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
                

    def populatecombobox_lvl(self):
        """
        Populate classes combobox on dialog creation
        """
        f = open(os.path.join(os.path.dirname(__file__), 'classes.txt'), 'r')
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
        for i in range(len(self.layer.slf.tags["times"])):
            self.comboBox_time.addItems([str(self.layer.slf.tags["times"][i])])
            
    def populatecombobox_param(self):
        """
        Populate parameters combobox on dialog update
        """
        #self.comboBox_param.clear()
        self.comboBox_parametreschooser.clear()
        
        for i in range(len(self.layer.parametres)):
            temp1 = [str(self.layer.parametres[i][0])+" : "+str(self.layer.parametres[i][1])]
            #self.comboBox_param.addItems(temp1)
            self.comboBox_parametreschooser.addItems(temp1)
        
        self.treeWidget_parameters.clear()
        itms = []
        for i in range(len(self.layer.parametres)):
            #self.itmModel = QStandardItemModel()
            itm = QTreeWidgetItem()
            itm.setText(0, str(self.layer.parametres[i][0]))
            itm.setText(1, str(self.layer.parametres[i][1]))
            if self.layer.parametres[i][2]:
                itm.setText(2, str(self.layer.parametres[i][2]))
            else:
                itm.setText(2, self.tr('Raw data'))
            """
            if len( self.layer.parametres[i]) >2:
                itm.setText(2, str(self.layer.parametres[i][2]))
            else:
                itm.setText(2, '/')
            """
            itms.append(itm)
        self.treeWidget_parameters.addTopLevelItems(itms)


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
            
    def getTreeWidgetSelectedIndex(self,widget):
        getSelected = widget.selectedItems()
        baseNode = getSelected[0]
        position = [widget.indexFromItem(baseNode).parent().row(),widget.indexFromItem(baseNode).row()]
        return position
        
    def setTreeWidgetIndex(self,widget,pos0,pos1):
        """
        """
        #widget.setItemSelected(widget.itemAt(pos0,pos1),True)
        #widget.itemAt(pos0,pos1).setSelected(True)
        #widget.topLevelItem(pos1).setSelected(True)
        widget.scrollToItem(widget.topLevelItem(pos1))
        widget.setCurrentItem(widget.topLevelItem(pos1))
        widget.setItemSelected(widget.topLevelItem(pos1), True)
        
        #widget.update()
        #widget.repaint()
        """
        itemAt (self, int ax, int ay)
        getSelected = widget.selectedItems()
        baseNode = getSelected[0]
        position = [widget.indexFromItem(baseNode).parent().row(),widget.indexFromItem(baseNode).row()]
        return position
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
                                        [[7,2],10,'2shape point' ]]

    
    def changepannelutils(self):
        """
        Method to choose the stackedwidget page linked mith the tree item
        """
        getSelected = self.treeWidget_utils.selectedItems()
        baseNode = getSelected[0]
        text = baseNode.text(0)
        position = [self.treeWidget_utils.indexFromItem(baseNode).parent().row(),self.treeWidget_utils.indexFromItem(baseNode).row()]
        indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
        try:
            self.stackedWidget.setCurrentIndex(self.treewidgettoolsindextab[indextabtemp.index(position)][1])
        except Exception, e:
            self.stackedWidget.setCurrentIndex(0)
        

            
    def mapToolChooser(self,int=None):
        """
        Activate maptool (specific mouse behaviour) when specifics items in the utilities tree is clicked
        """
        getSelected = self.treeWidget_utils.selectedItems()
        try:
            baseNode = getSelected[0]
            position = [self.treeWidget_utils.indexFromItem(baseNode).parent().row(),self.treeWidget_utils.indexFromItem(baseNode).row()]
            indextabtemp=[index[0] for index in self.treewidgettoolsindextab ]
            itemname = self.treewidgettoolsindextab[indextabtemp.index(position)][2]
        except Exception, e:
            itemname = None
        
        if (len(self.treeWidget_utils.selectedItems())>0 
            and itemname == 'Values' 
            and self.tabWidget.currentIndex() == 1):
            #Click sur valeur
            self.canvas.setMapTool(self.clickTool)
            try:self.clickTool.canvasClicked.disconnect()
            except Exception: pass
            self.clickTool.canvasClicked.connect(self.postutils.valeurs_click)
            self.postutils.valeurs_click(QgsPoint(0.0,0.0))
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
                  and itemname == 'Temporal graph' 
                  and self.tabWidget.currentIndex() == 1
                  and self.comboBox_2.currentIndex() == 0):
            #Click sur graphtemp - point temporaire
            if self.postutils.rubberband:
                self.postutils.rubberband.reset(QGis.Point)
            try:self.clickTool.canvasClicked.disconnect()
            except Exception: pass
            self.pushButton_limni.setEnabled(False)
            self.canvas.setMapTool(self.clickTool)
            self.clickTool.canvasClicked.connect(self.postutils.graphtemp_click)
            
        elif (len(self.treeWidget_utils.selectedItems())>0 
                  and itemname == 'Flow graph' 
                  and self.tabWidget.currentIndex() == 1
                  and (self.comboBox_3.currentIndex() in [0] )):
            #Click sur calcul debit - polyligne temporaire
            if self.postutils.rubberband:
                self.postutils.rubberband.reset(QGis.Point)
            try:self.clickTool.canvasClicked.disconnect()
            except Exception: pass
            self.pushButton_flow.setEnabled(False)
            self.postutils.computeFlow()
        else:
            #Le reste....
            self.pushButton_limni.setEnabled(True)
            self.pushButton_flow.setEnabled(True)
            try: self.canvas.setMapTool(self.maptooloriginal)
            except Exception, e : pass

        #Le systematique : reset du dessin temporaire au changement d element du treewidget
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
        
    
    #*********************************************************************************
    #*******************************Compare **************************************
    def initCompare(self):
        self.checkBox_6.setCheckState(0)
        #file to compare choice
        str1 = self.tr("Selafin file chooser")
        str2 = self.tr("Telemac files")
        str3 = self.tr("All files")  
        fname = self.qfiledlg.getOpenFileName(None,str1,self.layer.loaddirectory, str2 + " (*.res *.geo *.init);;" + str3 + " (*)")
        #fname = self.qfiledlg.getOpenFileName(None,"Choix du fichier res",self.layer.loaddirectory, "Fichier_Telemac (*.res *.geo)")
        #Things
        self.lineEdit_5.setText(fname)
        self.writeSelafinCaracteristics(self.textEdit_2,self.layer.slf)
        self.writeSelafinCaracteristics(self.textEdit_3,SELAFIN(fname))
        #Launch thread
        self.checkBox_6.setEnabled(False)
        self.threadcompare = initgetCompareValue(self.layer)
        self.threadcompare.compare.transmitvalues = False
        self.threadcompare.start()
        
    def writeSelafinCaracteristics(self,textedit,selafin):
        textedit.setText('')
        for var in selafin.VARNAMES:
            textedit.append(var)
        textedit.append("nombre d elements : "+str(len(selafin.getVALUES(0)[0])))
        
        
    def compare1(self,int1):
        if int1 == 2 :
            for i in range(len(self.threadcompare.var_corresp)):
                if self.threadcompare.var_corresp[i][1] is None:
                    self.layer.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsSelectable)
            self.layer.temps_memoire = None
            self.layer.param_memoire = None
            self.threadcompare.compare.transmitvalues = True
            self.layer.compare = True
            self.threadcompare.run()
            self.layer.updateSelafinValues()
            self.layer.triggerRepaint()
            
        elif int1 == 0 :
            #self.compare = None 
            self.layer.compare = False
            self.layer.temps_memoire = None
            self.layer.param_memoire = None
            self.populatecombobox_param()
            """
            for i in range(len(self.layer.parametres)):
                #self.layer.propertiesdialog.comboBox_param.model().item(i).setEnabled(True)
                self.layer.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsSelectable)
                self.layer.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsUserCheckable)
                self.layer.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsEnabled)
            """
            self.layer.updateSelafinValues()
            self.layer.triggerRepaint()

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
    #************translation                                        ***********************************
    #****************************************************************************************************

    
    
    def tr(self, message):  
        """Used for translation"""
        return QCoreApplication.translate('PostTelemacPropertiesDialog', message, None, QApplication.UnicodeUTF8)

            

            

        
        