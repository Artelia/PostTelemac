"""@author David H. Roscoe, Matthew J. Wood and Sebastien E. Bourban
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
"""@history 15/08/2011 -- Sebastien Bourban
"""
"""@brief
         This includes a series of tools to parse the content of a TELEMAC
         sortie file (generated with the '-s' TELEMAC runcode option)
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#

# ~~> dependencies towards standard python
import re
import sys
from os import path,walk
from fnmatch import fnmatch
# ~~> dependencies towards other pytel/modules
from utils.files import getFileContent

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#
"""
   Inspired from matchSafe in utils.py
   Follows first the simple template casFile+'_*??h??min??s.sortie'
   and then look for the parallel equivalent.
"""
def getLatestSortieFiles(fi):
   # ~~> list all entries
   dp, _, filenames = walk(path.dirname(fi)).next()
   # ~~> match expression
   exnames = [] #[ path.basename(fi) ]
   for fo in filenames:
      if fnmatch(fo,path.basename(fi)+'_*??h??min??s.sortie'): exnames.append(fo)
   if exnames == []: return []
   casbase = sorted(exnames).pop()
   exnames = [ path.join(dp,casbase) ]
   casbase = path.splitext(casbase)[0]
   for fo in filenames:
      if fnmatch(fo,casbase+'_*.sortie'): exnames.append(path.join(dp,fo))
   return exnames

# _____                         ____________________________________
# ____/ Primary Classes:Sortie /___________________________________/
#

