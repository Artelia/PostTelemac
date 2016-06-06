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
"""

#import QT
from PyQt4 import QtCore ,QtGui
#import qgis
import qgis.core
#Other standart libs import
import os.path
import time
import sys
import subprocess
sys.path.append(os.path.join(os.path.dirname(__file__),'libs_telemac'))
#Posttelemac library import
import resources_rc
from libs.post_telemac_pluginlayer import SelafinPluginLayer
from libs.post_telemac_pluginlayer_type import SelafinPluginLayerType
from dialogs.posttelemac_about import aboutDialog

#Processing
DOPROCESSING = False #set to false to make the plugin reloader work
if DOPROCESSING:
    from processing.core.Processing import Processing
    from posttelemacprovider.PostTelemacProvider import PostTelemacProvider
    cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
    if cmd_folder not in sys.path:
        sys.path.insert(0, cmd_folder)

        
"""
/***************************************************************************

Main Class

 ***************************************************************************/
"""
        
        
class PostTelemac:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.
    
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        #***********************************************************************
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QtCore.QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'posttelemac_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            #app=QApplication([''])
            self.translator = QtCore.QTranslator()
            #self.translator = QTranslator(app)
            self.translator.load(locale_path)
            QtCore.QCoreApplication.installTranslator(self.translator)
            """

            if qVersion() > '4.3.3':
                print 'ok'
                QCoreApplication.installTranslator(self.translator)
                #app.installTranslator(self.translator)
            """
        #***********************************************************************

        self.pluginLayerType = None
        self.addToRegistry()
        self.slf=[]

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&PostTelemac')
        # TODO: We are going to let the user set this up in a future iteration
        #toolbar
        toolbars = self.iface.mainWindow().findChildren(QtGui.QToolBar)
        test = True
        for toolbar1 in toolbars:
            if toolbar1.windowTitle() == u'Telemac':
                self.toolbar = toolbar1
                test = False
                break
        if test:
            self.toolbar = self.iface.addToolBar(u'Telemac')
            self.toolbar.setObjectName(u'Telemac')
        
        self.dlg_about = None
        
        #Processing
        if DOPROCESSING : self.provider = PostTelemacProvider()

    
    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.
        :param message: String for translation.
        :type message: str, QString
        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QtCore.QCoreApplication.translate('PostTelemac', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QtGui.QIcon(icon_path)
        action = QtGui.QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)
        
        if add_to_toolbar:
            self.toolbar.addAction(action)
        
        
        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        
        icon_path = ':/plugins/PostTelemac/icons/posttelemac.png'
        self.add_action(
            icon_path,
            text=self.tr(u'PostTelemac'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.add_action(
            icon_path,
            text=self.tr(u'PostTelemac Help'),
            add_to_toolbar=False,
            callback=self.showHelp,
            parent=self.iface.mainWindow())
        self.add_action(
            icon_path,
            text=self.tr(u'PostTelemac About'),
            add_to_toolbar=False,
            callback=self.showAbout,
            parent=self.iface.mainWindow())
        
            
        #Processing thing
        if DOPROCESSING : Processing.addProvider(self.provider)
        


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&PostTelemac'),
                action)
            self.toolbar.removeAction(action)
        # remove the toolbar
        if len(self.toolbar.actions()) == 0 :
            del self.toolbar
        if DOPROCESSING : Processing.removeProvider(self.provider)

    def run(self):
        """Run method that performs all the real work"""
        self.slf.append(SelafinPluginLayer(self.tr('Click properties to load selafin file')))     #add selafin to list otherwise it can not work with multiple selafin files
        self.slf[len(self.slf)-1].setRealCrs(self.iface.mapCanvas().mapSettings().destinationCrs())   #to prevent weird bug with weird crs
        qgis.core.QgsMapLayerRegistry.instance().addMapLayer(self.slf[len(self.slf)-1])
        self.iface.showLayerProperties(self.slf[len(self.slf)-1])
        #check library things
        self.checkLibrary()
        
    def showHelp(self):
        if sys.platform == 'linux2':
            subprocess.call(["xdg-open", 'https://github.com/ArteliaTelemac/PostTelemac/wiki'])
        else:
            os.startfile('https://github.com/ArteliaTelemac/PostTelemac/wiki')
        
    def showAbout(self):
        if not self.dlg_about:
            self.dlg_about = aboutDialog()
        self.dlg_about.setWindowModality(2)
        r = self.dlg_about.exec_()
        
        
    #Specific functions
    def addToRegistry(self):
        #Add telemac_viewer in QgsPluginLayerRegistry
        if u'selafin_viewer' in qgis.core.QgsPluginLayerRegistry.instance().pluginLayerTypes():
            qgis.core.QgsPluginLayerRegistry.instance().removePluginLayerType('selafin_viewer')
        self.pluginLayerType = SelafinPluginLayerType()
        qgis.core.QgsPluginLayerRegistry.instance().addPluginLayerType(self.pluginLayerType)

    
    def checkLibrary(self):
        try:
            import matplotlib
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Matplotlib loaded'))
        except Exception, e :
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Install Matplotlib (Start menu/All programs/OSGeo4W/setup/advanced install - "maplotlib" library) and restard qgis'))
        try:
            import shapely
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Shapely loaded'))
        except Exception, e :
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Install shapely (Start menu/All programs/OSGeo4W/setup/advanced install - "python-shapely" library) and restard qgis'))
        try:
            import networkx
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - networkx loaded'))
        except Exception, e :
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Install networkx (Start menu/All programs/OSGeo4W/setup/advanced install - "networkx" library) and restard qgis'))
        try:
            import numpy
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - numpy loaded'))
        except Exception, e :
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Install numpy (Start menu/All programs/OSGeo4W/setup/advanced install - "python-numpy" library) and restard qgis'))
        try:
            import scipy
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - scipy loaded'))
        except Exception, e :
            self.slf[len(self.slf)-1].propertiesdialog.textBrowser_main.append(time.ctime()+self.tr(' - Install scipy (Start menu/All programs/OSGeo4W/setup/advanced install - "python-scipy" library) and restard qgis'))
            