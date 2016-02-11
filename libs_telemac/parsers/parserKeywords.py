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
"""@history 28/04/2011 -- Sebastien E. Bourban
         Now supports SYSTELCFG as a directory (old Perl version, to which
         systel.cfg is added) or as a file.
"""
"""@history 30/04/2011 -- Sebastien E. Bourban
         Upgrade made to config parsing to include the option to reset
         the version and the root from the command line option:
         -v <version>, reset the version read in the config file with this
         -r <root>, reset the root path read in the config file with this
"""
"""@history 21/05/2012 -- Sebastien E. Bourban
         Addition of the method setKeyValue, in order to force keyword values,
         for instance, in the case of running scalar case with parallel
         Also, scanDICO now understands the type of each keyword.
"""
"""@history 10/07/2012 -- Christophe Coulet
         Addition of a specific test and management of long lines because some
         variables, such as the path could be greater than 72 characters.
         Update (FD,30/08/212) : '<73' changed to '<72' (bug in 015_bosse_mixte)
"""
"""@history 04/12/2012 -- Juliette Parisi and Sebastien E. Bourban
   Simplifying call to parseConfigFile, which now takes two arguments
      options.configFile, and options.configName and return one or more
      valid configurations in an array. Testing for validity is now done
      within config.py
"""
"""@history 17/06/2013 -- Sebastien E. Bourban
   keywords are now placed into a list (as opposed to dictionary) so to
      remember the order of entrance in the CAS file.
"""
"""@history 17/06/2013 -- Sebastien E. Bourban
   values of keywords are now checked for their type against the declared type
      in the DICO.
"""
"""@history 23/09/2014 -- Sebastien E. Bourban and Yoann Audoin
   The content of the log files from GRETEL and PARTEL are now reported
   in the error report.
"""
"""@brief
"""

# _____          ___________________________________________________
# ____/ Imports /__________________________________________________/
#
# ~~> dependencies towards standard python
import re
from os import path,walk,environ
import sys
# ~~> dependencies towards the root of pytel
from config import OptionParser,parseConfigFile, parseConfig_ValidateTELEMAC
# ~~> dependencies towards other pytel/modules
from utils.files import getFileContent,putFileContent

# _____               ______________________________________________
# ____/ Instructions /_____________________________________________/
#

debug = False

# _____                 ____________________________________________
# ____/ Keyword parse  /___________________________________________/
#

key_comment = re.compile(r"(?P<before>([^'/]*'[^']*'[^'/]*|[^/]*)*){1}(?P<after>.*)",re.I)
continued = re.compile(r"(?P<before>[^']*)(?P<after>'[^']*)\s*\Z",re.I)
emptyline = re.compile(r'\s*\Z',re.I)

entryquote = re.compile(r'(?P<before>[^\'"]*)(?P<after>.*)\s*\Z',re.I)
exitsquote = re.compile(r"'(?P<before>(.*?[^']+|))'(?P<after>[^']+.*)\s*\Z",re.I)
exitdquote = re.compile(r'"(?P<before>(.*?[^"]+|))"(?P<after>[^"]+.*)\s*\Z',re.I)

key_none = re.compile(r'\s*(?P<key>&\w*)\s+(?P<after>.*)',re.I)
key_equals = re.compile(r'(?P<key>[^=:]*)(?P<after>.*)',re.I)
val_equals = re.compile(r"[=:;]\s*(?P<val>('.*?'|[^\s;']*))\s*(?P<after>.*)",re.I)

key_word = r'\s*(?P<this>(%s))\s*(?P<after>.*)\s*\Z'
val_word = r"\s*[=:;]\s*(?P<this>('.*?'|%s))\s*(?P<after>.*)\s*\Z"

dicokeys = ['AIDE','AIDE1','APPARENCE','CHOIX','CHOIX1','COMPORT','COMPOSE',
    'CONTROLE','DEFAUT','DEFAUT1','INDEX','MNEMO','NIVEAU','NOM','NOM1', \
    'RUBRIQUE','RUBRIQUE1','TAILLE','TYPE','SUBMIT']
