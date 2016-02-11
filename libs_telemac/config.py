#!/usr/bin/env python
"""@author Sebastien E. Bourban and Noemie Durand
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
"""@history 30/04/2011 -- Sebastien E. Bourban
         Upgrade made to parseConfig_CompileTELEMAC, which does not use the
         GLOBAL variable anymore. The configuration is passed in argument.
"""
"""@history 30/04/2011 -- Sebastien E. Bourban
         Upgrade made to the others parseConfig_***TELEMAC just as
         previously done
"""
"""@history 19/06/2012 -- Yoann Audouin
         Bug corrected, replace the '<root>' in the output from getEXTERNALs
         by the actual root of the system
"""
"""@history 04/12/2012 -- Juliette Parisi and Sebastien E. Bourban
   Allowing users to define own a new section, "general", with own user
      keys as well as own user keys within each configuration.
      User keys are then replaced throughout all other values whenever [userkey]
      is used, such as (where fflags is an arbitrary user key):
fflags:     -c -O3 -ffixed-line-length-132 -fconvert=big-endian -frecord-marker=4
cmd_obj:    gfortran [fflags] <mods> <incs> <f95name>
   Note that if -c or USETELCFG is set, the replacement of user keys will only
      be done for that configuration
"""
"""@history 05/12/2012 -- Sebastien E. Bourban
   Allowing the user to set keys such as cmd_exe, cmd_obj and cmd_lib per
      module (for instance cmd_exe_parallel). For this, cfgTELEMAC['COMPILER']
      has been removed and replaced with a COMPILER for each module, just as
      for the incs, libs and mods.
   Also works where _all is not set, i.e. incs or incs_all work the same magic.
"""
"""@history 12/12/2012 -- Sebastien E. Bourban
   Addition of the --delete option to purge unwanted configuration-related
      sub-directories. Note that it will not remove the configuration from the
      config file.
   If the unwanted configuration does not exist in the config file anymore, it
      will read the [general] section, trying to guess the root and the version at
      the very least. One can also use -r and -v to inform of these values.
"""
"""@history 25/12/2014 -- Sebastien E. Bourban
   'version' is not mandatroy anymore.
   It has been removed from having to be in the configuration file.
"""
"""@brief
"""
"""@details
   A new TELEMAC config file has been designed to be more generic
   while simplifying the user input when dealing with Compilers,
   Zippers and other platform specific programs.
   The same TELEMAC config file is used to either Compile or Run
   the TELEMAC system, on a specific platform for a specific
   compiler, or even to translate the sources or the CAS files of
   a simulation or to create the Doxygen documentation. It is a
   multi-purpose config file.

   The structure os a TELEMAC config file always starts with the
   section:
      [Configurations]
   within which only one key is expected, 'configs', the list of
   configurations to be acted upon. Here are a few instances:
       configs: wintel32s wintel32p wing9532s wintel64s
       configs: source.gb
       configs: ubunsun32p ubunsun32s ubugfor32s
   The value field of the key 'configs' is space-delimited. Each
   sub-value will then be used as a pointer to its own section in
   the same TELEMAC config file. For instance:
      [wintel32s] ...
      [source.gb] ...
      [ubugfor32s] ...
   The name of each configuration is user difined.

   The rest of the TELEMAC config file is a list of these
   configurations, each of which follows the structure defined
   here below.

   Each configuration has a number of key/values, some of which
   are mandatory while others are dependant upon the action carried
   out for that configuration. For instance, for the translation of
   the source code (from French to English) the configuration is as
   follows:
      [sources.gb]
      root:       D:\systel\v6p0r8
      modules:    parallel artemis telemac2d
   - The key 'root' defines the directory path to the base of the
   TELEMAC system files.

   - the key 'module' defines the name of the modules upon which
     the action of the configuration is carried out. The module
   names that are not recognised as part of the TELEMAC system
   (following the template root\module) are
   ignored. Three additonal names are however allowed:
   - system: which is replaced by the list of all available modules
   - clean: which trigger the action to be carried out as if it was
     the first time
   - update: which trigger the action only to update the parts
     that are necessary.
   For instance, the compilation of the entire TELEMAC system,
   removing all existing object and libraries would simply write:
      [wintel32s]
      root:       D:\systel\v6p0r8
      modules:    clean system
   Note that the order of appearance of the names of the module has
   no bearing on the action. For the compilation of modules of the
   TELEMAC system, for instance, the python defines the true tree
   of dependencies.

   For the compilation of (parts of) the TELEMAC system, the
   following key are also required:
      cmd_obj:   ifort.exe /c /Ot /iface:cref /iface:nomixed_str_len_arg /nologo /names:uppercase /convert:big_endian /extend_source:132 <mods> <incs> <f95name>
      cmd_lib:   xilib.exe /nologo /out:<libname> <?libname?> <objs>
      cmd_exe:   xilink.exe /nologo /subsystem:console /stack:536870912 /out:<exename> <objs> <libs>
   and
      sfx_lib:         .lib
      sfx_obj:         .obj
      sfx_mod:         .mod
      sfx_exe:         .exe
   The 'cmd_' keys are commands, written in full as executed in a
   terminal windows. Within each command, a few tags are defined,
   such as <libname>, which are used by the compiler to replace by
   the appropriate value.
   The 'sfx_' keys are used to define the suffix of each type of
   file. A library would have a '.lib' extension on windows while
   having a '.a' extension on Linux, for instance. The suffix can
   also be empty, which is appropriate for executables on Linux,
   for instance, as opposed to '.exe' on windows.

   Note that sfx_zip is used to define what type of ZIPPER will be called,
   depending on the platform. So .zip will launch a windows-like zip archive
   while .gztar will launch the stadard tarball and gzip tools, if installed.

   For the compilation of (parts of) the TELEMAC system, the
   following key are optional, but there to provide flexibility:
      mods_all:        -M<config>
      libs_all:        <root>\XDMF\XdmfUtils.a
   and
      incs_parallel:   -I/usr/include/mpich2
      libs_parallel:   /usr/lib/metis-4.0/libmetis.a
      libs_sisyphe:    /usr/lib/libfmpich.so
   While the '_all' are use commonly accorss all modules, it is
   possible to also specify specific dependencies, such as
   libs_parallel, for which the libmetix only applies to the
   executables of the parallel module (partel, gretel, etc.). The
   first 4 letters, are incs, libs, or mods and define how the
   compiler should link to include, library and module files.
