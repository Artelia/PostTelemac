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

from __future__ import unicode_literals

from qgis.PyQt import uic
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QWidget, QTreeWidgetItem

import os


class AbstractMeshLayerTool(QWidget):

    SOFTWARE = []

    def __init__(self, meshlayer, dialog, parent=None):
        super(AbstractMeshLayerTool, self).__init__(parent)
        self.meshlayer = meshlayer
        self.propertiesdialog = dialog
        self.widgetindex = None
        self.iconpath = None
        self.initTool()
        self.loadWidget()

    def initTool(self):
        """
        Load widget and icons and init things
        must contain :
            self.setupUi(self)
            self.iconpath = '...path to icon...'
        """
        pass

    def onActivation(self):
        pass

    def onDesactivation(self):
        pass

    def loadWidget(self):
        name = self.objectName()
        arb = name.split("_")
        self.qtreewidgetitem = QTreeWidgetItem()
        self.qtreewidgetitem.setText(0, arb[-1])
        if self.iconpath != None:
            self.qtreewidgetitem.setIcon(0, QIcon(self.iconpath))

        if arb[0] == "Main":
            root = self.propertiesdialog.treeWidget_utils.invisibleRootItem()
            child_count = root.childCount()

            if child_count == 0:
                self.propertiesdialog.treeWidget_utils.addTopLevelItems([self.qtreewidgetitem])
            else:
                for i in range(child_count):
                    item = root.child(i)
                    if item.childCount() > 0:
                        self.propertiesdialog.treeWidget_utils.insertTopLevelItems(i, [self.qtreewidgetitem])
                        break
                    if i == child_count - 1:
                        self.propertiesdialog.treeWidget_utils.insertTopLevelItems(i, [self.qtreewidgetitem])

        else:
            wdgitem = None
            root = self.propertiesdialog.treeWidget_utils.invisibleRootItem()
            child_count = root.childCount()
            for i in range(child_count):
                item = root.child(i)
                if item.text(0) == arb[0]:
                    wdgitem = item
                    break

            if wdgitem is None:
                wdgitem = QTreeWidgetItem()
                wdgitem.setText(0, arb[0])
                self.propertiesdialog.treeWidget_utils.addTopLevelItems([wdgitem])

            wdgitem.addChild(self.qtreewidgetitem)
            wdgitem.setExpanded(True)

        self.propertiesdialog.stackedWidget.addWidget(self)

        self.widgetindex = self.propertiesdialog.stackedWidget.indexOf(self)

        # connect signals
        self.propertiesdialog.treeWidget_utils.itemClicked.connect(self.onClickRaw)
        self.propertiesdialog.tabWidget.currentChanged.connect(self.onClickRaw)

    def onClickRaw(self, param1, param2=None):
        """
        Mangage the activation of tool when tool's icon is clicked
        """
        if isinstance(param1, QTreeWidgetItem):  # signal from treeWidget_utils
            if param1 == self.qtreewidgetitem:
                self.propertiesdialog.stackedWidget.setCurrentWidget(self)
                self.onActivation()
            else:
                self.onDesactivation()
        elif isinstance(param1, int):  # signal from tabWidget
            if self.propertiesdialog.tabWidget.widget(param1).objectName() == "Toolstab":
                if self.propertiesdialog.treeWidget_utils.currentItem() == self.qtreewidgetitem:
                    self.onActivation()
            else:
                self.onDesactivation()
