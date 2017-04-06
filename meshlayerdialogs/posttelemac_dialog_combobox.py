# -*- coding: utf-8 -*-
"""
/***************************************************************************
Layer to labeled layer
                                 A QGIS plugin
Make it possible to use data-defined labeling on existing layer.
The plug-in creates new attributes in the existing shapefile.
                             -------------------
        begin                : 2012-11-01
        copyright            : (C) 2012 by Victor Axbom
        email                : -
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         * 
 *   This program is distributed in the hope that it will be useful,       *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU General Public License for more details.                          *
 *                                                                         *
 *   You should have received a copy of the GNU General Public License     *
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>. *
 *                                                                         *
 ***************************************************************************/
"""
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
"""
from  qgis.PyQt import QtCore, QtGui, uic
try:        #qt4
    from qgis.PyQt.QtGui import QDialog, QComboBox, QVBoxLayout, QDialogButtonBox, QLabel
except:     #qt5
    from qgis.PyQt.QtWidgets import  QDialog, QComboBox, QVBoxLayout, QDialogButtonBox, QLabel
import os
from qgis.core import *


class postTelemacComboboxDialog(QDialog):
    
    def __init__(self,  parent = None):
        super(postTelemacComboboxDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        #self.setupUi(self)
        self.layout = QVBoxLayout()
        self.label = QLabel()
        self.combobox = QComboBox()
        self.dlgbuttonbox = QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.combobox)
        self.layout.addWidget(self.dlgbuttonbox)
        self.setLayout(self.layout)
        
        self.dlgbuttonbox.accepted.connect(self.accept)
        self.dlgbuttonbox.rejected.connect(self.reject)
        
        #self.loadvalues(ldp)
        
    def loadValues(self,ldp):

        self.combobox.clear()
        self.combobox.addItems(ldp)
