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
#unicode behaviour
from __future__ import unicode_literals
from PyQt4 import uic, QtGui
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__),'..', 'ui', 'about.ui'))

class aboutDialog(QtGui.QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(aboutDialog, self).__init__(parent)
        self.setupUi(self)