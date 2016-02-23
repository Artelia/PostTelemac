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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.gui import *
from qgis.core import *
from PyQt4 import QtGui, uic

import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__),'..', 'ui', 'usercolorramp.ui'))

class UserColorRampDialog(QtGui.QDialog, FORM_CLASS):

    def __init__(self, selafinlayer, parent=None):
        """Constructor."""
        super(UserColorRampDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.finished.connect(self.dialogIsFinished)
        self.selafinlayer = selafinlayer
        self.populateDialog()
        if self.selafinlayer.propertiesdialog.comboBox_levelstype.currentIndex() == 2 :
            self.lineEdit_name.setText(self.selafinlayer.propertiesdialog.comboBox_clrramp_preset.currentText())
        #Connecting signals
        self.lineEdit_name.textEdited.connect(self.active_bb_valide)
        self.pushButton_add.clicked.connect(self.addrow)
        self.pushButton_remove.clicked.connect(self.removerow)
        self.tableWidget.cellChanged.connect(self.checkUpperLower)
        self.pushButton_3.clicked.connect(self.saveMapRamp)
        self.pushButton_4.clicked.connect(self.deleteMapRamp)
        
        #end
        self.active_bb_valide()
        
        
    def populateDialog(self):
        self.tableWidget.setRowCount(len(self.selafinlayer.lvl_contour)-1)
        for i in range(len(self.selafinlayer.lvl_contour)-1):
            colorwdg = QgsColorButtonV2()
            colorwdg.setColor(QColor(self.selafinlayer.color_mpl_contour[i][0]*255,self.selafinlayer.color_mpl_contour[i][1]*255,self.selafinlayer.color_mpl_contour[i][2]*255))
            self.tableWidget.setCellWidget(i,0,colorwdg)
            self.tableWidget.setItem(i, 1, QtGui.QTableWidgetItem(str(self.selafinlayer.lvl_contour[i])))
            self.tableWidget.setItem(i, 2, QtGui.QTableWidgetItem(str(self.selafinlayer.lvl_contour[i+1])))
            
    def addrow(self):
        introw = self.tableWidget.currentRow()
        self.tableWidget.insertRow(introw+1)
        colorwdg = QgsColorButtonV2()
        self.tableWidget.setCellWidget(introw+1,0,colorwdg)
        self.tableWidget.setItem(introw+1, 1, QtGui.QTableWidgetItem(self.tableWidget.item(introw,2)))
        self.tableWidget.setItem(introw+1, 2, QtGui.QTableWidgetItem(self.tableWidget.item(introw+2,1)))
        
        
    def removerow(self):
        introw = self.tableWidget.currentRow()
        self.tableWidget.removeRow(introw)
        if  introw != 0 and  introw != (self.tableWidget.rowCount()):
            self.tableWidget.setItem(introw, 1, QtGui.QTableWidgetItem(self.tableWidget.item(introw-1,2)))
        
        
    def checkUpperLower(self, row,column):
        try:
            self.tableWidget.cellChanged.disconnect(self.checkUpperLower)
        except Excetion, e:
            pass
        if column == 1:
            self.tableWidget.setItem(row-1, 2, QtGui.QTableWidgetItem(self.tableWidget.item(row,column)))
        elif column == 2:
            self.tableWidget.setItem(row+1, 1, QtGui.QTableWidgetItem(self.tableWidget.item(row,column)))
        
        self.tableWidget.cellChanged.connect(self.checkUpperLower)
        
        
     
            
    def dialogIsFinished(self):
        """
        return level list
        return color array like this : [stop in 0 < stop > 1 ,r,g,b]
        """
        if (self.result() == 1):
            colors, levels = self.returnColorsLevels()
            return (colors,levels)
        else:
            return (None,None)
            
    def returnColorsLevels(self):
        colors = []
        levels=[]
        rowcount = self.tableWidget.rowCount()
        for i in range(rowcount):
            levels.append(float(self.tableWidget.item(i,1).text()))
            wdg = self.tableWidget.cellWidget(i,0)
            colors.append([float(float(i)/(rowcount-1)),wdg.color().red(),wdg.color().green(),wdg.color().blue(),wdg.color().alpha()])

        levels.append(float(self.tableWidget.item(rowcount-1,2).text()))
        return (colors,levels)
        
            
    def saveMapRamp(self):
        self.selafinlayer.propertiesdialog.saveMapRamp()
        
    def deleteMapRamp(self):
        self.selafinlayer.propertiesdialog.deleteMapRamp()

        
    def active_bb_valide(self):
        if  (self.lineEdit_name.text()==""):
            self.pushButton_3.setEnabled(False)
            self.pushButton_4.setEnabled(False)
            #self.bb_valide.button(self.bb_valide.Ok).setEnabled(False)
        else:
            #self.bb_valide.button(self.bb_valide.Ok).setEnabled(True)
            self.pushButton_3.setEnabled(True)
            self.pushButton_4.setEnabled(True)