# _____             ________________________________________________
# ____/ CAS FILES  /_______________________________________________/
#
def scanCAS(lines):
   keylist = []; vallist = []
   # ~~ clean ending empty lines
   lines = (''.join(lines).rstrip('\n ')).split('\n')
   # ~~ clean lines' endings
   core = []
   for line in lines:
      proc = re.match(key_none,line)
      if proc: line = line.lstrip()
      core.append(line.rstrip(' '))
   lines = core
 
   # ~~ clean comments
   core = []
   for i in range(len(lines)):
      line = lines[i].replace('"""',"'''").replace('"',"'").replace("''",'"')
      proc = re.match(key_comment,line+'/')
      line = proc.group('before').strip() + ' '
      proc = re.match(emptyline,line)
      if not proc: core.append(line)
   # TODO: See what thar replace was for
   casStream = (' '.join(core))#.replace('  ',' ')
   # ~~ clean values to keep only the keys
   while casStream != '':
      # ~~ non-key
      proc = re.match(key_none,casStream)
      if proc:
         casStream = proc.group('after')
         keylist.append(proc.group('key').strip())
         vallist.append([''])
         continue
      # ~~ key
      proc = re.match(key_equals,casStream)
      if not proc:
         raise Exception([{'name':'scanCAS','msg':'... hmmm, did not see this one coming ...\n   around there :'+casStream[:100]}])
      kw = proc.group('key').strip()
      casStream = proc.group('after')   # still hold the separator
      # ~~ val
      proc = re.match(val_equals,casStream)
      if not proc: raise Exception([{'name':'scanCAS','msg':'no value to keyword '+kw}])
      val = []
      while proc:
         if proc.group('val') == '"': val.append('')
         else: val.append(proc.group('val').replace("'",''))
         casStream = proc.group('after')   # still hold the separator
         proc = re.match(val_equals,casStream)
      if kw in keylist:
         vallist[keylist.index(kw)] = val
      else:
         keylist.append(kw)
         vallist.append(val)

   return lines,(keylist,vallist)

def readCAS(cas,dico,frgb):

   vint = re.compile(r'\d+\Z')
   vflt = re.compile(r'(-)?\d*(|\.)\d*([dDeE](\+|\-)?\d+|)\Z')
   lines,keywords = cas
   keylist,vallist = keywords
   for key,value in zip(*keywords):
      kw = key
      if kw[0] == '&': continue
      if kw not in dico:
         if kw not in frgb['GB']:
            raise Exception([{'name':'readCAS','msg':'... could not find the following keyword in the selected dictionary file: '+key+'\n     ~> you may not be running the code associated to your CAS file.'}])
         kw = frgb['GB'][kw]
      if dico[kw]['TYPE'][0] == 'LOGIQUE':
         vals = []
         for val in value:
            if val.upper() in ['YES','Y','TRUE','OUI','O','VRAI']: vals.append('TRUE')
            elif val.upper() in ['NO','N','FALSE','NON','N','FAUX']: vals.append('FALSE')
            else: raise Exception([{'name':'readCAS','msg':'... I am looking for a LOGICAL but found an inapropriate value set for keyword: '+key}])
         vallist[keylist.index(key)] = vals
      elif dico[kw]['TYPE'][0] in ['ENTIER','INTEGER']:
         vals = []
         for val in value:
            if re.match(vint,val): vals.append(int(val))
            else: raise Exception([{'name':'readCAS','msg':'... I am looking for an INTEGER but found an inapropriate value set for keyword: '+key}])
         vallist[keylist.index(key)] = vals
      elif dico[kw]['TYPE'][0] in ['REEL','REAL']:
         vals = []
         for val in value:
            if re.match(vflt,val.lower().replace('d','e')): vals.append(val)
            else: raise Exception([{'name':'readCAS','msg':'... I am looking for an FLOAT but found an inapropriate value set for keyword: '+key}])
         vallist[keylist.index(key)] = vals
      else:
         vals = []
         for val in value: vals.append(repr(val.replace('"',"''")).replace('"',"'"))
         vallist[keylist.index(key)] = vals

   return lines,(keylist,vallist)

