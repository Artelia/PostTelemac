"""@author David H. Roscoe and Sebastien E. Bourban
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
"""@history 15/08/2011 -- Sebastien E. Bourban:
         Major re-work of this XML parser
"""
"""@history 16/03/2011 -- Sebastien E. Bourban:
         Development of new classes to handle ACTIONS and PLOTS
"""
"""@history 19/03/2011 -- Sebastien E. Bourban:
         Addition of a figure name for the non display option and
         handling of the backend display switch option for Jenkins's
         virtual boxes
"""
"""@history 19/05/2012 -- Fabien Decung:
         For partial compatibility issues with Python 2.6.6, replaced
         iter() by findall()
"""
"""@history 18/06/2012 -- Sebastien E. Bourban & Fabien Decung
         Calls to sys.exit() and os.system() have been progressively captured
         into a try/except statement to better manage errors.
         This, however, assumes that all errors are anticipated.
"""
"""@history 19/03/2011 -- Sebastien E. Bourban:
         Now capable of running/tranlating, etc. coupled simulations
         "links" has been added to the active aciton list.
"""
"""@history 08/03/2013 -- Juliette Parisi:
         Added the new extract Class in order to run post processing steps
		       as running executables, other python scripts, reading and writting
		       csv files ...
"""
"""@history 27/04/2013 -- Sebastien E. Bourban:
         Now capable of differentiating PRINCI files by comparing with
         original sources.
         Also separated python / executable running as an action rather
         than an extraction
"""
"""@history 27/07/2013 -- Sebastien E. Bourban:
         Addition of a rank at the level of the XML file, in the top
            "validation" key.
"""
"""@history 27/05/2014 -- Sebastien E. Bourban:
         Major modification to the looping logic of the XML file.
         Instead of split ACTIONs, GETs, PLOTs, ... it now does these in order
            of appreance in the XML file.
"""
"""@brief
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
from os import path, remove, walk, chdir
from optparse import Values
import sys
from copy import deepcopy
from socket import gethostname
from types import StringTypes
from fractions import gcd
# ~~> dependencies added for casting within XML
import numpy as np
import math
# ~~> dependencies from within pytel/parsers
from parserKeywords import scanDICO,scanCAS,readCAS,rewriteCAS,translateCAS, getCASLang,getKeyWord,setKeyValue, getIOFilesSubmit
from parserSortie import getLatestSortieFiles
#from parserCSV import getVariableCSV,putDataCSV,addColumnCSV
from parserFortran import getPrincipalWrapNames,filterPrincipalWrapNames
# ~~> dependencies towards the root of pytel
from runcode import runCAS,getNCSIZE,compilePRINCI
# ~~> dependencies towards other pytel/modules
sys.path.append( path.join( path.dirname(sys.argv[0]), '..' ) ) # clever you !
from utils.files import getFileContent,putFileContent,addFileContent,createDirectories,copyFile,moveFile, matchSafe,diffTextFiles
from utils.messages import filterMessage, MESSAGES
from mtlplots.myplot1d import decoDefault as decoDefault1D
from mtlplots.myplot2d import decoDefault as decoDefault2D
from mtlplots.myplot3d import decoDefault as decoDefault3D
from mtlplots.myplot1d import Figure1D,Dumper1D
from mtlplots.myplot2d import Figure2D,Dumper2D
from mtlplots.myplot3d import Figure3D,Dumper3D
from samplers.mycast import Caster

# _____                  ___________________________________________
# ____/ Test case validation Toolkit /_____________________________/
#
# Function used in the xml files to do the comparaison between two files
#
def mapdiff(a1,a2):
   """
      @brief Create a new values containing the diff of the values 
      of the two arguments 

      @param a1 A Values object containing the keys {support,names,values,time}
      @param a2 A Values object containing the keys {support,names,values,time}

      @return A 4-uple (time,nameOfTheVariables,support,values)
   """
   # Cheking they have the same shape should be (ntime,nvar,npoin)
   diff = np.zeros(a2.values.shape,dtype=a2.values.dtype)
   # With ntime = 1
   if a1.values.shape != a2.values.shape:
      print "Error in files the two array do not have the same shape"
      print "a1 shape: ",a1.values.shape
      print "a2 shape: ",a2.values.shape
      return None
   # Shape of the values should be (ntime,nvar,npoin)
   ntime,nvar,npoin = a2.values.shape

   # Checking that it is the same variables in each files
   for ivar in range(nvar):
      if a1.names[ivar][0:15] != a2.names[ivar][0:15]:
         raise Exception([{
              'name':'mapdiff',
              'msg':'The name of the two variable are different \n'+\
                    a1.names[ivar][0:15]+' for a1\n'+\
                    a2.names[ivar][0:15]+' for a2'}])

   # Checking if we have the same time step
   if abs(a1.time[0] - a2.time[0]) > 1e-6:
      raise Exception([{
           'name':'mapdiff',
           'msg':'The time of the two times are different \n'+\
                 a1.time[0]+' for a1\n'+\
                 a2.time[0]+' for a2'}])

   # Making a1-a2 for each variable and each point
   for ivar in range(nvar):
      for i in range(npoin):
         diff[0][ivar][i] = abs(a2.values[0][ivar][i]\
                                 - a1.values[0][ivar][i])
   return a2.time,a2.names,a2.support,diff

def checkval(a0,eps):
   """
      @brief Will loop on all variable and display the max error

      @param a0 A Values object containg the difference between two results
      @param eps The epsilon for each variable or a global one

      @return True if all the variable max are below EPS
              False otherwise
   """
   ntime,nvar,npoin = a0.values.shape
   # Getting eps for each variable 
   if not eps:
      # if eps is empty setting default value i.e. 1
      print " "*8+"~> TODO: Set Epsilon value"
      EPS = [1.e-4]*nvar
   elif len(eps) == 1:
      # If only one was given using it for all the variables
      EPS = [eps[0]]*nvar
   elif len(eps) != nvar:
      # Otherwise one mus be given for each variable
      print "Error in length of espilon"
      return False
   else:
      EPS = eps

   print " "*8+"~> Validation for time (in reference file):",a0.time[0]
   # Loop on variables 
   value=False
   for ivar in range(nvar):
      err = max(a0.values[0][ivar])
      print " "*10+"- Difference for variable ",a0.names[ivar],": ",err
      if err >= EPS[ivar]:
         print " "*12+"Epsilon reached",EPS[ivar]
         value=True
   return value   
# _____                           __________________________________
# ____/ Specific TELEMAC Toolbox /_________________________________/
#
#   Global dictionnaries to avoid having to read these more than once
#   The keys are the full path to the dictionnaries and therefore
#      allows for <root> and <version> to change
DICOS = {}

def getDICO(cfg,code):

   dicoFile = path.join(cfg['MODULES'][code]['path'],code+'.dico')
   if dicoFile not in DICOS:
      print '    +> register this DICO file: ' + dicoFile
      frgb,dico = scanDICO(dicoFile)
      idico,odico = getIOFilesSubmit(frgb,dico)
      globals()['DICOS'].update({dicoFile:{ 'frgb':frgb, 'dico':dico, 'input':idico, 'output':odico }})

   return dicoFile

# _____                      _______________________________________
# ____/ General XML Toolbox /______________________________________/
#
"""
   Will read the xml's XML keys based on the template do.
   +: those with None are must have
   +: those without None are optional and reset if there
   Will add extra keys even if it does ont know what to do.
"""
def getXMLKeys(xml,do):

   xcpt = []                            # try all keys for full report
   done = do.copy()                     # shallow copy is here sufficient
   for key in done:
      if key not in xml.keys():
         if done[key] == None:
            xcpt.append({'name':'getXMLKeys','msg':'cannot find the key: '+key})
      else:
         done[key] = xml.attrib[key]
   if xcpt != []: raise Exception(xcpt) # raise full report
   for key in xml.keys():
      if key not in done:
         done[key] = xml.attrib[key]

   return done

def setSafe(casFile,cas,idico,odico,safe):

   sacFile = path.join(safe,path.basename(casFile))
   putFileContent(sacFile,rewriteCAS(cas))
   # copyFile(casFile,safe)   # TODO: look at relative paths
   wDir = path.dirname(casFile)

   # ~~> process sortie files if any
   sortieFiles = getLatestSortieFiles(sacFile)

   # ~~> process input / output
   iFS = []; oFS = []
   for k,v in zip(*cas[1]):
      if k in idico:
         if idico[k].split(';')[-1] == 'CAS': continue
         if v[0].strip("'\"") == '': continue
         copyFile(path.join(wDir,v[0].strip("'\"")),safe)
         ifile = path.join(safe,v[0].strip("'\""))
         iFS.append([k,[ifile],idico[k]])
         #if not path.isfile(ifile):
         #   print '... file does not exist ',ifile
         #   sys.exit(1)
      if k in odico:
         ofile = path.join(safe,v[0].strip("'\""))
         oFS.append([k,[ofile],odico[k]])

   return sortieFiles,iFS,oFS

def findTargets(dido,src):
   layer = []

   if src in dido: layer = [dido[src],'',src]
   if layer == [] and 'input' in dido:
      for i,j,k in dido['input']:
         k = k.split(';')
         if src in k[1]:               # filename, fileForm, fileType
            # /!\ Temporary fix because TOMAWAC's IOs names are not yet standard TELEMAC
            if k[5] =='SCAL': k[5] = k[1]
            # \!/
            layer = [j,k[3],k[5]]
   if layer == []  and 'output' in dido:
      if dido['code'] == 'postel3d':
         for file in dido['output']:
            if src == path.basename(file) : layer = [[file],'','SELAFIN']
      else :
         for i,j,k in dido['output']:
            k = k.split(';')
            if src in k[1]:               # filename, fileForm, fileType
               # /!\ Temporary fix because TOMAWAC's IOs names are not yet standard TELEMAC
               if k[5] =='SCAL': k[5] = k[1]
               # \!/
               layer = [j,k[3],k[5]]
   if layer == [] and 'links' in dido:
      for mod in dido['links']:
         if layer == [] and 'iFS' in dido['links'][mod]:
            for i,j,k in dido['links'][mod]['iFS']:
               k = k.split(';')
               if src in k[1]:               # filename, fileForm, fileType
                  # /!\ Temporary fix because TOMAWAC's IOs names are not yet standard TELEMAC
                  if k[5] =='SCAL': k[5] = k[1]
                  # \!/
                  layer = [j,k[3],k[5]]
         if layer == []  and 'oFS' in dido['links'][mod]:
            if dido['links'][mod]['code'] == 'postel3d':
               for file in dido['links'][mod]['oFS']:
                  if src == path.basename(file) : layer = [[file],'','SELAFIN']
            else :
               for i,j,k in dido['links'][mod]['oFS']:
                  k = k.split(';')
                  if src in k[1]:               # filename, fileForm, fileType
                     # /!\ Temporary fix because TOMAWAC's IOs names are not yet standard TELEMAC
                     if k[5] =='SCAL': k[5] = k[1]
                     # \!/
                     layer = [j,k[3],k[5]]

   if layer == [] and 'type' in dido:
      if dido['type'] == src: layer = [[dido['target']],'',src]

   return layer

