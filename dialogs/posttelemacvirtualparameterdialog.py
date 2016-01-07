# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Telemac2ContoursDialog
                                 A QGIS plugin
 Création de contours à partir d'un fichier TELEMAC
                             -------------------
        begin                : 2015-05-27
        git sha              : $Format:%H$
        copyright            : (C) 2015 by ARTELIA Eau & Environnement
        email                : adlane.rebai@arteliagroup.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

#from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, SIGNAL, QObject, QSize
from PyQt4.QtCore import *
from PyQt4.QtGui import QAction, QIcon, QPixmap, QTreeWidgetItem, QListWidgetItem, QStandardItem, QStandardItemModel, QDialog
from qgis.gui import QgsGenericProjectionSelector
from qgis.core import QgsApplication
import os.path
import os
import decimal
import copy
import pickle

#from classes_valeurs import ClassesValeursDialog
from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__),'..', 'ui', 'def_variable.ui'))

class DefVariablesDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, lst_param, lst_var, parent=None):
        """Constructor."""
        super(DefVariablesDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.setFixedSize(400, 475)

        #icTool = QIcon(os.path.dirname(os.path.realpath(__file__)) + "\\icones\\btn_tools.png")
        #self.btn_open_classe.setIcon(icTool)

        lst_fn = ["+","-","*","/","**","abs()", "cos()", "int()", "sin()"]

        self.tab_variables.itemDoubleClicked.connect(self.add_variable)
        self.lst_fonctions.doubleClicked.connect(self.add_fonction)
        self.txt_nom_variable.textEdited.connect(self.active_bb_valide)
        self.txt_formule.textChanged.connect(self.active_bb_valide)
        self.finished.connect(self.dialogIsFinished)

        self.tab_variables.headerItem().setText(0, "Pos")
        self.tab_variables.headerItem().setText(1, "Nom")
        self.tab_variables.resizeColumnToContents(0)

        self.fill_tab(self.tab_variables, lst_var)
        self.fill_list(self.lst_fonctions, lst_fn)
        #self.init_cb_classe("")

        self.txt_nom_variable.setText(lst_param[0])
        self.txt_formule.setText(lst_param[1])

        self.active_bb_valide()
        
    def open_gestion_classe(self):
        self.dlg_cv = ClassesValeursDialog()
        self.dlg_cv.setWindowModality(2)
        self.dlg_cv.setAttribute(Qt.WA_DeleteOnClose, True)
        self.dlg_cv.exec_()
        self.init_cb_classe(self.cb_classe.currentText())
        
    def dialogIsFinished(self):
        if (self.result() == 1):
            new_var = {}
            new_var["nom"] = self.txt_nom_variable.text()
            new_var["formule"] = self.txt_formule.toPlainText()
            #new_var["classe"] = self.cb_classe.currentText()
            #return (new_var) 
            return [self.txt_nom_variable.text(),self.txt_formule.toPlainText() ]
        
    def init_cb_classe(self, txt):
        idx = 0
        self.cb_classe.clear()
        
        with open(os.path.dirname(os.path.realpath(__file__)) + '\\classes','rb') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            self.classe_val = mon_depickler.load()
            temp = sorted(self.classe_val)
            for i, t in enumerate(temp):
                self.cb_classe.addItem(t)
                if txt == t:
                    idx = i

        self.cb_classe.setCurrentIndex(idx)

    def aff_classe(self, l):
        if l != -1:
            nom_classe = self.cb_classe.itemText(l)
            self.lbl_classe.setText(str(self.classe_val[nom_classe]))

            
    def fill_list(self, name_list, lst_var):

        model = QStandardItemModel(name_list)
        for i, elt in enumerate(lst_var):
            item = QStandardItem(str(elt))
            item.setEditable(False)
            model.appendRow(item)
        name_list.setModel(model)
        

    def fill_tab(self, name_list, lst_var):
        itms = []
        for elt in lst_var:
            itm = QTreeWidgetItem()
            itm.setText(0, str(elt[0]))
            itm.setText(1, elt[1])
            itms.append(itm)

        name_list.addTopLevelItems(itms)


    def add_variable(self, itm, c):
        txt = "V" + itm.text(0)
        self.txt_formule.insertPlainText(txt)
        self.txt_formule.setFocus()

 
    def add_fonction(self, itm):
        item = self.lst_fonctions.model().item(itm.row())
        txt = item.text()
        
        txtCurs =  self.txt_formule.textCursor()
        
        if txtCurs.hasSelection():
            txt = txt.replace("()", "(" + txtCurs.selectedText() + ")")
            self.txt_formule.insertPlainText(txt)
        else :
            self.txt_formule.insertPlainText(txt)
            if txt[-1] == ')':
                self.txt_formule.moveCursor(7,0)
            
        self.txt_formule.setFocus()


    def active_bb_valide(self):
        if ((self.txt_formule.toPlainText()=="") or (self.txt_nom_variable.text()=="")):
            self.bb_valide.button(self.bb_valide.Ok).setEnabled(False)
        else:
            self.bb_valide.button(self.bb_valide.Ok).setEnabled(True)