def rewriteCAS(cas):

   lines = []
   for key,val in zip(*cas[1]):
      if val == []: raise Exception([{'name':'rewriteCAS','msg':'... inapropriate value set for keyword: '+key}])

      # ~~~> Special keys starting with '&'
      if key[0] == '&':
         line = ''; lcur = key
      # ~~~> Check if final size more than 72 characters
      elif len(' ' + key + ' : ' + str(val[0])) < 73:
         line = ''; lcur = ' ' + key + ' : ' + str(val[0])
      else:
         line = ' ' + key + ' :\n'
         if len('   ' + str(val[0])) < 73: lcur = '   ' + str(val[0])
         else: lcur = '\n' + format72(str(val[0]))
      for v in val[1:]:
         if len(lcur + ';'+str(v)) < 72:
            lcur = lcur + ';'+str(v)
         else:
            if len(lcur) < 72:
               line = line + lcur + ';\n'
               lcur = '   '+str(v)
            else:  print '... warning: CAS file cannot read this value: ',lcur
      lines.append(line+lcur)

   lines.append('')
   return lines

def translateCAS(cas,frgb):
   casLines = getFileContent(cas)

   core = []
   for i in range(len(casLines)):
      # ~~> scan through to remove all comments
      casLines[i] = casLines[i].replace('"""',"'''").replace('"',"'")
      proc = re.match(key_comment,casLines[i]+'/')
      head = proc.group('before').strip()
      core.append(head)
   casStream = ' '.join(core)

   frLines = []; gbLines = []
   for i in range(len(casLines)):

      # ~~> split comments
      casLines[i] = casLines[i].replace('"""',"'''").replace('"',"'")
      proc = re.match(key_comment,casLines[i]+'/')
      head = proc.group('before').strip()
      tail = proc.group('after').rstrip('/').strip()  # /!\ is not translated
      # ~~ special keys starting with '&'
      p = re.match(key_none,head+' ')
      if p:
         head = ''
         tail = casLines[i].strip()
      frline = head
      gbline = head

      if head != '' and casStream == '':
         raise Exception([{'name':'translateCAS','msg':'could not translate this cas file after the line:\n'+head}])
      # ~~> this is a must for multiple keywords on one line
      while casStream != '':
         proc = re.match(key_equals,casStream)
         if not proc:
            raise Exception([{'name':'scanCAS','msg':'... hmmm, did not see this one coming ...\n   around there :'+casStream[:100]}])
         kw = proc.group('key').strip()
         if kw not in head: break  # move on to next line

         # ~~> translate the keyword
         head = head.replace(kw,'',1)
         if kw.upper() in frgb['GB']: frline = frline.replace(kw,frgb['GB'][kw],1)
         if kw.upper() in frgb['FR']: gbline = gbline.replace(kw,frgb['FR'][kw],1)

         # ~~> look for less obvious keywords
         casStream = proc.group('after')   # still hold the separator
         proc = re.match(val_equals,casStream)
         if not proc:
            raise Exception([{'name':'translateCAS','msg':'no value to keyword: '+kw}])
         while proc:
            casStream = proc.group('after')   # still hold the separator
            proc = re.match(val_equals,casStream)

      # final append
      if frline != '': frline = ' ' + frline
      frLines.append(frline + tail)
      if gbline != '': gbline = ' ' + gbline
      gbLines.append(gbline + tail)

   # ~~ print FR and GB versions of the CAS file
   putFileContent(cas+'.fr',frLines)
   putFileContent(cas+'.gb',gbLines)

   return cas+'.fr',cas+'.gb'

