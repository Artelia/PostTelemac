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


from PyQt4 import uic, QtCore, QtGui
from meshlayer_abstract_tool import *
import qgis

import matplotlib
import numpy as np
from ..meshlayerparsers.posttelemac_selafin_parser import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'CompareTool.ui'))



class CompareTool(AbstractMeshLayerTool,FORM_CLASS):

    def __init__(self, meshlayer,dialog):
        AbstractMeshLayerTool.__init__(self,meshlayer,dialog)
        self.compareprocess = None
        
        
        self.writeSelafinCaracteristics(self.textEdit_2,self.meshlayer.hydrauparser)
        self.pushButton_8.clicked.connect(self.initCompare)
        self.checkBox_6.stateChanged.connect(self.compare1)
        self.comboBox_compare_method.currentIndexChanged.connect(self.compare1)
        
        self.propertiesdialog.meshlayerschangedsignal.connect(self.layerChanged)
        
#*********************************************************************************************
#***************Imlemented functions  **********************************************************
#********************************************************************************************
        
    def initTool(self):
        self.setupUi(self)
        self.iconpath = os.path.join(os.path.dirname(__file__),'..','icons','tools','Files_Copy.png' )
        

        

    def onActivation(self):
        """Click on temopral graph + temporary point selection method"""            
        pass
        
        
    def onDesactivation(self):
        pass
            

    def initCompare(self):
        self.checkBox_6.setCheckState(0)
        #file to compare choice
        str1 = self.tr("Selafin file chooser")
        str2 = self.tr("Telemac files")
        str3 = self.tr("All files")  
        fname = self.propertiesdialog.qfiledlg.getOpenFileName(None,str1,self.propertiesdialog.loaddirectory, str2 + " (*.res *.geo *.init *.slf);;" + str3 + " (*)")
        #Things
        if fname:
            #update dialog
            self.reset_dialog()
            self.lineEdit_5.setText(fname)
            #Launch thread
            self.checkBox_6.setEnabled(False)
            self.compareselafin()
            #self.writeSelafinCaracteristics(self.textEdit_3,self.postutils.compareprocess.hydrauparsercompared)
            self.writeSelafinCaracteristics(self.textEdit_3,self.compareprocess.hydrauparsercompared)
    
    def reset_dialog(self):
        #self.textEdit_2.clear()
        self.textEdit_3.clear()
        self.lineEdit_5.clear()
        self.lineEdit.clear()
        self.checkBox_6.setCheckState(0)
        self.checkBox_6.setEnabled(False)
        
    

        
    def writeSelafinCaracteristics(self,textedit,hydrauparser):
        textedit.setText('')
        """
        for var in hydrauparser.getVarnames():
            textedit.append(var)
        """
        if hydrauparser != None:
            for var in hydrauparser.parametres:
                textedit.append(str(var[0]) + ' : ' + str(var[1]))
            
            textedit.append("nombre d elements : "+str(len(hydrauparser.getValues(0)[0])))
            
    def layerChanged(self):
        self.writeSelafinCaracteristics(self.textEdit_2,self.meshlayer.hydrauparser)
        if self.compareprocess is not None:
            self.reset_dialog()
            self.compareprocess = None
        
        
    #****************************************************************************************************
    #************* Tools - compare***********************************************************
    #****************************************************************************************************
    
    def compareselafin(self):
        self.compareprocess = getCompareValue(self.meshlayer,self)
        self.getCorrespondingParameters()
        self.checkBox_6.setEnabled(True)
        
        
    def getCorrespondingParameters(self):
        if False:
            for var in self.selafinlayer.hydrauparser.parametres:
                for param in self.compareprocess.hydrauparsercompared.getVarnames() :
                    if var[1] in param.strip()  :
                        self.selafinlayer.hydrauparser.parametres[var[0]][3] = self.compareprocess.hydrauparsercompared.getVarnames().index(param)
                        break
                    else:
                        self.selafinlayer.hydrauparser.parametres[var[0]][3] = None
            self.selafinlayer.propertiesdialog.lineEdit.setText(str([[param[0],param[3]] for param in self.selafinlayer.hydrauparser.parametres]))
        else:
            for var in self.meshlayer.hydrauparser.parametres:
                for param in self.compareprocess.hydrauparsercompared.parametres :
                    if var[1] == param[1]  :
                        self.meshlayer.hydrauparser.parametres[var[0]][3] = param[0]
                        break
                    else:
                        self.meshlayer.hydrauparser.parametres[var[0]][3] = None
            self.lineEdit.setText(str([[param[0],param[3]] for param in self.meshlayer.hydrauparser.parametres]))
        
    def reinitCorrespondingParameters(self):
        for i, var in enumerate(self.meshlayer.hydrauparser.parametres):
                self.meshlayer.hydrauparser.parametres[i][3] = i
                
                
        
    def compare1(self,int1):
        # selafinlayer
        try:
            #if int1 == 2 :
            if self.checkBox_6.checkState() == 2 :
                self.getCorrespondingParameters()
                #change signals
                try:
                    self.meshlayer.updatevalue.disconnect(self.meshlayer.updateSelafinValues1)
                    self.meshlayer.updatevalue.connect(self.compareprocess.updateSelafinValue)
                except Exception, e:
                    pass
                #self.initclassgraphtemp.compare = True
                self.meshlayer.triinterp = None
                #desactive non matching parameters
                for i in range(len(self.meshlayer.hydrauparser.parametres)):
                    if self.meshlayer.hydrauparser.parametres[i][3] == None:
                        self.propertiesdialog.treeWidget_parameters.topLevelItem(i).setFlags(Qt.ItemIsSelectable)
                self.compareprocess.comparetime = None
                self.meshlayer.forcerefresh = True
                self.meshlayer.updateSelafinValues()
                self.meshlayer.triggerRepaint()
            elif self.checkBox_6.checkState() == 0 :
                #change signals
                try:
                    self.meshlayer.updatevalue.disconnect(self.compareprocess.updateSelafinValue)
                    self.meshlayer.updatevalue.connect(self.meshlayer.updateSelafinValues1)
                except Exception, e:
                    pass
                #self.initclassgraphtemp.compare = False
                self.meshlayer.triinterp = None
                self.meshlayer.forcerefresh = True
                self.reinitCorrespondingParameters()
                self.propertiesdialog.populatecombobox_param()
                self.propertiesdialog.setTreeWidgetIndex(self.propertiesdialog.treeWidget_parameters,0,self.meshlayer.param_displayed)
                self.meshlayer.updateSelafinValues()
                self.meshlayer.triggerRepaint()
        except Exception, e:
            print str(e)

            
            
            
            
            
            
            