class Sortie:

   def __init__(self,fileName=''):
      self.sortie = []
      if fileName != '': self.sortie = self.getFileContent(fileName)

   def getFileContent(self,fileName):
      if not path.exists(fileName):
         print '... could not find your CSV file: ',fileName
         sys.exit(1)
      self.sortie = getFileContent(fileName)

   # ~~ Time support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # Returns the time profile in iteration and in seconds,
   #    read from the TELEMAC sortie file
   # Also sets the xLabel to either 'Time (s)' or 'Iteration #'
   def getTimeProfile(self):
      form = re.compile(r'\s*ITERATION\s+(?P<iteration>\d+)\s+(TEMPS|TIME)[\s:]*'
            + r'(?P<others>.*?)'
            + r'(?P<number>\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+S\s*(|\))'
            + r'\s*\Z',re.I)
      itr = []; time = []
      for line in self.sortie:
         proc = re.match(form,line)
         if proc:
            itr.append(int(proc.group('iteration')))
            time.append(float(proc.group('number')))
      return ('Iteration #',itr), ('Time (s)',time)

   # ~~ Name of the study ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # Returns the name of the study, read from the TELEMAC sortie file
   #   +> If no name, returns NO NAME
   #   +> If not found, returns NAME NO FOUND
   def getNameOfStudy(self):
      form = re.compile(r'\s*(?P<before>.*?)(NAME OF THE STUDY|TITRE DE L\'ETUDE)[\s:]*(?P<after>.*?)\s*\Z',re.I)
      #form = re.compile(r'\s*(?P<before>.*?)(TITLE|TITRE)[\s=]*(?P<after>.*?)\s*\Z',re.I)
      for line in range(len(self.sortie)):
         proc = re.match(form,self.sortie[line])
         if proc:
            if self.sortie[line+1].strip() == '': return 'NO NAME'
            return self.sortie[line+1].strip()
         #proc = re.match(form,self.sortie[line])
         #if proc:
         #   if proc.group('after').strip() == '': return 'NO NAME'
         #   return proc.group('after').strip()
      return 'NAME NOT FOUND'

   # ~~ Volumes and Fluxes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # Returns the time series of Values, read from the TELEMAC sortie file
   #   volumes, fluxes, errors, etc.
   # Assumptions:
   #   +> if VOLUME ... is not found, will not try to read FLUX and ERROR
   #   +> for every VOLUME instance, it will advance to find FLUX and ERROR
   # Also sets the yLabel to either 'Volume (m3/s)' or 'Fluxes (-)' or 'Error (-)'
   def getVolumeProfile(self):
      form_liqnumbers = re.compile(r'\s*(THERE IS|IL Y A)\s+(?P<number>\d+)'
                  + r'\s+(LIQUID BOUNDARIES:|FRONTIERE\(S\) LIQUIDE\(S\) :)\s*\Z',re.I)
      form_liqnumberp = re.compile(r'\s*(NUMBER OF LIQUID BOUNDARIES|NOMBRE DE FRONTIERES LIQUIDES :)\s+(?P<number>\d+)\s*\Z',re.I)
      form_volinitial = re.compile(r'\s*(INITIAL VOLUME |VOLUME INITIAL)[\s:]*'
                  + r'\s+(?P<value>\b([-+]|)((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+'
                  + r'(?P<after>.*?)\s*\Z',re.I)
      form_voltotal = re.compile(r'\s*(VOLUME IN THE DOMAIN|VOLUME DANS LE DOMAINE)[\s:]*'
                  + r'\s+(?P<value>\b([-+]|)((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+'
                  + r'(?P<after>.*?)\s*\Z',re.I)
      form_volfluxes = re.compile(r'\s*(FLUX BOUNDARY|FLUX FRONTIERE)\s+(?P<number>\d+)\s*:\s*'
                  + r'(?P<value>[+-]*\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))(.\s|\s)+'
                  + r'(?P<after>.*?)\s*\Z',re.I)
      form_volerror = re.compile(r'\s*(RELATIVE ERROR IN VOLUME AT T =|ERREUR RELATIVE EN VOLUME A T =)\s+'
                  + r'(?P<at>[+-]*\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+S :\s+'
                  + r'(?P<value>[+-]*\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))'
                  + r'\s*\Z',re.I)
      iLine = 0

      # ~~ Searches for number of liquid boundaries ~~~~~~~~~~~~~~~~~~~
      fluxesProf = []; fluxesName = []; boundNames = []
      liqnumber = 0
      while iLine < len(self.sortie):
         proc = re.match(form_liqnumbers,self.sortie[iLine])
         if not proc: proc = re.match(form_liqnumberp,self.sortie[iLine])
         if proc:
            liqnumber = int(proc.group('number'))
            for i in range(liqnumber):
               fluxesProf.append([])
               boundNames.append( 'Boundary ' + str(i+1) )
            #print '... Could find ' + str(liqnumber) + ' open boundaries'
            break
         iLine = iLine + 1
      # ~~ Initiates profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      volumesProf = []; volumesName = 'Volumes (m3/s)'
      errorsProf = []; errorsName = 'Error (-)'
      fluxesName = 'Fluxes (-)'

      # ~~ Reads the rest of time profiles ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      while iLine < len(self.sortie):
         if re.match(form_volinitial,self.sortie[iLine]): break

         proc = re.match(form_voltotal,self.sortie[iLine])
         if proc:
            volumesProf.append(float(proc.group('value')))
            for i in range(liqnumber):
               iLine = iLine + 1
               proc = re.match(form_volfluxes,self.sortie[iLine])
               while not proc:
                  iLine = iLine + 1
                  if iLine >= len(self.sortie):
                     print '... Could not parse FLUXES FOR BOUNDARY ' + str(i+1)
                     sys.exit(1)
                  proc = re.match(form_volfluxes,self.sortie[iLine])
               fluxesProf[i].append(float(proc.group('value')))
            iLine = iLine + 1
            proc = re.match(form_volerror,self.sortie[iLine])
            while not proc:
               iLine = iLine + 1
               if iLine >= len(self.sortie):
                  print '... Could not parse RELATIVE ERROR IN VOLUME '
                  sys.exit(1)
                  proc = re.match(form_volerror,self.sortie[iLine])
            errorsProf.append(float(proc.group('value')))

         iLine = iLine + 1

      # ~~ Adds initial volume ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      while iLine < len(self.sortie):
         proc = re.match(form_volinitial,self.sortie[iLine])
         if proc:
            volumesProf.insert(0,float(proc.group('value')))
            break
         iLine = iLine + 1
      # ~~ Adds initial error ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      errorsProf.insert(0,0.0) # assumed
      # ~~ Adds initial fluxes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      for i in range(liqnumber):      # 0.0 may not be the correct value
         fluxesProf[i].insert(0,0.0)

      return (volumesName,volumesProf),(fluxesName,boundNames,fluxesProf),(errorsName,errorsProf)
      #/!\ remember that "fluxes" is an array already

   # ~~ Data support ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # Returns the time series of Values, read from the TELEMAC sortie file
   #      where "Values" is volumes, fluxes, errors, etc.
   #   Assumptions:
   #      +> if VOLUME ... is not found, will not try to read FLUX and ERROR
   #      +> for every VOLUME instance, it will advance to find FLUX and ERROR
   #   Also sets the yLabel to either 'Volume (m3/s)' or 'Fluxes (-)' or 'Error (-)'
   """
      Creates the x,y arrays for plotting
      Values read from the TELEMAC sortie file ... every time this is called
   """
   def getValueHistorySortie(self,vrs):
      # ~~ Extract data
      i,x0 = self.getTimeProfile()
      y1,y2,y3 = self.getVolumeProfile()
      y0 = []
      for var in vrs.split(';'):
         v,s = var.split(':')
         # ~~ y-axis ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         if v == "voltotal": y0.append(y1)
         elif v == "volfluxes": y0.append(y2)
         elif v == "volerror": y0.append(y3)
         else:
            print '... do not know how to extract: ' + v + ' of support ' + s
            sys.exit(1)
      return x0,y0
