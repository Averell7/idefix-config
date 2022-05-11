#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Dysmas
#
# Created:     19/01/2022
# Copyright:   (c) Dysmas 2022
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import json
from collections import OrderedDict

def main():
    with open("idefix3.json", "r") as f1:
        config3 = json.load(f1, object_pairs_hook=OrderedDict)
    config4 = OrderedDict()
    f4 = open("idefix4.json", "w")

    for list1 in config3:
        if list1 == "users":
            id = 1
            config4[list1] = OrderedDict()

            for section in config3[list1]:
                for user in config3[list1][section]:
                    try:
                        config4[list1][id] = OrderedDict()
                        config4[list1][id]["name"] = user
                        config4[list1][id].update(config3[list1][section][user])
                        #config4[list1][id]["subusers"] = config3[list1][section][user]["subusers"]
                        id +=1
                    except:
                        print("Error for : ", section, user)
        elif list1 in ["rules", "groups"]:
            id = 1
            config4[list1] = OrderedDict()
            for user in config3[list1]:
##                    try:
                        config4[list1][id] = OrderedDict()
                        config4[list1][id]["name"] = user
                        config4[list1][id].update(config3[list1][user])
                        if "active" in config4[list1][id]:
                            del config4[list1][id]["active"]
                        if "strict_end" in config4[list1][id] and  config4[list1][id]["strict_end"]:
                            config4[list1][id]["strict_end"] = 1
                        else:
                            config4[list1][id]["strict_end"] = 0
                        id +=1

    json.dump(config4, f4, indent = 3)

if __name__ == '__main__':
    main()
