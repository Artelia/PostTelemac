"""@author Sebastien E. Bourban
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
         Tools for handling Time Series files (such as LQD) in python.
"""
"""@details
         Contains getLQD and putLQD, which read/write python variables
         into ASCII LQD files
"""
"""@history 26/12/2011 -- Sebastien E. Bourban:
         First trial at writting LDQ having sampled SELAFIN files at nodes
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
import re
import numpy as np
# ~~> dependencies towards other pytel/modules
from utils.files import getFileContent,putFileContent

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#
lqd_header = re.compile(r'#')

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def cleanSpaces(istr): # same as in parserFortran
   return istr.strip().replace('  ',' ').replace('  ',' ')

# _____                  ___________________________________________
# ____/ Toolbox for LDQ /__________________________________________/
#

def getLQD(file):
   # ~~ Get all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   core = getFileContent(file)

   # ~~ Parse head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   icore = 0
   while re.match(lqd_header,core[icore]): icore += 1
   head = core[0:icore]
   # /!\ icore starts the body

   # ~~ Parse variables ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   jcore = icore+1
   while icore < len(core) and jcore < len(core):
      if re.match(lqd_header,core[icore]):
         icore += 1; jcore += 1
         continue
      if re.match(lqd_header,core[jcore]):
         jcore += 1
         continue
      core[icore].replace(',',' ')
      core[jcore].replace(',',' ')
      # ~~> Variable header
      if core[icore].split()[0].upper() != 'T':
         print '\nThought I would find T for this LQD file on this line: '+core[icore]
         sys.exit(1)
      if len(core[icore].split()) != len(core[jcore].split()):
         print '\nThought I to corresponding units for this LQD file on this line: '+core[jcore]
         sys.exit(1)
      vrs = zip( core[icore].upper().split(),core[jcore].upper().split() )

   # ~~ Size valid values ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   icore = jcore+1
   while icore < len(core):
      if not re.match(lqd_header,core[jcore]): icore += 1

   # ~~ Parse body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # This is also fairly fast, so you might not need a progress bar
   t = np.zeros( jcore-icore )
   z = np.zeros( len(vrs)-1,jcore-icore )
   itime = 0
   for icore in core[jcore+1:]:
      if re.match(lqd_header,icore): continue
      values = icore.replace(',',' ').split()
      t[itime] = float(values[0])
      for ivar in range(len(values[1:])): z[itime][ivar] = float(values[ivar])

   return head,vrs[1:],t,z

def putLQD(fle,head,vrs,date0,time,xyz):

   # ~~ Write head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   core = head
   from datetime import datetime
   core.append( "#Date&Time: "+datetime(*date0).strftime("%d/%m/%Y %H:%M:%S") )
   
   names = 'T'; units = 's'
   if xyz.ndim == 2:
      for name,unit in vrs:
         names += ' ' + name.strip().replace(' ','_')
         units += ' ' + unit.strip().replace(' ','_')
      core.append(names+'\n'+units)
   elif xyz.ndim == 3:
      for ivar in range(len(vrs[0])):
         for inod in vrs[1]:
            names += ' ' + vrs[0][ivar][0].strip().replace(' ','_') + '(' + str(inod) + ')'
            units += ' ' + vrs[0][ivar][1].strip().replace(' ','_')
      core.append(names+'\n'+units)
   if xyz.ndim == 2:
      for itim in range(xyz.shape[1]):
         line = str(time[itim])
         for ivar in range(xyz.shape[0]): line += ' ' + str(xyz[ivar][itim])
         core.append(line)
   elif xyz.ndim == 3:
      for itim in range(xyz.shape[2]):
         line = str(time[itim])
         for ivar in range(xyz.shape[0]):
            for inod in range(xyz.shape[1]): line += ' ' + str(xyz[ivar][inod][itim])
         core.append(line)

   # ~~ Put all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   putFileContent(fle,core)

   return

"""
   self.poly is a numpy object, while self.type is not.
"""
class LQD:
   fileName = ''; head = []

   def __init__(self,fileName='', vars=[],date=[1972,07,13,17,24,27],times=[],series=[]):
      if fileName != '': # read from file
         self.head,self.vrs,self.times,self.series = getLQD(self.fileName)
      else:              # set content values
         self.vrs = vars; self.times = times; self.series = series
      self.date=date

   def putContent(self,fileName):
      putLQD(fileName,self.head,self.vrs,self.date,self.times,self.series)

