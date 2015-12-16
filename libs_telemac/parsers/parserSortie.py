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
   for dp,dn,filenames in walk(path.dirname(fi)): break
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

# _____                             ________________________________
# ____/ Global Regular Expressions /_______________________________/
#
# _____                        _____________________________________
# ____/ Sortie Parser Toolbox /____________________________________/
#
"""
   Returns the time profile in iteration and in seconds, read from the TELEMAC sortie file
   Also sets the xLabel to either 'Time (s)' or 'Iteration #'
"""
sortie_time = re.compile(r'\s*ITERATION\s+(?P<iteration>\d+)\s+(TEMPS|TIME)[\s:]*'
            + r'(?P<others>.*?)'
            + r'(?P<number>\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+S\s*(|\))'
            + r'\s*\Z',re.I)

def parseTimeProfile(sortieLines):
   iter = []; time = []
   for line in sortieLines:
      proc = re.match(sortie_time,line)
      if proc:
         iter.append(int(proc.group('iteration')))
         time.append(float(proc.group('number')))
   return ('Iteration #',iter), ('Time (s)',time)

"""
   Returns the name of the study, read from the TELEMAC sortie file
   +> If no name, returns NO NAME
   +> If not found, returns NAME NO FOUND
"""
sortie_nameofstudy = re.compile(r'\s*(?P<before>.*?)(NAME OF THE STUDY|TITRE DE L\'ETUDE)[\s:]*(?P<after>.*?)\s*\Z',re.I)
#sortie_title = re.compile(r'\s*(?P<before>.*?)(TITLE|TITRE)[\s=]*(?P<after>.*?)\s*\Z',re.I)

def parseNameOfStudy(sortieLines):
   for line in range(len(sortieLines)):
      proc = re.match(sortie_nameofstudy,sortieLines[line])
      if proc:
         if sortieLines[line+1].strip() == '': return 'NO NAME'
         return sortieLines[line+1].strip()
      #proc = re.match(sortie_title,sortieLines[line])
      #if proc:
      #   if proc.group('after').strip() == '': return 'NO NAME'
      #   return proc.group('after').strip()
   return 'NAME NOT FOUND'
"""
   Returns the time series of Values, read from the TELEMAC sortie file
      where "Values" is volumes, fluxes, errors, etc.
   Assumptions:
      +> if VOLUME ... is not found, will not try to read FLUX and ERROR
      +> for every VOLUME instance, it will advance to find FLUX and ERROR
   Also sets the yLabel to either 'Volume (m3/s)' or 'Fluxes (-)' or 'Error (-)'
"""
sortie_liqnumbers = re.compile(r'\s*(THERE IS|IL Y A)\s+(?P<number>\d+)'
            + r'\s+(LIQUID BOUNDARIES:|FRONTIERE\(S\) LIQUIDE\(S\) :)\s*\Z',re.I)
sortie_liqnumberp = re.compile(r'\s*(NUMBER OF LIQUID BOUNDARIES|NOMBRE DE FRONTIERES LIQUIDES :)\s+(?P<number>\d+)\s*\Z',re.I)
sortie_volinitial = re.compile(r'\s*(INITIAL VOLUME |VOLUME INITIAL)[\s:]*'
            + r'\s+(?P<value>\b([-+]|)((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+'
            + r'(?P<after>.*?)\s*\Z',re.I)
sortie_voltotal = re.compile(r'\s*(VOLUME IN THE DOMAIN|VOLUME DANS LE DOMAINE)[\s:]*'
            + r'\s+(?P<value>\b([-+]|)((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+'
            + r'(?P<after>.*?)\s*\Z',re.I)
sortie_volfluxes = re.compile(r'\s*(FLUX BOUNDARY|FLUX FRONTIERE)\s+(?P<number>\d+)\s*:\s*'
            + r'(?P<value>[+-]*\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))(.\s|\s)+'
            + r'(?P<after>.*?)\s*\Z',re.I)
sortie_volerror = re.compile(r'\s*(RELATIVE ERROR IN VOLUME AT T =|ERREUR RELATIVE EN VOLUME A T =)\s+'
            + r'(?P<at>[+-]*\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))\s+S :\s+'
            + r'(?P<value>[+-]*\b((?:(\d+)\b)|(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+))))'
            + r'\s*\Z',re.I)

def parseValueProfile(sortieLines):
   iLine = 0

   # ~~ Searches for number of liquid boundaries ~~~~~~~~~~~~~~~~~~~
   fluxesProf = []; fluxesName = []; boundNames = []
   liqnumber = 0
   while iLine < len(sortieLines):
      proc = re.match(sortie_liqnumbers,sortieLines[iLine])
      if not proc: proc = re.match(sortie_liqnumberp,sortieLines[iLine])
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
   while iLine < len(sortieLines):
      if re.match(sortie_volinitial,sortieLines[iLine]): break

      proc = re.match(sortie_voltotal,sortieLines[iLine])
      if proc:
         volumesProf.append(float(proc.group('value')))
         for i in range(liqnumber):
            iLine = iLine + 1
            proc = re.match(sortie_volfluxes,sortieLines[iLine])
            while not proc:
               iLine = iLine + 1
               if iLine >= len(sortieLines):
                  print '... Could not parse FLUXES FOR BOUNDARY ' + str(i+1)
                  sys.exit()
               proc = re.match(sortie_volfluxes,sortieLines[iLine])
            fluxesProf[i].append(float(proc.group('value')))
         iLine = iLine + 1
         proc = re.match(sortie_volerror,sortieLines[iLine])
         while not proc:
            iLine = iLine + 1
            if iLine >= len(sortieLines):
               print '... Could not parse RELATIVE ERROR IN VOLUME '
               sys.exit()
               proc = re.match(sortie_volerror,sortieLines[iLine])
         errorsProf.append(float(proc.group('value')))

      iLine = iLine + 1

   # ~~ Adds initial volume ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   while iLine < len(sortieLines):
      proc = re.match(sortie_volinitial,sortieLines[iLine])
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

"""
   Creates the x,y arrays for plotting
   Values read from the TELEMAC sortie file ... every time this is called
"""
def getValueHistorySortie(content,vars):

   # ~~ Extract data
   title = parseNameOfStudy(content)
   i,x0 = parseTimeProfile(content)
   y1,y2,y3 = parseValueProfile(content)

   y0 = []
   for var in vars.split(';'):
      v,s = var.split(':')
      
      # ~~ y-axis ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if v == "voltotal": y0.append(y1)
      elif v == "volfluxes": y0.append(y2)
      elif v == "volerror": y0.append(y3)
      else:
         print '... do not know how to extract: ' + v + ' of support ' + s
         sys.exit()
   
   return x0,y0

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="David H. Roscoe; Sebastien E. Bourban"
__date__ ="$2-Aug-2011 11:51:36$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Reads config file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #sortieFile = "C:\\opentelemac\\validation\\telemac2d\\tel2d_v6p2\\011_bumpflu\\t2d_bumpflu_v1p0.cas_2011-08-29-08h29min55s.sortie"
   sortieFile = "C:\\opentelemac\\validation\\telemac2d\\tel2d_v6p2\\011_bumpflu\\t2d_bumpflu_v1p0.cas_2011-09-11-15h40min27s.sortie"
   sortie = { 'fileName': sortieFile, 'typePlot': "voltotal", 'outFormat': '.png' }

   # ~~ Extract data
   content = getFileContent(sortieFile)
   title = getNameOfStudy(content)
   i,x = getTimeProfile(content)
   y1,y2,y3 = getValueProfile(content)

   print 'my job is done'