# _____              _______________________________________________
# ____/ DICO FILES  /______________________________________________/
#
"""
   keywords.keys() are in French. dico provides you with the translation
"""
def scanDICO(dicoFile):
   keylist = []
   dicoLines = getFileContent(dicoFile)
   # ~~ buddle continuations (long strings) and remove comments and empty lines
   core = []; i = -1
   while i < len(dicoLines) - 1:
      i = i + 1; line = ''
      l = dicoLines[i].strip()
      #proc = re.match(key_comment,l)
      #if proc: l = proc.group('before').strip() + ' '
      if l.strip()[0:1] == '/' : continue
      proc = re.match(emptyline,l)
      if proc: continue
      proc = re.match(key_none,l)
      if proc: continue
      proc = re.match(entryquote,l)
      line = proc.group('before')
      l = proc.group('after')
      while l != '':
         if l[0:1] == '"':
            proc = re.match(exitdquote,l+' ')
            if proc:
               line = line + "'" + proc.group('before').replace("'",'"') + "'"
               proc = re.match(entryquote,proc.group('after').strip())
               line = line + proc.group('before')
               l = proc.group('after').strip()
               print '>',l
            else:
               i = i + 1
               l = l.strip() + ' ' + dicoLines[i].strip()
         elif l[0:1] == "'":
            proc = re.match(exitsquote,l+' ')
            if proc:
               line = line + "'" + proc.group('before').replace("'",'"') + "'"
               proc = re.match(entryquote,proc.group('after').strip())
               line = line + proc.group('before')
               l = proc.group('after').strip()
            else:
               i = i + 1
               l = l.strip() + ' ' + dicoLines[i].strip()
      core.append(line)
   dicoStream = (' '.join(core)).replace('  ',' ').replace('""','"')
   # ~~ clean values to keep only the keys
   while dicoStream != '':
      # ~~ non-key
      proc = re.match(key_none,dicoStream)
      if proc:
         dicoStream = proc.group('after')
         continue
      # ~~ key
      proc = re.match(key_equals,dicoStream)
      if not proc: break
      kw = proc.group('key').strip()
      if kw not in dicokeys:
         print 'unknown key ',kw,proc.group('after'),dicoStream
         sys.exit(1)
      dicoStream = proc.group('after')   # still hold the separator
      # ~~ val
      proc = re.match(val_equals,dicoStream)
      if not proc:
         print 'no value to keyword ',kw
         sys.exit(1)
      val = []
      while proc:
         if proc.group('val')[0] == "'":
            val.append(proc.group('val')[1:len(proc.group('val'))-1])
         else:
            val.append(proc.group('val'))
         dicoStream = proc.group('after')   # still hold the separator
         proc = re.match(val_equals,dicoStream)
      keylist.append([kw,val])
   # ~~ sort out the groups, starting with 'NOM'
   dico = {'FR':{},'GB':{},'DICO':dicoFile}; keywords = {}
   while keylist != []:
      if keylist[0][0] != 'NOM' and keylist[1][0] != 'NOM1':
         print 'could not read NOM or NOM1 from ',keylist[0][1]
         sys.exit(1)
      dico['FR'].update({keylist[0][1][0].replace('"',"'"):keylist[1][1][0].replace('"',"'")})
      dico['GB'].update({keylist[1][1][0].replace('"',"'"):keylist[0][1][0].replace('"',"'")})
      key = keylist[0][1][0].replace('"',"'")
      words = {}
      words = {'NOM':keylist[0][1]}
      keylist.pop(0)
      while keylist != []:
         if keylist[0][0] == 'NOM': break
         words.update({keylist[0][0]:keylist[0][1]})
         keylist.pop(0)
      keywords.update({key:words})

   return dico,keywords

