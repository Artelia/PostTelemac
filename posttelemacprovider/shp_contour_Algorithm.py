# -*- coding: utf-8 -*-

"""
***************************************************************************
    __init__.py
    ---------------------
    Date                 : July 2013
    Copyright            : (C) 2013 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'July 2013'
__copyright__ = '(C) 2013, Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from PyQt4.QtCore import QSettings
from qgis.core import QgsVectorFileWriter

from processing.core.GeoAlgorithm import GeoAlgorithm
#from processing.core.parameters import ParameterVector
from processing.core.parameters import *
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector
from processing.core.GeoAlgorithmExecutionException import  GeoAlgorithmExecutionException
from ..libs.posttelemac_util_extractshp import InitSelafinContour2Shp


class ShpContourAlgorithm(GeoAlgorithm):
    """This is an example algorithm that takes a vector layer and
    creates a new one just with just those features of the input
    layer that are selected.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the GeoAlgorithm class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROCESS_TYPE = 'PROCESS_TYPE'
    SELAFIN_FILE = 'SELAFIN_FILE'
    SELAFIN_TIME = 'SELAFIN_TIME'
    SELAFIN_LVL_STD = 'SELAFIN_LVL_STD'
    SELAFIN_LVL_SPE = 'SELAFIN_LVL_SPE'
    SELAFIN_PARAM_STD = 'SELAFIN_PARAM_STD'
    SELAFIN_PARAM_SPE = 'SELAFIN_PARAM_SPE'
    QUICK_PROCESS = 'QUICK_PROCESS'
    SELAFIN_CRS = 'SELAFIN_CRS'
    TRANS_CRS = 'TRANS_CRS'
    SHP_CRS = 'SHP_CRS'
    SHP_NAME = 'SHP_NAME'
    SHP_PROCESS = 'SHP_PROCESS'
    
    PROCESS_TYPES = ['En arriere plan', 'Modeler', 'Modeler avec creation de fichier']
    SELAFIN_LVL_STDS = ['[H_simple : 0.0,0.05,0.5,1.0,2.0,,5.0,9999.0]' , '[H_complet : 0.0,0.01,0.05,0.1,0.25,0.5,1.0,1.5,2.0,5.0,9999.0]' , '[H_AMC]' , '[V_AMC_simple : 0.0,0.5,1.0,2.0,4.0]' , '[V_complet : 0,0.25,0.5,1.0,2.0,4.0,9999.0]' , '[Onde : mn : 0,5,10,15,30,h : 1, 2, 3, 6, 12, 24, >24]' , '[Delta_SL : -9999,0.5,-0.25,-0.10,-0.05,-0.02,-0.01,0.01,0.02,0.10,0.25,0.50,9999]' , '[Duree_AMC]']
    SELAFIN_PARAM_STDS = ['Hmax','Vmax','SLmax','?SLmax','SUBMERSION']
    
    

    def defineCharacteristics(self):
        """Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # The name that the user will see in the toolbox
        self.name = 'Create contour'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Shapefile extraction'
        """
        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterVector(self.INPUT_LAYER,
            self.tr('Input layer'), [ParameterVector.VECTOR_TYPE_ANY], False))

        # We add a vector layer as output
        self.addOutput(OutputVector(self.OUTPUT_LAYER,
            self.tr('Output layer with selected features')))
        """
        self.addParameter(ParameterSelection(self.PROCESS_TYPE,
            self.tr('Process type'), self.PROCESS_TYPES, 0))
        self.addParameter(ParameterFile(self.SELAFIN_FILE,
            self.tr('Selafin file'), False,False))
        self.addParameter(ParameterNumber(self.SELAFIN_TIME,
            self.tr('Selafin time'), 0.0, 99999999.0, 0.0))
        self.addParameter(ParameterSelection(self.SELAFIN_LVL_STD,
            self.tr('Levels standards'), self.SELAFIN_LVL_STDS, 0))
        self.addParameter(ParameterString(self.SELAFIN_LVL_SPE,
            self.tr('Levels specific')))
        self.addParameter(ParameterSelection(self.SELAFIN_PARAM_STD,
            self.tr('Parameters standards'), self.SELAFIN_PARAM_STDS, 0))
        self.addParameter(ParameterString(self.SELAFIN_PARAM_SPE,
            self.tr('Parameters specific')))
        self.addParameter(ParameterBoolean(self.QUICK_PROCESS,
            self.tr('Quick process'), False))
        self.addParameter(ParameterCrs(self.SELAFIN_CRS,
            self.tr('Selafin CRS'), 'EPSG:2154'))
        self.addParameter(ParameterBoolean(self.TRANS_CRS,
            self.tr('Transform CRS'), False))
        self.addParameter(ParameterCrs(self.SHP_CRS,
            self.tr('Shp CRS'), 'EPSG:2154'))
        self.addParameter(ParameterString(self.SHP_NAME,
            self.tr('Specific name')))
        self.addOutput(OutputVector(self.SHP_PROCESS, self.tr('Telemac layer')))
        
        
    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""

        # The first thing to do is retrieve the values of the parameters
        # entered by the user
        """
        inputFilename = self.getParameterValue(self.INPUT_LAYER)
        output = self.getOutputValue(self.OUTPUT_LAYER)
        """
        self.initclass=InitSelafinContour2Shp()
        self.initclass.status.connect(progress.setText)
        self.initclass.error.connect(self.raiseError)
        self.initclass.finished1.connect(self.workerFinished)
        
        #Determine param
        params = ['Hmax','Vmax','SLmax','?SLmax','SUBMERSION']
        if self.getParameterValue(self.SELAFIN_PARAM_SPE) == '':
            param = params[self.getParameterValue(self.SELAFIN_PARAM_STD)]
        else : 
            param = self.getParameterValue(self.SELAFIN_PARAM_SPE)
            
        #define level
        levels= [[-99.0,0.05,0.5,1.0,2.0,5.0,9999.0],
                [-99.0,0.01,0.05,0.1,0.25,0.5,1.0,1.5,2.0,5.0,9999.0],
                [0.0,0.05,0.15,0.25,0.35,0.45,0.55,0.65,0.75,0.85,0.95,1.05,1.15,1.25,1.35,1.45,1.55,1.65,1.75,1.85,1.95,2.05,2.15,2.25,2.35,2.45,2.55,2.65,2.75,2.85,2.95,3.05,9999.0],
                [-99.0,0.5,1.0,2.0,4.0,9999.0],
                [-99.0,0.25,0.5,1.0,2.0,4.0,9999.0],
                [-604800.0,0.0,300.0,600.0,900.0,1800.0,3600.0,7200.0,10800.0,21600.0,43200.0,86400.0,1e21],
                [-9999.0,-0.5,-0.25,-0.10,-0.05,-0.02,-0.01,0.01,0.02,0.05,0.10,0.25,0.50,9999],
                [0,86400.0,172800.0,432000.0,864000.0,2592000.0]]
        if self.getParameterValue(self.SELAFIN_LVL_SPE) == '':
            level = levels[self.getParameterValue(self.SELAFIN_LVL_STD)]
        else : 
            level = [float(self.getParameterValue(self.SELAFIN_LVL_SPE).split(";")[i]) for i in range(len(self.getParameterValue(self.SELAFIN_LVL_SPE).split(";")))]
                
        self.initclass.start(int(self.getParameterValue(self.PROCESS_TYPE))+1,                 #0 : thread inside qgis (plugin) - 1 : thread processing - 2 : modeler (no thread) - 3 : modeler + shpouput - 4: outsideqgis
                         os.path.normpath(self.getParameterValue(self.SELAFIN_FILE)),                 #path to selafin file
                         self.getParameterValue(self.SELAFIN_TIME),                            #time to process (selafin time in seconds)
                         param,                     #parameter to process name (string) or id (int)
                         level,                       #levels to create
                         self.getParameterValue(self.SELAFIN_CRS),      #selafin crs
                         self.getParameterValue(self.SHP_CRS) if self.getParameterValue(self.TRANS_CRS) else None,   #if no none, specify crs of output file
                         self.getParameterValue(self.QUICK_PROCESS),                #quickprocess option - don't make ring
                         self.getParameterValue(self.SHP_NAME),           #change generic outputname to specific one
                          None,         #if not none, create shp in this directory
                        forcedvalue = None,          #force value for plugin
                          self.getOutputValue(self.SHP_PROCESS))
        

        # Input layers vales are always a string with its location.
        # That string can be converted into a QGIS object (a
        # QgsVectorLayer in this case) using the
        # processing.getObjectFromUri() method.
        """
        vectorLayer = dataobjects.getObjectFromUri(inputFilename)
        """
        # And now we can process

        # First we create the output layer. The output value entered by
        # the user is a string containing a filename, so we can use it
        # directly
        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')
        """
        provider = vectorLayer.dataProvider()
        writer = QgsVectorFileWriter(output, systemEncoding,
                                     provider.fields(),
                                     provider.geometryType(), provider.crs())
        """
        # Now we take the features from input layer and add them to the
        # output. Method features() returns an iterator, considering the
        # selection that might exist in layer and the configuration that
        # indicates should algorithm use only selected features or all
        # of them
        """
        features = vector.features(vectorLayer)
        for f in features:
            writer.addFeature(f)
        """
        
        # There is nothing more to do here. We do not have to open the
        # layer that we have created. The framework will take care of
        # that, or will handle it if this algorithm is executed within
        # a complex model
        
    def workerFinished(self,strpath):
        #progress.setText(str(ctime()) +" - Fin du thread - Chargement du fichier resultat")
        #self.selafinlayer.propertiesdialog.textBrowser_2.append('finish')
        #print 'finf'
        #vlayer = QgsVectorLayer( self.donnees_d_entree['pathshp'], os.path.basename(self.donnees_d_entree['pathshp']).split('.')[0],"ogr")
        vlayer = QgsVectorLayer( strpath, os.path.basename(strpath).split('.')[0],"ogr")
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)
        
    def raiseError(self,str1):
        raise GeoAlgorithmExecutionException(str1)