# _____                        _____________________________________
# ____/ Primary Class: ACTION /____________________________________/
#
"""
   In the classes below, the double quoted keys refer to the keys
      of the XML file. Contrarily, the single quoted keys in
      because they are internal to the python scripts.
   In the XML file, you can have multiple actions and each action
      will be associated with multiple configurations:
      did.keys() => array [xref] for each action
      did[xref].keys() => array [cfgname] for each possible configuration
      did[xref][cfgname].keys() =>
         - 'target', basename of the CAS file
         - 'cas', scanned CAS file
         - 'code', name of the module
         - 'title', title of the action (xref)
         - 'cmaps', refer to the directory 'ColourMaps' for colour plotting
         - 'deprefs', refer to the files that need copying from path to safe
         - 'outrefs', refer to the files that need copying from safe to path
         - 'where' will not default to xref anymore, allowing files to
      be shared and located at the same place between actions
"""
class ACTION:

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #                                                General Methods
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   availacts = ''
   availkeys = { 'path':'','safe':'','cfg':'',
         "target": '', "xref": '', "do": '', "rank":'', "set": '',
         "title": '', "deprefs":'', "outrefs":'', "where":'' }

   def __init__(self,title='',bypass=True):
      self.active = {}
      if title != '': self.active["title"] = title
      self.bypass = bypass
      self.dids = {}
      self.path = ''
      self.safe = ''

   def addAction(self,actions,rank=''):
      self.active.update(deepcopy(self.availkeys))
      self.active['path'] = self.path
      self.active['safe'] = self.safe
      try:
         self.active = getXMLKeys(actions,self.active)
      except Exception as e:
         raise Exception([filterMessage({'name':'ACTION::addACTION'},e,self.bypass)])  # only one item here
      if self.active["xref"] in self.dids:
         raise Exception([{'name':'ACTION::addACTION','msg':'you are getting me confused, this xref already exists: '+self.active["xref"]}])
      self.dids.update({ self.active["xref"]:{} })
      if self.active["rank"] == '': self.active["rank"] = rank
      if self.active["rank"] == '': self.active["rank"] = '953'
      self.active["rank"] = int(self.active["rank"])
      if isinstance(self.active["deprefs"], StringTypes):
         deprefs = {}
         if self.active["deprefs"] != '':
            for depref in self.active["deprefs"].split(';'):
               if ':' in depref: ref,dep = depref.split(':')
               else: # ref becomes the name itself if no dependencies to other actions
                  ref = depref
                  dep = depref
               deprefs.update({ref:dep})
         self.active["deprefs"] = deprefs
      if isinstance(self.active["outrefs"], StringTypes):
         outrefs = {}
         if self.active["outrefs"] != '':
            for outref in self.active["outrefs"].split(';'):
               ref,out = outref.split(':')
               outrefs.update({ref:out})
         self.active["outrefs"] = outrefs
      return self.active["target"]

   def addCFG(self,cfgname,cfg):
      self.active['cfg'] = cfgname
      if self.active["where"] != '':
         self.active['safe'] = path.join( path.join(self.active['path'],self.active["where"]),cfgname )
      else: self.active['safe'] = path.join( path.join(self.active['path'],self.active["xref"]),cfgname )
      self.dids[self.active["xref"]].update( { cfgname: {
         'target': self.active["target"],
         'safe': self.active['safe'],
         'path': self.active['path'],
         'title': self.active["title"],
         'set': self.active["set"],
         'cmaps': path.join(cfg['PWD'],'ColourMaps')
         } } )

   def updateCFG(self,d): self.dids[self.active["xref"]][self.active['cfg']].update( d )

# _____                        _____________________________________
# ____/ Primary Class: GROUPS /____________________________________/
#
"""
   In the classes below, the double quoted keys refer to the keys
      of the XML file. Contrarily, the single quoted keys in
      because they are internal to the python scripts.
   In the XML file, you can have multiple actions and each action
      will be associated with multiple configurations:
      did.keys() => array [xref] for each action
      did[xref].keys() => array [cfgname] for each possible configuration
      did[xref][cfgname].keys() =>
         - 'target', basename of the CAS file
         - 'cas', scanned CAS file
         - 'code', name of the module
         - 'title', title of the action (xref)
         - 'cmaps', refer to the directory 'ColourMaps' for colour plotting
         - 'deprefs', refer to the files that need copying from path to safe
         - 'outrefs', refer to the files that need copying from safe to path
         - 'where' will not default to xref anymore, allowing files to
      be shared and located at the same place between groups
"""

class GROUPS:

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #                                                General Methods
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   availacts = ''
   availkeys = { "xref": None, "deco": '' }
   groupkeys = { }
   avaylkeys = { }

   def __init__(self,title='',bypass=True):
      self.active = deepcopy(self.availkeys)
      if title != '': self.active["title"] = title
      self.bypass = bypass
      self.dids = {}
      # those you need to see in the XML file
      self.active["target"] = None
      self.active["code"] = None
      self.active["do"] = None
      self.active["type"] = None
      # additional entities
      self.tasks = {}

   def addGroupType(self,group):
      self.dids.update({group:{}})
      self.active['type'] = group

   def addGroup(self,group,rank=''):
      tasks = deepcopy(self.availkeys)
      try:
         self.tasks = getXMLKeys(group,tasks)
      except Exception as e:
         raise Exception([filterMessage({'name':'GROUP::addGroup'},e,self.bypass)])
      self.active['xref'] = self.tasks["xref"]
      if self.tasks["xref"] in self.dids[self.active['type']]:
         raise Exception([{'name':'GROUP::addGroup','msg':'you are getting me confused, this xref already exists: '+self.tasks["xref"]}])
      self.dids[self.active['type']].update({self.tasks["xref"]:self.tasks})

   def update(self,d): self.dids[self.active['type']][self.active['xref']].update( d )

   def addSubTask(self,layer,nametask='layers'):
      # ~~> set default from the upper grouper
      subtasks = {}
      for k in self.groupkeys: subtasks.update({k:self.tasks[k]})
      for k in self.avaylkeys: subtasks.update({k:self.avaylkeys[k]})
      # ~~> reset from layer
      try:
         subtasks = getXMLKeys(layer,subtasks)
      except Exception as e:
         raise Exception([filterMessage({'name':'GROUP::addSubTask'},e,self.bypass)])
      # ~~> filling-in remaining gaps
      subtasks = self.distributeDeco(subtasks)
      # ~~> adding subtask to the list of tasks
      if nametask in self.tasks: self.tasks[nametask].append(subtasks)
      else: self.tasks.update({nametask:[subtasks]})
      return len(self.tasks[nametask])-1,nametask

   def targetSubTask(self,target,index=0,nametask='layers'):
      self.tasks[nametask][index].update({ 'fileName': target })
      if nametask not in self.dids[self.active['type']][self.active['xref']]: 
         self.dids[self.active['type']][self.active['xref']].update({nametask:[self.tasks[nametask][index]]})

   def distributeDeco(self,subtask): return subtask

   def decoTasks(self,deco={},index=0,nametask='layers'):
      # ~~> set default
      self.tasks[nametask][index]['deco'] = deco


# _____                        _____________________________________
# ____/ Secondary Class: DECO /____________________________________/
#
class groupDECO(GROUPS):

   availkeys = deepcopy(GROUPS.availkeys)
   #availkeys.update(decoDefault) # depends on 1D, 2D or 3D plotting packages
   groupkeys = deepcopy(GROUPS.groupkeys)

   def __init__(self,xmlFile,title='',bypass=True):
      GROUPS.__init__(self,title,bypass)
      # those you reset
      self.path = path.dirname(xmlFile)
      # those you need to see in the XML file
      self.active["deco"] = {}

   def addDraw(self,deco):
      GROUPS.addGroup(self,deco)
      self.active['path'] = self.path

   def addLookTask(self,layer,nametask='look'):
      #self.avaylkeys = deepcopy(GROUPS.avaylkeys)
      self.avaylkeys = {}
      for key in layer.attrib: self.avaylkeys.update({key:layer.attrib[key]})
      return GROUPS.addSubTask(self,layer,nametask)

   def addDataTask(self,layer,nametask='data'):
      self.avaylkeys = deepcopy(GROUPS.avaylkeys)
      self.avaylkeys.update({ "title":'', "contact":'', "author":'' })
      return GROUPS.addSubTask(self,layer,nametask)

# _____                            __________________________________
# ____/ Secondary Class actionRUN /_________________________________/
#
# actionRUN is to do with the modules of the TELEMAC system and
#    other execution (pre- and post-processes).
#    . It understands what a PRINCI and what a CAS file and will do
#    the necessary steps to run modules accordingly.
#    . It includes specific methods to do with CAS and PRINCI
#    . It will organise the tranfer of files (inputs and outputs)
#