"""
# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import re
import sys
from os import path, walk, listdir, environ, sep
from socket import gethostname
import ConfigParser
from optparse import OptionParser
from utils.files import removeDirectories
from utils.messages import MESSAGES,filterMessage,banner

# _____                   __________________________________________
# ____/ Global Variables /_________________________________________/
#
"""
   Contains the entire configuration tree for all user configurations.
   By default the name is systel.cfg stored locally
"""
CONFIGS = {}

# _____                        _____________________________________
# ____/ Configuration Toolbox /____________________________________/
#
"""
   Read the content of the config file and extract all cfgs,
   and their key/values -- Returns a dictionary of all configs in
   the files that are highlighted in [Configurations]
"""
def getConfigs(file,name,bypass=False):
   # ~~ Read Configuration File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   cfgfile = ConfigParser.RawConfigParser()
   try:
      cfgfile.read(file)
   except Exception as e:
      raise Exception([filterMessage({'name':'getConfigs','msg':' ... Some of the lines may not start with a comment #.'},e,bypass)])
   # ~~ Read Config Names ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   cfgs = cfgfile.get('Configurations','configs')
   if cfgs == '' :
      print '\nPlease specify appropriate configuration names for key [Configurations] in the config file\n'
      sys.exit(1)
   # ~~ Filter Config Names ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   cfgnames = cfgs.split()
   if name != '':
      if name not in cfgnames:
         print '\nNot able to find your configuration [' + name + '] in the configuration file: ' + file
         if bypass: print ' ... will try to gess the configuration from the general keys and move on ...'
         else:
            print '\n ... use instead:'
            for cfg in cfgnames : print '    +> ',cfg
            sys.exit(1)

      cfgnames = [name]
   # ~~ Verify presence of configs ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for cfg in cfgnames:
      if cfg not in cfgfile.sections():
         print '\nNot able to find the configuration [' + cfg + '] in the configuration file: ' + file
         sys.exit(1)
   # ~~ Read General ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   try:
      general = dict(cfgfile.items('general'))
   except:
      general = {}
   # ~~ Loads Configurations ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   configs = {}
   for cfg in cfgnames :
      try:
         configs.update({cfg:dict(cfgfile.items(cfg))}) # convert all keys in lower case !
      except:
         configs.update({cfg:{}})

   return general,configs

"""
   Get the name of the config file from command line arguments
   and store its rough content in a dict -- Returns the dict
   set globals CONFIGS
"""
def parseConfigFile(file,name,bypass=False):
   # ~~ Parse CFG File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print "... parsing configuration file: " + file
   generalDict,configDict = getConfigs(file,name,bypass)

   # ~~ Replacing user keys throughout ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   key_sqbrack = re.compile(r'(?P<brack>\[[\w_.-~=+]*?\])') #,re.I)
   for cfgname in configDict:
      # ~~> making sure cfgname also includes all keys from general
      for genkey in generalDict :
         if not genkey in configDict[cfgname]: configDict[cfgname].update({genkey:generalDict[genkey]})
      # ~~> replacing [key] by its value
      for cfgkey in configDict[cfgname]:
         for k in re.findall(key_sqbrack,configDict[cfgname][cfgkey]):
            key = k.strip('[]')
            if configDict[cfgname].has_key(key): configDict[cfgname][cfgkey] = configDict[cfgname][cfgkey].replace(k,configDict[cfgname][key])
            elif environ.has_key(key): configDict[cfgname][cfgkey] = configDict[cfgname][cfgkey].replace(k,environ[key])
            else:
               print '... Could not find your special key ',k,' in key ',cfgkey,' of configuration ',cfgname
   globals()["CONFIGS"] = configDict
   return configDict

"""
   Get the value of a key from the config cfg. Further, test if
   the key is there and if it is empty -- Return the value
"""
def getConfigKey(cfg,key,there,empty):
   # ~~ Get the root of the System ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if there and not key in cfg:
      print ('\nKey %s required in configuration (or on the command line as an option) \n' % (key))
      sys.exit(1)
   if empty and cfg[key] == '':
      print ('\nKey %s required non empty field \n' % (key))
      sys.exit(1)
   if not key in cfg: return ''
   return cfg[key]

# _____                  ___________________________________________
# ____/ TELEMAC Toolbox /__________________________________________/
#
"""
   Extract all the information required for
   the Compilation of TELEMAC
   Requires: root,
   Optional: mods_, incs_, libs_, ... and options
