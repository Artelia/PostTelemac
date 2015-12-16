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
from samplers.polygons import isClockwise

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#
ken_header = re.compile(r'[#:]')

asc_FileType = re.compile(r':FileType\s(?P<type>\b\w\w\w\b)') #\s(?P<after>.*?)\Z')
asc_AttributeName = re.compile(r':AttributeName\s(?P<number>\b(|[^a-zA-Z(,])(?:(\d+)(\b|[^a-zA-Z,)])))(?P<after>.*?)\Z')

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

def getInS(file):
   # TODO: Read the whole header, for the time being head is copied
   #       over
   # TODO: Read variables depending on type and on a list

   # ~~ Get all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   core = getFileContent(file)

   # ~~ Parse head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   icore = 0; atrbut = {}; natrbut = 0
   while re.match(ken_header,core[icore]):
      # ~~> instruction FileType
      proc = re.match(asc_FileType,core[icore])
      if proc: fileType = proc.group('type').lower()
      # ~~> instruction AttributeName
      proc = re.match(asc_AttributeName,core[icore])
      if proc:
         natrbut += 1
         if natrbut == int(proc.group('number')):
            atrbut.update({natrbut:[proc.group('after').strip()]})
         else:
            print '... Could not read the order of your Attributes:',core[icore]
            sys.exit()
      # ... more instruction coming ...
      icore += 1
   head = core[0:icore]
   # /!\ icore starts the body

   # ~~ Parse body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # This is also fairly fast, so you might not need a progress bar
   poly = []; type = []; npoin = 0
   while icore < len(core):
      if core[icore].strip() == '':
         icore += 1
         continue
      # ~~> polygon head
      proc = re.match(var_1int,core[icore])
      if not proc:
         print '\nCould not parse the following polyline header: '+core[icore]
         sys.exit()
      nrec = int(proc.group('number'))
      a = proc.group('after').strip().split()
      if len(a) != natrbut:
         print '... Could not find the correct number of attribute:',core[icore],', ',natrbut,' expected'
         sys.exit()
      for i in atrbut.keys(): atrbut[i].append(a[i-1])
      xyi = []; icore += 1
      for irec in range(nrec):
         nbres = core[icore+irec].split()
         proc = re.match(var_1dbl,nbres[0])
         if not proc:
            proc = re.match(var_1int,nbres[0])
            if not proc:
               print '\nCould not parse the following polyline record: '+core[icore+irec]
               sys.exit()
         nbres[0] = float(proc.group('number'))
         proc = re.match(var_1dbl,nbres[1])
         if not proc:
            proc = re.match(var_1int,nbres[1])
            if not proc:
               print '\nCould not parse the following polyline record: '+core[icore+irec]
               sys.exit()
         nbres[1] = float(proc.group('number'))
         xyi.append(nbres)
      if xyi != []:
         cls = 0
         if isClose(xyi[0],xyi[len(xyi)-1],size=10) :
            xyi.pop(len(xyi)-1)
            cls = 1
         poly.append(np.asarray(xyi))
         type.append(cls)
      npoin += len(xyi)
      icore += nrec

   return head,fileType,npoin,poly,type,atrbut

def putInS(file,head,fileType,poly,type=None,atrbut=None):

   # ~~ Write head ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if head != []: core = head
   else: core = [':FileType '+fileType+' ASCII EnSim 1.0',
      ':Application BlueKenue', ':Version 3.2.24',
      ':WrittenBy sebourban', ':CreationDate Thu, Dec 08, 2011 02:47 PM',
      ':Name ' + path.basename(file),
      ':AttributeUnits 1 m',
      ':EndHeader' ]

   # ~~ Look for closed lines ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if type == None:
      type = []
      for ip in poly:
         if isClose(ip[0],ip[len(ip)-1]): type.append(True)
         else: type.append(False)

   # ~~ Look for closed lines ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if atrbut == None:
      atrbut = {1:['name']}
      for p in poly: atrbut[1].append('0')

   # ~~ Write body ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for i,ip,it in zip(range(len(poly)),poly,type):
      il = len(ip)
      if il != 0 and not isClose(ip[0],ip[len(ip)-1]): il += it
      line = str(il)
      for a in range(len(atrbut.keys())): line  = line + ' ' + atrbut[a+1][i+1]
      core.append(line)
      if fileType == 'i2s':
         for xyi in ip: core.append(str(xyi[0])+' '+str(xyi[1]))
         if il != len(ip): core.append(str(ip[0][0])+' '+str(ip[0][1]))
      elif fileType == 'i3s':
         for xyi in ip: core.append(str(xyi[0])+' '+str(xyi[1])+' '+str(xyi[2]))
         if il != len(ip): core.append(str(ip[0][0])+' '+str(ip[0][1])+' '+str(ip[0][2]))

   # ~~ Put all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   putFileContent(file,core)

   return

