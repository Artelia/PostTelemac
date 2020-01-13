# -*- coding: utf-8 -*-

import os
import sys
import qgis
import qgis.gui
import qgis.utils
from qgis.PyQt import uic, QtCore


try:
    from qgis.PyQt.QtGui import (QWidget,QDialog,QMainWindow)
except ImportError:
    from qgis.PyQt.QtWidgets import (QWidget,QDialog,QMainWindow)

from PostTelemac.meshlayer.post_telemac_pluginlayer import SelafinPluginLayer
from PostTelemac.meshlayer.post_telemac_pluginlayer_type import SelafinPluginLayerType


class Test(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.wind = None

    def launchTest(self):

        try:
            qgisversion_int = qgis.utils.QGis.QGIS_VERSION_INT
        except AttributeError:  #qgis 3
            qgisversion_int = qgis.utils.Qgis.QGIS_VERSION_INT
        #print(qgisversion_int)

        if int(str(qgisversion_int)[0:3]) < 220:
            qgis_path = "C://OSGeo4W64//apps//qgis-ltr"
        else:
            qgis_path = "C://Program Files//OSGeo4W64-310//apps//qgis"
            #os.environ["QT_QPA_PLATFORM"] = "offscreen"

        # qgis_path = "C://OSGeo4W64//apps//qgis-ltr"
        app = qgis.core.QgsApplication([], True)
        qgis.core.QgsApplication.setPrefixPath(qgis_path, True)
        qgis.core.QgsApplication.initQgis()
        self.canvas = qgis.gui.QgsMapCanvas()
        self.canvas.enableAntiAliasing(True)
        self.canvas.setDestinationCrs(qgis.core.QgsCoordinateReferenceSystem(2154))



        self.testMethod()
        #program.run(self.canvas, True, "spatialite")
        app.exec_()
        qgis.core.QgsApplication.exitQgis()
        print('Test fini')


    def testMethod(self):
        self.createMainWin()
        self.mainwin.resize(QtCore.QSize(1000,800))

        if True:

            if int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 4:  # qgis2
                reg = qgis.core.QgsPluginLayerRegistry.instance()
            elif int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 5:  # qgis3
                reg = qgis.core.QgsApplication.pluginLayerRegistry()

            # qgisRegistryInstance = qgis.core.QgsApplication.pluginLayerRegistry()
            reg.addPluginLayerType(SelafinPluginLayerType())

        if True:
            layer = SelafinPluginLayer(self.tr('Click properties to load selafin file'), specificmapcanvas=self.canvas)


            if True:
                self.dialogslf = layer.propertiesdialog
                self.mainwin.frame_2.layout().addWidget(self.dialogslf)

            if True:
                print('********* SELAFI created ***************************** ')


                pathslf = os.path.join(os.path.dirname(__file__), 'telemac_files', 'res_pluie_2010_cn100_Max.res')
                # pathslf = os.path.join(os.path.dirname(__file__), 'telemac_files', 'res_pluie_2010_Max.res')
                pathslf = os.path.join(os.path.dirname(__file__), 'telemac_files', 'res_tempete.slf')

                layer.load_selafin(pathslf,'TELEMAC')


            if True:
                print('********* SELAFI loaded ***************************** ')

                self.canvas.setLayers([layer])
                self.canvas.refresh()

                print('********* SELAFI on canvas ***************************** ')





        print('launch window')
        self.mainwin.exec_()






    def createMainWin(self):
        self.mainwin = UserUI()
        self.mainwin.frame.layout().addWidget(self.canvas)
        #self.mainwin.frame_2.layout().addWidget(self.wind)

        self.mainwin.setParent(None)


class UserUI(QDialog):

    def __init__(self, parent=None):
        super(UserUI, self).__init__(parent=parent)
        uipath = os.path.join(os.path.dirname(__file__), 'mainwindows_1.ui')
        uic.loadUi(uipath, self)


print('start')
test = Test()
test.launchTest()

print('end')