"""
def parseConfig_CompileTELEMAC(cfg):
   #  cfg is the dictionary of either  wintel32s wintel32p wing9532s wing9532p ...
   cfgTELEMAC = {}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(cfg,'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC.update({'root':path.normpath(get)})
   # Get version if present
   get = getConfigKey(cfg,'version',False,False).lower()
   cfgTELEMAC.update({'version':get})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\*telver\
   cfgTELEMAC.update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC['root'])})
   # Get libs_all: ... libs_artemis: ... mods_all: ... etc.
   # for every module in the list of modules to account for
   # specific external includes for all or each module
   for mod in cfgTELEMAC['MODULES']:
      cfgTELEMAC['MODULES'][mod].update({'mods':addEXTERNALs(cfg,'mods',mod).replace('<root>',cfgTELEMAC['root'])})
      cfgTELEMAC['MODULES'][mod].update({'incs':addEXTERNALs(cfg,'incs',mod).replace('<root>',cfgTELEMAC['root'])})
      cfgTELEMAC['MODULES'][mod].update({'libs':addEXTERNALs(cfg,'libs',mod).replace('<root>',cfgTELEMAC['root'])})
   # Get cmd_obj: ... cmd_lib: ... cmd_exe: ...
   # the compiler dependent command lines to create obj, lib and exe
   for mod in cfgTELEMAC['MODULES']:
      cfgTELEMAC['MODULES'][mod].update({'xobj':getEXTERNALs(cfg,'cmd_obj',mod).replace('<root>',cfgTELEMAC['root'])})
      cfgTELEMAC['MODULES'][mod].update({'xlib':getEXTERNALs(cfg,'cmd_lib',mod).replace('<root>',cfgTELEMAC['root'])})
      cfgTELEMAC['MODULES'][mod].update({'xexe':getEXTERNALs(cfg,'cmd_exe',mod).replace('<root>',cfgTELEMAC['root'])})

   cfgTELEMAC.update({'COMPILER':{}})
   # Get modules: user list of module
   # in which 'system' means all existing modules,
   # and in which 'update' means a rebuild of the lib and exe
   # and in which 'clean' means a rebuild of the obj, lib and exe
   # and Get options: for the switches such as parallel, openmi, mumps, etc.
   get,tbd = parseUserModules(cfg,cfgTELEMAC['MODULES'])
   cfgTELEMAC['COMPILER'].update({'MODULES':get.split()})
   cfgTELEMAC['COMPILER'].update({'REBUILD':tbd})
   for mod in get.split():
      if mod not in cfgTELEMAC['MODULES']:
         print ('\nThe following module does not exist %s \n' % (mod))
         sys.exit(1)
   for mod in get.split():
      if mod not in cfgTELEMAC['MODULES']:
         del cfgTELEMAC['COMPILER']['MODULES'][cfgTELEMAC['COMPILER']['MODULES'].index(mod)]

   # Get command_zip: and command_piz:
   # the command lines to zip/unzip respectively
   cfgTELEMAC.update({'ZIPPER':getConfigKey(cfg,'sfx_zip',True,False)[1:]})

   # Get system's suffixes for obj, lib, mod, and exe
   system = {}
   system.update({'sfx_obj':getConfigKey(cfg,'sfx_obj',True,False).lower()})
   system.update({'sfx_exe':getConfigKey(cfg,'sfx_exe',True,False).lower()})
   system.update({'sfx_lib':getConfigKey(cfg,'sfx_lib',True,False).lower()})
   system.update({'sfx_mod':getConfigKey(cfg,'sfx_mod',True,False).lower()})
   cfgTELEMAC.update({'SYSTEM':system})

   # tagged fields for cmdx and cmdo
   cfgTELEMAC.update({'TRACE':{}})
   for k in cfg:
      if k[0:4] in ['root','libs']:
          get = getConfigKey(cfg,k,False,False)
          if get != '': cfgTELEMAC['TRACE'].update({k:get})

   return cfgTELEMAC

"""
   Extract all the information required for
   the Translation of the source code of the TELEMAC system
"""
def parseConfig_TranslateTELEMAC(cfg):
   #  cfg is either  sources.gb ...
   cfgTELEMAC = {cfg:{}}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(CONFIGS[cfg],'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC[cfg].update({'root':path.normpath(get)})
   # Get version if present
   get = getConfigKey(CONFIGS[cfg],'version',False,False).lower()
   cfgTELEMAC[cfg].update({'version':get})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\*telver\
   cfgTELEMAC[cfg].update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC[cfg]['root'])})
   cfgTELEMAC[cfg].update({'COMPILER':{}})
   # Get cmplr_mod: user list of module
   get,tbd = parseUserModules(CONFIGS[cfg],cfgTELEMAC[cfg]['MODULES'])
   cfgTELEMAC[cfg]['COMPILER'].update({'MODULES':get.split()})
   for mod in get.split():
      if mod not in cfgTELEMAC[cfg]['MODULES']:
         print ('\nThe following module does not exist %s \n' % (mod))
         sys.exit(1)
   for mod in get.split():
      if mod not in cfgTELEMAC[cfg]['MODULES']:
         del cfgTELEMAC[cfg]['COMPILER']['MODULES'][cfgTELEMAC[cfg]['COMPILER']['MODULES'].index(mod)]

   return cfgTELEMAC

"""
   Extract all the information required for
   the Translation of CAS files when running TELEMAC
"""
def parseConfig_TranslateCAS(cfg):
   #  cfg is either  sources.gb ...
   cfgTELEMAC = {cfg:{}}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(CONFIGS[cfg],'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC[cfg].update({'root':path.normpath(get)})
   # Get version if present
   get = getConfigKey(CONFIGS[cfg],'version',False,False).lower()
   cfgTELEMAC[cfg].update({'version':get})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\*telver\
   cfgTELEMAC[cfg].update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC[cfg]['root'])})
   cfgTELEMAC[cfg].update({'COMPILER':{}})
   # Get cmplr_mod: user list of module
   get,tbd = parseUserModules(CONFIGS[cfg],cfgTELEMAC[cfg]['MODULES'])
   cfgTELEMAC[cfg]['COMPILER'].update({'MODULES':get.split()})
   for mod in get.split():
      if mod not in cfgTELEMAC[cfg]['MODULES']:
         print ('\nThe following module does not exist %s \n' % (mod))
         sys.exit(1)
   for mod in get.split():
      if mod not in cfgTELEMAC[cfg]['MODULES']:
        del cfgTELEMAC[cfg]['COMPILER']['MODULES'][cfgTELEMAC[cfg]['COMPILER']['MODULES'].index(mod)]

   # Get tellng:
   # TELEMAC language code, to know the default language
   # tellng = 1, French; tellng = 2, English
   get = getConfigKey(CONFIGS[cfg],'language',True,True)
   cfgTELEMAC[cfg].update({'language':get})

   return cfgTELEMAC

"""
   Extract all the information required for
   the Documentation of TELEMAC preparing for Doxygen
