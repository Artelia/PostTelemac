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
         Tools for handling DELWAQ files when created by TELEMAC
"""
"""@details
         Contains read/write functions for binary (big-endian) DELWAQ files
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
from struct import unpack,pack
import re
import sys
from os import path,environ,walk
import numpy as np
# ~~> dependencies towards the root of pytel
sys.path.append( path.join( path.dirname(sys.argv[0]), '..' ) ) # clever you !
from config import OptionParser,parseConfigFile, parseConfig_CompileTELEMAC
# ~~> dependencies towards other pytel/modules
from parsers.parserSELAFIN import SELAFIN,CONLIM
from utils.progressbar import ProgressBar
from utils.files import getFileContent

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#

# _____                  ___________________________________________
# ____/ Primary Classes /__________________________________________/
#

class DELWAQ:

   simplekeys = { "task":'',"geometry":'', "horizontal-aggregation":'', \
      "minimum-vert-diffusion-used":'', "vertical-diffusion":'', \
      "reference-time":'', \
      "hydrodynamic-start-time":'', "hydrodynamic-stop-time":'', "hydrodynamic-timestep":'', \
      "conversion-ref-time":'', "conversion-start-time":'', "conversion-stop-time":'', "conversion-timestep":'', \
      "grid-cells-first-direction":'', "grid-cells-second-direction":'', \
      "number-hydrodynamic-layers":'', "number-water-quality-layers":'', \
      "hydrodynamic-file":'', "aggregation-file":'', \
      "grid-indices-file":'', "grid-coordinates-file":'', "pointers-file":'', "lengths-file":'', \
      "volumes-file":'', "areas-file":'', "flows-file":'', "salinity-file":'', "temperature-file":'', \
      "vert-diffusion-file":'', "surfaces-file":'', "total-grid-file":'', "discharges-file":'', \
      "chezy-coefficients-file":'', "shear-stresses-file":'', "walking-discharges-file":'' }
   
   complxkeys = { "description":[], "constant-dispersion":[], \
      "hydrodynamic-layers":[], "water-quality-layers":[], "discharges":[] }

   emptyline = re.compile(r'\s*\Z')
   comments = re.compile(r'[#]')
   var_dquot = re.compile(r'"(?P<dquot>[^"]*)"')
   var_squot = re.compile(r"'(?P<squot>[^']*)'")
   key_word = re.compile(r'(?P<key>[^\s]+)\s*(?P<word>[^#]*)(?P<after>.*)\s*\Z',re.I)
   key_field = re.compile(r'(?P<key>[^\s]+)\s*(?P<after>.*)\s*\Z',re.I)
   grp_word = re.compile(r'(?P<key>[^\s]*)\s*\Z',re.I)

   def __init__(self,fileName):

      # ~~> Read the steering file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if not path.exists(fileName):
         print '... Could not file your DELWAQ file: ',fileName
         sys.exit()
      self.dwqList = self.parseDWQ(getFileContent(fileName))

      # ~~> Read the geometry file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = self.dwqList['grid-indices-file']
      if not path.exists(file):
         print '...Could not find the GEO file: ',file
         sys.exit()
      self.geo = SELAFIN(file)
      self.NPOIN3 = int(self.dwqList['grid-cells-first-direction'])
      if self.NPOIN3 != self.geo.NPOIN3:
         print '...In consistency in numbers with GEO file: ',self.NPOIN3,self.geo.NPOIN3
         sys.exit()
      self.NSEG3 = int(self.dwqList['grid-cells-second-direction'])

      # ~~> Read the CONLIM file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = self.dwqList['grid-coordinates-file']
      if not path.exists(file):
         print '...Could not find the CONLIM file: ',file
         sys.exit()
      self.conlim = CONLIM(file)

      # ~~> Time records ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      self.HYDRO0T = int(self.dwqList['hydrodynamic-start-time'])
      self.HYDROAT = int(self.dwqList['hydrodynamic-stop-time'])
      self.HYDRODT = int(self.dwqList['hydrodynamic-timestep'])
      self.HYDROIT = 1 + ( self.HYDROAT-self.HYDRO0T ) / self.HYDRODT
      self.HYDRO00 = 0
      self.tfrom = self.HYDRO0T
      self.tstop = self.HYDROAT

   def resetDWQ(self): self.HYDRO00 = self.HYDRO0T
 
   def minvolDWQ(self,value): self.minvol = float(value)

   def sampleDWQ(self,tfrom,tstop):
      self.tfrom = float(tfrom)
      if self.tfrom < 0: self.tfrom = self.HYDROAT + self.tfrom + 1
      self.tstop = float(tstop)
      if self.tstop < 0: self.tstop = self.HYDROAT + self.tstop + 1
      if self.tfrom > self.tstop: self.tstop = self.tfrom

   def parseDWQ(self,lines):
      dwqList = {}
      i = 0
      while i < len(lines):
         line = lines[i].strip()
         if re.match(self.comments,line):
            i += 1
            continue
         if re.match(self.emptyline,line):
            i += 1
            continue
         proc = re.match(self.grp_word,line)
         if proc:
            i += 1
            if proc.group('key').lower() in self.complxkeys.keys():
               end = 'end-' + proc.group('key')
               sroc = re.match(self.key_word,lines[i].strip())
               word = []
               while sroc.group('key').lower() != end:
                  dval = re.match(self.var_dquot,lines[i].strip())
                  sval = re.match(self.var_squot,lines[i].strip())
                  sroc = re.match(self.key_field,lines[i].strip())
                  if dval: word.append(dval.group('dquot').strip('"'))
                  elif sval: word.append(sval.group('squot').strip("'"))
                  else: word.append(lines[i].strip().strip("'"))
                  i += 1
                  sroc = re.match(self.key_word,lines[i].strip())
               i += 1
               dwqList.update({proc.group('key').lower():word})
               continue
            else:
               print '... Could not understand the following complex key: ',proc.group('key')
         proc = re.match(self.key_word,line)
         if proc:
            i += 1
            if proc.group('key').lower() in self.simplekeys.keys():
               dval = re.match(self.var_dquot,proc.group('after').strip())
               sval = re.match(self.var_squot,proc.group('after').strip())
               if dval: dwqList.update({proc.group('key').lower():dval.group('dquot').strip('"')})
               elif sval: dwqList.update({proc.group('key').lower():sval.group('squot').strip("'")})
               else: dwqList.update({proc.group('key').lower():proc.group('word').strip().strip("'")})
            else:
               print '... Could not understand the following simple key: ',proc.group('key')
         
      return dwqList

   def big2little(self):

      file = self.dwqList["surfaces-file"]
      fole = path.splitext(path.basename(file))[0] + '.qwd'
      self.big2littleBOT(file,fole)

      file = self.dwqList["lengths-file"]
      fole = path.splitext(path.basename(file))[0] + '.qwd'
      self.big2littleNDS(file,fole)

      file = self.dwqList["pointers-file"]
      fole = path.splitext(path.basename(file))[0] + '.qwd'
      self.big2littleNFX(file,fole)

      file = self.dwqList["volumes-file"]
      fole = path.splitext(path.basename(file))[0] + '.qwd'
      self.big2littlePTS(file,fole)

      file = self.dwqList["flows-file"]
      fole = path.splitext(path.basename(file))[0] + '.qwd'
      self.big2littleVFX(file,fole)

      file = self.dwqList["areas-file"]
      fole = path.splitext(path.basename(file))[0] + '.qwd'
      self.big2littleARE(file,fole)

   def big2littleBOT(self,fileName,foleName):

      # ~~ Openning files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = open(fileName,'rb')
      fole = open(foleName,'wb')
      print '           +> writing the surfaces-file: ',foleName

      # ~~ Read/Write dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      l,n1,n2,n3,n4,n5,n6,chk = unpack('>i6ii',file.read(4+24+4))
      if l != chk:
         print '... Cannot read the first 6 INTEGER from your DELWAQ file'
         sys.exit()
      fole.write(pack('<i6ii',4*6,n1,n2,n3,n4,n5,n6,4*6))

      # ~~ Read areas ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file.seek(4,1)
      AREA = np.asarray( unpack('>'+str(n1)+'f',file.read(4*n1)) )
      file.seek(4,1)
      fole.write(pack('<i',4*n1))
      fole.write(pack('<'+str(n1)+'f',*(AREA)))
      fole.write(pack('<i',4*n1))

      file.close()
      fole.close()

   def big2littleNDS(self,fileName,foleName):

      # ~~ Openning files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = open(fileName,'rb')
      fole = open(foleName,'wb')
      print '           +> writing the lengths-file: ',foleName

      # ~~ Read/Write dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      NSEG2 = ( 3*self.geo.NELEM3 + self.conlim.NPTFR )/2
      MBND2 = np.count_nonzero(self.conlim.BOR['lih'] != 2)
      n3 = 2*self.geo.NPLAN*( NSEG2 + MBND2 )
      n4 = 2*( self.geo.NPLAN-1 )*self.geo.NPOIN3

      # ~~ Read lengths ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file.seek(4*4,1)
      LENGTH = np.asarray( unpack('>'+str(n3)+'f',file.read(4*n3)) )
      file.seek(4,1)
      fole.write(pack('<iii',4,0,4))
      fole.write(pack('<i',4*n3))
      fole.write(pack('<'+str(n3)+'f',*(LENGTH)))
      fole.write(pack('<i',4*n3))

      # ~~ 3D lengths ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      #if n4 != 0:
      #   file.seek(4*n4+8,1)

      file.close()
      fole.close()

   def big2littleNFX(self,fileName,foleName):

      # ~~ Openning files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = open(fileName,'rb')
      fole = open(foleName,'wb')
      print '           +> writing the pointers-file: ',foleName

      # ~~ Read lengths ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      for iplan in range(self.geo.NPLAN):
         for i in range(self.NSEG3):
            l,n1,n2,n3,n4,chk = unpack('>i4ii',file.read(4+16+4))
            fole.write(pack('<i4ii',4*4,n1,n2,n3,n4,4*4))
         #for i in range(self.conlim.NPTFR):
         #   if self.conlim.BOR['lih'][i] != 2:
         #      l,n1,n2,n3,n4,chk = unpack('>i4ii',file.read(4+16+4))
         #      fole.write(pack('<i4ii',4*4,n1,n2,n3,n4,4*4))

      file.close()
      fole.close()

   def big2littlePTS(self,fileName,foleName):

      # ~~ Openning files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = open(fileName,'rb')
      fole = open(foleName,'wb')
      print '           +> writing the volumes-file: ',foleName

      # ~~ Read/Write dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      n1 = self.NPOIN3+1
      minvol = self.minvol * np.ones(self.NPOIN3,dtype=np.float32)

      # ~~ Read volumes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      pbar = ProgressBar(maxval=self.HYDROIT).start()
      for i in range(self.HYDROIT):
         l,it = unpack('>ii',file.read(4+4))
         VOLUME = np.asarray( unpack('>'+str(self.NPOIN3)+'f',file.read(4*self.NPOIN3)) )
         VOLUME = np.maximum(VOLUME,minvol)
         file.seek(4,1)
         if it >= self.tfrom and it <= self.tstop:
            pbar.write('            ~> read iteration: '+str(it),i)
            fole.write(pack('<ii',4*n1,it-self.HYDRO00))
            fole.write(pack('<'+str(self.NPOIN3)+'f',*(VOLUME)))
            fole.write(pack('<i',4*n1))
         else:
            pbar.write('            ~> ignore iteration: '+str(it),i)
         pbar.update(i)
      pbar.finish()

      file.close()
      fole.close()

   def big2littleVFX(self,fileName,foleName):

      # ~~ Openning files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = open(fileName,'rb')
      fole = open(foleName,'wb')
      print '           +> writing the flows-file: ',foleName

      # ~~ Read/Write dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      NSEG2 = ( 3*self.geo.NELEM3 + self.conlim.NPTFR )/2
      MBND2 = np.count_nonzero(self.conlim.BOR['lih'] != 2)
      n3 = ( NSEG2 + MBND2 )
      n4 = 2*( self.geo.NPLAN-1 )*self.geo.NPOIN3

      # ~~ Read volumes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      pbar = ProgressBar(maxval=self.HYDROIT).start()
      for i in range(self.HYDROIT):
         l,it = unpack('>ii',file.read(4+4))
         VFLUXES = np.asarray( unpack('>'+str(n3)+'f',file.read(4*n3)) )
         file.seek(4,1)
         if it >= self.tfrom and it <= self.tstop:
            pbar.write('            ~> read iteration: '+str(it),i)
            fole.write(pack('<ii',4*n3,it-self.HYDRO00))
            fole.write(pack('<'+str(n3)+'f',*(VFLUXES)))
            fole.write(pack('<i',4*n3))
         else:
            pbar.write('            ~> ignore iteration: '+str(it),i)
         pbar.update(i)
      pbar.finish()

      file.close()
      fole.close()

   def big2littleARE(self,fileName,foleName):

      # ~~ Openning files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      file = open(fileName,'rb')
      fole = open(foleName,'wb')
      print '           +> writing the areas-file: ',foleName

      # ~~ Read/Write dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      NSEG2 = ( 3*self.geo.NELEM3 + self.conlim.NPTFR )/2
      MBND2 = np.count_nonzero(self.conlim.BOR['lih'] != 2)
      n3 = ( NSEG2 + MBND2 )
      n4 = 2*( self.geo.NPLAN-1 )*self.geo.NPOIN3

      # ~~ Read volumes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      pbar = ProgressBar(maxval=self.HYDROIT).start()
      for i in range(self.HYDROIT):
         l,it = unpack('>ii',file.read(4+4))
         AREAS = np.asarray( unpack('>'+str(n3)+'f',file.read(4*n3)) )
         file.seek(4,1)
         if it >= self.tfrom and it <= self.tstop:
            pbar.write('            ~> read iteration: '+str(it),i)
            fole.write(pack('<ii',4*n3,it-self.HYDRO00))
            fole.write(pack('<'+str(n3)+'f',*(AREAS)))
            fole.write(pack('<i',4*n3))
         else:
            pbar.write('            ~> ignore iteration: '+str(it),i)
         pbar.update(i)
      pbar.finish()

      file.close()
      fole.close()


# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban"
__date__ ="$21-Jun-2013 17:51:29$"

if __name__ == "__main__":
   debug = False

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Reads config file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nLoading Options and Configurations\n\
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
   USETELCFG = ''
   if environ.has_key('USETELCFG'): USETELCFG = environ['USETELCFG']
   SYSTELCFG = 'systel.cfg'
   if environ.has_key('SYSTELCFG'): SYSTELCFG = environ['SYSTELCFG']
   if path.isdir(SYSTELCFG): SYSTELCFG = path.join(SYSTELCFG,'systel.cfg')
   parser = OptionParser("usage: %prog [options] \nuse -h for more help.")
   parser.add_option("-c", "--configname",type="string",dest="configName",default=USETELCFG,help="specify configuration name, default is randomly found in the configuration file" )
   parser.add_option("-f", "--configfile",type="string",dest="configFile",default=SYSTELCFG,help="specify configuration file, default is systel.cfg" )
   parser.add_option("-r", "--rootdir",type="string",dest="rootDir",default='',help="specify the root, default is taken from config file" )
   parser.add_option("-v", "--version",type="string",dest="version",default='',help="specify the version number, default is taken from config file" )
   parser.add_option("--reset",action="store_true",dest="areset",default=False,help="reset the start time to zero" )
   parser.add_option("--minvol",type="string",dest="minvol",default='0.001',help="make sure there is a minimum volume" )
   parser.add_option("--from",type="string",dest="tfrom",default="1",help="specify the first frame included" )
   parser.add_option("--stop",type="string",dest="tstop",default="-1",help="specify the last frame included (negative from the end)" )
   options, args = parser.parse_args()
   if not path.isfile(options.configFile):
      print '\nNot able to get to the configuration file: ' + options.configFile + '\n'
      dircfg = path.abspath(path.dirname(options.configFile))
      if path.isdir(dircfg) :
         print ' ... in directory: ' + dircfg + '\n ... use instead: '
         for dirpath,dirnames,filenames in walk(dircfg) : break
         for file in filenames :
            head,tail = path.splitext(file)
            if tail == '.cfg' : print '    +> ',file
      sys.exit()

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Works for only one configuration ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   cfgs = parseConfigFile(options.configFile,options.configName)
   cfgname = cfgs.keys()[0]
   if options.rootDir != '': cfgs[cfgname]['root'] = options.rootDir
   if options.version != '': cfgs[cfgname]['version'] = options.version
   cfg = parseConfig_CompileTELEMAC(cfgs[cfgname])

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Reads command line arguments ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if len(args) < 1:
      print '\nAt least one DELWAQ steering file name is required\n'
      parser.print_help()
      sys.exit()
   fileNames = args

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Loop over the DELWAQ files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for file in fileNames:

      # ~~> Parse DELWAQ steering file
      print '      ~> scanning your DELWAQ file: ',path.basename(file)
      dwq = DELWAQ(file)
      
      # ~~> Possible options so far
      if options.areset: dwq.resetDWQ()
      dwq.minvolDWQ(options.minvol)
      dwq.sampleDWQ(options.tfrom,options.tstop)

      # ~~> Convert to Little Endian
      dwq.big2little()


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit()