class actionRUN(ACTION):

   availkeys = deepcopy(ACTION.availkeys)
   availkeys.update({ 'dico':'', "ncsize":'', "code": '' })

   def __init__(self,xmlFile,title='',bypass=True):
      ACTION.__init__(self,title,bypass)
      # those you reset
      self.path = path.dirname(xmlFile)
      # those you need to see in the XML file
      self.active["target"] = None
      self.active["code"] = None
      self.active["xref"] = None
      self.active["do"] = None

   def addAction(self,actions,rank=''):
      target = ACTION.addAction(self,actions,rank)
      self.active['path'] = self.path
      self.code = self.active["code"]
      return target

   def addCFG(self,cfgname,cfg):
      if not ( self.active["code"] == 'exec' or
               self.active["code"] in cfg['MODULES'] ):
         print '... do not know about: ' + self.active["code"] + ' in configuration: ' + cfgname
         sys.exit(1)
      ACTION.addCFG(self,cfgname,cfg)
      ACTION.updateCFG(self,{ "links": {},
         'code': self.active["code"],
         'deprefs': self.active['deprefs'],
         'outrefs': self.active['outrefs'] })

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #                                            CAS related Methods
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   # ~~ todo: difference of CAS file with default keys ~~~~~~~~~~~~~
   def diffCAS(self):
      updated = False
      return updated

   # ~~ Translate the CAS file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   def translateCAS(self,rebuild):
      updated = False
      if not "translate" in self.availacts.split(';'): return updated
      xref = self.active["xref"]; cfgname = self.active['cfg']
      active = self.dids[xref][cfgname]
      # ~~> principal CAS file
      casFile = path.join(active['path'],active["target"])
      sacFile = path.join(active['safe'],active["target"])
      oneup = path.dirname(active['safe'])            # copied one level up
      if matchSafe(casFile,active["target"]+'.??',oneup,rebuild):
         print '      ~> translate cas file: ' + active["target"]
         casfr,casgb = translateCAS(casFile,DICOS[active['dico']]['frgb'])  #/!\ removes comments at end of lines
         moveFile(casfr,oneup)
         moveFile(casgb,oneup)
      # ~~> associated CAS files
      for mod in active["links"]:
         link = active["links"][mod]
         casFile = path.join(active['path'],link['target'])
         sacFile = path.join(active['safe'],link['target'])
         if matchSafe(casFile,link['target']+'.??',oneup,rebuild):
            print '      ~> translate cas file: ' + link['target']
            casfr,casgb = translateCAS(casFile,DICOS[link['dico']]['frgb'])  #/!\ removes comments at end of lines
            moveFile(casfr,oneup)
            moveFile(casgb,oneup)
            updated = True
      return updated

   # ~~ Run the CAS file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   def runCAS(self,options,cfg,rebuild):
      updated = False
      if not "run" in self.availacts.split(';'): return updated

      # ~~> prepare options as if run from command line
      specs = Values()
      specs.configName = options.configName
      specs.configFile = options.configFile
      specs.sortieFile = True
      specs.tmpdirectory = True
      specs.rootDir = options.rootDir
      specs.wDir = options.wDir
      specs.compileonly = False
      if options.hosts != '':
         specs.hosts = options.hosts
      else:
         specs.hosts = gethostname().split('.')[0]
      specs.split = options.split
      specs.run = options.run
      specs.merge = options.merge
      specs.jobname = options.jobname
      specs.hpc_queue = options.hpc_queue
      specs.walltime = options.walltime
      specs.email = options.email
      specs.mpi = options.mpi
      if options.ncsize != '' and self.active["ncsize"] != '':
         self.active["ncsize"] = options.ncsize
      specs.ncsize = self.active["ncsize"]
      specs.nctile = ''    # default but should not be used for validation
      specs.ncnode = ''    # default but should not be used for validation
      specs.bypass = self.bypass
      specs.use_link = options.use_link

      # ~~> check on sorties and run
      casFile = path.join(self.active['path'],self.active["target"])
      sacFile = path.join(self.active['safe'],self.active["target"])
      sortieFiles = getLatestSortieFiles(sacFile)
      outputs = self.dids[self.active["xref"]][self.active['cfg']]['output']
      if matchSafe(casFile,self.active["target"]+'_*??h??min??s*.sortie',self.active['safe'],rebuild):
         print '     +> running cas file: ' + self.active["target"]
         for k in outputs:
            # In case k is read and write
            if 'LIT' in k[2]:
               continue
            matchSafe('',path.basename(k[1][0]),self.active['safe'],2)
         try:
            sortieFiles = runCAS(self.active['cfg'],cfg,self.active["code"],[sacFile],specs)
            updated = True
         except Exception as e:
            raise Exception([filterMessage({'name':'ACTION::runCAS'},e,self.bypass)])  # only one item here
      if sortieFiles != []: self.updateCFG({ 'sortie': sortieFiles })
      return updated

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #                                         PRINCI related Methods
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   # ~~ Highligh user PRINCI differences ~~~~~~~~~~~~~~~~~~~~~~~~~~~
   def diffPRINCI(self,options,cfg,rebuild):
      updated = False
      if not "princi" in self.availacts.split(';'): return updated
      xref = self.active["xref"]; cfgname = self.active['cfg']
      active = self.dids[xref][cfgname]
      oneup = path.dirname(active['safe'])            # copied one level up
      # ~~> principal PRINCI file
      value,default = getKeyWord('FICHIER FORTRAN',active['cas'],DICOS[active['dico']]['dico'],DICOS[active['dico']]['frgb'])
      princiFile = ''
      if value != []:
         princiFile = path.join(active['path'],value[0].strip("'\""))
         if path.isfile(princiFile):
            htmlFile = path.join(oneup,path.splitext(path.basename(princiFile))[0]+'.html')
            if matchSafe(htmlFile,path.basename(htmlFile),oneup,rebuild):
               # ~~> Scans the principal user PRINCI file
               print '      ~> scanning your PRINCI file: ',path.basename(princiFile)
               pFiles = getPrincipalWrapNames(princiFile)
               if pFiles == []:
                  raise Exception([{'name':'ACTION::diffPRINCI','msg':'I could not recognised entities in your PRINCI: '+princiFile}])
               else:
                  print '        +> found:'
                  for pType,pFile in pFiles: print '           - ',pFile
               # ~~> Scans the entire system
               oFiles = {}
               for mod in cfg['MODULES']:
                  dirpath, _, filenames = walk(cfg['MODULES'][mod]['path']).next()
                  for fle in filenames:
                     n,e = path.splitext(fle)
                     # Only looking for fortran files
                     if e.lower() not in ['.f','.f90']: continue
                     for pType,pFile in pFiles:
                        if pFile.lower() == n:
                           oFiles.update( filterPrincipalWrapNames( [pFile],[path.join(dirpath,fle)] ) )
               if oFiles == {}:
                  raise Exception([{'name':'ACTION::diffPRINCI','msg':'I could not relate your PRINCI with the system: '+princiFile}])
               else:
                  print '        +> found:'
                  for oFile in oFiles: print '           - ',oFile
               # ~~> Save temporarily for subsequent difference
               oriFile = path.splitext(princiFile)[0]+'.original'+path.splitext(princiFile)[1]
               putFileContent(oriFile,[])
               for pType,p in pFiles:
                  if p in oFiles: addFileContent(oriFile,getFileContent(oFiles[p]))
               # ~~> Process difference and write output into an HTML file
               diff = diffTextFiles(oriFile,princiFile,options)
               remove(oriFile)
               of = open(htmlFile,'wb')
               of.writelines( diff )
               of.close()
               print '       ~> comparison successful ! created: ' + path.basename(htmlFile)
               updated = True
         else:
            raise Exception([{'name':'ACTION::diffPRINCI','msg':'I could not find your PRINCI file: '+princiFile}])
      # ~~> associated PRINCI file
      # TODO: case of coupling with multiple PRINCI files
      return updated

   # ~~ Compile the PRINCI file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   def compilePRINCI(self,cfg,rebuild):
      updated = False
      if not "compile" in self.availacts.split(';'): return updated
      xref = self.active["xref"]; cfgname = self.active['cfg']
      active = self.dids[xref][cfgname]
      confirmed = False
      # ~~> principal PRINCI file
      value,default = getKeyWord('FICHIER FORTRAN',active['cas'],
                                 DICOS[active['dico']]['dico'],
                                 DICOS[active['dico']]['frgb'])
      princiFile = ''; princiSafe = ''
      if value != []:       # you do not need to compile the default executable
         princiFile = path.join(active['path'],value[0].strip("'\""))
         if path.isfile(princiFile):
            exeFile = path.join(active['safe'],path.splitext(value[0].strip("'\""))[0] + \
                      cfg['SYSTEM']['sfx_exe'])
            if not path.exists(exeFile) or cfg['REBUILD'] == 0:
               print '     +> compiling princi file: ' + path.basename(princiFile)
               copyFile(princiFile,active['safe'])
               print '*********copying '+princiFile+' '+active['safe']
               princiSafe = path.join(active['safe'],path.basename(princiFile))
               confirmed = True
         else:
            raise Exception([{'name':'ACTION::compilePRINCI','msg':'I could not find your PRINCI file: '+princiFile}])
      # ~~> associated PRINCI file
      for mod in active["links"]:
         link = active["links"][mod]
         value,default = getKeyWord('FICHIER FORTRAN',link['cas'],DICOS[link['dico']]['dico'],DICOS[link['dico']]['frgb'])
         princiFilePlage = ''
         if value != []:       # you do not need to compile the default executable
            princiFilePlage = path.join(active['path'],value[0].strip("'\""))
            if path.isfile(princiFilePlage):
               if princiSafe != '':
                  print '*********adding content of '+path.basename(princiFilePlage)+' to '+princiSafe
                  putFileContent(princiSafe,getFileContent(princiSafe)+['']+getFileContent(princiFilePlage))
               else:
                  print '     +> compiling princi file: ' + path.basename(princiFilePlage)
                  exeFile = path.join(active['safe'],path.splitext(value[0].strip("'\""))[0] + cfg['SYSTEM']['sfx_exe'])
                  princiSafe = path.join(active['safe'],path.basename(princiFilePlage))
                  print '*********copying '+path.basename(princiFilePlage)+ ' ' + active['safe']
                  copyFile(princiFilePlage,active['safe'])
               confirmed = True
            else:
               raise Exception([{'name':'ACTION::compilePRINCI','msg':'I could not find your PRINCI file: '+princiFilePlage}])
      if confirmed:
         try:
            compilePRINCI(princiSafe,active["code"],self.active['cfg'],cfg,self.bypass)
            updated = True
         except Exception as e:
            raise Exception([filterMessage({'name':'ACTION::compilePRINCI'},e,self.bypass)])  # only one item here
         #moveFile(exeFile,active['safe'])
         print '       ~> compilation successful ! created: ' + path.basename(exeFile)
      #else: you may wish to retrieve the executable for later analysis
      return updated

   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #                                              Direct Executions
   # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   def runCommand(self,rebuild):

      updated = False
      print '    +> executing your command:\n      ', self.active["do"]
      mes = MESSAGES(size=10)

      # ~~> copy of inputs
      iFile = ''
      exeCmd = self.active["do"]
      if path.isfile(path.join(self.active['path'],self.active["target"])):
         iFile = path.join(self.active['path'],self.active["target"])
         try:
            copyFile(iFile,self.active['safe'])
         except Exception as e:
            raise Exception([filterMessage({'name':'runCommand','msg':'I can see your input file '+iFile+'but cannot copy it'},e,True)])
      else:
         for dir in sys.path:   # /!\ in that case, you do not copy the target locally
            if path.isfile(path.join(dir,self.active["target"])): iFile = path.join(dir,self.active["target"])
         if iFile == '': raise Exception([{'name':'runCommand','msg':'could not find reference to the target: '+iFile}])
         exeCmd = self.active["do"].replace(self.active["target"],iFile)

      for oFile in self.active["deprefs"]:
         if oFile in self.dids:
            if self.active['cfg'] in self.dids[oFile]:
               layer = findTargets(self.dids[oFile][self.active['cfg']],self.active["deprefs"][oFile])
               if layer != []:
                  if path.isfile(layer[0][0]):
                     try:
                        copyFile(layer[0][0],self.active['safe'])
                     except Exception as e:
                        raise Exception([filterMessage({'name':'runCommand','msg':'I can see your input file '+layer[0][0]+'but cannot copy it'},e,True)])
                  else: raise Exception([{'name':'runCommand','msg':'could not find reference to the dependant: '+layer[0][0]}])
            else : raise Exception([{'name':'runCommand','msg':'could not find the configuration '+self.active['cfg']+'for the dependant: '+oFile}])
         else:
            if self.active["where"] != '':
               if path.exists(path.join(self.active["where"],oFile)): copyFile(path.join(self.active["where"],oFile),self.active['safe'])
            elif path.exists(path.join(self.path,oFile)): copyFile(path.join(self.path,oFile),self.active['safe'])
            else: raise Exception([{'name':'runCommand','msg':'could not find reference to the dependant: '+oFile}])

      # ~~> associated secondary inputs
      for xref in self.active["deprefs"]:
         if xref in self.dids.keys():
            cfgname = self.active['cfg']
            if cfgname in self.dids[xref]:
               active = self.dids[xref][cfgname]
               if self.active["deprefs"][xref].lower() == "sortie":
                  if path.isfile(active["sortie"]): copyFile(active["sortie"],self.active['safe'])
                  else: raise Exception([{'name':'runCommand','msg':'could not find reference to the sortie: '+active["sortie"]}])
               elif self.active["deprefs"][xref] in active["outrefs"]:
                  if path.exists(path.join(active['safe'],active["outrefs"][self.active["deprefs"][xref]])):
                     try:
                        copyFile(path.join(active['safe'],active["outrefs"][self.active["deprefs"][xref]]),self.active['safe'])
                     except Exception as e:
                        raise Exception([filterMessage({'name':'runCommand','msg':'I can see your file '+self.active["deprefs"][xref]+'but cannot copy it'},e,True)])
                  else: raise Exception([{'name':'runCommand','msg':'I cannot see your output file '+self.active["deprefs"][xref]}])
               else:
                  layer = []
                  for oFile in active["output"]:
                     layer = findTargets(active,self.active["deprefs"][xref])
                     if layer != []:
                        if path.isfile(layer[0][0]):
                           try:
                              copyFile(layer[0][0],self.active['safe'])
                           except Exception as e:
                              raise Exception([filterMessage({'name':'runCommand','msg':'I can see your input file '+layer[0][0]+'but cannot copy it'},e,True)])
                        else: raise Exception([{'name':'runCommand','msg':'could not find reference to the dependant: '+layer[0][0]}])
                  for mod in active["links"]:
                     for iFile in active["links"][mod]["oFS"]:
                        layer = findTargets({'code':mod,'output':active["links"][mod]["oFS"]},self.active["deprefs"][xref])
                        if layer != []:
                           if path.isfile(layer[0][0]):
                              try:
                                 copyFile(layer[0][0],self.active['safe'])
                              except Exception as e:
                                 raise Exception([filterMessage({'name':'runCommand','msg':'I can see your input file '+layer[0][0]+'but cannot copy it'},e,True)])
                           else: raise Exception([{'name':'runCommand','msg':'could not find reference to the dependant: '+layer[0][0]}])
                  if layer == []: raise Exception([{'name':'runCommand','msg':'could not find reference to the linked file: '+self.active["deprefs"][xref]}])

      # ~~> execute command locally
      chdir(self.active['safe'])
      try:
         tail,code = mes.runCmd(exeCmd,self.bypass) # /!\ Do you really need True here ?
         updated = True
      except Exception as e:
         raise Exception([filterMessage({'name':'runCommand','msg':'something went wrong when executing you command.'},e,True)])
      if code != 0: raise Exception([{'name':'runCommand','msg':'Could not run your command ('+exeCmd+').\n      '+tail}])

      # ~~> copy of outputs /!\ you are replacing one config by another
      for oFile in self.active["outrefs"]:
         if path.exists(path.join(self.active['safe'],self.active["outrefs"][oFile])):
            try:
               copyFile(path.join(self.active['safe'],self.active["outrefs"][oFile]),self.active['path'])
            except Exception as e:
               raise Exception([filterMessage({'name':'runCommand','msg':'I can see your file '+oFile+': '+self.active["outrefs"][oFile]+'but cannot copy it'},e,True)])
         else: raise Exception([{'name':'runCommand','msg':'I cannot see your output file '+oFile+': '+self.active["outrefs"][oFile]}])
      return updated

