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
# unicode behaviour
from __future__ import unicode_literals

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "XY_translation_dialog.ui"))


class xyTranslationDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(xyTranslationDialog, self).__init__(parent)
        self.setupUi(self)
        self.xtranslate = None
        self.ytranslate = None

        self.finished.connect(self.dialogIsFinished)

    def setXandY(self, xtranslate=0, ytranslate=0):
        self.xtranslate = xtranslate
        self.ytranslate = ytranslate
        self.doubleSpinBox_x.setValue(self.xtranslate)
        self.doubleSpinBox_y.setValue(self.ytranslate)

    def dialogIsFinished(self):
        """
        return level list
        return color array like this : [stop in 0 < stop > 1 ,r,g,b]
        """
        if self.result() == 1:
            self.xtranslate = self.doubleSpinBox_x.value()
            self.ytranslate = self.doubleSpinBox_y.value()
            return (self.xtranslate, self.ytranslate)
        else:
            return (None, None)
