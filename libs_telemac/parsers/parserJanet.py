"""@author Sebastien E. Bourban and Michael S. Turnbull
"""
"""@note ... this work is based on a collaborative effort between
  .________.                                                          ,--.
  |        |                                                      .  (  (
  |,-.    /   HR Wallingford                EDF - LNHE           / \_ \_/ .--.
  /   \  /    Howbery Park,                 6, quai Watier       \   )   /_   )
   ,.  `'     Wallingford, Oxfordshire      78401 Cedex           `-'_  __ `--
  /  \   /    OX10 8BA, United Kingdom      Chatou, France        __/ \ \ `.
 /    `-'|    www.hrwallingford.com         innovation.edf.com   |    )  )  )
!________!                                                        `--'   `--
"""
"""@brief
         Tools for handling Janet native files in python.
         Janet and its related software (..., )
         are property of Smile Consulting
"""
"""@details
         Contains
"""
"""@history 26/12/2011 -- Sebastien E. Bourban:
         First trial at parsing I2S and I3S
"""
"""@history 13/01/2012 -- Sebastien E. Bourban:
         Creates INSEL class with associated methods including
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
import re
import numpy as np
from os import path
# ~~> dependencies towards other pytel/modules
from utils.files import getFileContent,putFileContent
from utils.progressbar import ProgressBar
from utils.geometry import isClose

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#
dat_openh = re.compile(r'(DAMM|INSEL)')
dat_closh = re.compile(r'(DAMM|INSEL)')
dat_footer = re.compile(r'ENDE DATEI')

var_1int = re.compile(r'(?P<before>[^+-]*?)(?P<number>\b(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')
var_1dbl = re.compile(r'(?P<number>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<after>.*?)\Z')
var_2dbl = re.compile(r'(?P<number1>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<number2>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')
var_3dbl = re.compile(r'(?P<number1>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<number2>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<number3>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def cleanSpaces(istr): # same as in parserFortran
   return istr.strip().replace('  ',' ').replace('  ',' ')

# _____                      _______________________________________
# ____/ Toolbox for I2S/I3S /______________________________________/
#

def getINSEL(file):
   # ~~ Get all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   core = getFileContent(file)
   if not re.match(dat_footer,core[len(core)-1]):
      print '\nCould not parse the following end line of the file: '+core[len(core)-1]
      sys.exit()

   # ~~ First scan at INSEL and DAMM ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # This is also fairly fast, so you might not need a progress bar
   core.pop(len(core)-1)
   poly = []; type = []; npoin = 0
   iline = 0; xyi = []; fileType = True
   while iline < len(core):
      proco = re.match(dat_openh,core[iline])
      if proco: t = 0
      procc = re.match(dat_closh,core[iline])
      if procc: t = 1
      if proco or procc:
         iline += 1
         if xyi != []:
            poly.append(xyi); npoin += len(xyi); type.append(t)
            xyi = []
      else:
         proc = re.match(var_3dbl,core[iline].strip())
         if proc:
            xyi.append((proc.group('number1'),proc.group('number2'),proc.group('number3')))
         else:
            fileType = False
            proc = re.match(var_2dbl,core[iline].strip())
            if proc:
               xyi.append((proc.group('number1'),proc.group('number2')))
            else:
               print '\nCould not parse the following polyline record: '+core[iline]
               sys.exit()
      iline += 1
   poly.append(xyi); npoin += len(xyi); type.append(t)

   # ~~ Second scan at INSEL and DAMM ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # This is also fairly fast, so you might not need a progress bar
   if fileType:
      for pline in range(len(poly)):
         xyi = []
         for iline in range(len(poly[pline])):
            a,b,c = poly[pline][iline]
            poly[pline][iline] = [ float(a),float(b),float(c) ]
         poly[pline] = np.asarray(poly[pline])
   else:
      for pline in range(len(poly)):
         xyi = []
         for iline in range(len(poly[pline])):
            a,b = poly[pline][iline]
            poly[pline][iline] = [ float(a),float(b) ]
         poly[pline] = np.asarray(poly[pline])

   return fileType,npoin,poly,type

"""
   self.poly is a numpy object, while self.type is not.
"""
class INSEL:

   def __init__(self,fileName):
      self.fileName = fileName
      self.fileType,self.npoin,self.poly,self.type = getINSEL(self.fileName)

   def toi2s(self,ins):
      ins.head = []
      if self.fileType: ins.fileType = 'i3s'
      else: ins.fileType = 'i2s'
      ins.npoin = self.npoin
      ins.poly = self.poly
      ins.type = self.type
      return ins