"""
def parseConfig_DoxygenTELEMAC(cfg):
   #  cfg is either  sources.gb ...
   cfgTELEMAC = {}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(cfg,'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC.update({'root':path.normpath(get)})
   # Get destination doxydocs: ...
   get = getConfigKey(cfg,'doxydocs',True,True).lower()
   cfgTELEMAC.update({'doxydocs':get})
   # Get doxygen command: ...
   get = getConfigKey(cfg,'cmd_doxygen',True,True).lower()
   cfgTELEMAC.update({'cmd_doxygen':get})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\*telver\
   cfgTELEMAC.update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC['root'])})

   cfgTELEMAC.update({'COMPILER':{}})
   # Get modules: user list of module
   # in which 'system' means all existing modules,
   # and in which 'update' means an update only of the source files and tags
   # and in which 'clean' means a rebuild of all source files and tags
   # and Get options: for the switches such as parallel, openmi, mumps, etc.
   get,tbd = parseUserModules(cfg,cfgTELEMAC['MODULES'])
   cfgTELEMAC['COMPILER'].update({'MODULES':get.split()})
   cfgTELEMAC['COMPILER'].update({'REBUILD':tbd})
   for mod in get.split():
      if mod not in cfgTELEMAC['MODULES']:
         print ('\nThe following module does not exist %s \n' % (mod))
         sys.exit(1)
   for mod in get.split():
      if mod not in cfgTELEMAC['MODULES']:
        del cfgTELEMAC['COMPILER']['MODULES'][cfgTELEMAC['COMPILER']['MODULES'].index(mod)]

   # Get command_zip: and command_piz:
   # the command lines to zip/unzip respectively
   cfgTELEMAC.update({'ZIPPER':getConfigKey(cfg,'sfx_zip',True,False)[1:]})

   # Get system's suffixes for obj, lib, mod, and exe
   system = {}
   #system.update({'sfx_obj':getConfigKey(cfg,'sfx_obj',True,False).lower()})
   #system.update({'sfx_exe':getConfigKey(cfg,'sfx_exe',True,False).lower()})
   #system.update({'sfx_lib':getConfigKey(cfg,'sfx_lib',True,False).lower()})
   #system.update({'sfx_mod':getConfigKey(cfg,'sfx_mod',True,False).lower()})
   cfgTELEMAC.update({'SYSTEM':system})

   return cfgTELEMAC

"""
   Extract all the information required for the Extraction
   of the relevant binaries and files for each configuration
"""
def parseConfig_CompactTELEMAC(cfg):
   #  cfg is either  sources.gb ...
   cfgTELEMAC = {}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(cfg,'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC.update({'root':path.normpath(get)})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\*telver\
   cfgTELEMAC.update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC['root'])})

   # Get command_zip: and command_piz:
   # the command lines to zip/unzip respectively
   cfgTELEMAC.update({'ZIPPER':getConfigKey(cfg,'sfx_zip',True,True)[1:]})

   return cfgTELEMAC

"""
   Extract all the information required for the validation
   of the relevant modules for each configuration
   The principal assumption is that the validation cases are
   either under:
     + val_root\\*
     + teldir\\examples\\module\\val_root\\*
   If the 'val_root' key is not in the config, the default
   path is assumed to be based on the second option
