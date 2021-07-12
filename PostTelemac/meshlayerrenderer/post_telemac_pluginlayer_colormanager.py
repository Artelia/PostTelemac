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
 Propertiy dialog class
 
Versions :
0.0 : debut

 ***************************************************************************/
"""
# unicode behaviour
from __future__ import unicode_literals

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QPixmap, QColor
from qgis.PyQt.QtWidgets import QApplication

import os
import numpy as np

try:
    import matplotlib.colors

    MATPLOTLIBOK = True
except:
    MATPLOTLIBOK = False


class PostTelemacColorManager:
    def __init__(self, meshlayer, meshrenderer):
        self.meshlayer = meshlayer
        self.meshrenderer = meshrenderer

    # *********************** color ramp transformation ******************************************************

    def qgsvectorgradientcolorrampv2ToColumncolor(self, temp1, inverse):

        if (
            str(temp1.__class__.__name__) == "QgsVectorGradientColorRampV2"
            or str(temp1.__class__.__name__) == "QgsGradientColorRamp"
        ):

            firstcol = temp1.properties()["color1"]
            lastcol = temp1.properties()["color2"]
            if inverse:
                firstv = 1
                lastv = 0
            else:
                firstv = 0
                lastv = 1
            otherscol = [
                [
                    firstv,
                    int(firstcol.split(",")[0]),
                    int(firstcol.split(",")[1]),
                    int(firstcol.split(",")[2]),
                    int(firstcol.split(",")[3]),
                ]
            ]

            try:
                otherscoltemp = temp1.properties()["stops"].split(":")
                bool_stops = True
            except Exception as e:
                bool_stops = False

            if bool_stops:
                for col in otherscoltemp:
                    if inverse:
                        intv = 1.0 - float(col.split(";")[0])
                    else:
                        intv = float(col.split(";")[0])
                    otherscol.append(
                        [
                            intv,
                            int(col.split(";")[1].split(",")[0]),
                            int(col.split(";")[1].split(",")[1]),
                            int(col.split(";")[1].split(",")[2]),
                            int(col.split(";")[1].split(",")[3]),
                        ]
                    )
            otherscol.append(
                [
                    lastv,
                    int(lastcol.split(",")[0]),
                    int(lastcol.split(",")[1]),
                    int(lastcol.split(",")[2]),
                    int(lastcol.split(",")[3]),
                ]
            )
            if inverse:
                otherscol.sort()
            return otherscol

        elif str(temp1.__class__.__name__) == "QgsCptCityColorRampV2":
            temp1 = temp1.cloneGradientRamp()
            firstcol = temp1.properties()["color1"]
            lastcol = temp1.properties()["color2"]
            if inverse:
                firstv = 1
                lastv = 0
            else:
                firstv = 0
                lastv = 1
            otherscol = [
                [
                    firstv,
                    int(firstcol.split(",")[0]),
                    int(firstcol.split(",")[1]),
                    int(firstcol.split(",")[2]),
                    int(firstcol.split(",")[3]),
                ]
            ]

            try:
                otherscoltemp = temp1.properties()["stops"].split(":")
                bool_stops = True
            except Exception as e:
                bool_stops = False

            if bool_stops:
                for col in otherscoltemp:
                    if inverse:
                        intv = 1.0 - float(col.split(";")[0])
                    else:
                        intv = float(col.split(";")[0])
                    otherscol.append(
                        [
                            intv,
                            int(col.split(";")[1].split(",")[0]),
                            int(col.split(";")[1].split(",")[1]),
                            int(col.split(";")[1].split(",")[2]),
                            int(col.split(";")[1].split(",")[3]),
                        ]
                    )
            otherscol.append(
                [
                    lastv,
                    int(lastcol.split(",")[0]),
                    int(lastcol.split(",")[1]),
                    int(lastcol.split(",")[2]),
                    int(lastcol.split(",")[3]),
                ]
            )
            if inverse:
                otherscol.sort()
            return otherscol

        else:
            return None

    def columncolorToCmap(self, otherscol):
        return self.arrayStepRGBAToCmap(otherscol)

    def arrayStepRGBAToCmap(self, temp1):
        if MATPLOTLIBOK and str(temp1.__class__.__name__) == "list":
            # arrange it to fit dict of matplotlib:
            #
            # http://matplotlib.org/examples/pylab_examples/custom_cmap.html
            #
            otherscol = temp1
            dict = {}
            identcolors = ["red", "green", "blue", "alpha"]
            for col in range(len(identcolors)):
                dict[identcolors[col]] = []
                lendict = len(otherscol)
                dict[identcolors[col]].append(
                    (0, float(otherscol[0][col + 1]) / 255.0, float(otherscol[0][col + 1]) / 255.0)
                )
                for i in range(1, lendict - 1):
                    dict[identcolors[col]].append(
                        (
                            float(otherscol[i][0]),
                            float(otherscol[i][col + 1]) / 255.0,
                            float(otherscol[i][col + 1]) / 255.0,
                        )
                    )
                dict[identcolors[col]].append(
                    (1, float(otherscol[lendict - 1][col + 1]) / 255.0, float(otherscol[lendict - 1][col + 1]) / 255.0)
                )
                dict[identcolors[col]] = tuple(dict[identcolors[col]])

            cmap = matplotlib.colors.LinearSegmentedColormap("temp", dict)
            return cmap

        else:
            return None

    # *********************** .Clr sparser ******************************************************

    def readClrColorRamp(self, path):
        f = open(path, "r")
        colors = []
        levels = None
        processtype = 0
        for line in f:
            if "colors" in line:
                processtype = 1
                continue
            elif "levels" in line:
                processtype = 2
                continue
            if processtype == 1:
                colors.append([float(elem) for elem in line.split(";")])
                # print 'col ' + str(colors)
            if processtype == 2:
                levels = [float(elem) for elem in line.split(";")]
        f.close()
        if colors and levels:
            return (colors, levels)
        else:
            return (None, None)

    def saveClrColorRamp(self, name, colors, levels):
        path = os.path.join(self.meshlayer.propertiesdialog.posttelemacdir, str(name) + ".clr")
        f = open(path, "w")
        f.write(str(name) + "\n")
        f.write("colors\n")
        for color in colors:
            f.write(str(";".join(str(col) for col in color)) + "\n")
        f.write("levels\n")
        f.write(str(";".join(str(lvl) for lvl in levels)) + "\n")
        f.close()

    def changeColorMap(self, cm, levels1):
        if MATPLOTLIBOK and len(levels1) >= 2:
            lvls = levels1
            tab1 = []
            max1 = 256
            if len(lvls) == 2:
                tab1 = [1.0]
            else:
                tab1 = [int(max1 * i / (len(lvls) - 2)) for i in range(len(lvls) - 1)]
            color_mpl_contour = cm(tab1)
            cmap_mpl, norm_mpl = matplotlib.colors.from_levels_and_colors(lvls, color_mpl_contour)
            return (cmap_mpl, norm_mpl, color_mpl_contour)
        else:
            return None, None, None

    def fromColorrampAndLevels(self, levels, arraycolorrampraw):
        try:
            debug = False

            if debug:
                print(str(levels) + " " + str(arraycolorrampraw))

            levelclasscount = len(levels) - 2

            # fist value unchanged
            arraycolorresult = [(np.array(arraycolorrampraw[0][1:5]) / 255.0).tolist()]

            for i in range(1, levelclasscount):
                normalizedvalue = float(i) / float(levelclasscount)
                # search where normalizedvalue is in arraycolorrampraw[j][0]
                j = 0
                while normalizedvalue >= float(arraycolorrampraw[j][0]) and j < len(arraycolorrampraw) - 1:
                    j += 1

                colortemp = np.array(arraycolorrampraw[j - 1][1:5]) + (
                    normalizedvalue - arraycolorrampraw[j - 1][0]
                ) / (arraycolorrampraw[j][0] - arraycolorrampraw[j - 1][0]) * (
                    np.array(arraycolorrampraw[j][1:5]) - np.array(arraycolorrampraw[j - 1][1:5])
                )
                if debug:
                    print(
                        str(normalizedvalue)
                        + " "
                        + str(arraycolorrampraw[j - 1])
                        + " / "
                        + str(arraycolorrampraw[j])
                        + "\n"
                        + str(colortemp)
                    )
                arraycolorresult.append((colortemp / 255.0).tolist())

            # last value unchanged
            arraycolorresult.append((np.array(arraycolorrampraw[-1][1:5]) / 255.0).tolist())

            return arraycolorresult
        except Exception as e:
            self.meshlayer.propertiesdialog.errorMessage("colormanager - fromColorrampAndLevels : " + str(e))
            return [[0.0, 0.0, 0.0, 0.0]] * (levelclasscount + 1)

    # ****************************************************************************************************
    # ************translation                                        ***********************************
    # ****************************************************************************************************

    def tr(self, message):
        """Used for translation"""
        return QCoreApplication.translate("PostTelemacColorManager", message, None, QApplication.UnicodeUTF8)
