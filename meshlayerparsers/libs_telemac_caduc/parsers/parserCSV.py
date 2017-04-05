#!/usr/bin/env python
"""@author Juliette Parisi
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
         Tools for handling ASCII data files (such as CSV) in python.
"""
"""@details
         Contains the main classes allowing read/write of data
         into ASCII CSV files
"""
"""@history 17/05/2013 -- Sebastien E. Bourban, Juliette Parisi
         Addition of the CSV class with its read/write methods
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import sys
import re
from os import path,remove
from types import *
import numpy as np

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#
csv_header = re.compile(r'#')

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def cleanSpaces(istr): # same as in parserFortran
   return istr.strip().replace('  ',' ').replace('  ',' ')

# _____                  ___________________________________________
# ____/ Primary Classes /__________________________________________/
#
var_bracks = re.compile(r'(?P<name>.*?)(?P<unit>\([\w,*\s+-/:]*?\))')
csv_header = re.compile(r'[#]')

class CSV:
   
   def __init__(self,fileName=''):
      self.rowheader = []
      self.rowvars = []
      self.rowunits = []
      self.colvars = ''
      self.colunits = ''
      self.colcore = None
      if fileName != '': self.getFileContent(fileName)

   def getColumns(self,vrs):
      # ~~> identify column subset
      subset = []
      colvar = self.colvars+' '+self.colunits
      rowvar = []
      v = vrs.split(';')
      for ivar in range(len(v)):
         vi = v[ivar].split(':')[0]
         for i in range(len(self.rowvars)):
            if vi.lower() in self.rowvars[i].lower():
               subset.append(i+1)
               rowvar.append(self.rowvars[i]+' '+self.rowunits[i])
      return (colvar,self.colcore[0]),[('',rowvar,self.colcore[subset])]

   def addColumns(self,x,ys):
      if self.colcore == None:
         xunit = '(-)'
         xname,x0 = x
         proc = re.match(var_bracks,xname)
         if proc:
            xname = proc.group('name').strip()
            xunit = proc.group('unit').strip()
         self.colvars = xname
         self.colunits = xunit
         self.colcore = np.array([x0])
      elif len(x[1]) != len(self.colcore[0]):
         print '... cannot aggregate columns of different supports: ',x[0]
         sys.exit(1)
      u0 = '(-)'
      ynames,y0 = ys
      dim = len(ynames) - 1
      # ynames[0] is an extra meta data
      if dim == 1:         # /!\ This has been checked
         # ~~> This is called for cast objects, for intance
         n0 = ynames[1]
         for i0 in range(len(n0)): # each variables
            proc = re.match(var_bracks,n0[i0])
            if proc:
               n0[i0] = proc.group('name').strip()
               u0 = proc.group('unit').strip()
            self.rowvars.append(n0[i0])
            self.rowunits.append(u0)
            self.colcore = np.vstack((self.colcore,y0[i0]))
      elif dim == 2:
         # ~~> This is called for 1d:history, for instance
         n0,n1 = ynames[1:]
         for i1 in range(len(n1)):
            for i0 in range(len(n0)):
               proc = re.match(var_bracks,n0[i0])
               if proc:
                  n0[i0] = proc.group('name').strip()
                  u0 = proc.group('unit').strip()
               self.rowvars.append(n0[i0]+':'+str(n1[i1]))
               self.rowunits.append(u0)
               self.colcore = np.vstack((self.colcore,y0[i0][i1]))
      elif dim == 3:       # /!\ This has been checked
         # ~~> This is called for 1d:v-section, for instance
         n0,n1,n2 = ynames[1:]
         for i2 in range(len(n2)):       # each plan
            for i1 in range(len(n1)):    # each time
               for i0 in range(len(n0)): # each variables
                  self.rowvars.append(n0[i0]+':'+str(n1[i1])+'_'+str(n2[i2]))
                  self.rowunits.append(u0)
                  self.colcore = np.vstack((self.colcore,y0[i0][i1][i2]))
      elif dim == 4:
         n0,n1,n2,n3 = ynames[1:]
         for i3 in range(len(n3)):
            for i2 in range(len(n2)):
               for i1 in range(len(n1)):
                  for i0 in range(len(n0)):
                     self.rowvars.append(n0[i0]+':'+str(n1[i1])+'_'+str(n2[i2])+'_'+str(n3[i3]))
                     self.rowunits.append(u0)
                     self.colcore = np.vstack((self.colcore,y0[i0][i1][i2][i3]))

   def putFileContent(self,fileName):
      if path.exists(fileName): remove(fileName)
      SrcF = open(fileName,'wb')
      if len(self.rowheader) > 0: SrcF.write('\n'.join(self.rowheader)+'\n')
      else: SrcF.write('#\n#\n') # TODO: use header for meta data
      SrcF.write(self.colvars+','+','.join(self.rowvars)+'\n')
      SrcF.write(self.colunits+','+','.join(self.rowunits)+'\n')
      np.savetxt(SrcF,self.colcore.T,delimiter=',')
      SrcF.close()

   def getFileContent(self,fileName):
      if not path.exists(fileName):
         print '... could not find your CSV file: ',fileName
         sys.exit(1)
      SrcF = open(fileName,'r')
      # ~~> parse header
      isHead = True
      while isHead:
         line = SrcF.readline()
         if line[0] == '#': self.rowheader.append(line.rstrip())
         else: isHead = False
      # ~~> parse variables / units
      if ',' not in line.rstrip():
         print '... could not find more than one column in your CSV file: ',fileName
         print 'you need at one support column, either T(time), L(length), X and Y (coordinates), but found only ',line
         sys.exit(1)
      vars = line.rstrip().split(',')
      self.colvars = vars[0]
      self.rowvars = vars[1:]
      line = SrcF.readline()
      units = line.rstrip().split(',')
      self.colunits = units[0]
      self.rowunits = units[1:]
      # ~~> parse main values
      SrcF.seek(0)
      data = np.loadtxt(SrcF, comments='#', skiprows=4, delimiter=',')
      self.colcore = data.T
      # ~~> closure
      SrcF.close()

if __name__ == "__main__":
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Loading comand line options ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)