# _____                            __________________________________
# ____/ Secondary Class actionGET /_________________________________/
#
# actionGET is to do with loading data in memory for future use.
#

class actionGET(ACTION):

   availkeys = deepcopy(ACTION.availkeys)
   availkeys.update({ 'type':'' })

   def __init__(self,xmlFile,title='',bypass=True):
      ACTION.__init__(self,title,bypass)
      # those you reset
      self.path = path.dirname(xmlFile)
      # those you need to see in the XML file
      self.active["target"] = None
      self.active["xref"] = None
      self.active["type"] = None

   def addAction(self,actions,rank=''):
      target = ACTION.addAction(self,actions,rank)
      self.active['path'] = self.path
      return target

   def addCFG(self,cfgname,cfg):
      ACTION.addCFG(self,cfgname,cfg)
      self.active['path'] = self.path
      ACTION.updateCFG(self,{ "type": self.active["type"],
         "target":path.join(self.active['path'],self.active["target"]) })

# _____                            __________________________________
# ____/ Secondary Class groupPLOT /_________________________________/
#
# groupPLOT is to do with plotting and producing PNG (mainly)
#

class groupPLOT(GROUPS):

   availkeys = deepcopy(GROUPS.availkeys)
   availkeys.update({ 'path':'','safe':'','cfg':'',
         "time": '[-1]', "extract": '', "vars": '', 'outFormat': 'png',
         "sample": '', "target": '', "do": '', "rank":'',
         "deprefs":'', "outrefs":'', "where":'',
         "type":'', "config": 'distinct' })
   groupkeys = deepcopy(GROUPS.groupkeys)
   groupkeys.update({ "vars":'', "time":'', "extract":'', "sample": '', "config":'', "where":'', "type":''})
   avaylkeys = deepcopy(GROUPS.avaylkeys)
   avaylkeys.update({ "title":'', "target":'', "deco":'' })

   def __init__(self,xmlFile,title='',bypass=True):
      GROUPS.__init__(self,title,bypass)
      # those you reset
      self.path = path.dirname(xmlFile)
      self.safe = self.path
      self.order = []

   def addDraw(self,draw,rank=''):
      GROUPS.addGroup(self,draw)
      self.active['path'] = self.path
      self.active['safe'] = self.safe
      if self.dids[self.active['type']][self.tasks["xref"]]['rank'] == '': self.dids[self.active['type']][self.tasks["xref"]]['rank'] = rank
      if self.dids[self.active['type']][self.tasks["xref"]]['rank'] == '': self.dids[self.active['type']][self.tasks["xref"]]['rank'] = '953'
      self.dids[self.active['type']][self.tasks["xref"]]['rank'] = int(self.dids[self.active['type']][self.tasks["xref"]]['rank'])
      self.dids[self.active['type']][self.tasks["xref"]]['deco'] = self.tasks["deco"]
      self.order.append(self.tasks["xref"])

   def distributeDeco(self,subtask):
      # ~~> distribute decoration
      vrs = subtask["vars"].split(';')
      for i in range(len(vrs)):
         if ':' not in vrs[i]: vrs[i] = vrs[i] + ':' + self.tasks["deco"]
      subtask["vars"] = ';'.join(vrs)
      return subtask

# _____                           ___________________________________
# ____/ Secondary Class groupGET /__________________________________/
#
class groupGET(GROUPS):

   availkeys = deepcopy(GROUPS.availkeys)
   availkeys.update({ 'path':'','safe':'','cfg':'',
         "time": '[-1]', "extract": '', "sample": '', "vars": '',
         'outFormat': '', "target": '', "do": '', "rank":'',
         "deprefs":'', "outrefs":'', "where":'',
         "type":'', "config": 'distinct' })
   groupkeys = deepcopy(GROUPS.groupkeys)
   groupkeys.update({ "vars":'', "time":'', "extract":'', "sample": '', "config":'', "where":'' })
   avaylkeys = deepcopy(GROUPS.avaylkeys)
   avaylkeys.update({ "title":'', "target":'', "deco":'' })

   def __init__(self,xmlFile,title='',bypass=True):
      GROUPS.__init__(self,title,bypass)
      # those you reset
      self.path = path.dirname(xmlFile)
      self.safe = self.path
      self.order = []

   def addGroup(self,draw,rank=''):
      GROUPS.addGroup(self,draw)
      self.active['path'] = self.path
      self.active['safe'] = self.safe
      if self.dids[self.active['type']][self.tasks["xref"]]['rank'] == '': self.dids[self.active['type']][self.tasks["xref"]]['rank'] = rank
      if self.dids[self.active['type']][self.tasks["xref"]]['rank'] == '': self.dids[self.active['type']][self.tasks["xref"]]['rank'] = '953'
      self.dids[self.active['type']][self.tasks["xref"]]['rank'] = int(self.dids[self.active['type']][self.tasks["xref"]]['rank'])
      #self.active['deco'] = self.tasks["deco"]
      self.order.append(self.tasks["xref"])

   def distributeDeco(self,subtask):
      # ~~> distribute decoration
      vrs = subtask["vars"].split(';')
      for i in range(len(vrs)):
         if ':' not in vrs[i]: vrs[i] = vrs[i] + ':xyz'   # :xyz is not used
      subtask["vars"] = ';'.join(vrs)
      return subtask

# _____                             _________________________________
# ____/ Secondary Class groupCHECK /________________________________/
#

class groupCAST(GROUPS):

   availkeys = deepcopy(GROUPS.availkeys)
   availkeys.update({ 'path':'','safe':'','cfg':'',
         "time": '[-1]', "extract": '', "vars": [],
         "sample": '', "target": '', "rank":'',
         "deprefs":'', "outrefs":'', "where":'',
         "type":'', "config": 'distinct' })
   groupkeys = deepcopy(GROUPS.groupkeys)
   groupkeys.update({ "vars":'', "time":'', "extract":'', "sample": '', "config":'', "where":'', "type":'' })
   avaylkeys = deepcopy(GROUPS.avaylkeys)
   avaylkeys.update({ "title":'', "target":'' })

   def __init__(self,xmlFile,title='',bypass=True):
      GROUPS.__init__(self,title,bypass)
      # those you reset
      self.path = path.dirname(xmlFile)
      self.safe = self.path

   def addCast(self,cast,rank=''):
      GROUPS.addGroup(self,cast)
      self.active['path'] = self.path
      self.active['safe'] = self.safe
      if self.dids[self.active['type']][self.tasks["xref"]]['rank'] == '': self.dids[self.active['type']][self.tasks["xref"]]['rank'] = rank
      if self.dids[self.active['type']][self.tasks["xref"]]['rank'] == '': self.dids[self.active['type']][self.tasks["xref"]]['rank'] = '953'
      self.dids[self.active['type']][self.tasks["xref"]]['rank'] = int(self.dids[self.active['type']][self.tasks["xref"]]['rank'])

   def addPythonTask(self,code,nametask='python'):
      self.tasks.update({nametask:code.text})

   def addReturnTask(self,code,nametask='return'):
      self.tasks.update({nametask:{}})
      for key in code.attrib: self.tasks[nametask].update({key:code.attrib[key]})

   def addVariableTask(self,code,nametask):
      subtasks = { 'xref':nametask }
      for key in self.groupkeys: subtasks.update({key:self.tasks[key]})
      for key in self.avaylkeys: subtasks.update({key:self.avaylkeys[key]})
      for key in code.attrib: subtasks.update({key:code.attrib[key]})
      self.tasks['vars'].append(subtasks)
      return len(self.tasks['vars'])-1,'vars'

   def update(self,d): self.dids[self.active["type"]][self.active["xref"]].update( d )