"""
   getIOFilesSubmit returns both French and English keys + SUBMIT actions

"""
def getIOFilesSubmit(frgb,dico):
   iFiles = {}; oFiles = {}
   for key in dico:
      if 'SUBMIT' in dico[key]:
         if 'LIT' in dico[key]['SUBMIT'][0]:
            iFiles.update({key:dico[key]['SUBMIT'][0]})
            iFiles.update({frgb['FR'][key]:dico[key]['SUBMIT'][0]})
            # File can be both read and write
            if 'ECR' in dico[key]['SUBMIT'][0]:
               oFiles.update({key:dico[key]['SUBMIT'][0]})
               oFiles.update({frgb['FR'][key]:dico[key]['SUBMIT'][0]})
         elif 'ECR' in dico[key]['SUBMIT'][0]:
            oFiles.update({key:dico[key]['SUBMIT'][0]})
            oFiles.update({frgb['FR'][key]:dico[key]['SUBMIT'][0]})
         else:
            if 'void' not in dico[key]['SUBMIT'][0]:
               print '... hmm, this is embarrassing. I do not know what to do with ', key
               sys.exit(1)

   return iFiles,oFiles

def getKeyWord(key,cas,dico,frgb):

   value = []; defaut = []
   kl,vl = cas[1]
   if key in frgb['GB']:
      defaut = dico[frgb['GB'][key]]['DEFAUT1']
      if key in kl: value = vl[kl.index(key)]
      elif frgb['GB'][key] in kl: value = vl[kl.index(frgb['GB'][key])]
   if key in frgb['FR']:
      defaut = dico[key]['DEFAUT']
      if key in kl: value = vl[kl.index(key)]
      elif frgb['FR'][key] in kl: value = vl[kl.index(frgb['FR'][key])]

   return value,defaut

def getSubmitWord(key,cas,iFS,oFS):

   value = []; kl,vl = cas[1]
   for i in iFS:
      if key == iFS[i].split(';')[1]:
         if i in kl: value = vl[kl.index(i)]
   for i in oFS:
      if key == oFS[i].split(';')[1]:
         if i in kl: value = vl[kl.index(i)]

   return value

def getCASLang(cas,frgb):
   # ~~> add DICTIONARY and STEERING FILE to the CAS file
   lang = 1
   kl = cas[1][0]
   # Look to find the first key that is different in both language
   i = 0
   while kl[i][0] == '&' or \
      ( kl[i] in frgb['FR'] and kl[i] in frgb['GB'] ):
      i+=1
   if kl[i] not in frgb['FR']: lang = 2

   return lang

def setKeyValue(key,cas,frgb,value):
#~ detail:
#~+   maintains both the list of key / value and the lines
#~+      from the original file.
#~+   add new key at the end of lines just in case the key exists already
#~+      but in anycase, before $FIN
#~assumption:
#~+   single value is assumed at this stage
#
   lines,keys = cas
   lang = getCASLang(cas,frgb)
   if key in frgb['GB'] and lang == 1: key =  frgb['GB'][key]
   if key in frgb['FR'] and lang == 2: key =  frgb['FR'][key]
   kl,vl = keys
   # ~~> Identify where is &FIN for possible insertion of new key before it
   try:
      for line,j in zip(lines,range(len(lines))):
         if '&FIN' in line.strip(): jndex = j
      kndex = kl.index('&FIN')
   except:
      jndex = len(lines)
      kndex = len(kl)
   # English keys
   if key in frgb['GB']:
      if key in kl:
         vl[kl.index(key)] = [value]
         lines.insert(jndex,format72(key+' : '+str(value)))
      elif frgb['GB'][key] in kl:
         vl[kl.index(frgb['GB'][key])] = [value]
         lines.insert(jndex,format72(frgb['GB'][key]+' : '+str(value)))
      else:
         kl.insert(kndex,key)
         vl.insert(kndex,[value])
         lines.insert(jndex,format72(key+' : '+str(value)))
   # French keys
   if key in frgb['FR']:
      if key in kl:
         vl[kl.index(key)] = [value]
         lines.insert(jndex,format72(key+' : '+str(value)))
      elif frgb['FR'][key] in kl:
         vl[kl.index(frgb['FR'][key])] = [value]
         lines.insert(jndex,format72(frgb['FR'][key]+' : '+str(value)))
      else:
         kl.insert(kndex,key)
         vl.insert(kndex,[value])
         lines.insert(jndex,format72(key+' : '+str(value)))

   return lines,(kl,vl)