"""
def parseConfig_ValidateTELEMAC(cfg):
   #  cfg is either  wintel32s wintel32p wing9532s wing9532p ...
   cfgTELEMAC = {}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(cfg,'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC.update({'root':path.normpath(get)})
   # Get version if present
   get = getConfigKey(cfg,'version',False,False).lower()
   cfgTELEMAC.update({'version':get})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\
   cfgTELEMAC.update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC['root'])})
   # Get libs_all: ... libs_artemis: ... mods_all: ... etc.
   # for every module in the list of modules to account for
   # specific external includes for all or each module
   for mod in cfgTELEMAC['MODULES']:
      cfgTELEMAC['MODULES'][mod].update({'mods':addEXTERNALs(cfg,'mods',mod).replace('<root>',cfgTELEMAC['root'])})
      cfgTELEMAC['MODULES'][mod].update({'incs':addEXTERNALs(cfg,'incs',mod).replace('<root>',cfgTELEMAC['root'])})
      cfgTELEMAC['MODULES'][mod].update({'libs':addEXTERNALs(cfg,'libs',mod).replace('<root>',cfgTELEMAC['root'])})

   cfgTELEMAC.update({'VALIDATION':{}})
   # Get ranks: user list of ranks to filter the list of validation cases
   # in which 'all' means all possible ranks,
   # in which '<n' means all ranks less than n,
   # in which 'n' means all ranks equal to n,
   # in which '>n' means all ranks greater than n,
   # where 'n', '>n', and '<n' can be combined if necessary
   if not 'val_rank' in cfg: val_ranks = range(10)
   else: val_ranks = parseValidationRanks(cfg['val_rank'])
   # Get validation: user list of module and there associated directories
   # in which 'system' means all existing modules,
   # and in which 'update' means a continuation, ignoring previously completed runs
   # and in which 'clean' means a re-run of all validation tests
   if not 'val_root' in cfg:
      val_root = path.realpath(path.join(cfgTELEMAC['root'],'examples'))
      if not path.isdir(val_root):
         print '\nNot able to find your validation set from the path: ' + val_root + '\n'
         print ' ... check the val_root key in your configuration file'
         sys.exit(1)
   else:
      val_root = cfg['val_root'].replace('<root>',cfgTELEMAC['root'])
   _, examples, _ = walk(val_root).next()
   get,tbd = parseUserModules(cfg,cfgTELEMAC['MODULES'])
   cfgTELEMAC.update({'REBUILD':tbd})
   for mod in (' '.join(examples)).split():   # /!\ other ways to copy ?
      if mod not in get and mod in cfgTELEMAC['MODULES']: examples.remove(mod)
   for mod in examples:
      val_dir = path.join(val_root,mod)
      val_mod = getFiles_ValidationTELEMAC(val_dir,val_ranks)
      if val_mod != {}:
         cfgTELEMAC['VALIDATION'].update({mod:{'path':path.realpath(val_dir)}})
         cfgTELEMAC['VALIDATION'][mod].update(val_mod)

   # Get path_parallel for partel
   cfgTELEMAC.update({'PARTEL':getPARTEL(cfg)})
   # Get mpi_cpulist and mpi_cmdexec: for mpi option
   # .. in theory, mpi could be replaced by something else (?)
   cfgTELEMAC.update({'MPI':getMPI(cfg)})
   # Get hpc_cmdexec and hpc_infile for hpc option
   # .. in theory, bsub could be replaced by another queueing system
   cfgTELEMAC.update({'HPC':getHPC(cfg)})

   # Get command_zip: and command_piz:
   # the command lines to zip/unzip respectively
   cfgTELEMAC.update({'ZIPPER':getConfigKey(cfg,'sfx_zip',True,True)[1:]})

   # Get system's suffixes for obj, lib, mod, and exe
   system = {}
   system.update({'sfx_obj':getConfigKey(cfg,'sfx_obj',True,False).lower()})
   system.update({'sfx_exe':getConfigKey(cfg,'sfx_exe',True,False).lower()})
   system.update({'sfx_lib':getConfigKey(cfg,'sfx_lib',True,False).lower()})
   system.update({'sfx_mod':getConfigKey(cfg,'sfx_mod',True,False).lower()})
   cfgTELEMAC.update({'SYSTEM':system})

   # tagged fields for cmdx and cmdo
   cfgTELEMAC.update({'TRACE':{}})
   for k in cfg:
      if k[0:4] in ['root','libs']:
          get = getConfigKey(cfg,k,False,False)
          if get != '': cfgTELEMAC['TRACE'].update({k:get})

   return cfgTELEMAC

"""
   Extract all the information required for the launch and execution
   of TELEMAC based on one CAS file, for each configuration
"""
def parseConfig_RunningTELEMAC(cfg):
   #  cfg is either  wintel32s wintel32p wing9532s wing9532p ...
   cfgTELEMAC = {}
   # Get teldir: ...
   # or the absolute path to the TELEMAC root
   get = getConfigKey(cfg,'root',True,True)
   if not path.exists(get):
      print ('\nThe following directory does not exist %s \n' % (get))
      sys.exit(1)
   cfgTELEMAC.update({'root':path.normpath(get)})
   # Get version if present
   get = getConfigKey(cfg,'version',False,False).lower()
   cfgTELEMAC.update({'version':get})
   # Get options for printing purposes
   get = getConfigKey(cfg,'options',False,False).lower()
   cfgTELEMAC.update({'options':get})

   # Deduce the actual list of modules existing within the root teldir,
   # identified by matching the directory structure to the template
   # teldir\module_name\*telver\
   cfgTELEMAC.update({'MODULES':getFolders_ModulesTELEMAC(cfgTELEMAC['root'])})

   get,tbd = parseUserModules(cfg,cfgTELEMAC['MODULES'])
   cfgTELEMAC.update({'REBUILD':tbd})
   # You do not need 'get' at this stage

   # Get path_parallel: for parallel option
   # the parallel dependent command line executables (partel, gretel, ...)
   cfgTELEMAC.update({'PARTEL':getPARTEL(cfg)})
   # Get mpi_cpulist and mpi_cmdexec: for mpi option
   # .. in theory, mpi could be replaced by something else (?)
   cfgTELEMAC.update({'MPI':getMPI(cfg)})
   # Get hpc_cmdexec and hpc_infile for hpc option
   # .. in theory, bsub could be replaced by another queueing system
   cfgTELEMAC.update({'HPC':getHPC(cfg)})

   # Get command_zip: and command_piz:
   # the command lines to zip/unzip respectively
   cfgTELEMAC.update({'ZIPPER':getConfigKey(cfg,'sfx_zip',True,True)[1:]})

   # Get system's suffixes for obj, lib, mod, and exe
   system = {}
   system.update({'sfx_obj':getConfigKey(cfg,'sfx_obj',True,False).lower()})
   system.update({'sfx_exe':getConfigKey(cfg,'sfx_exe',True,False).lower()})
   system.update({'sfx_lib':getConfigKey(cfg,'sfx_lib',True,False).lower()})
   system.update({'sfx_mod':getConfigKey(cfg,'sfx_mod',True,False).lower()})
   cfgTELEMAC.update({'SYSTEM':system})

   # tagged fields for cmdx and cmdo
   cfgTELEMAC.update({'TRACE':{}})
   for k in cfg:
      if k[0:4] in ['root','libs']:
          get = getConfigKey(cfg,k,False,False)
          if get != '': cfgTELEMAC['TRACE'].update({k:get})

   return cfgTELEMAC

"""
   Get the root of the validation directory and walk from there
   through the directory structure to identify modules with the template
   val_root\module_name\*\*.xml