class getCompareValue(QtCore.QObject):

    def __init__(self,layer,tool):
        QtCore.QObject.__init__(self)
        self.layer = layer
        self.tool = tool
        #self.slf1 = layer.slf
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.toPlainText())
        #self.slf2 = SELAFIN(layer.propertiesdialog.lineEdit_5.text())
        self.hydrauparsercompared = PostTelemacSelafinParser()
        self.hydrauparsercompared.loadHydrauFile(self.tool.lineEdit_5.text())
        self.hydrauparsercompared.setXYTranslation(self.layer.hydrauparser.translatex, self.layer.hydrauparser.translatey)
        
        
        
        
        #layer.compare = True
        
        #layer.updatevalue.connect(self.updateSelafinValue)
        self.triinterp=None
        #self.comparetime = None
        self.values = None
        #self.transmitvalues = False
        #self.var_corresp = var_corresp

                
        
    def oppositeValues(self):
        self.values = -self.values
        
    def updateSelafinValue(self,onlyparamtimeunchanged = -1):
        temp1 = []
        lenvarnames = len(self.layer.hydrauparser.parametres)
        meshx1,meshy1 = self.layer.hydrauparser.getMesh()
        ikle1 = self.layer.hydrauparser.getIkle()
        meshx2,meshy2 = self.hydrauparsercompared.getMesh()
        ikle2 = self.hydrauparsercompared.getIkle()


        try:
            #desactive non matching parameters
            if onlyparamtimeunchanged < 0 : 
                if (np.array_equal(ikle1 , ikle2) 
                    and np.array_equal(meshx1 , meshx2) 
                    and np.array_equal(meshy1 , meshy2)):
                    
                    #self.status.emit("fichiers identiques ")
                    self.layer.propertiesdialog.textBrowser_2.append("fichiers identiques ")
                    valuetab = []
                    for i in range(lenvarnames):
                        if self.layer.hydrauparser.parametres[i][3] is not None :
                            value = self.hydrauparsercompared.getValues(self.layer.time_displayed)[self.layer.hydrauparser.parametres[i][3]] - self.layer.hydrauparser.getValues(self.layer.time_displayed)[i]
                        else:
                            value = [np.nan]*len(meshx1)
                            value = np.array(value).transpose()
                        valuetab.append(value)
                    self.values = np.array(valuetab)
                    
                    if self.tool.comboBox_compare_method.currentIndex() == 1:
                        self.oppositeValues()
                    

                else:
                    #self.status.emit("fichiers non egaux")
                    self.layer.propertiesdialog.textBrowser_2.append("fichiers non egaux")

                    #projection of slf2 to slf1
                    #triinterp
                    triang = matplotlib.tri.Triangulation(meshx2,meshy2,np.array(ikle2))
                    self.triinterp = []
                    for i in range(lenvarnames):
                        if self.layer.hydrauparser.parametres[i][3] is not None:
                            self.triinterp.append(matplotlib.tri.LinearTriInterpolator(triang, self.hydrauparsercompared.getValues(self.layer.time_displayed)[self.layer.hydrauparser.parametres[i][3]]))
                        else:
                            self.triinterp.append(None)
                    valuesslf2 = []
                    count = self.layer.hydrauparser.pointcount
                    #projection for matching parameters
                    tabtemp=[]
                    for  j in range(lenvarnames):
                        if self.layer.hydrauparser.parametres[j][3] is not None:
                            tabtemp = self.triinterp[j].__call__(meshx1,meshy1)
                        else:
                            tabtemp = np.array([np.nan]*count)
                            tabtemp = tabtemp.transpose()
                        valuesslf2.append(tabtemp)
                    temp1 = valuesslf2 - self.layer.hydrauparser.getValues(self.layer.time_displayed)
                    self.values = np.nan_to_num(temp1)
                    
                    if self.tool.comboBox_compare_method.currentIndex() == 1:
                        self.oppositeValues()
                        
                        
                self.layer.values = self.values
                self.layer.value = self.values[self.layer.param_displayed]
            else:
                self.layer.value = self.values[self.layer.param_displayed]
                

                
        except Exception, e:
            print str("updateSelafinValue :"+str(e))
            #self.status.emit("updateSelafinValue :"+str(e))
            self.values = None
            #self.finished.emit()
                

        #self.comparetime = self.layer.time_displayed

