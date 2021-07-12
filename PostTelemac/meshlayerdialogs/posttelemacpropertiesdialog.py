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
# unicode behaviour
from __future__ import unicode_literals

# import Qt
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QCoreApplication, QSettings, QSize, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QTreeWidgetItem,
    QTableWidgetItem,
    QApplication,
    QMessageBox,
    QHeaderView,
)

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsStyle,
    QgsSymbolLayerUtils,
)
from qgis.gui import QgsProjectionSelectionDialog
from qgis.utils import iface

# other import
import os
import time
import shutil

# local import
from .posttelemac_dialog_combobox import postTelemacComboboxDialog
from .posttelemacvirtualparameterdialog import *
from .posttelemacusercolorrampdialog import *
from .posttelemac_xytranslation import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "properties.ui"))


class PostTelemacPropertiesDialog(QDockWidget, FORM_CLASS):

    updateparamsignal = pyqtSignal()
    meshlayerschangedsignal = pyqtSignal()

    def __init__(self, layer1, parent=None):
        """
        Constructor, inherited from  QDockWidget
        Doing :
            connecting PostTelemacPropertiesDialog ' s signals to methods :
                methods for viewer are set in SelafinPluginLayer class
                methods for utilities are set in PostTelemacUtils class
        """
        super(PostTelemacPropertiesDialog, self).__init__(parent)
        self.setupUi(self)

        self.unloadtools = False

        # general variables
        self.meshlayer = layer1  # the associated selafin layer
        self.qfiledlg = QFileDialog(self)  # the filedialog for opening res file
        self.predeflevels = []  # the levels in classes.txt
        self.lastscolorparams = None  # used to save the color ramp state
        self.canvas = self.meshlayer.canvas
        self.maptooloriginal = self.canvas.mapTool()  # Initial map tool (ie mouse behaviour)
        self.crsselector = QgsProjectionSelectionDialog()
        self.playstep = None
        self.playactive = False

        # the directory of "load telemac" button
        if QSettings().value("posttelemac/lastdirectory") != "":
            self.loaddirectory = QSettings().value("posttelemac/lastdirectory")
        else:
            self.loaddirectory = None

        self.debugtoprint = False  # for test - enable dialog out in console if set True

        # setup user dir in home
        profiledir = os.path.normpath(QgsApplication.qgisSettingsDirPath())
        self.posttelemacdir = os.path.join(profiledir, "PostTelemac")
        if not os.path.isdir(self.posttelemacdir):
            shutil.copytree(os.path.join(os.path.dirname(__file__), "..", "config"), self.posttelemacdir)

        self.combodialog = postTelemacComboboxDialog()  # usefull for asking something

        # ********* ********** ******************************************
        # ********* Connecting ******************************************
        # ********* ********** ******************************************
        self.pushButton_loadslf.clicked.connect(self.loadSelafin)
        self.pushButton_crs.clicked.connect(self.set_layercrs)
        self.pushbutton_crstranslation.clicked.connect(self.translateCrs)

        # Time
        self.horizontalSlider_time.sliderPressed.connect(self.sliderPressed)
        self.horizontalSlider_time.sliderReleased.connect(self.sliderReleased)
        self.comboBox_time.currentIndexChanged.connect(self.change_timetxt)
        self.horizontalSlider_time.valueChanged.connect(self.change_timetxt)
        self.pushButton_Read.clicked.connect(self.readHydrauFile)
        # Contour box
        # parameters
        self.treeWidget_parameters.itemSelectionChanged.connect(self.change_param)
        try:
            self.treeWidget_parameters.header().setResizeMode(QHeaderView.ResizeToContents)
            self.treeWidget_parameters.setColumnWidth(0, 40)
            self.treeWidget_parameters.header().setResizeMode(0, QHeaderView.Fixed)
        except:
            self.treeWidget_parameters.setColumnWidth(0, 40)
        # virtual parameter
        self.pushButton_param_add.clicked.connect(self.open_def_variables)
        self.pushButton_param_edit.clicked.connect(self.open_def_variables)
        self.pushButton_param_delete.clicked.connect(self.delete_def_variables)
        # levels and color ramp
        self.populatecombobox_lvl()
        self.populatecombobox_colorpalette()
        self.InitMapRamp()
        self.checkBox_inverse_clr.setCheckState(0)
        self.checkBox_inverse_clr2.setCheckState(0)
        self.tabWidget_lvl_vel.currentChanged.connect(self.updateColorParams)

        self.connectColorRampSignals()

        # Velocity bpx
        # Velocity
        self.groupBox_schowvel.toggled.connect(self.setVelocityRendererParams)
        self.comboBox_vel_method.currentIndexChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_vel_spatial_step.valueChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_vel_scale.valueChanged.connect(self.setVelocityRendererParams)
        self.spinBox_vel_relative.valueChanged.connect(self.setVelocityRendererParams)
        self.comboBox_viewer_arow.currentIndexChanged.connect(self.setVelocityRendererParams)
        self.doubleSpinBox_uniform_vel_arrow.valueChanged.connect(self.setVelocityRendererParams)
        # colorramp
        # self.comboBox_genericlevels_2.currentIndexChanged.connect(self.change_cmchoosergenericlvl_vel)
        # self.comboBox_clrgame_2.currentIndexChanged.connect(self.color_palette_changed_vel)
        # Mesh box
        self.checkBox_showmesh.stateChanged.connect(self.meshlayer.showMesh)
        # transparency box
        self.horizontalSlider_transp.valueChanged.connect(self.changeAlpha)
        self.horizontalSlider_transp.sliderPressed.connect(self.sliderPressed)
        self.horizontalSlider_transp.sliderReleased.connect(self.sliderReleased)
        # progressbar
        self.progressBar.reset()

        # rednertype
        allitems = [self.comboBox_rendertype.itemText(i) for i in range(self.comboBox_rendertype.count())]
        if QSettings().value("posttelemac/renderlib") is not None:
            self.comboBox_rendertype.setCurrentIndex(allitems.index(QSettings().value("posttelemac/renderlib")))
        self.comboBox_rendertype.currentIndexChanged.connect(self.changeMeshLayerRenderer)

        # ********* ********** ******************************************
        # Tools tab  *****************************************************
        # ********* ********** ******************************************

        self.tools = []
        self.treeWidget_utils.expandAll()

    # *********************************************************************************
    # update properties dialog with selafin layer modification *************************
    # *********************************************************************************
    def update(self):
        """
        update dialog when selafin layer changes
        """
        if self.meshlayer.hydraufilepath is not None:
            paramtemp = self.meshlayer.param_displayed  # param_gachete deleted with clear - so save it
            tempstemp = self.meshlayer.time_displayed
            alphatemp = self.meshlayer.meshrenderer.alpha_displayed
            # name
            self.label_loadslf.setText(os.path.basename(self.meshlayer.hydraufilepath).split(".")[0])

            self.loaddirectory = os.path.dirname(self.meshlayer.hydraufilepath)
            QSettings().setValue("posttelemac/lastdirectory", self.loaddirectory)
            # param
            self.populatecombobox_param()
            if paramtemp:
                self.setTreeWidgetIndex(self.treeWidget_parameters, 0, paramtemp)
            else:
                self.setTreeWidgetIndex(self.treeWidget_parameters, 0, 0)
            self.tab_contour.setEnabled(True)
            self.groupBox_param.setEnabled(True)
            self.groupBox_time.setEnabled(True)
            self.treeWidget_parameters.setEnabled(True)
            # time
            self.horizontalSlider_time.setEnabled(True)
            self.comboBox_time.setEnabled(True)
            self.horizontalSlider_time.setMaximum(self.meshlayer.hydrauparser.itertimecount)
            self.horizontalSlider_time.setPageStep(min(10, int(self.meshlayer.hydrauparser.itertimecount / 20)))
            self.populatecombobox_time()
            self.change_timetxt(tempstemp)
            self.horizontalSlider_time.setValue(tempstemp)
            self.comboBox_time.setCurrentIndex(tempstemp)
            # transparency
            self.horizontalSlider_transp.setEnabled(True)
            self.horizontalSlider_transp.setValue(int(alphatemp))
            # crs
            if self.meshlayer.crs().authid():
                self.label_selafin_crs.setText(self.meshlayer.crs().authid())
            self.pushButton_crs.setEnabled(True)

            # renderer
            if self.meshlayer.parametrestoload["renderer"] is not None:
                # preset
                self.comboBox_genericlevels.setCurrentIndex(self.meshlayer.parametrestoload["renderer"][1][1])
                self.comboBox_clrgame.setCurrentIndex(self.meshlayer.parametrestoload["renderer"][1][0])
                # range
                self.lineEdit_levelmin.setText(self.meshlayer.parametrestoload["renderer"][2][1][0])
                self.lineEdit_levelmax.setText(self.meshlayer.parametrestoload["renderer"][2][1][1])
                self.lineEdit_levelstep.setText(self.meshlayer.parametrestoload["renderer"][2][1][2])
                # user
                index = self.comboBox_clrramp_preset.findText(
                    self.meshlayer.parametrestoload["renderer"][3], Qt.MatchFixedString
                )
                if index > 0:
                    self.comboBox_clrramp_preset.setCurrentIndex(index)
                # render type
                self.comboBox_levelstype.setCurrentIndex(self.meshlayer.parametrestoload["renderer"][0])
                if False:
                    if self.meshlayer.parametrestoload["renderer"][0] == 0:
                        self.color_palette_changed(type="contour")  # initialize colors in renderer
                    elif self.meshlayer.parametrestoload["renderer"][0] == 1:
                        self.createstepclass()
                        self.color_palette_changed(type="contour")  # initialize colors in renderer
                    elif self.meshlayer.parametrestoload["renderer"][0] == 2:
                        self.loadMapRamp(self.meshlayer.parametrestoload["renderer"][3])

                    """
                    if int(element.attribute('level_type')) == 0:
                        self.propertiesdialog.change_cmchoosergenericlvl()
                    elif int(element.attribute('level_type')) == 1:
                        self.propertiesdialog.createstepclass()
                    """

                    # reset parametrestoload
                    self.meshlayer.parametrestoload["renderer"] = None

            # utils
            self.textBrowser_2.clear()

            if self.unloadtools:
                # compare
                self.writeSelafinCaracteristics(self.textEdit_2, self.meshlayer.hydrauparser)
                if self.postutils.compareprocess is not None:
                    self.reset_dialog()
                    self.postutils.compareprocess = None

                # movie
                self.reinitcomposeurlist()
                self.reinitcomposeurimages(0)

            self.meshlayerschangedsignal.emit()

    def loadTools(self, filetype=None):

        import glob, inspect, importlib

        self.unloadTools()

        self.normalMessage("Loading tools")
        path = os.path.join(os.path.dirname(__file__), "..", "meshlayertools")
        modules = glob.glob(path + "/*.py")
        __all__ = [os.path.basename(f)[:-3] for f in modules if os.path.isfile(f)]
        for x in __all__:
            try:
                moduletemp = importlib.import_module("." + str(x), "PostTelemac.meshlayertools")
                for name, obj in inspect.getmembers(moduletemp, inspect.isclass):
                    if moduletemp.__name__ == obj.__module__:
                        try:  # case obj has NAME
                            istool = obj.NAME
                            if filetype is None:
                                try:
                                    self.tools.append(obj(self.meshlayer, self))
                                except Exception as e:
                                    self.errorMessage(istool + " : " + str(e))
                            else:  # specific software tool
                                try:  # case obj has SOFTWARE
                                    if len(obj.SOFTWARE) > 0 and filetype in obj.SOFTWARE:
                                        try:
                                            self.tools.append(obj(self.meshlayer, self))
                                        except Exception as e:
                                            self.errorMessage(istool + " : " + str(e))
                                    elif len(obj.SOFTWARE) == 0:
                                        try:
                                            self.tools.append(obj(self.meshlayer, self))
                                        except Exception as e:
                                            self.errorMessage(istool + " : " + str(e))
                                except:
                                    pass
                        except Exception as e:
                            pass
            except Exception as e:
                self.errorMessage("Error importing tool - " + str(x) + " : " + str(e))
        self.stackedWidget.setCurrentIndex(0)
        self.normalMessage("Tools loaded")

    def unloadTools(self):
        # clear tools tab
        try:
            self.treeWidget_utils.clear()
            for i in range(1, self.stackedWidget.count()):
                widg = self.stackedWidget.widget(i)
                self.stackedWidget.removeWidget(widg)
            self.tools = []
        except Exception as e:
            self.errorMessage("Eror unloading tools : ", e)

    # *********************************************************************************
    # Standart output ****************************************************************
    # *********************************************************************************

    def errorMessage(self, message):
        """
        Show message str in main textbrowser
        """
        self.textBrowser_main.setTextColor(QColor("red"))
        self.textBrowser_main.setFontWeight(QFont.Bold)
        self.textBrowser_main.append(str(time.strftime("[%H:%M:%S] ", time.localtime())) + str(message))
        self.textBrowser_main.setTextColor(QColor("black"))
        self.textBrowser_main.setFontWeight(QFont.Normal)
        self.textBrowser_main.verticalScrollBar().setValue(self.textBrowser_main.verticalScrollBar().maximum())

        if self.debugtoprint:
            print("error message : ", message)

    def normalMessage(self, message):
        """
        Show message error str in main textbrowser
        """
        self.textBrowser_main.append(str(time.strftime("[%H:%M:%S] ", time.localtime())) + str(message))
        self.textBrowser_main.setTextColor(QColor("black"))
        self.textBrowser_main.setFontWeight(QFont.Normal)
        self.textBrowser_main.verticalScrollBar().setValue(self.textBrowser_main.verticalScrollBar().maximum())

        if self.debugtoprint:
            print("normal message : ", message)

    def logMessage(self, message):
        """
        Show message error str in main textbrowser
        """
        self.textBrowser_2.append(str(time.strftime("[%H:%M:%S] ", time.localtime())) + str(message))
        if self.debugtoprint:
            print("log message : ", message)

    # *********************************************************************************
    # General tools****************************************************************
    # *********************************************************************************

    def loadSelafin(self):
        """
        Called when clicking on load selafin button
        """
        # filedialog
        # create filter
        str1 = ""
        for parser in self.meshlayer.parsers:
            str1 += parser[1] + " ("
            for extension in parser[2]:
                str1 += " *." + extension
            str1 += " );;"
        # show dialog
        tempname, extension = self.qfiledlg.getOpenFileName(None, "Choose the file", self.loaddirectory, str1)

        # something selected
        if tempname:
            if extension is not None:
                software = extension.split(" ")[0]
            timestart = time.perf_counter()
            self.loaddirectory = os.path.dirname(tempname)
            QSettings().setValue("posttelemac/lastdirectory", self.loaddirectory)
            self.meshlayer.clearParameters()
            success = self.meshlayer.load_selafin(tempname, software)
            if success:
                nom = os.path.basename(tempname).split(".")[0]
                self.normalMessage(
                    self.tr("File ")
                    + str(nom)
                    + self.tr(" loaded in ")
                    + str(round(time.perf_counter() - timestart, 1))
                    + " s"
                )
        else:
            if not self.meshlayer.hydraufilepath:
                self.label_loadslf.setText(self.tr("No file selected"))

    def set_layercrs(self):
        """
        Called when clicking on  selafin'crs button
        """
        source = self.sender()
        self.crsselector.exec_()
        crs = self.crsselector.crs().authid()
        if source == self.pushButton_crs:
            self.label_selafin_crs.setText(crs)
        else:
            source.setText(crs)
        self.meshlayer.setRealCrs(QgsCoordinateReferenceSystem(crs))

    def translateCrs(self):
        if self.meshlayer.hydrauparser is not None:
            self.dlg_xytranslate = xyTranslationDialog()
            self.dlg_xytranslate.setXandY(
                self.meshlayer.hydrauparser.translatex, self.meshlayer.hydrauparser.translatey
            )
            self.dlg_xytranslate.setWindowModality(2)
            r = self.dlg_xytranslate.exec_()
            xtranslate, ytranslate = self.dlg_xytranslate.dialogIsFinished()
            if xtranslate is not None and ytranslate is not None:
                self.meshlayer.hydrauparser.setXYTranslation(xtranslate, ytranslate)
                self.meshlayer.meshrenderer.changeTriangulationCRS()
                self.meshlayer.hydrauparser.createInterpolator()

                self.meshlayer.forcerefresh = True
                self.meshlayer.triggerRepaint()
                iface.mapCanvas().setExtent(self.meshlayer.extent())
        else:
            QMessageBox.about(self, "My message box", "Load a file first")

    # *********************************************************************************
    # *********************************************************************************
    # Display tools ****************************************************************
    # *********************************************************************************
    # *********************************************************************************

    # Display tools - time  ***********************************************

    def change_timetxt(self, intitmetireation):
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

        self.label_time.setText(
            self.tr("time (hours)")
            + " : "
            + str(time2)
            + "\n"
            + self.tr("time (iteration)")
            + " : "
            + str(intitmetireation)
            + "\n"
            + self.tr("time (seconds)")
            + " : "
            + str(self.meshlayer.hydrauparser.getTimes()[intitmetireation])
        )

    def sliderReleased(self):
        """Associated with time slider behaviour"""
        self.meshlayer.draw = True
        self.meshlayer.triggerRepaint()

    def sliderPressed(self):
        """Associated with time slider behaviour"""
        self.meshlayer.draw = False

    def readHydrauFile(self):
        """Action when play clicked"""
        iconplay = QIcon(":/plugins/PostTelemac/icons/play/play.png")
        iconstop = QIcon(":/plugins/PostTelemac/icons/play/stop.png")
        if not self.playactive:  # action on click when not playing
            self.pushButton_Read.setIcon(iconstop)
            self.playactive = True
            self.meshlayer.canvas.mapCanvasRefreshed.connect(self.readHydrauFile2)
            self.change_timetxt(self.meshlayer.time_displayed)
            self.meshlayer.canvas.refresh()
        else:  # action on click when  playing
            self.pushButton_Read.setIcon(iconplay)
            self.playactive = False
            self.meshlayer.canvas.mapCanvasRefreshed.disconnect(self.readHydrauFile2)

    def readHydrauFile2(self):
        self.playstep = int(self.spinBox_readtimestep.value())
        if self.meshlayer.time_displayed < len(self.meshlayer.hydrauparser.getTimes()) - self.playstep:
            self.horizontalSlider_time.setValue(self.meshlayer.time_displayed + self.playstep)
            self.meshlayer.canvas.refresh()
        else:  # end of time reached
            iconplay = QIcon(":/plugins/PostTelemac/icons/play/play.png")
            self.pushButton_Read.setIcon(iconplay)
            self.playactive = False
            self.meshlayer.canvas.mapCanvasRefreshed.disconnect(self.readHydrauFile2)

    # *********************************************************************************
    # Display tools - contour  ***********************************************
    # *********************************************************************************

    # Display tools - contour -  parameter ***********************************************

    def change_param(self, int1=None):
        """When changing parameter value"""
        position = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)
        # print position
        self.meshlayer.changeParam(position[1])
        if self.meshlayer.hydrauparser.parametres[position[1]][4]:
            self.pushButton_param_edit.setEnabled(True)
            self.pushButton_param_delete.setEnabled(True)
        else:
            self.pushButton_param_edit.setEnabled(False)
            self.pushButton_param_delete.setEnabled(False)

    # Display tools - contour -  virtual parameter ***********************************************

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
            if self.meshlayer.hydrauparser.parametres[index][4]:
                lst_param = [
                    self.meshlayer.hydrauparser.parametres[index][1],
                    self.meshlayer.hydrauparser.parametres[index][4],
                    "",
                ]
            else:
                return False

        lst_var = [param for param in self.meshlayer.hydrauparser.parametres if not param[4]]
        # launch dialog
        self.dlg_dv = DefVariablesDialog(lst_param, lst_var)
        self.dlg_dv.setWindowModality(2)

        r = self.dlg_dv.exec_()

        # Process new/edited param
        if r == 1:
            itms = []
            new_var = self.dlg_dv.dialogIsFinished()
            if source == self.pushButton_param_add:
                self.meshlayer.hydrauparser.parametres.append(
                    [
                        len(self.meshlayer.hydrauparser.parametres),
                        new_var[0],
                        self.meshlayer.hydrauparser.parametres[new_var[2]][2],
                        None,
                        new_var[1],
                        None,
                    ]
                )
                self.populatecombobox_param()
                self.meshlayer.updateSelafinValuesEmit()
                self.setTreeWidgetIndex(self.treeWidget_parameters, 0, len(self.meshlayer.hydrauparser.parametres) - 1)
            elif source == self.pushButton_param_edit:
                self.meshlayer.hydrauparser.parametres[index] = [
                    index,
                    new_var[0],
                    self.meshlayer.hydrauparser.parametres[index][2],
                    self.meshlayer.hydrauparser.parametres[index][3],
                    new_var[1],
                    self.meshlayer.hydrauparser.parametres[index][5],
                ]
                self.populatecombobox_param()
                self.meshlayer.updateSelafinValuesEmit()
                self.setTreeWidgetIndex(self.treeWidget_parameters, 0, index)

    def delete_def_variables(self):
        """
        Delete virtual parameter
        When clicking on delete virtual parameter
        """
        index = self.getTreeWidgetSelectedIndex(self.treeWidget_parameters)[1]
        if self.meshlayer.hydrauparser.parametres[index][4]:
            self.meshlayer.param_displayed = index - 1
            self.meshlayer.hydrauparser.parametres[index : index + 1] = []
            # checkkeysparameter
            self.meshlayer.parametreh = None
            self.meshlayer.parametrevx = None
            self.meshlayer.parametrevy = None
            # update all
            self.meshlayer.updateSelafinValuesEmit()
            self.populatecombobox_param()
            self.setTreeWidgetIndex(self.treeWidget_parameters, 0, index - 1)

    # Display tools - contour - color ramp things ***********************************************

    def updateColorParams(self, int1):
        """
        Remember state of color ramp when changing contour/velocity tabwidget
        """
        # save current color ramp state
        if self.comboBox_levelstype.currentIndex() == 0:
            lastscolorparamstemp = [
                0,
                self.lineEdit_levelschoosen.text(),
                self.comboBox_clrgame.currentIndex(),
                self.comboBox_genericlevels.currentIndex(),
            ]
        elif self.comboBox_levelstype.currentIndex() == 1:
            lastscolorparamstemp = [
                1,
                self.lineEdit_levelschoosen.text(),
                self.comboBox_clrgame2.currentIndex(),
                self.lineEdit_levelmin.text(),
                self.lineEdit_levelmax.text(),
                self.lineEdit_levelstep.text(),
            ]
        elif self.comboBox_levelstype.currentIndex() == 2:
            lastscolorparamstemp = [2, self.lineEdit_levelschoosen.text(), self.comboBox_clrramp_preset.currentIndex()]

        if self.lastscolorparams != None:
            # update color ramp widget
            self.disconnectColorRampSignals()
            self.comboBox_levelstype.setCurrentIndex(self.lastscolorparams[0])
            self.stackedWidget_colorramp.setCurrentIndex(self.lastscolorparams[0])
            if self.lastscolorparams[0] == 0:
                self.lineEdit_levelschoosen.setText(self.lastscolorparams[1])
                self.comboBox_clrgame.setCurrentIndex(self.lastscolorparams[2])
                self.comboBox_genericlevels.setCurrentIndex(self.lastscolorparams[3])
            elif self.lastscolorparams[0] == 1:
                self.lineEdit_levelschoosen.setText(self.lastscolorparams[1])
                self.comboBox_clrgame2.setCurrentIndex(self.lastscolorparams[2])
                self.lineEdit_levelmin.setText(self.lastscolorparams[3])
                self.lineEdit_levelmax.setText(self.lastscolorparams[4])
                self.lineEdit_levelstep.setText(self.lastscolorparams[5])
            elif self.lastscolorparams[0] == 2:
                self.lineEdit_levelschoosen.setText(self.lastscolorparams[1])
                self.comboBox_clrramp_preset.setCurrentIndex(self.lastscolorparams[2])
            self.connectColorRampSignals()

        # update name
        if int1 == 0:
            self.groupBox_colorramp.setTitle("Color ramp - contour")
        elif int1 == 1:
            self.groupBox_colorramp.setTitle("Color ramp - velocity")

        # update lastscolorparams
        self.lastscolorparams = lastscolorparamstemp

    def connectColorRampSignals(self):
        self.comboBox_levelstype.currentIndexChanged.connect(self.stackedWidget_colorramp.setCurrentIndex)
        self.comboBox_levelstype.currentIndexChanged.connect(self.colorRampChooserType)
        # 1
        self.comboBox_clrgame.currentIndexChanged.connect(self.color_palette_changed)
        self.comboBox_clrgame.currentIndexChanged.connect(self.comboBox_clrgame2.setCurrentIndex)
        self.checkBox_inverse_clr.stateChanged.connect(self.color_palette_changed)
        self.checkBox_inverse_clr.stateChanged.connect(self.checkBox_inverse_clr2.setCheckState)
        self.comboBox_genericlevels.currentIndexChanged.connect(self.change_cmchoosergenericlvl)
        # 2
        self.comboBox_clrgame2.currentIndexChanged.connect(self.comboBox_clrgame.setCurrentIndex)
        self.checkBox_inverse_clr2.stateChanged.connect(self.color_palette_changed)
        self.checkBox_inverse_clr2.stateChanged.connect(self.checkBox_inverse_clr.setCheckState)
        self.pushButton_createsteplevel.clicked.connect(self.createstepclass)
        # 3
        self.comboBox_clrramp_preset.currentIndexChanged.connect(self.loadMapRamp)
        # all
        self.pushButton_editcolorramp.clicked.connect(self.openColorRampDialog)

    def disconnectColorRampSignals(self):
        self.comboBox_levelstype.currentIndexChanged.disconnect(self.stackedWidget_colorramp.setCurrentIndex)
        self.comboBox_levelstype.currentIndexChanged.disconnect(self.colorRampChooserType)
        # 1
        # self.comboBox_clrgame.currentIndexChanged.disconnect(self.color_palette_changed_contour)
        self.comboBox_clrgame.currentIndexChanged.disconnect(self.color_palette_changed)
        self.comboBox_clrgame.currentIndexChanged.disconnect(self.comboBox_clrgame2.setCurrentIndex)
        self.checkBox_inverse_clr.stateChanged.disconnect(self.color_palette_changed)
        self.checkBox_inverse_clr2.setCheckState(self.checkBox_inverse_clr.checkState())
        self.comboBox_genericlevels.currentIndexChanged.disconnect(self.change_cmchoosergenericlvl)
        # 2
        self.comboBox_clrgame2.currentIndexChanged.disconnect(self.comboBox_clrgame.setCurrentIndex)
        self.checkBox_inverse_clr2.stateChanged.disconnect(self.color_palette_changed)
        self.checkBox_inverse_clr.setCheckState(self.checkBox_inverse_clr2.checkState())
        self.pushButton_createsteplevel.clicked.disconnect(self.createstepclass)
        # 3
        self.comboBox_clrramp_preset.currentIndexChanged.disconnect(self.loadMapRamp)
        # all
        self.pushButton_editcolorramp.clicked.disconnect(self.openColorRampDialog)

    def colorRampChooserType(self, item):
        """
        main chooser of color ramp type (predef, step, user defined)
        """
        if self.meshlayer.meshrenderer != None:
            if item == 0:
                if self.tabWidget_lvl_vel.currentIndex() == 0:  # contour
                    self.color_palette_changed(0)
                    self.meshlayer.meshrenderer.change_lvl_contour(
                        self.predeflevels[self.comboBox_genericlevels.currentIndex()][1]
                    )
                elif self.tabWidget_lvl_vel.currentIndex() == 1:  # velocity
                    self.color_palette_changed(0)
                    self.meshlayer.meshrenderer.change_lvl_vel(
                        self.predeflevels[self.comboBox_genericlevels.currentIndex()][1]
                    )
            elif item == 1:
                pass
            elif item == 2:
                self.loadMapRamp(self.comboBox_clrramp_preset.currentText())
            else:
                pass

    def change_cmchoosergenericlvl(self):
        """
        change levels of selafin layer when generics levels are changed
        """
        if self.meshlayer.meshrenderer != None:
            if self.tabWidget_lvl_vel.currentIndex() == 0:  # contour
                self.meshlayer.meshrenderer.change_lvl_contour(
                    self.predeflevels[self.comboBox_genericlevels.currentIndex()][1]
                )
            elif self.tabWidget_lvl_vel.currentIndex() == 1:  # velocity
                self.meshlayer.meshrenderer.change_lvl_vel(
                    self.predeflevels[self.comboBox_genericlevels.currentIndex()][1]
                )

    def createstepclass(self):
        """
        create steps classes and change levels of selafin layer when steps classes are changed
        """

        if self.lineEdit_levelmin.text() == "":
            zmin = min(
                self.meshlayer.hydrauparser.getValues(self.meshlayer.time_displayed)[self.meshlayer.param_displayed]
            )
            self.lineEdit_levelmin.setText(str(round(float(zmin), 3)))
        else:
            zmin = float(self.lineEdit_levelmin.text())
        if self.lineEdit_levelmax.text() == "":
            zmax = max(
                self.meshlayer.hydrauparser.getValues(self.meshlayer.time_displayed)[self.meshlayer.param_displayed]
            )
            self.lineEdit_levelmax.setText(str(round(float(zmax), 3)))
        else:
            zmax = float(self.lineEdit_levelmax.text())
        precision = len(str(float(self.lineEdit_levelstep.text())).split(".")[1])
        pdn = round(float(self.lineEdit_levelstep.text()) * 10 ** precision) / 10 ** precision
        zmin1 = zmin

        while zmin1 <= zmin:
            zmin1 = zmin1 + pdn
        zmin1 = zmin1 - pdn
        zmax1 = int(zmax) + 1
        while zmax1 >= zmax:
            zmax1 = zmax1 - pdn
        zmax1 = zmax1
        # Remplissage tableau
        temp = zmin1
        levels = [temp]
        while temp <= zmax1:
            temp = round(temp + pdn, precision)
            levels.append(temp)

        if self.meshlayer.meshrenderer != None:
            if self.tabWidget_lvl_vel.currentIndex() == 0:  # contour
                self.meshlayer.meshrenderer.change_lvl_contour(levels)
            elif self.tabWidget_lvl_vel.currentIndex() == 1:  # velocity
                self.meshlayer.meshrenderer.change_lvl_vel(levels)

    def color_palette_changed(self, int1=None, type=None):
        """
        change color map of selafin layer (matplotlib's style) when color palette combobox is changed
        """
        temp1 = QgsStyle.defaultStyle().colorRamp(self.comboBox_clrgame.currentText())

        inverse = self.checkBox_inverse_clr.isChecked()
        if self.meshlayer.meshrenderer != None:
            if type == None:
                if self.tabWidget_lvl_vel.currentIndex() == 0:  # contour
                    self.meshlayer.meshrenderer.color_palette_changed_contour(temp1, inverse)
                elif self.tabWidget_lvl_vel.currentIndex() == 1:  # velocity
                    self.meshlayer.meshrenderer.color_palette_changed_vel(temp1, inverse)
            else:
                if type == "contour":
                    self.meshlayer.meshrenderer.color_palette_changed_contour(temp1, inverse)
                elif type == "velocity":
                    self.meshlayer.meshrenderer.color_palette_changed_vel(temp1, inverse)

    def changeAlpha(self, nb):
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

        colors, levels = self.dlg_color.dialogIsFinished()

        if self.meshlayer.meshrenderer != None:
            if colors and levels:
                if self.tabWidget_lvl_vel.currentIndex() == 0:  # contour
                    # self.meshlayer.meshrenderer.cmap_mpl_contour_raw = self.meshlayer.meshrenderer.colormanager.arrayStepRGBAToCmap(colors)
                    # self.meshlayer.meshrenderer.cmap_mpl_contour_raw = colors
                    self.meshlayer.meshrenderer.cmap_contour_raw = colors
                    self.meshlayer.meshrenderer.change_lvl_contour(levels)
                elif self.tabWidget_lvl_vel.currentIndex() == 1:  # velocity
                    # self.meshlayer.meshrenderer.cmap_mpl_vel_raw = self.meshlayer.meshrenderer.colormanager.arrayStepRGBAToCmap(colors)
                    # self.meshlayer.meshrenderer.cmap_mpl_vel_raw = colors
                    self.meshlayer.meshrenderer.cmap_vel_raw = colors

                    self.meshlayer.meshrenderer.change_lvl_vel(levels)

    def saveMapRamp(self):
        """
        Save user defined color ramp on /config/"name"".clr
        """
        if self.meshlayer.meshrenderer != None:
            colors, levels = self.dlg_color.returnColorsLevels()
            self.meshlayer.meshrenderer.colormanager.saveClrColorRamp(
                self.dlg_color.lineEdit_name.text(), colors, levels
            )
            self.InitMapRamp()
            int2 = self.comboBox_clrramp_preset.findText(self.dlg_color.lineEdit_name.text())
            self.comboBox_clrramp_preset.setCurrentIndex(int2)

    def deleteMapRamp(self):
        """
        delete user defined color ramp
        """
        name = self.dlg_color.lineEdit_name.text()
        if self.comboBox_clrramp_preset.findText(name) > -1:
            path = os.path.join(self.posttelemacdir, name + ".clr")
            os.remove(path)
            self.dlg_color.close()
            self.InitMapRamp()

    def loadMapRamp(self, name, fullpath=False):
        """
        load clr file and apply it
        """

        if self.meshlayer.meshrenderer != None:

            if isinstance(name, int):
                name = self.comboBox_clrramp_preset.currentText()

            if fullpath:
                path = name
            else:
                path = os.path.join(self.posttelemacdir, str(name) + ".clr")
            if name:
                cmap, levels = self.meshlayer.meshrenderer.colormanager.readClrColorRamp(path)

                if cmap and levels:
                    if self.tabWidget_lvl_vel.currentIndex() == 0:  # contour
                        self.meshlayer.meshrenderer.cmap_contour_raw = cmap
                        self.meshlayer.meshrenderer.change_lvl_contour(levels)
                    elif self.tabWidget_lvl_vel.currentIndex() == 1:  # veolicty
                        self.meshlayer.meshrenderer.cmap_vel_raw = cmap
                        self.meshlayer.meshrenderer.change_lvl_vel(levels)

    def InitMapRamp(self):
        """
        Load user defined color ramp in user defined color ramp combobox
        """
        self.comboBox_clrramp_preset.clear()
        for file in os.listdir(self.posttelemacdir):
            if file.endswith(".clr") and file.split(".")[0]:
                self.comboBox_clrramp_preset.addItem(file.split(".")[0])

    # Display tools - velocity - user color ramp things ***********************************************

    def setVelocityRendererParams(self):
        """
        set parameters for velocity rendering in layer.showvelocityparams like this :
            [enabled Bool, type int , poinst step float , lenght of normal velocity float ]
        """
        if self.comboBox_viewer_arow.currentIndex() == 0:
            if self.comboBox_vel_method.currentIndex() == 0:
                self.meshlayer.showvelocityparams = {
                    "show": self.groupBox_schowvel.isChecked(),
                    "type": self.comboBox_vel_method.currentIndex(),
                    "step": self.spinBox_vel_relative.value(),
                    "norm": 1 / self.doubleSpinBox_vel_scale.value(),
                }
            elif self.comboBox_vel_method.currentIndex() == 1:
                self.meshlayer.showvelocityparams = {
                    "show": self.groupBox_schowvel.isChecked(),
                    "type": self.comboBox_vel_method.currentIndex(),
                    "step": self.doubleSpinBox_vel_spatial_step.value(),
                    "norm": 1 / self.doubleSpinBox_vel_scale.value(),
                }
            elif self.comboBox_vel_method.currentIndex() == 2:
                self.meshlayer.showvelocityparams = {
                    "show": self.groupBox_schowvel.isChecked(),
                    "type": self.comboBox_vel_method.currentIndex(),
                    "step": None,
                    "norm": 1 / self.doubleSpinBox_vel_scale.value(),
                }
        elif self.comboBox_viewer_arow.currentIndex() == 1:
            if self.comboBox_vel_method.currentIndex() == 0:
                self.meshlayer.showvelocityparams = {
                    "show": self.groupBox_schowvel.isChecked(),
                    "type": self.comboBox_vel_method.currentIndex(),
                    "step": self.spinBox_vel_relative.value(),
                    "norm": -self.doubleSpinBox_uniform_vel_arrow.value(),
                }
            elif self.comboBox_vel_method.currentIndex() == 1:
                self.meshlayer.showvelocityparams = {
                    "show": self.groupBox_schowvel.isChecked(),
                    "type": self.comboBox_vel_method.currentIndex(),
                    "step": self.doubleSpinBox_vel_spatial_step.value(),
                    "norm": -self.doubleSpinBox_uniform_vel_arrow.value(),
                }
            elif self.comboBox_vel_method.currentIndex() == 2:
                self.meshlayer.showvelocityparams = {
                    "show": self.groupBox_schowvel.isChecked(),
                    "type": self.comboBox_vel_method.currentIndex(),
                    "step": None,
                    "norm": -self.doubleSpinBox_uniform_vel_arrow.value(),
                }
        self.meshlayer.showVelocity()

    def populatecombobox_lvl(self):
        """
        Populate classes combobox on dialog creation
        """
        f = open(os.path.join(self.posttelemacdir, "classes.txt"), "r")
        for line in f:
            tabtemp = []
            for txt in line.split("=")[1].split("\n")[0].split(";"):
                tabtemp.append(float(txt))
            self.predeflevels.append([line.split("=")[0], tabtemp])
        for i in range(len(self.predeflevels)):
            self.comboBox_genericlevels.addItem(self.predeflevels[i][0])
        f.close()

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
        # tree widget
        self.treeWidget_parameters.clear()
        itms = []
        for i in range(len(self.meshlayer.hydrauparser.parametres)):
            itm = QTreeWidgetItem()
            itm.setText(0, str(self.meshlayer.hydrauparser.parametres[i][0]))
            itm.setText(1, str(self.meshlayer.hydrauparser.parametres[i][1]))
            itm.setText(2, str(self.meshlayer.hydrauparser.parametres[i][2]))
            if self.meshlayer.hydrauparser.parametres[i][4]:
                itm.setText(3, str(self.meshlayer.hydrauparser.parametres[i][4]))
            else:
                itm.setText(3, self.tr("Raw data"))
            itms.append(itm)
        self.treeWidget_parameters.addTopLevelItems(itms)

        if self.unloadtools:
            self.tableWidget_values.clearContents()
            self.tableWidget_values.setRowCount(len(self.meshlayer.hydrauparser.parametres))
            for i, param in enumerate(self.meshlayer.hydrauparser.parametres):
                self.tableWidget_values.setItem(i, 0, QTableWidgetItem(param[1]))
            self.tableWidget_values.setFixedHeight(
                (self.tableWidget_values.rowHeight(0) - 1) * (len(self.meshlayer.hydrauparser.parametres) + 1) + 1
            )

        self.updateparamsignal.emit()

    def populatecombobox_colorpalette(self):
        """
        Populate colorpalette combobox on dialog creation
        """
        style = QgsStyle.defaultStyle()
        rampIconSize = QSize(50, 20)
        for rampName in style.colorRampNames():
            ramp = style.colorRamp(rampName)
            icon = QgsSymbolLayerUtils.colorRampPreviewIcon(ramp, rampIconSize)
            self.comboBox_clrgame.addItem(icon, rampName)
            self.comboBox_clrgame2.addItem(icon, rampName)

    def changeMeshLayerRenderer(self, typerenderer):
        if typerenderer == 0:  # openGL
            QSettings().setValue("posttelemac/renderlib", "OpenGL")
            if self.meshlayer.hydraufilepath != None:
                self.meshlayer.load_selafin(self.meshlayer.hydraufilepath, self.meshlayer.hydrauparser.SOFTWARE)
        elif typerenderer == 1:  # matplotlib
            QSettings().setValue("posttelemac/renderlib", "MatPlotLib")
            if self.meshlayer.hydraufilepath != None:
                self.meshlayer.load_selafin(self.meshlayer.hydraufilepath, self.meshlayer.hydrauparser.SOFTWARE)

    # ****************************************************************************************************
    # ************translation  / general method                                      ***********************************
    # ****************************************************************************************************

    def tr(self, message):
        """Used for translation"""
        # if False:
        # try:
        # return QCoreApplication.translate(
        # "PostTelemacPropertiesDialog", message, None, QApplication.UnicodeUTF8
        # )
        # except Exception as e:
        # return message
        if True:
            return message

    def getTreeWidgetSelectedIndex(self, widget):
        """"""
        getSelected = widget.selectedItems()
        if getSelected:
            baseNode = getSelected[0]
            position = [widget.indexFromItem(baseNode).parent().row(), widget.indexFromItem(baseNode).row()]
            return position
        else:
            return [-1, 0]

    def setTreeWidgetIndex(self, widget, pos0, pos1):
        """"""
        widget.scrollToItem(widget.topLevelItem(pos1))
        widget.setCurrentItem(widget.topLevelItem(pos1))
        try:
            widget.setItemSelected(widget.topLevelItem(pos1), True)
        except:
            widget.topLevelItem(pos1).setSelected(True)

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

        # enable veolocity tool if velocity u and v are present in parser params
        if self.meshlayer.hydrauparser.parametrevx == None or self.meshlayer.hydrauparser.parametrevy == None:
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