"""
def getFiles_ValidationTELEMAC(root,ranks):
   validation = {}

   dirpath, dirnames, _ = walk(root).next()
   for ddir in dirnames:
      val = { ddir:[] }
      _, _, filenames = walk(path.join(dirpath,ddir)).next()
      for fle in filenames:
         if path.splitext(fle)[1] == '.xml' : val[ddir].append(fle)
      if val[ddir] != []: validation.update(val)

   return validation

"""
   Walk through the directory structure available from the root
   and identifies modules with the template
   sources\module_name
"""
def getFolders_ModulesTELEMAC(root):
   modules = {}
   sources = path.join(root,'sources')
   if not path.exists(sources):
      print '... I could not locate the source code in ',sources
      print '\nThe root key in your cfg file may not be valid.'
      sys.exit(1)
   for moddir in listdir(sources) :
      if not (moddir[0] == '.' or path.isfile(path.join(sources,moddir))) :
         modroot = path.join(sources,moddir.lower())
         if path.exists(modroot) :
            dirpath, dirnames, filenames = walk(modroot).next()
            # ~~> One level in modroot
            for fle in filenames :
               f = path.splitext(fle)
               if f[len(f)-1].lower() in ['.dico']:   # /!\ you found an executable module
                  if not moddir in modules: modules.update({moddir:{'path':dirpath,'dico':fle,'cmdfs':[]}})
                  else: modules[moddir].update({'dico':fle})
               if f[len(f)-1].lower() in ['.cmdf']:   # /!\ you found at least one cmdf file
                  if not moddir in modules: modules.update({moddir:{'path':dirpath,'cmdfs':[path.join(dirpath,fle)]}})
                  elif not 'cmdfs' in modules[moddir]: modules[moddir].update({'cmdfs':[path.join(dirpath,fle)]})
                  else: modules[moddir]['cmdfs'].append(path.join(dirpath,fle))
               if f[len(f)-1].lower() in ['.f','.f90']:      # /!\ you found a source file
                  if not moddir in modules: modules.update({moddir:{'path':dirpath,'files':[path.join(dirpath,fle)],'cmdfs':[]}})
                  elif not 'files' in modules[moddir]: modules[moddir].update({'files':[path.join(dirpath,fle)]})
                  else: modules[moddir]['files'].append(path.join(dirpath,fle))
            # ~~> Two levels in modroot

            for subdir in dirnames:
               if subdir[0] != '.':
                  # Special treatment for folders in utils as they are like the one
                  if path.basename(modroot) == 'utils':
                     subpath, subnames, filenames = walk(path.join(modroot,subdir)).next()
                     for fle in filenames :
                        f = path.splitext(fle)
                        if f[len(f)-1].lower() in ['.dico']:   # /!\ you found an executable module
                           if not subdir in modules: modules.update({subdir:{'path':subpath,'dico':fle,'cmdfs':[]}})
                           else: modules[subdir].update({'dico':fle})
                        if f[len(f)-1].lower() in ['.cmdf']:   # /!\ you found at least one cmdf file
                           if not subdir in modules: modules.update({subdir:{'path':subpath,'cmdfs':[path.join(subpath,fle)]}})
                           elif not 'cmdfs' in modules[subdir]: modules[subdir].update({'cmdfs':[path.join(subpath,fle)]})
                           else: modules[subdir]['cmdfs'].append(path.join(subpath,fle))
                        if f[len(f)-1].lower() in ['.f','.f90']:      # /!\ you found a source file
                           if not subdir in modules: modules.update({subdir:{'path':subpath,'files':[path.join(subpath,fle)],'cmdfs':[]}})
                           elif not 'files' in modules[subdir]: modules[subdir].update({'files':[path.join(subpath,fle)]})
                           else: modules[subdir]['files'].append(path.join(subpath,fle))
                     for subsubdir in subnames:
                        if subsubdir[0] != '.':
                           _, _, filenames = walk(path.join(modroot,subdir,subsubdir)).next()
                           for fle in filenames :
                              modName=path.basename(subsubdir)
                              f = path.splitext(fle)
                              if f[len(f)-1].lower() in ['.f','.f90']:      # /!\ you found a source file
                                 if not modName in modules: modules.update({modName:{'path':subpath,'files':[path.join(subpath,fle)],'cmdfs':[]}})
                                 elif not 'files' in modules[modName]: modules[modName].update({'files':[path.join(subpath,fle)]})
                                 else: modules[modName]['files'].append(path.join(subpath,fle))
                  else:
                     subpath, _, filenames = walk(path.join(modroot,subdir)).next()
                     for fle in filenames :
                        modName=path.basename(modroot)
                        f = path.splitext(fle)
                        if f[len(f)-1].lower() in ['.f','.f90']:      # /!\ you found a source file
                           if not modName in modules: modules.update({modName:{'path':subpath,'files':[path.join(subpath,fle)],'cmdfs':[]}})
                           elif not 'files' in modules[modName]: modules[modName].update({'files':[path.join(subpath,fle).replace(sep,'|')]})
                           else: modules[modName]['files'].append(path.join(subpath,fle))


   return modules

"""
   Etract links to user defined external dependencies
   whether a lib, a mod or an include following the template
   key ext_all and ext_..., with ext = mods, incs, libs