"""
   self.poly is a numpy object, while self.type is not.
"""
class InS:

   def __init__(self,fileName):
      self.fileName = fileName
      if fileName != '':
         self.head,self.fileType,self.npoin,self.poly,self.type,self.atrbut = getInS(self.fileName)

   def putContent(self,fileName):
      putInS(fileName,self.head,self.fileType,self.poly,self.type,self.atrbut)

   def sph2ll(self,(long0,lat0)):
      radius  = 6371000.
      long0 = np.deg2rad(float(long0)); lat0 = np.deg2rad(float(lat0))
      const = np.tan( lat0/2. + np.pi/4. )
      for poly in self.poly:
         for ip in range(len(poly)):
            poly[ip] = [np.rad2deg( poly[ip][0]/radius + long0 ),np.rad2deg( 2.*np.arctan( const*np.exp(poly[ip][1]/radius) ) - np.pi/2. )]

   def ll2sph(self,(long0,lat0)):
      radius  = 6371000.
      long0 = np.deg2rad(float(long0)); lat0 = np.deg2rad(float(lat0))
      const = np.tan( lat0/2. + np.pi/4. )
      for poly in self.poly:
         for ip in range(len(poly)):
            poly[ip] = [radius * ( np.deg2rad(poly[ip][0]) - long0 ),radius * ( np.log( np.tan( np.deg2rad(poly[ip][1])/2. + np.pi/4. ) ) - np.log( const ) )]

   def removeDuplicates(self):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      ip = 0
      while ip < len(self.poly):
         ibar += len(self.poly[ip])
         lb = len(self.poly[ip])
         self.poly[ip],self.type[ip] = removeDuplicates(self.poly[ip],self.type[ip])
         la = len(self.poly[ip])
         if la < lb: pbar.write('    +> removed '+str(lb-la)+' points of '+str(lb)+' from polygon '+str(ip+1),ibar)
         if self.poly[ip] == []:
            pbar.write('    +> removed entire polygon '+str(ip+1),ibar)
            self.poly.pop(ip)
            self.type.pop(ip)
         else: ip += 1
         pbar.update(ibar)
      pbar.finish()
      return self.poly,self.type

   def removeDuplilines(self):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      ip = 0
      while ip < len(self.poly):
         ibar += len(self.poly[ip])
         p,t = removeDuplilines(self.poly[ip],self.type[ip])
         pbar.trace() # /!\ the call requires sub-progress bar
         if len(p) > 1:
            pbar.maxval -= len(self.poly[ip])
            ibar -= len(self.poly[ip])
            self.poly.pop(ip)
            self.type.pop(ip)
            for po,to in zip(p,t):
               pbar.maxval += len(po)
               self.poly.append(po)
               self.type.append(to)
         else:
            ip += 1
         pbar.update(ibar)
      pbar.finish()
      return self.poly,self.type

   def removeDuplangles(self):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      ip = 0
      while ip < len(self.poly):
         ibar += len(self.poly[ip])
         lb = len(self.poly[ip])
         self.poly[ip],self.type[ip] = removeDuplangles(self.poly[ip],self.type[ip])
         la = len(self.poly[ip])
         if la < lb: pbar.write('    +> removed '+str(lb-la)+' points of '+str(lb)+' from polygon '+str(ip+1),ibar)
         if self.poly[ip] == []:
            pbar.write('    +> removed entire polygon '+str(ip+1),ibar)
            self.poly.pop(ip)
            self.type.pop(ip)
         else: ip += 1
         pbar.update(ibar)

      pbar.finish()
      return self.poly,self.type

   def makeClockwise(self):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      for ip in range(len(self.poly)):
         ibar += len(self.poly[ip])
         if self.type[ip] != 0:
            if not isClockwise(self.poly[ip]):
               pbar.write('    +> turned clockwise polygon '+str(ip+1),ibar)
               self.poly[ip] = np.flipud(self.poly[ip])
         pbar.update(ibar)
      pbar.finish()
      return self.poly

   def makeAntiClockwise(self):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      for ip in range(len(self.poly)):
         ibar += len(self.poly[ip])
         if self.type[ip] != 0:
            if isClockwise(self.poly[ip]):
               pbar.write('    +> turned anti-clockwise polygon '+str(ip+1),ibar)
               self.poly[ip] = np.flipud(self.poly[ip])
         pbar.update(ibar)
      pbar.finish()
      return

   def smoothSubdivise(self,weight=0.5):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      for ip in range(len(self.poly)):
         ibar += len(self.poly[ip])
         lb = len(self.poly[ip])
         self.poly[ip],self.type[ip] = smoothSubdivise(self.poly[ip],self.type[ip],weight)
         la = len(self.poly[ip])
         if la > lb: pbar.write('    +> added '+str(la-lb)+' points to polygon '+str(ip+1),ibar)
         pbar.update(ibar)
      pbar.finish()
      return self.poly,self.type

   def smoothSubsampleDistance(self,distance):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~/^\~~~~~~~~
      #                          subsampling by distance \_/
      ip = 0
      while ip < len(self.poly):
         ibar += len(self.poly[ip])
         lb = len(self.poly[ip])
         self.poly[ip],self.type[ip] = subsampleDistance(self.poly[ip],self.type[ip],distance)
         la = len(self.poly[ip])
         if la < lb: pbar.write('    +> removed '+str(lb-la)+' points of '+str(lb)+' from polygon '+str(ip+1),ibar)
         if self.poly[ip] == []:
            pbar.write('    +> removed entire polygon '+str(ip+1),ibar)
            self.poly.pop(ip)
            self.type.pop(ip)
         else: ip += 1
         #pbar.update(ibar)

      pbar.finish()
      return self.poly,self.type

   def smoothSubsampleAngle(self,angle):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~/^\~~~~~~~~
      #                            subsampling by anlgle \_/
      ip = 0
      while ip < len(self.poly):
         ibar += len(self.poly[ip])
         lb = len(self.poly[ip])
         self.poly[ip],self.type[ip] = subsampleAngle(self.poly[ip],self.type[ip],angle)
         la = len(self.poly[ip])
         if la < lb: pbar.write('    +> removed '+str(lb-la)+' points of '+str(lb)+' from polygon '+str(ip+1),ibar)
         if self.poly[ip] == []:
            pbar.write('    +> removed entire polygon '+str(ip+1),ibar)
            self.poly.pop(ip)
            self.type.pop(ip)
         else: ip += 1
         #pbar.update(ibar)

      pbar.finish()
      return self.poly,self.type

   """
   Early work by S.E.Bourban ... will be replaced by more recent work from M.S.Turnbull

   def cutAngleJoinSplit(self,angle,distance,stencil):
      ibar = 0; pbar = ProgressBar(maxval=self.npoin).start()
      ip = 0
      while ip < len(self.poly):
         ibar += len(self.poly[ip])
         if self.type[ip] == 0:
            ip += 1; pbar.update(ibar)
            continue # \!/ Only do the rest for closed polygons
         lb = len(self.poly[ip])
         if isClockwise(self.poly[ip]):
            self.poly[ip],loops = cutAngleJoinSplit(
               np.flipud(self.poly[ip]),angle,distance,stencil )
         else:
            self.poly[ip],loops = cutAngleJoinSplit(
               self.poly[ip],angle,distance,stencil )
         sys.exit()
         la = len(self.poly[ip])
         if la < lb: pbar.write('    +> removed '+str(lb-la)+' points of '+str(lb)+' from polygon '+str(ip+1),ibar)
         if len(loops) > 0: pbar.write('    +> separate loops created from polygon '+str(ip+1),ibar)
         if self.poly[ip] == []:
            pbar.write('    +> removed entire polygon '+str(ip+1),ibar)
            self.poly.pop(ip)
            self.type.pop(ip)
         else: ip += 1
         pbar.update(ibar)

      return self.poly,self.type
   """

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
            sys.exit()
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
            sys.exit()
         xyz.append([float(proc.group('number1')),float(proc.group('number2'))])
      elif fileType == 'xyz':
         proc = re.match(var_3dbl,core[icore]+' ')
         if not proc:
            print '\nCould not parse the following xyz record: '+core[icore]
            sys.exit()
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
      for i in xyz: core.append(str(xyz[0])+' '+str(xyz[1]))
   elif fileType == 'xyz':
      for i in xyz: core.append(str(xyz[0])+' '+str(xyz[1])+' '+str(xyz[2]))

   # ~~ Put all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   putFileContent(file,core)

   return
