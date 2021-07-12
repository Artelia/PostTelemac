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

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .ExtractMax_Algorithm import PostTelemacExtractMax
from .PointsShapeTool_Algorithm import PostTelemacPointsShapeTool
from .ContourShapeTool_Algorithm import PostTelemacContourShapeTool
from .PostControlSections_Algorithm import PostTelemacControlSections
from .ExtractTSFromSortie_Algorithm import ExtractTSFromSortie

# ExampleAlgorithmProvider


class PostTelemacProvider(QgsProcessingProvider):
    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(PostTelemacExtractMax())
        self.addAlgorithm(PostTelemacPointsShapeTool())
        self.addAlgorithm(PostTelemacContourShapeTool())
        self.addAlgorithm(PostTelemacControlSections())
        self.addAlgorithm(ExtractTSFromSortie())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return "posttelemac"

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return "PostTelemac"

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(":/plugins/PostTelemac/icons/posttelemac.png")

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