"""
def addEXTERNALs(cfgDict,ext,mod): # key ext_all and ext_..., with ext = mods, incs, libs, cmd_*
   # ~~ Loads External Dependencies ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   extList = ''
   if ext in cfgDict: extList = cfgDict[ext]
   ext_all = ext + '_all'
   if ext_all in cfgDict: extList += ' ' + cfgDict[ext_all]
   ext_mod = ext + '_' + mod
   if ext_mod in cfgDict: extList += ' ' + cfgDict[ext_mod]
   return extList

"""
   Etract links to user defined external dependencies
   whether a lib, a mod or an include following the template
   key ext_all and ext_..., with ext = cmd_obj, cmd_lib, cmd_exe
"""
def getEXTERNALs(cfgDict,ext,mod): # key ext_all and ext_..., with ext = mods, incs, libs, cmd_*
   # ~~ Loads External Dependencies ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   extList = ''
   if ext in cfgDict: extList = cfgDict[ext]
   ext_all = ext + '_all'
   if ext_all in cfgDict: extList = cfgDict[ext_all]
   ext_mod = ext + '_' + mod
   if ext_mod in cfgDict: extList = cfgDict[ext_mod]
   return extList

"""
   Extract full user defined comand line
   for the treatment of the PARTEL in parallel
"""
def getPARTEL(cfgDict):
   # ~~ Loads Compiler Commands ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   partel = {}
   if cfgDict.has_key('par_path'): partel.update({'PATH':cfgDict['par_path']})
   if cfgDict.has_key('par_cmdexec'): partel.update({'EXEC':cfgDict['par_cmdexec']})
   return partel

"""
   Extract full user defined comand line
   for the treatment of the option 'mpi'
"""
def getMPI(cfgDict):
   # ~~ Loads Compiler Commands ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   mpi = {}
   if cfgDict.has_key('mpi_cmdexec'):
      mpi.update({'EXEC':cfgDict['mpi_cmdexec']})
      if cfgDict.has_key('mpi_infile'): mpi.update({'INFILE':cfgDict['mpi_infile']})
      mpi.update({'HOSTS':gethostname().split('.')[0]}) # /!\ defaulting on  the local hostname
      if cfgDict.has_key('mpi_hosts'):
         if len(cfgDict['mpi_hosts'].split()) > 0: mpi['HOSTS'] = cfgDict['mpi_hosts']
      mpi.update({'HOSTFILE': 'MPI_HOSTFILE'})
   return mpi

"""
   Extract full user defined comand line
   for the treatment of the option 'hpc', Here bsub is used as an example
"""
def getHPC(cfgDict):
   # ~~ Loads Compiler Commands ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   hpc = {}
   if cfgDict.has_key('hpc_cmdexec'):
      hpc.update({'EXCODE':cfgDict['hpc_cmdexec']})
      if cfgDict.has_key('hpc_stdin'): hpc.update({'STDIN':['HPC_STDIN',cfgDict['hpc_stdin'].replace(r'\n','\n')]})
   if cfgDict.has_key('hpc_runcode'):
      hpc.update({'PYCODE':cfgDict['hpc_runcode']})
      if cfgDict.has_key('hpc_stdin'): hpc.update({'STDIN':['HPC_STDIN',cfgDict['hpc_stdin'].replace(r'\n','\n')]})
   if cfgDict.has_key('hpc_depend'):
      hpc.update({'DEPEND':cfgDict['hpc_depend']})
   return hpc

"""
   Read the list of user defined modules for action -- Certain
   keyword such as clean, update, system will trigger additonal
   behaviours:
    - clean: rebuilt = 1, rebuild object, libs and executables
    - update: rebuilt = 2, rebuild libs and executables
    - modify: rebuilt = 3, compile only the necessary files and rebuild libs and executables
    - system (or nothing): include all modules
   Will alos read the specif option and build the list of modules
   according to the stwiches, i.e. parallel, openmi, xdmf, etc.
"""
def parseUserModules(cfgDict,modules):
   # ~~ Loads To-Be Compiled ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   typeBuild = 0; userList = ''
   userList = 'clean ' + ' '.join(modules.keys())
   if 'modules' in cfgDict:
      if cfgDict['modules'].strip() != '': userList = cfgDict['modules']
   # ~~ Loads To-Be Compiled ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   word = r'\s*(?P<before>.*)\s*(?P<this>(\b(%s)\b))\s*(?P<after>.*)\s*\Z'
   proc = re.match(re.compile(word%('clean'),re.I),userList)
   if proc :
      userList = proc.group('before') + ' ' + proc.group('after')
      typeBuild = 2
   proc = re.match(re.compile(word%('update'),re.I),userList)
   if proc :
      userList = proc.group('before') + ' ' + proc.group('after')
      typeBuild = 1
   proc = re.match(re.compile(word%('modify'),re.I),userList)
   if proc :
      userList = proc.group('before') + ' ' + proc.group('after')
      typeBuild = 3
   # ~~ Remove unwanted ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   word = r'(?P<before>.*?)\s*?-(?P<this>(%s)\b)\s*(?P<after>.*)\s*\Z'
   for mod in modules.keys():
      proc = re.match(re.compile(word%(mod),re.I),userList)
      if proc :
         userList = proc.group('before') + ' ' + proc.group('after')
         del modules[mod]
   # ~~ Check forgotten ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   for mod in userList.split():
      if '-' == mod[0:1]:
         print '\nCould not find the following module:',mod[1:]
         sys.exit(1)
   # ~~ Deal with all ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   if 'system' in userList : userList = ' '.join(modules.keys())

   return userList,typeBuild

"""
   Read the list of user defined ranks used as a filter of the
   validation test case directory names in the form rnn_*,
   where r takes values from 0 to 9 inclusive. Special keywords
   such as all, >, or < will trigger additonal behaviours:
    - all: includes all numbers from 0 to 9
    - <n: includes all numbers below n
    - >n: includes all numbers above n
    - n: includes the number n
