#!/usr/bin/python3
# -*- coding: utf8 -*-

from __future__ import print_function
from __future__ import unicode_literals

# version 1.1.0 : @optional parameter added in read
# rc3 
# version 0.17.0 - mytextParser added
# version 0.16.2 - bug fix
# version 0.16.1 - isdata parameter added

import os, sys, codecs
from collections import OrderedDict


class myConfigParser():
    def __init__(self):
        pass

    def read(self,
            iniFile_s,
            category,
            comments = False,
            merge = False,
            encoding = "utf-8-sig",       # utf-8-sig will handle the BOM
            isdata = False,
            optional = False):
        # ----
        # read ini file and creates a dictionary
        # lines which are not comments (start with #) and don't match the key = value pattern, are stored in a special "lines" entry
        # @iniFile_s : ini file path
        # @category : a string which will be used as first level key of the dictionary.
        #             When merging several configurations, it prevents the mixing of the different sources
        # @comments : if True, comments are included in a "#comments" section. Otherwise they are skipped
        # @merge : if True, instead of building a new dictionary, the function adds data to the dictionary passed in parameter
        # @encoding : should be obvious
        # @isdata : if True, @inifile_s contains the full text of the inifile to treat, and not a filename. 
        # @optional : if True, no error message if the file is not found. 
        # @return : The config dictionary, if successful, False otherwise
        #           But if merge is not False and the function fails, it returns the dictionary which passed in merge.

        if isdata == False:
            if not os.path.isfile(iniFile_s):
                print("fichier non trouvé " + iniFile_s)
                if merge != False:
                    return merge
                else:
                    return False
        else:
            if iniFile_s == None:
                print("no data !")
                if merge != False:
                    return merge
                else:
                    return False


        if merge == False:                         # nouveau fichier de configuration
            myconfig = OrderedDict()
        else:
            myconfig = merge                   # on ajoute la configuration à un fichier existant

        myconfig[category] = OrderedDict()

        if isdata == True:
            data1 = iniFile_s
        else:
            fileIni = open(iniFile_s, "r", encoding = "utf-8-sig")
            data1 = fileIni.readlines()
            fileIni.close()

        section_s = ""

        for record_s in data1:


            # format line : strip and replace possible \ by /
            record_s = record_s.strip()
            try:
                record_s = record_s.replace("\\", "/")      # TODO : or better : formatPath()
            except:
                print(record_s + "not supported")
            # If the  line is a section
            if record_s[0:1] == "[" and record_s[-1:] == "]":      # section
                section_s = record_s[1:-1]
                myconfig[category][section_s] = OrderedDict()
            else:
                # Skip useless lines
                if section_s == "":            # comment in the beginning of the file
                    continue
                if len(record_s) == 0:         # empty line
                    continue
                if record_s[0:1] == "#":       # comment
                    comment_b = True
                else:
                    comment_b = False
                if comments == False:          # Skip comments
                    if comment_b == True:
                        continue


                # otherwise, store data in section
                if comment_b == True:
                    if  not "#comments" in myconfig[category][section_s]:
                        myconfig[category][section_s]["#comments"] = []
                    myconfig[category][section_s]["#comments"].append(record_s)
                    continue
                record_data = record_s.split("=",1)
                if len(record_data) > 1:
                    key = record_data[0].strip()
                    if ' #' in record_data[1]:
                        # Contains a comment
                        data, comment = record_data[1].split(' #')
                        linedata = data.strip()
                    else:
                        linedata = record_data[1].strip()
                    if linedata == "False":
                        linedata = False
                    if linedata == "True":
                        linedata = True
                    if not key in myconfig[category][section_s]:
                        myconfig[category][section_s][key] = [linedata]
                    else:
                        myconfig[category][section_s][key].append(linedata)
                else:
                    if  not "lines" in myconfig[category][section_s]:
                        myconfig[category][section_s]["lines"] = ""
                    myconfig[category][section_s]["lines"] += record_data[0] + "\n"

        return myconfig

    def write(self, myconfig, filename):       # inutilisé dans ce programme
        if sys.version_info[0] == 3:
            iniFile = open(filename, "w", encoding = "utf8")
        else:
            iniFile = open(filename, "w")
        for a in myconfig:
            iniFile.write("[" + a + "]\n")
            for b in myconfig[a]:
                values = myconfig[a][b]
                if not isinstance(values, list):
                    values = [values]
                for value in values:
                    if value == True:
                        value = '1'
                    elif value == False:
                        value = '0'
                    data1 = (b + " = " + value + "\n").encode("utf8")  # En python 3 cette ligne convertit en bytes !!!
                    data1 = (b + " = " + value + "\n")
                    iniFile.write(data1)
            iniFile.write("\n")
        iniFile.close()
        return True


class mySimpleParser():
    def __init__(self):
        pass
    def read(self,
            iniFile_s):

        # read ini file and creates a dictionary
        # @param iniFile_s : ini file path

        if not os.path.isfile(iniFile_s):
            print("fichier non trouvé " + iniFile_s)
            return False

        config = {}

        with open(iniFile_s) as f1:
            while True:
                record_s = f1.readline()
                if record_s == "":   # end of file
                    break
                record_data = record_s.split("=",1)
                if len(record_data) > 1:
                    key = record_data[0].strip()
                    linedata = record_data[1].strip()
                    if linedata == "False":
                        linedata = False
                    if linedata == "True":
                        linedata = True
                    config[key] = linedata

        return config
        
class myTextParser():
    def __init__(self):
        pass
    def read(self,
            iniFile_s):

        # read txt file and creates a dictionary
        # @param iniFile_s : ini file path

        if not os.path.isfile(iniFile_s):
            print("fichier non trouvé " + iniFile_s)
            return False

        
        fileIni = open(iniFile_s, "r", encoding = "utf-8-sig")
        data1 = fileIni.readlines()

        mytext = {}
        section_s = ""

        for record_s in data1:
          
            record_s = record_s.strip()
            
            # If the  line is a section
            if record_s.startswith("[") and record_s.endswith("]"):      # section
                section_s = record_s[1:-1]
                mytext[section_s] = ""
            else:
                # Skip useless lines
                if section_s == "":            # comment in the beginning of the file
                    continue                
                if record_s[0:1] == "#":       # comment
                    continue
                else:
                    mytext[section_s] += record_s +"\n"
                   
        return mytext
        
        
def main():
    pass

if __name__ == '__main__':
    main()
