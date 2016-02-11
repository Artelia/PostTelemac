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
         Tools for handling Kenue native files in python.
         Kenue and its related software (Blue Kenue, Greem Kenue, )
         are property of the NRC Canadian Hydrualics Centre
"""
"""@details
         Contains getI2S, getI3S and putI2S, putI3S, which read/write
         python variables into ASCII I2S and I3S files
"""
"""@history 26/12/2011 -- Sebastien E. Bourban:
         First trial at parsing I2S and I3S
"""
"""@history 09/01/2012 -- Sebastien E. Bourban:
         Addition of XY and XYZ parsing
"""
"""@history 13/01/2012 -- Sebastien E. Bourban:
         Creates InS class with associated methods including:
         + removeDuplicates (remove duplicated points based on proximity)
         + makeClockwise (make closed loops clockwise)
         + makeAntiClockwise (make closed loops anti-clockwise)
         + smoothSubdivise (add points and weigthed average move)
         + smoothSubsampleDistance (remove points based on proximity)
         + smoothSubsampleAngle (remove points based on flatness)
"""
"""@history 29/02/2012 -- Sebastien E. Bourban:
         The type of a contour can now be checked automatically so that
         mixed set can be stored into one I2S/I3S file. To use this
         feature, type must be absent from the putInS call.
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
ken_header = re.compile(r'[#:]')

asc_FileType = re.compile(r':FileType\s(?P<type>\b\w\w\w\b)') #\s(?P<after>.*?)\Z')
asc_AttributeName = re.compile(r':AttributeName\s(?P<number>\b(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')

var_1int = re.compile(r'(?P<before>[^\'"]*?)\b(?P<number>[+-]?(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))(?P<after>[^.].*?)\Z')
var_1dbl = re.compile(r'(?P<number>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<after>.*?)\Z')
var_2dbl = re.compile(r'(?P<number1>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<number2>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')
var_3dbl = re.compile(r'(?P<number1>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<number2>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))[\s,;]*(?P<number3>[+-]?(|[^a-zA-Z(,])(?:(\d+(|\.)\d*[dDeE](\+|\-)?\d+|\d+\.\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')
var_1str = re.compile(r'(?P<string>)(".*?")[\s,;]*(?P<after>.*?)\Z')

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def cleanSpaces(istr): # same as in parserFortran
   return istr.strip().replace('  ',' ').replace('  ',' ')