"""
def parseValidationRanks(userList):

   # ~~ 'all' in key ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   word = r'(?P<before>.*)\s*(?P<this>(\b(%s)\b))\s*(?P<after>.*)\s*\Z'
   proc = re.match(re.compile(word%('all'),re.I),userList)
   if proc : return range(10)

   ranks = []
   # ~~ '<' and '>' in key ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   word = r'(?P<before>.*?)\s*(?P<symbol>([><]|))(?P<this>\d\b)\s*(?P<after>.*)\s*\Z'
   while 1:
      ul = userList
      proc = re.match(re.compile(word,re.I),userList)
      if proc :
         if proc.group('symbol') == '<' :
            ranks.extend(range(0,int(proc.group('this'))))
         elif proc.group('symbol') == '>' :
            ranks.extend(range(int(proc.group('this'))+1,10))
         else:
            ranks.append(int(proc.group('this')))
         userList = proc.group('before') + proc.group('after')
      if ul == userList: break

   # ~~ sorting out duplicates ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # there must be a better way (with tuples maybe ?)
   for u in range(10):
      while ranks.count(u) > 1: ranks.remove(u)

   return sorted(ranks)

def cleanConfig(cfg,cfgname):

   cfgDir = path.join(path.join(cfg['root'],'builds'),cfgname)
   if path.exists(cfgDir):
      removeDirectories(cfgDir)
      print '\n    +> build deleted!'
   else: print '\n ... Found no build to delete!'


# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban; Noemie Durand"
__date__ ="$19-Jul-2010 08:51:29$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Reads config file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nLoading Options and Configurations\n\
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
   parser = OptionParser("usage: %prog [options] \nuse -h for more help.")
   parser.add_option("-c", "--configname",
                      type="string",
                      dest="configName",
                      default='',
                      help="specify configuration name, default is randomly found in the configuration file" )
   parser.add_option("-f", "--configfile",
                      type="string",
                      dest="configFile",
                      default='',
                      help="specify configuration file, default is systel.cfg" )
   parser.add_option("-r", "--rootdir",
                      type="string",
                      dest="rootDir",
                      default='',
                      help="specify the root, default is taken from config file" )
   parser.add_option("--clean",
                      action="store_true",
                      dest="configDelete",
                      default=False,
                      help="remove the directories in relation to the named configuration(s)" )
   options, args = parser.parse_args()

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Environment ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   # path to the root
   PWD = path.dirname(path.dirname(path.dirname(sys.argv[0])))
   if options.rootDir != '': PWD = options.rootDir
   # user configuration name
   USETELCFG = ''
   if 'USETELCFG' in environ: USETELCFG = environ['USETELCFG']
   if options.configName == '': options.configName = USETELCFG
   # user configuration file
   SYSTELCFG = path.join(PWD,'configs')
   if 'SYSTELCFG' in environ: SYSTELCFG = environ['SYSTELCFG']
   if options.configFile != '': SYSTELCFG = options.configFile
   if path.isdir(SYSTELCFG): SYSTELCFG = path.join(SYSTELCFG,'systel.cfg')
   options.configFile = SYSTELCFG

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ banners ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   mes = MESSAGES()  # runcode takes its version number from the CAS file
   svnrev = ''
   svnurl = ''
   svnban = 'unknown revision'
   try:
      key_equals = re.compile(r'(?P<key>[^:]*)(?P<after>.*)',re.I)
      tail,code = mes.runCmd('svn info '+PWD,True)
      for line in tail.split('\n'):
         proc = re.match(key_equals,line)
         if proc:
            if proc.group('key').strip() == 'Revision': svnrev = proc.group('after')[1:].strip()
            if proc.group('key').strip() == 'URL': svnurl = proc.group('after')[1:].strip()
   except:
      pass
   if svnrev+svnurl == '':
      print '\n'.join(banner('unknown revision'))
   else:
      if svnurl != '': print '\n'.join(banner(svnurl.split('/')[-1]))
      if svnrev != '': print '\n'.join(banner('rev. #'+svnrev))

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Works for all configurations unless specified ~~~~~~~~~~~~~~~
   if not path.isfile(options.configFile):
      print '\nNot able to get to the configuration file: ' + options.configFile + '\n'
      dircfg = path.dirname(options.configFile)
      if path.isdir(dircfg) :
         print ' ... in directory: ' + dircfg + '\n ... use instead: '
         _, _, filenames = walk(dircfg).next()
         for fle in filenames:
            head,tail = path.splitext(fle)
            if tail == '.cfg' :
               print '    +> ',fle
      sys.exit(1)

   cfgs = parseConfigFile(options.configFile,options.configName,False)

   for cfgname in cfgs:
      print '\n\n'+'~'*72+'\n'
      # still in lower case
      if not cfgs[cfgname].has_key('root'): cfgs[cfgname]['root'] = PWD
      if options.rootDir != '': cfgs[cfgname]['root'] = options.rootDir
      # parsing for proper naming
      cfg = parseConfig_CompileTELEMAC(cfgs[cfgname])

      print cfgname + ': \n    '
      if 'brief' in cfgs[cfgname]: print '    +> '+'\n    |  '.join(cfgs[cfgname]['brief'].split('\n'))
      print '    +> root:    ',cfg['root']
      print '    +> module:  ',' / '.join(cfg['MODULES'].keys())
      if options.configDelete: cleanConfig(cfg,cfgname)

   print '\n\n'+'~'*72+'\n'
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Jenkins' success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nMy work is done\n\n'

   sys.exit(0)