# _____                     ________________________________________
# ____/ XML Parser Toolbox /_______________________________________/
#
"""
   Assumes that the directory ColourMaps is in PWD (i.e. ~root/pytel.)
"""
def runXML(xmlFile,xmlConfig,reports,bypass):

   xcpt = []            # try all keys for full report

   # ~~ Parse xmlFile ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   import xml.etree.ElementTree as XML
   f = open(xmlFile,'r')
   xmlTree = XML.parse(f)  # may need to try first and report error
   xmlRoot = xmlTree.getroot()
   f.close()

   # ~~ Simplying Ranking ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   dodo = True
   # /!\ There is a lot more to dodo
   rank = '1'
   if "rank" in xmlRoot.keys(): rank = xmlRoot.attrib["rank"]
   rankdo = int(rank)
   rankdont = 0
   if xmlConfig[xmlConfig.keys()[0]]['options'].rank != '': rankdont = int(xmlConfig[xmlConfig.keys()[0]]['options'].rank)
   if rankdont == 1: dodo = False
   if gcd(rankdont,rankdo) == 1: dodo = False
   if not dodo:
      print '    > nothing to do here at this stage'
      return reports

   print '... interpreting XML test specification file: ' + path.basename(xmlFile)
   # ~~ Decoration process ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #
   #    This needs to be developed further
   #
   title = ""
   dc = groupDECO(xmlFile,title,bypass)
   dc.addGroupType("deco")
   for decoing in xmlRoot.findall("deco"):

      # ~~ Step 1. Common check for keys ~~~~~~~~~~~~~~~~~~~~~~~~
      try:
         dc.addGroup(decoing)
      except Exception as e:
         xcpt.append(filterMessage({'name':'runXML','msg':'add deco object to the list'},e,bypass))
         continue   # bypass the rest of the for loop

      # ~~ Step 2. Cumul looks ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if len(decoing.findall("look")) > 1:
         raise Exception([{'name':'runXML','msg':'you can only have one look in deco referenced: '+dc.tasks["xref"]}])
      if len(decoing.findall("look")) > 0:
         look = decoing.findall("look")[0]
         try:
            dc.addLookTask(look)
         except Exception as e:
            xcpt.append(filterMessage({'name':'runXML','msg':'add look to the list'},e,bypass))
            continue   # bypass the rest of the for loop
      # ~~ Step 2. Cumul decos ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      if len(decoing.findall("data")) > 1:
         raise Exception([{'name':'runXML','msg':'you can only have one data in deco referenced: '+dc.tasks["xref"]}])
      if len(decoing.findall("data")) > 0:
         data = decoing.findall("data")[0]
         try:
            dc.addDataTask(data)
         except Exception as e:
            xcpt.append(filterMessage({'name':'runXML','msg':'add deco to the list'},e,bypass))
            continue   # bypass the rest of the for loop

      dc.update(dc.tasks)

   if xcpt != []: raise Exception({'name':'runXML','msg':'looking at deco in xmlFile: '+xmlFile,'tree':xcpt})

   # ~~ Looping logic in order of appearance ~~~~~~~~~~~~~~~~~~~~~~~
   do = actionRUN(xmlFile,title,bypass)
   save = groupGET(xmlFile,title,bypass)
   for typeSave in ["save1d","save2d","save3d"]: save.addGroupType(typeSave)
   plot = groupPLOT(xmlFile,title,bypass)
   for typePlot in ["plot1d","plot2d","plot3d","plotpv"]: plot.addGroupType(typePlot)
   cast = groupCAST(xmlFile,title,bypass)
   cast.addGroupType("cast")
   # ~~> Create casts for future references
   caster = Caster({'object':{},'obdata':{}})

   # ~~ The new frontier ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   space = locals()

   for xmlChild in xmlRoot:

   # ~~ Main action process ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   #
   #    Whether an action is carried out or not, it is known through:
   #       xmlConfig[cfgname]['options'].todos
   #    CAS file will still be loaded to register various other files
   #       for possible subsequent extraction, plotting or analysis
   #    TODO: limit the number of path / safe duplication
   # _______________________________________________________//        \\
   # _______________________________________________________>> ACTION <<
   #                                                        \\        //
   #for action in xmlRoot.findall("action"):
      if xmlChild.tag == "action":
         report = {}; updated = False
         action = xmlChild

         # ~~ Step 1. Common check for keys and driving file ~~~~~~~
         try:
            targetFile = do.addAction(action,rank)
            report.update({ 'xref':do.active['xref'], 'updt':False, 'fail':False, 'warn':False, 'rank':do.active['rank'], 'value':0, 'title':'This was ignored' })
         except Exception as e:
            xcpt.append(filterMessage({'name':'runXML','msg':'add todo to the list'},e,bypass))
            continue    # bypass rest of the loop
         else:
            oneFound = False
            if path.isfile(path.join(do.active['path'],targetFile)): oneFound = True
            for d in sys.path:
               if path.isfile(path.join(d,targetFile)): oneFound = True
            if not oneFound:
               raise Exception([{'name':'runXML','msg':'could not find your target file'+targetFile}])
               #continue    # bypass rest of the loop

         # ~~ Step 2. Loop over configurations ~~~~~~~~~~~~~~~~~~~~~
         for cfgname in xmlConfig:
            cfg = xmlConfig[cfgname]['cfg']
            do.addCFG(cfgname,cfg) #if not : continue

            # ~~> Temper with rank but still gather intelligence
            #dodo = True
            #rankdo = do.active['rank']
            #rankdont = xmlConfig[cfgname]['options'].rank
            #if rankdont == 1: dodo = False
            #if gcd(rankdont,rankdo) == 1: dodo = False
            #do.updateCFG({'dodo':dodo})

            # ~~> Create the safe
            createDirectories(do.active['safe'])

            # ~~ Step 3a. Deals with TELEMAC launchers ~~~~~~~~~~~~~
            if do.active["code"] in cfg['MODULES']:

               do.availacts = "translate;run;compile;princi"

               # ~~> Manage targetFile and other inputs
               casFile = path.join(do.active['path'],targetFile)
               # ~~> Parse DICO File and its IO Files default (only once)
               dicoFile = getDICO(cfg,do.active["code"])
               do.updateCFG({'dico':dicoFile})
               dico = DICOS[dicoFile]['dico']
               frgb = DICOS[dicoFile]['frgb']
               cas = readCAS(scanCAS(getFileContent(casFile)),dico,frgb)
               lang = getCASLang(cas,frgb)
               if lang == 1:
                  cas = setKeyValue('FICHIER DES PARAMETRES',cas,frgb,repr(path.basename(casFile)))
                  cas = setKeyValue('DICTIONNAIRE',cas,frgb,repr(path.normpath(frgb['DICO'])))
               if lang == 2:
                  cas = setKeyValue('STEERING FILE',cas,frgb,repr(path.basename(casFile)))
                  cas = setKeyValue('DICTIONARY',cas,frgb,repr(path.normpath(frgb['DICO'])))
               # ~~> Parse user defined keywords
               if do.active['set'] != '':
                  for set in do.active['set'].split('|'):
                     kw,val = scanCAS(set)[1]
                     cas = setKeyValue(kw[0],cas,frgb,';'.join(val[0]))
               # ~~> Parse other special keys
               if do.active["ncsize"] != '': cas = setKeyValue('PROCESSEURS PARALLELES',cas,frgb,int(do.active["ncsize"]))
               ncsize = getNCSIZE(cas,dico,frgb)
               do.updateCFG({'cas':cas})
               if ( cfg['MPI'] != {} or cfg['HPC'] != {} ) and ncsize == 0: continue
               if not ( cfg['MPI'] != {} or cfg['HPC'] != {} ) and ncsize > 0: continue

               idico = DICOS[dicoFile]['input']
               odico = DICOS[dicoFile]['output']

               # ~~> Define config-split storage
               sortieFiles,iFS,oFS = setSafe(casFile,cas,idico,odico,do.active['safe'])   # TODO: look at relative paths
               if sortieFiles != []: do.updateCFG({ 'sortie': sortieFiles })
               do.updateCFG({ 'input':iFS })
               do.updateCFG({ 'output':oFS })

               # ~~> Case of coupling
               cplages,defaut = getKeyWord('COUPLING WITH',cas,dico,frgb)
               links = {}
               for cplage in cplages:
                  for mod in cfg['MODULES']:
                     if mod in cplage.lower():
                        # ~~> Extract the CAS File name
                        casFilePlage,defaut = getKeyWord(mod.upper()+' STEERING FILE',cas,dico,frgb)
                        if casFilePlage == []: casFilePlage = defaut[0]
                        else: casFilePlage = casFilePlage[0].strip("'\"")
                        casFilePlage = path.join(path.dirname(casFile),casFilePlage)
                        if not path.isfile(casFilePlage): raise Exception([{'name':'runCAS','msg':'missing coupling CAS file for '+mod+': '+casFilePlage}])
                        # ~~> Read the DICO File
                        dicoFilePlage = getDICO(cfg,mod)
                        dicoPlage = DICOS[dicoFilePlage]['dico']
                        frgbPlage = DICOS[dicoFilePlage]['frgb']
                        # ~~> Read the coupled CAS File
                        casPlage = readCAS(scanCAS(getFileContent(casFilePlage)),dicoPlage,frgbPlage)
                        # ~~> Fill-in the safe
                        idicoPlage = DICOS[dicoFilePlage]['input']
                        odicoPlage = DICOS[dicoFilePlage]['output']
                        sortiePlage,iFSPlage,oFSPlage = setSafe(casFilePlage,casPlage,idicoPlage,odicoPlage,do.active['safe'])   # TODO: look at relative paths
                        links.update({mod:{}})
                        links[mod].update({ 'code':mod, 'target':path.basename(casFilePlage),
                           'cas':casPlage, 'frgb':frgbPlage, 'dico':dicoFilePlage,
                           'iFS':iFSPlage, 'oFS':oFSPlage, 'sortie':sortiePlage })
                        if sortiePlage != []: links[mod].update({ 'sortie':sortiePlage })
               if links != {}: do.updateCFG({ "links":links })

               # ~~> Complete all actions
               # options.todos takes: translate;run;compile and none
               doable = xmlConfig[cfgname]['options'].todos
               if doable == '': doable = do.active["do"]
               if doable == '' or doable == 'all': doable = do.availacts

               # ~~> Action type A. Translate the CAS file
               if "translate" in doable.split(';'):
                  try:
                     # - exchange keywords between dictionaries
                     do.translateCAS(cfg['REBUILD'])
                     #updated = do.translateCAS(cfg['REBUILD'])
                  except Exception as e:
                     xcpt.append(filterMessage({'name':'runXML','msg':'   +> translate'},e,bypass))

               # ~~> Action type B. Analysis of the CAS file
               # TODO:
               # - comparison with DEFAULT values of the DICTIONARY
               #if "cas" in doable.split(';'):
               # - comparison of dictionnaries betwen configurations
               #if "dico" in doable.split(';'):

               # ~~> Action type C. Analysis of the PRINCI file
               if "princi" in doable.split(';'):
                  # - comparison with standard source files
                  specs = Values()
                  specs.unified = False
                  specs.ndiff = False
                  specs.html = True
                  specs.ablines = True
                  specs.context = False
                  do.diffPRINCI(specs,cfg,cfg['REBUILD'])
                  #updated = do.diffPRINCI(specs,cfg,cfg['REBUILD'])
               # TODO: - comparison of subroutines between action items

               # ~~> Action type E. Running CAS files
               if "run" in doable.split(';'):
                  try:
                     updated = do.runCAS(xmlConfig[cfgname]['options'],cfg,cfg['REBUILD'])
                  except Exception as e:
                     xcpt.append(filterMessage({'name':'runXML','msg':'   +> run'},e,bypass))

            # ~~ Step 3b. Deals with execute launchers ~~~~~~~~~~~~~
            elif do.active["code"] == 'exec':

               do.availacts = "exec"

               # ~~> Complete all actions
               # options.todos takes: exec and none
               doable = xmlConfig[cfgname]['options'].todos
               if doable == '': doable = do.active["code"]
               if doable == '' or doable == 'all': doable = do.availacts

               # ~~> Action type E. Running exec
               if "exec" in doable.split(';'):
                  try:
                     # - simply run the exec as stated
                     updated = do.runCommand(cfg['REBUILD'])
                  except Exception as e:
                     xcpt.append(filterMessage({'name':'runXML::runCommand','msg':'   +> '+do.active["do"]},e,bypass))

         if updated: report.update({ 'updt':updated, 'title':'My work is done' })

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at actions in xmlFile: '+xmlFile,'tree':xcpt})

         oneFound = False
         for i in range(len(reports)):
            if reports[i]['xref'] == report['xref']:  #/!\ You are sure there is one xref (?)
               reports[i] = report
               oneFound = True
         if not oneFound: reports.append(report)

   # _________________________________________________________//      \\
   # _________________________________________________________>> CAST <<
   #                                                          \\      //
      if xmlChild.tag[0:4] == "cast":
         report = {}
         typeCast = xmlChild.tag
         cast.active['type'] = typeCast
         casting = xmlChild

         # ~~ Step 1. Common check for keys ~~~~~~~~~~~~~~~~~~~~~~~~
         try:
            cast.addCast(casting,rank)
            report.update({ 'xref':cast.tasks['xref'], 'updt':False, 'rank':cast.tasks['rank'] })
         except Exception as e:
            xcpt.append(filterMessage({'name':'runXML','msg':'add extract object to the list'},e,bypass))
            continue   # bypass the rest of the for loop

         # ~~ Step 2. Python code ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         if len(casting.findall("python")) > 1:
            raise Exception([{'name':'runXML','msg':'you can only have one python key in cast referenced: '+cast.tasks["xref"]}])
         if len(casting.findall("python")) > 0:
            code = casting.findall("python")[0]
            try:
               cast.addPythonTask(code)
            except Exception as e:
               xcpt.append(filterMessage({'name':'runXML','msg':'add python code to the list'},e,bypass))
               continue   # bypass the rest of the for loop

         # ~~ Step 3. Return statement ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         if len(casting.findall("return")) > 1:
            raise Exception([{'name':'runXML','msg':'you can only have one return key in cast referenced: '+cast.tasks["xref"]}])
         if len(casting.findall("return")) > 0:
            code = casting.findall("return")[0]
            try:
               cast.addReturnTask(code)
            except Exception as e:
               xcpt.append(filterMessage({'name':'runXML','msg':'add return statement to the list'},e,bypass))
               continue   # bypass the rest of the for loop

         # ~~ Step 2. Variables ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         for vari in casting.getchildren():
            if vari.tag in ['python','return']: continue
            if vari.tag in cast.tasks: raise Exception([{'name':'runXML','msg':'The variable '+vari.tag+' is cast more than once in '+cast.tasks["xref"]}])
            try:
               index,namex = cast.addVariableTask(vari,vari.tag)
               target = cast.tasks[namex][index]["target"]
            except Exception as e:
               xcpt.append(filterMessage({'name':'runXML','msg':'add variable to the list'},e,bypass))
               continue   # bypass the rest of the for loop

            # ~~> just casting, no specific targets
            if target == '':
               cast.tasks[namex][index].update({ 'fileName':{},'target':cast.tasks["xref"] })
               continue
            # ~~> round up targets and their configurations looking in exes and does
            xref = target ; src = ''
            if len(target.split(':')) > 1: xref,src = target.split(':')

            xdid = ''
            for did in cast.dids:
               if xref in cast.dids[did].keys(): xdid = did
            if xdid != '':
               if src not in caster.obdata.keys(): raise Exception([{'name':'runXML','msg':'did not already cast variable '+src+' wihtin '+xref}])
               layers = {}
               for cfgname in xmlConfig:
                  layers.update({ cfgname:[[xref+':'+src],'',''] }) # TODO: maybe you do not need xref
               if layers != {}: cast.targetSubTask(layers,index,namex)
               continue # try finding the next variable

            for did in save.dids:
               if xref in save.dids[did].keys(): xdid = did
            if xdid != '':     # saved files can be reopened as target to do something else
               target = xref + '.' + save.dids[xdid][xref]['outFormat'] # TODO: 'outFormat' may not be correct
               if save.dids[xdid][xref]["where"] != '':
                  if path.exists(path.join(save.dids[xdid][xref]["where"],target)):
                     findlayer = {}
                     t = path.splitext(path.basename(target))[1].lower()[1:]
                     for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(save.dids[xdid][xref]["where"],target)],'',t] })
                     cast.targetSubTask(findlayer,index,namex)
                  else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the cast: '+target+' where '+cast.tasks[namex][index]["where"]}])
               elif path.exists(path.join(save.path,target)):
                  findlayer = {}
                  t = path.splitext(path.basename(target))[1].lower()[1:]
                  for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(save.path,target)],'',t] })
                  cast.targetSubTask(findlayer,index,namex)
               continue # try finding the next variable

            if xref in do.dids:
               layers = {}
               oneFound = False
               for cfgname in xmlConfig:
                  if rankdont == 1: continue
                  if gcd(rankdont,rankdo) == 1: continue
                  oneFound = True
                  findlayer = findTargets(do.dids[xref][cfgname],src)
                  if findlayer != []: layers.update({ cfgname:findlayer })
               if oneFound and layers == {}: raise Exception([{'name':'runXML','msg':'could not find reference to cast the action: '+xref+':'+src}])
               else:
                  cast.targetSubTask(layers,index,namex)
               continue # try finding the next variable

            if src == '':
               if cast.tasks["where"] != '':
                  if path.exists(path.join(cast.tasks["where"],target)):
                     findlayer = {}
                     t = path.splitext(path.basename(target))[1].lower()[1:]
                     for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(cast.tasks["where"],target)],'',t] })
                     cast.targetSubTask(findlayer,index,namex)
                  else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the cast: '+target+' where '+cast.tasks["where"]}])
               elif path.exists(path.join(cast.path,target)):
                  findlayer = {}
                  t = path.splitext(path.basename(target))[1].lower()[1:]
                  for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(cast.path,target)],'',t] })
                  cast.targetSubTask(findlayer,index,namex)
               else : raise Exception([{'name':'runXML','msg':'could not find reference to cast: '+target}])

         cast.update(cast.tasks)

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at casting in xmlFile: '+xmlFile,'tree':xcpt})

   # ~~ Matrix distribution by casting types ~~~~~~~~~~~~~~~~~~~~
   # /!\ you can only have one of them per variable
         xref = cast.tasks['xref']
         task = cast.dids[typeCast][xref]
         print '    +> reference: ',xref,' of type ',typeCast

         xvars = ''   # now done with strings as arrays proved to be too challenging
         for var in task["vars"]:
            if task['config'] == 'together':
               raise Exception([{'name':'runXML','msg':'could not have more than one configuration at a time for casting: '+var['xref']}])
            elif task['config'] == 'distinct':
               raise Exception([{'name':'runXML','msg':'could not have more than one configuration at a time for casting: '+var['xref']}])
            elif task['config'] == 'oneofall':
               xys = []
               if var['fileName'] != {}: 
                  cfg = var['fileName'].iterkeys().next()
               else: cfg = '-'
               for x in xvars.split('|'): xys.append( (x+';'+cfg).strip(';') )
               xvars = '|'.join(xys)
            else:
               xys = []
               if var['fileName'] != {}:
                  if task['config'] in var['fileName']:
                     for x in xvars.split('|'): xys.append( (x+';'+task['config']).strip(';') )
               else:
                  for x in xvars.split('|'): xys.append( (x+';'+'-').strip(';') )
               xvars = '|'.join(xys)

         # ~~> First, loading the user python (this is not executing anything yet ...)
         if 'python' in cast.tasks: exec( cast.tasks['python'] )

         # ~~> Second, casting and extracting data
         nbFile = 0; avars = xvars.split('|')

         for cfglist in avars:
            # ~~> Cast all variables
            for var,cfgs in zip(task["vars"],cfglist.split(';')):
               for cfg in cfgs.split(':'):
                  if var['fileName'] != {}: cfg = var['fileName'].keys()[0] # you just need one for a cast
                  space[var['xref']] = Values() # more practical than a dict { 'support':None, 'values':None }
                  if var['fileName'] != {} and var['fileName'][cfg][0] != []:
                     fileName = var['fileName'][cfg]
                     var.update({ 'file':fileName[0][0] })
                     caster.add( fileName[2], var )
                     space[var['xref']] = caster.get( fileName[2], var )
                  else:
                     r = eval( var["vars"] )
                     # The returned value should be a tuple
                     if type(r) != type(()): 
                        raise Exception([{
                             'name':'runXML',
                             'msg':'The result of the function '+\
                                   var["vars"]+' for '+cast.tasks["xref"]+\
                                   ' should be a tuple 4 arguments: time,names,support,values'}])
                     # The return value should be of dimension 4
                     if len(r) != 4: 
                        raise Exception([{
                             'name':'runXML',
                             'msg':'The result of the function '+var["vars"]+\
                                   ' for '+cast.tasks["xref"]+\
                                   ' should have 4 arguments: time,names,support,values'}])
                     time,names,support,values = r
                     caster.set( var['xref'],Values({'support':support, 'values':values, 
                                                     'names':names, 'time':time}) )
                     space[var['xref']].support = support
                     space[var['xref']].values = values
                     space[var['xref']].names = names
                     space[var['xref']].time = time

         # ~~> Last but not least, validating
         report.update({ 'updt':True })
         if 'return' not in cast.tasks:
            report.update({ 'fail':False, 'warn':False, 'value':0, 'title':'My work is done' })
         else:
            for var in cast.tasks['return']:
               if var in ['fail','warn','value']:
                  r = eval( cast.tasks['return'][var] )
                  report.update({ var:r })
                  print '        - cast:',var,' = ',repr(r),' ( expression: ',cast.tasks['return'][var],' )'
               else: report.update({ var:cast.tasks['return'][var] })

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at casting in xmlFile: '+xmlFile,'tree':xcpt})
         oneFound = False
         for i in range(len(reports)):
            if reports[i]['xref'] == report['xref']:  #/!\ You are sure there is one xref (?)
               reports[i] = report
               oneFound = True
         if not oneFound: reports.append(report)

   # _________________________________________________________//      \\
   # _________________________________________________________>> SAVE <<
   #                                                          \\      //
   # did has all the IO references and the latest sortie files
   #for extracting in xmlRoot.findall(typeSave):
      if xmlChild.tag[0:4] == "save":
         report = {}; updated = False
         # /!\ typeSave should be in ['save1d','save2d','save3d']
         typeSave = xmlChild.tag
         if "type" not in xmlChild.attrib:  #TODO: This will eventually be removed
            if len(typeSave) == 4: raise Exception([{'name':'runXML','msg':'do not know what dimension your saved data will be in: '+xmlChild.attrib["xref"]}])
            elif len(typeSave) == 6:     # defaults for each type
               if typePlot[4:6] == '1d': xmlChild.set("type",typePlot[4:6]+':history')
               if typePlot[4:6] == '2d': xmlChild.set("type",typePlot[4:6]+':p-section')
               if typePlot[4:6] == '3d': xmlChild.set("type",typePlot[4:6]+':i-surface')
            else: raise Exception([{'name':'runXML','msg':'the type of your saved data should be in: ["save1d","save2d","save3d"] for '+xmlChild.attrib["xref"]}])
         else:
            if len(typeSave) == 4:
               if len(xmlChild.attrib["type"].split(':')) == 2: typeSave = typeSave + xmlChild.attrib["type"].split(':')[0]
               else: raise Exception([{'name':'runXML','msg':'do not know what dimension your saved data will be in: '+xmlChild.attrib["xref"]}])
            elif len(typeSave) == 6:
               if len(xmlChild.attrib["type"].split(':')) == 2:
                  if typeSave[4:6] != xmlChild.attrib["type"].split(':')[0]: raise Exception([{'name':'runXML','msg':'inconsistency in the dimension of your plotted data in: '+xmlChild.attrib["xref"]}])
               else: xmlChild.attrib["type"] = typeSave[4:6] + ":" + xmlChild.attrib["type"]
            else: raise Exception([{'name':'runXML','msg':'the type of your saved data should be in: ["save1d","save2d","save3d"] for '+xmlChild.attrib["xref"]}])
         save.active['type'] = typeSave
         extracting = xmlChild

         # ~~ Step 1. Common check for keys ~~~~~~~~~~~~~~~~~~~~~~~~
         try:
            save.addGroup(extracting,rank)
            report.update({ 'xref':save.active['xref'], 'updt':False, 'fail':False, 'warn':False, 'rank':save.active['rank'], 'value':0, 'title':'This was ignored' })
         except Exception as e:
            xcpt.append(filterMessage({'name':'runXML','msg':'add extract object to the list'},e,bypass))
            continue   # bypass the rest of the for loop

         # ~~> Temper with rank but still gather intelligence
         rankdo = save.dids[typeSave][save.active['xref']]['rank']

         # ~~> Default output formats
         if save.dids[typeSave][save.active['xref']]['outFormat'] == '':
            if typeSave[4:6] == "1d": save.dids[typeSave][save.active['xref']]['outFormat'] = 'csv'
            if typeSave[4:6] == "2d": save.dids[typeSave][save.active['xref']]['outFormat'] = 'slf'
            if typeSave[4:6] == "3d": save.dids[typeSave][save.active['xref']]['outFormat'] = 'slf'

         # ~~ Step 2. Cumul layers ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         for layer in extracting.findall("layer"):
            try:
               index,namex = save.addSubTask(layer)
               target = save.tasks[namex][index]["target"]
            except Exception as e:
               xcpt.append(filterMessage({'name':'runXML','msg':'add layer to the list'},e,bypass))
               continue   # bypass the rest of the for loop

            # ~~> round up targets and their configurations looking in exes and does
            xref = target ; src = ''
            if len(target.split(':')) > 1: xref,src = target.split(':')

            if xref in cast.dids['cast']:
               if src == '': src = save.tasks[namex][index]['vars'].split(';')[0].split(':')[0]
               layers = {}
               oneFound = False
               findlayer = []
               for cfgname in xmlConfig:
                  for var in cast.dids['cast'][xref]['vars']:
                     if src == var['xref']:
                        oneFound = True
                        findlayer = [[src],'','']
                  if findlayer != []: layers.update({ cfgname:findlayer })
               if layers == {}:
                  raise Exception([{'name':'runXML','msg':'could not find reference to save the cast: '+xref+':'+src}])
                  save.targetSubTask({},index,namex)
                  continue    # bypass the rest of the for loop
               else:
                  save.targetSubTask(layers,index,namex)

            elif src != '':
               if xref in do.dids:
                  layers = {}
                  oneFound = False
                  for cfgname in xmlConfig:
                     oneFound = True
                     findlayer = findTargets(do.dids[xref][cfgname],src)
                     if findlayer != []: layers.update({ cfgname:findlayer })
                  if oneFound and layers == {}:
                     raise Exception([{'name':'runXML','msg':'could not find reference to extract within actions: '+xref+':'+src}])
                     save.targetSubTask({},index,namex)
                     continue    # bypass the rest of the for loop
                  else:
                     save.targetSubTask(layers,index,namex)
               else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the action: '+xref+':'+src}])

            else:
               if save.tasks[namex][index]["where"] != '':
                  if path.exists(path.join(save.tasks[namex][index]["where"],target)):
                     findlayer = {}
                     t = path.splitext(path.basename(target))[1].lower()[1:]
                     for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(save.tasks[namex][index]["where"],target)],'',t] })
                     save.targetSubTask(findlayer,index,namex)
                  else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the action: '+target+' where '+save.tasks[namex][index]["where"]}])
               elif path.exists(path.join(save.path,target)):
                  findlayer = {}
                  t = path.splitext(path.basename(target))[1].lower()[1:]
                  for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(save.path,target)],'',t] })
                  save.targetSubTask(findlayer,index,namex)
               else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the action: '+target}])

            # ~~> round up decos, replacing the name by the associated deco dico
            # > at the action level
            if type(save.tasks['deco']) == type(''):
               if save.tasks['deco'] != '':
                  decos = save.tasks['deco'].split(';')
                  save.tasks['deco'] = {}
                  for deco in decos:
                     if dc.dids['deco'].has_key(deco):
                        save.tasks['deco'].update(dc.dids['deco'][deco])
                     else: raise Exception([{'name':'runXML','msg':'could not find reference to deco tag <'+deco+'> for figure "'+save.tasks['xref']+'"'}])
               elif dc.dids['deco'].has_key(save.tasks['xref']):
                  save.tasks['deco'] = dc.dids['deco'][save.tasks['xref']]
               else:
                  if typeSave[4:6] == '1d': save.tasks['deco'] = decoDefault1D
                  if typeSave[4:6] == '2d': save.tasks['deco'] = decoDefault2D
                  if typeSave[4:6] == '3d': save.tasks['deco'] = decoDefault3D
            # > at the layer level
            if type(save.tasks[namex][index]['deco']) == type(''):
               if save.tasks[namex][index]['deco'] != '':
                  decos = save.tasks[namex][index]['deco'].split(';')
                  save.tasks[namex][index]['deco'] = {}
                  for deco in decos:
                     if dc.dids['deco'].has_key(deco):
                        for name in dc.dids['deco'][deco]:
                           if name in ['look','data']: save.tasks[namex][index]['deco'].update(dc.dids['deco'][deco][name][0])
                     else: raise Exception([{'name':'runXML','msg':'could not find reference to deco tag <'+deco+'> for figure "'+save.tasks['xref']+'"'}])
               else:
                  if typeSave[4:6] == '1d': save.tasks[namex][index]['deco'] = decoDefault1D
                  if typeSave[4:6] == '2d': save.tasks[namex][index]['deco'] = decoDefault2D
                  if typeSave[4:6] == '3d': save.tasks[namex][index]['deco'] = decoDefault3D

         save.update(save.tasks)

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at extractions in xmlFile: '+xmlFile,'tree':xcpt})

   # ~~ Matrix distribution by extraction types ~~~~~~~~~~~~~~~~~~~~
   #for xref in save.order:
   #   for did in save.dids:
   #      if xref in save.dids[did]: typeSave = did
         xref = save.tasks['xref']

         task = save.dids[typeSave][xref]
         if not "layers" in task: continue
         oneFound = False
         for layer in task["layers"]:
            if layer['fileName'] != {}: oneFound = True
         if not oneFound: continue
         print '    +> reference: ',xref,' of type ',typeSave

         xlayers = ''   # now done with strings as arrays proved to be too challenging
         for layer in task["layers"]:
            if layer['config'] == 'together':
               xys = []
               for x in xlayers.split('|'): xys.append( (x+';'+':'.join( layer['fileName'].keys() )).strip(';') )
               xlayers = '|'.join(xys)
            elif layer['config'] == 'distinct':
               ylayers = layer['fileName'].keys()
               xys = []
               for i in range(len(ylayers)):
                  for x in xlayers.split('|'): xys.append( (x+';'+ylayers[i]).strip(';') )
               xlayers = '|'.join(xys)
            elif layer['config'] == 'oneofall':
               xys = []; cfg = layer['fileName'].iterkeys().next()     #/!\ you are sure to have at least one (?)
               for x in xlayers.split('|'): xys.append( (x+';'+cfg).strip(';') )
               xlayers = '|'.join(xys)
            else:
               if layer['config'] in layer['fileName']:
                  xys = []
                  for x in xlayers.split('|'): xys.append( (x+';'+layer['config']).strip(';') )
               xlayers = '|'.join(xys)

         nbFile = 0; alayers = xlayers.split('|')
         for cfglist in alayers:
            # ~~> Figure name
            if len(alayers) == 1:
               extractName = '.'.join([xref.replace(' ','_'),task['outFormat']])
            else:
               nbFile += 1
               extractName = '.'.join([xref.replace(' ','_'),str(nbFile),task['outFormat']])
            print '       ~> saved as: ',extractName
            extractName = path.join(path.dirname(xmlFile),extractName)
            # ~~> Create Figure
            if typeSave[4:6] == "1d": figure = Dumper1D(caster,task)
            if typeSave[4:6] == "2d": figure = Dumper2D(caster,task)
            if typeSave[4:6] == "3d": figure = Dumper3D(caster,task)

            for layer,cfgs in zip(task["layers"],cfglist.split(';')):
               for cfg in cfgs.split(':'):
                  for fle in layer['fileName'][cfg][0]:
                     figure.add( layer['fileName'][cfg][2], { 'file': fle,
                        'deco': {}, 'xref':xref,
                        'vars': layer["vars"], 'extract':layer["extract"], 'sample':layer["sample"],
                        'type': task['type'], 'time':layer["time"] } )

            figure.save(extractName)
            updated = True

         if updated: report.update({ 'updt':updated, 'title':'My work is done' })

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at savings in xmlFile: '+xmlFile,'tree':xcpt})

         oneFound = False
         for i in range(len(reports)):
            if reports[i]['xref'] == report['xref']:  #/!\ You are sure there is one xref (?)
               reports[i] = report
               oneFound = True
         if not oneFound: reports.append(report)

   # _________________________________________________________//      \\
   # _________________________________________________________>> PLOT <<
   #                                                          \\      //
   #for ploting in xmlRoot.findall(typePlot):
      if xmlChild.tag[0:4] == "plot":
         report = {}; updated = False
         # /!\ typePlot should be in ['plot1d','plot2d','plot3d','plotpv']
         typePlot = xmlChild.tag
         if "type" not in xmlChild.attrib:  #TODO: This will eventually be removed
            if len(typePlot) == 4: raise Exception([{'name':'runXML','msg':'do not know what dimension your plotted data will be in: '+xmlChild.attrib["xref"]}])
            elif len(typePlot) == 6:     # defaults for each type
               if typePlot[4:6] == '1d': xmlChild.set("type",typePlot[4:6]+':history')
               if typePlot[4:6] == '2d': xmlChild.set("type",typePlot[4:6]+':p-section')
               if typePlot[4:6] == '3d': xmlChild.set("type",typePlot[4:6]+':i-surface')
            else: raise Exception([{'name':'runXML','msg':'the type of your plot should be in: ["plot1d","plot2d","plot3d","plotpv"] for '+xmlChild.attrib["xref"]}])
         else:
            if len(typePlot) == 4:
               if len(xmlChild.attrib["type"].split(':')) == 2: typePlot = typePlot + xmlChild.attrib["type"].split(':')[0]
               else: raise Exception([{'name':'runXML','msg':'do not know what dimension your plotted data will be in: '+xmlChild.attrib["xref"]}])
            elif len(typePlot) == 6:
               if len(xmlChild.attrib["type"].split(':')) == 2:
                  if typePlot[4:6] != xmlChild.attrib["type"].split(':')[0]: raise Exception([{'name':'runXML','msg':'inconsistency in the dimension of your plotted data in: '+xmlChild.attrib["xref"]}])
               else: xmlChild.attrib["type"] = typePlot[4:6] + ":" + xmlChild.attrib["type"]
            else: raise Exception([{'name':'runXML','msg':'the type of your plot should be in: ["plot1d","plot2d","plot3d","plotpv"] for '+xmlChild.attrib["xref"]}])
         plot.active['type'] = typePlot
         ploting = xmlChild

         # ~~ Step 1. Common check for keys ~~~~~~~~~~~~~~~~~~~~~~~~
         try:
            plot.addDraw(ploting,rank)
            report.update({ 'xref':plot.active['xref'], 'updt':False, 'fail':False, 'warn':False, 'rank':plot.active['rank'], 'value':0, 'title':'This was ignored' })
         except Exception as e:
            xcpt.append(filterMessage({'name':'runXML','msg':'add plot to the list'},e,bypass))
            continue   # bypass the rest of the for loop

         # ~~> Temper with rank but still gather intelligence
         rankdo = plot.dids[typePlot][plot.active['xref']]['rank']

         # ~~ Step 2. Cumul layers ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         for layer in ploting.findall("layer"):
            try:
               index,namex = plot.addSubTask(layer)
               target = plot.tasks[namex][index]["target"]
            except Exception as e:
               xcpt.append(filterMessage({'name':'runXML','msg':'add layer to the list'},e,bypass))
               continue   # bypass the rest of the for loop

            # ~~> round up targets and their configurations looking in exes and does
            xref = target ; src = ''
            if len(target.split(':')) > 1: xref,src = target.split(':')

            if xref in cast.dids['cast']:
               if src == '': src = plot.tasks[namex][index]['vars'].split(';')[0].split(':')[0]
               layers = {}
               oneFound = False
               findlayer = []
               for cfgname in xmlConfig:
                  for var in cast.dids['cast'][xref]['vars']:
                     if src == var['xref']:
                        oneFound = True
                        findlayer = [[src],'','']
                  if findlayer != []: layers.update({ cfgname:findlayer })
               if layers == {}:
                  raise Exception([{'name':'runXML','msg':'could not find reference to draw the cast: '+xref+':'+src}])
                  plot.targetSubTask({},index,namex)
                  continue    # bypass the rest of the for loop
               else:
                  plot.targetSubTask(layers,index,namex)

            elif src != '':
               if xref in save.dids:
                  layers = {}
                  oneFound = False
                  for cfgname in xmlConfig:
                     oneFound = True
                     findlayer = findTargets(save.dids[xref][cfgname],src)
                     if findlayer != []: layers.update({ cfgname:findlayer })
                  if oneFound and layers == {}:
                     raise Exception([{'name':'runXML','msg':'could not find reference to draw the extract: '+xref+':'+src}])
                     plot.targetSubTask({},index,namex)
                     continue    # bypass the rest of the for loop
                  else:
                     plot.targetSubTask(layers,index,namex)
               elif xref in do.dids:
                  layers = {}
                  oneFound = False
                  for cfgname in xmlConfig:
                     oneFound = True
                     findlayer = findTargets(do.dids[xref][cfgname],src)
                     if findlayer != []: layers.update({ cfgname:findlayer })
                  if oneFound and layers == {}:
                     xcpt.append({'name':'runXML','msg':'could not find reference to draw the action: '+xref+':'+src})
                     plot.targetSubTask({},index,namex)
                     continue    # bypass the rest of the for loop
                  else:
                     plot.targetSubTask(layers,index,namex)
               else : raise Exception([{'name':'runXML','msg':'could not find reference to draw the action: '+xref}])

            else:
               if plot.tasks[namex][index]["where"] != '':
                  if path.exists(path.join(plot.tasks[namex][index]["where"],target)):
                     findlayer = {}
                     t = path.splitext(path.basename(target))[1].lower()[1:]
                     for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(plot.tasks[namex][index]["where"],target)],'',t] })
                     plot.targetSubTask(findlayer,index,namex)
                  else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the action: '+target+' where '+plot.tasks[namex][index]["where"]}])
               elif path.exists(path.join(plot.path,target)):
                  findlayer = {}
                  t = path.splitext(path.basename(target))[1].lower()[1:]
                  for cfgname in xmlConfig: findlayer.update({ cfgname:[[path.join(plot.path,target)],'',t] })
                  plot.targetSubTask(findlayer,index,namex)
               else : raise Exception([{'name':'runXML','msg':'could not find reference to extract the action: '+target}])

            # ~~> round up decos, replacing the name by the associated deco dico
            # > at the action level
            if type(plot.tasks['deco']) == type(''):
               if plot.tasks['deco'] != '':
                  decos = plot.tasks['deco'].split(';')
                  plot.tasks['deco'] = {}
                  for deco in decos:
                     if dc.dids['deco'].has_key(deco):
                        plot.tasks['deco'].update(dc.dids['deco'][deco])
                     else: raise Exception([{'name':'runXML','msg':'could not find reference to deco tag <'+deco+'> for figure "'+plot.tasks['xref']+'"'}])
               elif dc.dids['deco'].has_key(plot.tasks['xref']):
                  plot.tasks['deco'] = dc.dids['deco'][plot.tasks['xref']]
               else:
                  if typePlot[4:6] == '1d': plot.tasks['deco'] = {} #{'look':[decoDefault1D]}
                  if typePlot[4:6] == '2d': plot.tasks['deco'] = decoDefault2D
                  if typePlot[4:6] == '3d': plot.tasks['deco'] = decoDefault3D
            # > at the layer level
            if type(plot.tasks[namex][index]['deco']) == type(''):
               if plot.tasks[namex][index]['deco'] != '':
                  decos = plot.tasks[namex][index]['deco'].split(';')
                  plot.tasks[namex][index]['deco'] = {}
                  for deco in decos:
                     if dc.dids['deco'].has_key(deco):
                        for name in dc.dids['deco'][deco]:
                           if name in ['look','data']: plot.tasks[namex][index]['deco'].update(dc.dids['deco'][deco][name][0])
                     else: raise Exception([{'name':'runXML','msg':'could not find reference to layer deco tag: '+deco+' for figure '+plot.tasks['xref']}])
               else:
                  if typePlot[4:6] == '1d': plot.tasks[namex][index]['deco'] = {} #{'look':[decoDefault1D]}
                  if typePlot[4:6] == '2d': plot.tasks[namex][index]['deco'] = decoDefault2D
                  if typePlot[4:6] == '3d': plot.tasks[namex][index]['deco'] = decoDefault3D

         plot.update(plot.tasks)

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at targets in xmlFile: '+xmlFile,'tree':xcpt})

   # ~~ Matrix distribution by plot types ~~~~~~~~~~~~~~~~~~~~~~~~~~
   # /!\ configurations cannot be called "together" or "distinct" or "oneofall"
   #for xref in plot.order:
   #   for did in plot.dids:
   #      if xref in plot.dids[did]: typePlot = did
         xref = plot.tasks['xref']

         draw = plot.dids[typePlot][xref]
         if not "layers" in draw: continue
         oneFound = False
         for layer in draw["layers"]:
            if layer['fileName'] != {}: oneFound = True
         if not oneFound: continue
         print '    +> reference: ',xref,' of type ',typePlot

         xlayers = ''   # now done with strings as arrays proved to be too challenging
         for layer in draw["layers"]:
            if layer['config'] == 'together':
               xys = []
               for x in xlayers.split('|'): xys.append( (x+';'+':'.join( layer['fileName'].keys() )).strip(';') )
               xlayers = '|'.join(xys)
            elif layer['config'] == 'distinct':
               ylayers = layer['fileName'].keys()
               xys = []
               for i in range(len(ylayers)):
                  for x in xlayers.split('|'): xys.append( (x+';'+ylayers[i]).strip(';') )
               xlayers = '|'.join(xys)
            elif layer['config'] == 'oneofall':
               xys = []; cfg = layer['fileName'].iterkeys().next()     #/!\ you are sure to have at least one (?)
               for x in xlayers.split('|'): xys.append( (x+';'+cfg).strip(';') )
               xlayers = '|'.join(xys)
            else:
               if layer['config'] in layer['fileName']:
                  xys = []
                  for x in xlayers.split('|'): xys.append( (x+';'+layer['config']).strip(';') )
               xlayers = '|'.join(xys)
         if xlayers == '':
            #xcpt.append({'name':'runXML','msg':'could not find reference to draw the action: '+target})
            continue

         nbFile = 0; alayers = xlayers.split('|')
         for cfglist in alayers:
            # ~~> Figure name
            if len(alayers) == 1:
               figureName = '.'.join([xref.replace(' ','_'),draw['outFormat']])
            else:
               nbFile += 1
               figureName = '.'.join([xref.replace(' ','_'),str(nbFile),draw['outFormat']])
            print '       ~> saved as: ',figureName
            figureName = path.join(path.dirname(xmlFile),figureName)
            # ~~> Create Figure
            if typePlot[4:6] == "1d": figure = Figure1D(caster,draw)
            if typePlot[4:6] == "2d": figure = Figure2D(caster,draw)
            if typePlot[4:6] == "3d": figure = Figure3D(caster,draw)

            display = False
            for layer,cfgs in zip(draw["layers"],cfglist.split(';')):
               for cfg in cfgs.split(':'):
                  display = display or xmlConfig[cfg]['options'].display
                  for fle in layer['fileName'][cfg][0]:
                     figure.add( layer['fileName'][cfg][2], { 'file': fle,
                        'deco': layer["deco"], 'xref':xref,
                        'vars': layer["vars"], 'extract':layer["extract"], 'sample':layer["sample"],
                        'type': layer['type'], 'time':layer["time"] } )

            if display: figure.show()
            else: figure.save(figureName)
            updated = True

         if updated: report.update({ 'updt':updated, 'title':'My work is done' })

         if xcpt != []: raise Exception({'name':'runXML','msg':'looking at plotting in xmlFile: '+xmlFile,'tree':xcpt})

         oneFound = False
         for i in range(len(reports)):
            if reports[i]['xref'] == report['xref']:  #/!\ You are sure there is one xref (?)
               reports[i] = report
               oneFound = True
         if not oneFound: reports.append(report)

   # ~~ Error management ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if xcpt != []:  # raise full failure report
      raise Exception({'name':'runXML','msg':'in xmlFile: '+xmlFile,'tree':xcpt})

   # ~~ Final report summary ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   return reports

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban; Juliette C. Parisi; David H. Roscoe; "
__date__ ="$2-Aug-2011 11:51:36$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)