# _____                              _______________________________
# ____/ Principal Class for I2S/I3S /______________________________/
#
"""
   self.poly is a numpy object, while self.type is not.
"""
class InS:

   def __init__(self,fileName):
      # file parsing is based on the name of the extension
      _,tail = path.splitext(fileName)
      # ~~> Case of a Kenue type i2s/i3s file
      if tail in ['.i2s','.i3s']: self.parseContent(fileName)
      else:
         print '\nThe polygon file extension is required to be either i2s or i3s'
         sys.exit(1)


   # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
   # ~~~~ Parse Content ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #

   def parseContent(self,fileName):
      # TODO: Read the whole header

      # ~~ Get all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      core = getFileContent(fileName)

      # ~~ Parse head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      icore = 0; self.atrbut = {}; self.natrbut = 0; self.oatrbut = []
      while re.match(ken_header,core[icore].strip()):
         # ~~> instruction FileType
         proc = re.match(asc_FileType,core[icore].strip())
         if proc: self.fileType = proc.group('type').lower()
         # ~~> instruction AttributeName
         proc = re.match(asc_AttributeName,core[icore].strip())
         if proc:
            self.natrbut += 1
            if self.natrbut == int(proc.group('number')):
               self.oatrbut.append(proc.group('after').strip())
               self.atrbut.update({self.oatrbut[-1]:[]})
            else:
               print '... Could not read the order of your Attributes:',core[icore]
               sys.exit(1)
         # ... more instruction coming ...
         icore += 1
      self.head = core[0:icore]
      # /!\ icore starts the body

      # ~~ Parse body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      # This is also fairly fast, so you might not need a progress bar
      self.poly = []; self.vals = []; self.type = []; self.npoin = 0
      while icore < len(core):
         if core[icore].strip() == '':
            icore += 1
            continue
         # ~~> polygon head
         proc = re.match(var_1int,core[icore].strip())
         if not proc:
            print '\nCould not parse the following polyline header: '+core[icore].strip()
            sys.exit(1)
         nrec = int(proc.group('number'))
         a = proc.group('after').strip().split()
         if len(a) != self.natrbut:
            if self.natrbut != 0:
               print '... Could not find the correct number of attribute:',core[icore].strip(),', ',self.natrbut,' expected'
               sys.exit(1)
            else:
               self.natrbut = len(a)
               self.oatrbut = range(1,len(a)+1)
               self.atrbut = dict([ (i+1,[a[i]]) for i in range(len(a)) ])
         else:
            for i in range(len(self.oatrbut)): self.atrbut[self.oatrbut[i]].append(a[i])
         xyi = []; val = []; icore += 1
         for irec in range(nrec):
            nbres = core[icore+irec].strip().split()
            proc = re.match(var_1dbl,nbres[0])
            if not proc:
               proc = re.match(var_1int,nbres[0])
               if not proc:
                  print '\nCould not parse the following polyline record: '+core[icore+irec].strip()
                  sys.exit(1)
            nbres[0] = float(proc.group('number'))
            procd = re.match(var_1dbl,nbres[1])
            proci = re.match(var_1int,nbres[1])
            if procd: nbres[1] = float(procd.group('number'))
            elif proci: nbres[1] = float(procd.group('number'))
            xyi.append(nbres[:2])
            val.append(nbres[2:])
         if xyi != []:
            cls = 0
            if isClose(xyi[0],xyi[len(xyi)-1],size=10) :
               xyi.pop(len(xyi)-1)
               val.pop(len(val)-1)
               cls = 1
            self.poly.append(np.asarray(xyi,dtype=np.float))
            self.vals.append(np.asarray(val,dtype=np.float))
            self.type.append(cls)
         self.npoin += len(xyi)
         icore += nrec

      self.npoly = len(self.poly)

      # ~~ Parse attributes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      #for o in self.oatrbut:
      #   proc = re.match(var_1int,self.atrbut[o][0])
      #   if not proc:
      #      proc = re.match(var_1dbl,self.atrbut[o][0])
      #      if proc: self.atrbut[o] = np.array( self.atrbut[o], dtype=np.float )
      #   else: self.atrbut[o] = np.array( self.atrbut[o], dtype=np.int )


   # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
   # ~~~~ Write-up Content ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #
   # Note:
   #    + file parsing is based on the name of the extension
   #
   def putContent(self,fileName,head=[]):

      # ~~> file extension processing
      _,tail = path.splitext(fileName)
      if tail[1:] != self.fileType:
         if head != []:
            head = ['\n'.join(head).replace(':FileType '+self.fileType,':FileType '+tail[1:])]
         self.fileType = tail[1:]

      # ~~> write head
      if head != []: core = head
      else: core = [':FileType '+self.fileType+' ASCII EnSim 1.0',
         ':Application BlueKenue', ':Version 3.2.24',
         ':WrittenBy sebourban', ':CreationDate Thu, Dec 08, 2011 02:47 PM',
         ':Name ' + path.basename(fileName),
         #':AttributeName 1 level',
         #':AttributeType 1 float',
         #':AttributeUnits 1 m',
         ':EndHeader' ]

      # ~~> look for closed lines
      if self.type == []:
         for ip in self.poly:
            if isClose(ip[0][:2],ip[len(ip)-1][:2]): self.type.append(1)
            else: self.type.append(0)

      # ~~> fill-up empty attributes
      if self.atrbut == {}:
         self.atrbut = {1:['ArbitraryName1']}
         for _ in self.poly: self.atrbut[1].append(0)
         self.oatrbut = [1]

      # ~~> fill-up attribute names
      if head == []:
         for i,o in zip(range(len(self.oatrbut)),self.oatrbut): core.insert(-1,':AttributeName '+repr(i+1)+' '+repr(o))

      # ~~ Write body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      for i,ip,iv,it in zip(range(len(self.poly)),self.poly,self.vals,self.type):
         il = len(ip)
         if il != 0 and not isClose(ip[0],ip[len(ip)-1]): il += it
         line = repr(il)
         for o in self.oatrbut: line  = line + ' ' + str(self.atrbut[o][i])
         core.append(line)
         if self.fileType == 'i2s':
            for xyi in ip: core.append(repr(xyi[0])+' '+repr(xyi[1]))
            if il != len(ip): core.append(repr(ip[0][0])+' '+repr(ip[0][1]))
         elif self.fileType == 'i3s':
            if np.shape(iv)[1] == 0:
               for xyi in ip: core.append(repr(xyi[0])+' '+repr(xyi[1])+' 0.0')
               if il != len(ip): core.append(repr(ip[0][0])+' '+repr(ip[0][1])+' 0.0')
            else:
               for xyi,val in zip(ip,iv): core.append(repr(xyi[0])+' '+repr(xyi[1])+' '+' '.join([ repr(v) for v in val ]))
               if il != len(ip): core.append(repr(ip[0][0])+' '+repr(ip[0][1])+' '+' '.join([ repr(v) for v in iv[0] ]))

      # ~~ Put all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      putFileContent(fileName,core)