# _____             ________________________________________________
# ____/ SPECIFICS  /_______________________________________________/
#
def format72(value):

   val72 = ''
   for i in range(len(value)/72+1):
      val72 = val72 + ( value+72*' ' )[72*i:72*i+72] + '\n'

   return val72.rstrip()

# _____             ________________________________________________
# ____/ MAIN CALL  /_______________________________________________/
#

__author__="Sebastien E. Bourban; Noemie Durand"
__date__ ="$19-Jul-2010 08:51:29$"

if __name__ == "__main__":

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Reads config file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   print '\n\nLoading Options and Configurations\n'+'~'*72+'\n'
   USETELCFG = ''
   PWD = path.dirname(path.dirname(path.dirname(path.dirname(sys.argv[0]))))
   if 'USETELCFG' in environ: USETELCFG = environ['USETELCFG']
   SYSTELCFG = 'systel.cfg'
   if 'SYSTELCFG' in environ: SYSTELCFG = environ['SYSTELCFG']
   if path.isdir(SYSTELCFG): SYSTELCFG = path.join(SYSTELCFG,'systel.cfg')
   parser = OptionParser("usage: %prog [options] \nuse -h for more help.")
   parser.add_option("-c", "--configname",
                      type="string",
                      dest="configName",
                      default=USETELCFG,
                      help="specify configuration name, default is the first found in the configuration file" )
   parser.add_option("-f", "--configfile",
                      type="string",
                      dest="configFile",
                      default=SYSTELCFG,
                      help="specify configuration file, default is systel.cfg" )
   parser.add_option("-r", "--rootdir",
                      type="string",
                      dest="rootDir",
                      default='',
                      help="specify the root, default is taken from config file" )
   parser.add_option("-k","--rank",type="string",dest="rank",default='all',
      help="the suite of validation ranks (all by defult)" )
   options, args = parser.parse_args()
   if not path.isfile(options.configFile):
      print '\nNot able to get to the configuration file: ' + options.configFile + '\n'
      dircfg = path.dirname(options.configFile)
      if path.isdir(dircfg) :
         print ' ... in directory: ' + dircfg + '\n ... use instead: '
         _, _, filenames = walk(dircfg).next()
         for fle in filenames :
            head,tail = path.splitext(fle)
            if tail == '.cfg' : print '    +> ',fle
      sys.exit(1)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Works for all configurations unless specified ~~~~~~~~~~~~~~~
   cfgs = parseConfigFile(options.configFile,options.configName)

   #  /!\  for testing purposes ... no real use
   for cfgname in cfgs:
      # still in lower case
      if not cfgs[cfgname].has_key('root'): cfgs[cfgname]['root'] = PWD
      if options.rootDir != '': cfgs[cfgname]['root'] = options.rootDir
      # parsing for proper naming
      if options.rank != '': cfgs[cfgname]['val_rank'] = options.rank
      cfg = parseConfig_ValidateTELEMAC(cfgs[cfgname])

      debug = True

      for mod in cfg['VALIDATION']:
# ~~ Scans all CAS files to launch validation ~~~~~~~~~~~~~~~~~~~~~~
         print '\n\nConfiguration ' + cfgname + ', Module '+ mod + '\n'+'~'*72+'\n'
         print '... reading module dictionary'
         frgb,dico = scanDICO(path.join(path.join(cfg['MODULES'][mod]['path'],'lib'),mod+'.dico'))
         for casFile in cfg['VALIDATION'][mod]:
            print '... CAS file: ',casFile
            casKeys = readCAS(scanCAS(getFileContent(casFile)),dico,frgb)
               #/!\ for testing purposes ... no real use.
               #/!\ Note that casKeys is made of lines,(keys,values)

   sys.exit(0)

