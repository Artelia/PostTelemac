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
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem

from qgis.gui import QgsColorButton

import os
import sys

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "usercolorramp.ui"))


class UserColorRampDialog(QDialog, FORM_CLASS):
    def __init__(self, selafinlayer, parent=None):
        """Constructor."""
        super(UserColorRampDialog, self).__init__(parent)
        self.setupUi(self)
        self.finished.connect(self.dialogIsFinished)
        self.meshlayer = selafinlayer
        self.populateDialog()
        if self.meshlayer.propertiesdialog.comboBox_levelstype.currentIndex() == 2:
            self.lineEdit_name.setText(self.meshlayer.propertiesdialog.comboBox_clrramp_preset.currentText())
        # Connecting signals
        self.lineEdit_name.textEdited.connect(self.active_bb_valide)
        self.pushButton_add.clicked.connect(self.addrow)
        self.pushButton_remove.clicked.connect(self.removerow)
        self.tableWidget.cellChanged.connect(self.checkUpperLower)
        self.pushButton_3.clicked.connect(self.saveMapRamp)
        self.pushButton_4.clicked.connect(self.deleteMapRamp)

        # end
        self.active_bb_valide()

    def populateDialog(self):
        if self.meshlayer.propertiesdialog.tabWidget_lvl_vel.currentIndex() == 0:  # contour
            self.tableWidget.setRowCount(len(self.meshlayer.meshrenderer.lvl_contour) - 1)
            for i in range(len(self.meshlayer.meshrenderer.lvl_contour) - 1):
                colorwdg = QgsColorButton()
                colorwdg.setAllowOpacity(True)
                colorwdg.setColor(
                    QColor(
                        int(self.meshlayer.meshrenderer.cmap_contour_leveled[i][0] * 255),
                        int(self.meshlayer.meshrenderer.cmap_contour_leveled[i][1] * 255),
                        int(self.meshlayer.meshrenderer.cmap_contour_leveled[i][2] * 255),
                        int(self.meshlayer.meshrenderer.cmap_contour_leveled[i][3] * 255),
                    )
                )
                self.tableWidget.setCellWidget(i, 0, colorwdg)
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(self.meshlayer.meshrenderer.lvl_contour[i])))
                self.tableWidget.setItem(i, 2, QTableWidgetItem(str(self.meshlayer.meshrenderer.lvl_contour[i + 1])))
        elif self.meshlayer.propertiesdialog.tabWidget_lvl_vel.currentIndex() == 1:  # velocity
            self.tableWidget.setRowCount(len(self.meshlayer.meshrenderer.lvl_vel) - 1)
            for i in range(len(self.meshlayer.meshrenderer.lvl_vel) - 1):
                colorwdg = QgsColorButton()
                colorwdg.setAllowAlpha(True)
                colorwdg.setColor(
                    QColor(
                        int(self.meshlayer.meshrenderer.cmap_vel_leveled[i][0] * 255),
                        int(self.meshlayer.meshrenderer.cmap_vel_leveled[i][1] * 255),
                        int(self.meshlayer.meshrenderer.cmap_vel_leveled[i][2] * 255),
                        int(self.meshlayer.meshrenderer.cmap_vel_leveled[i][3] * 255),
                    )
                )
                self.tableWidget.setCellWidget(i, 0, colorwdg)
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(self.meshlayer.meshrenderer.lvl_vel[i])))
                self.tableWidget.setItem(i, 2, QTableWidgetItem(str(self.meshlayer.meshrenderer.lvl_vel[i + 1])))

    def addrow(self):
        introw = self.tableWidget.currentRow()
        self.tableWidget.insertRow(introw + 1)
        colorwdg = QgsColorButton()
        self.tableWidget.setCellWidget(introw + 1, 0, colorwdg)
        self.tableWidget.setItem(introw + 1, 1, QTableWidgetItem(self.tableWidget.item(introw, 2)))
        self.tableWidget.setItem(introw + 1, 2, QTableWidgetItem(self.tableWidget.item(introw + 2, 1)))

    def removerow(self):
        introw = self.tableWidget.currentRow()
        self.tableWidget.removeRow(introw)
        if introw != 0 and introw != (self.tableWidget.rowCount()):
            self.tableWidget.setItem(introw, 1, QTableWidgetItem(self.tableWidget.item(introw - 1, 2)))

    def checkUpperLower(self, row, column):
        try:
            self.tableWidget.cellChanged.disconnect(self.checkUpperLower)
        except Exception as e:
            pass
        if column == 1:
            self.tableWidget.setItem(row - 1, 2, QTableWidgetItem(self.tableWidget.item(row, column)))
        elif column == 2:
            self.tableWidget.setItem(row + 1, 1, QTableWidgetItem(self.tableWidget.item(row, column)))

        self.tableWidget.cellChanged.connect(self.checkUpperLower)

    def dialogIsFinished(self):
        """
        return level list
        return color array like this : [stop in 0 < stop > 1 ,r,g,b,alpha]
        """
        if self.result() == 1:
            colors, levels = self.returnColorsLevels()
            return (colors, levels)
        else:
            return (None, None)

    def returnColorsLevels(self):
        colors = []
        levels = []
        rowcount = self.tableWidget.rowCount()
        if rowcount > 1:
            for i in range(rowcount):
                levels.append(float(self.tableWidget.item(i, 1).text()))
                wdg = self.tableWidget.cellWidget(i, 0)
                colors.append(
                    [
                        float(float(i) / (rowcount - 1)),
                        wdg.color().red(),
                        wdg.color().green(),
                        wdg.color().blue(),
                        wdg.color().alpha(),
                    ]
                )
        else:
            levels.append(float(self.tableWidget.item(0, 1).text()))
            wdg = self.tableWidget.cellWidget(0, 0)
            colors.append([0.0, wdg.color().red(), wdg.color().green(), wdg.color().blue(), wdg.color().alpha()])
            colors.append([1.0, wdg.color().red(), wdg.color().green(), wdg.color().blue(), wdg.color().alpha()])

        levels.append(float(self.tableWidget.item(rowcount - 1, 2).text()))
        return (colors, levels)

    def saveMapRamp(self):
        self.meshlayer.propertiesdialog.saveMapRamp()

    def deleteMapRamp(self):
        self.meshlayer.propertiesdialog.deleteMapRamp()

    def active_bb_valide(self):
        if self.lineEdit_name.text() == "":
            self.pushButton_3.setEnabled(False)
            self.pushButton_4.setEnabled(False)
        else:
            self.pushButton_3.setEnabled(True)
            self.pushButton_4.setEnabled(True)