# _____                  ___________________________________________
# ____/ Toolbox for XYZ /__________________________________________/
#

def getXYn(file):
   # TODO: Read the whole header, for the time being head is copied
   #       over
   # TODO: Read multiple variables depending on type and on a list

   # ~~ Get all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   core = getFileContent(file)

   # ~~ Parse head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   icore = 0; fileType = None
   while re.match(ken_header,core[icore]):
      # ~~> instruction FileType
      proc = re.match(asc_FileType,core[icore])
      if proc: fileType = proc.group('type').lower()
      # ... more instruction coming ...
      icore += 1
   head = core[0:icore]
   if fileType == None:
      proc = re.match(var_3dbl,core[icore]+' ')
      if not proc:
         proc = re.match(var_2dbl,core[icore]+' ')
         if not proc:
            print '\nCould not parse the first record: '+core[icore]
            sys.exit(1)
         else: fileType = 'xy'
      else: fileType = 'xyz'

   # /!\ icore starts the body

   # ~~ Parse body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # This is also fairly fast, so you might not need a progress bar
   xyz = [] #; pbar = ProgressBar(maxval=len(core)).start()
   while icore < len(core):
      if fileType == 'xy':
         proc = re.match(var_2dbl,core[icore]+' ')
         if not proc:
            print '\nCould not parse the following xyz record: '+core[icore]
            sys.exit(1)
         xyz.append([float(proc.group('number1')),float(proc.group('number2'))])
      elif fileType == 'xyz':
         proc = re.match(var_3dbl,core[icore]+' ')
         if not proc:
            print '\nCould not parse the following xyz record: '+core[icore]
            sys.exit(1)
         xyz.append([float(proc.group('number1')),float(proc.group('number2')),float(proc.group('number3'))])
      icore += 1
   #pbar.finish()

   return head,fileType,xyz

def putXYn(file,head,fileType,xyz):

   # ~~ Write head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   core = head
   #if head != []: core = head
   #<else: core = [':FileType '+fileType+' ASCII EnSim 1.0',
   #   ':Application BlueKenue', ':Version 3.2.24',
   #   ':WrittenBy sebourban', ':CreationDate Thu, Dec 08, 2011 02:47 PM',
   #   ':Name ' + path.basename(file),
   #   ':AttributeUnits 1 m',
   #   ':EndHeader' ]

   # ~~ Write body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if fileType == 'xy':
      for _ in xyz: core.append(str(xyz[0])+' '+str(xyz[1]))
   elif fileType == 'xyz':
      for _ in xyz: core.append(str(xyz[0])+' '+str(xyz[1])+' '+str(xyz[2]))

   # ~~ Put all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   putFileContent(file,core)

   return
