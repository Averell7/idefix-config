import io
import subprocess
import time

from ftp_client import ftp_connect, ftp_get
from util import showwarning


class Information:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

    def getmac(self, widget):
        getmac_txt = subprocess.check_output(["getmac", "-v"]).decode("cp850")
        x = getmac_txt.replace("\r", "").split("\n")
        message = ""
        for line in x:
            x = line.strip()
            if x[0:3] == "===":
                x = "----------------------------------------------"
            # words = line.split()
            # message += chr(9).join(words[0:7]) + "\n"
            message += x + "\n"
        showwarning(_("Mac addresses"), message)

    def idefix_infos(self, widget):
        action = widget.name
        if action == "show_technical_data":
            command = self.arw["infos_technical"].get_active_id().replace("info_", "")
        else:
            command = action.replace("infos_", "")
        command_f = io.BytesIO()
        command_f.write(bytes(command, "utf-8"))
        command_f.seek(0)
        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        ftp.storlines('STOR trigger', command_f)
        time.sleep(2)
        data1 = ftp_get(ftp, "result")
        if command in ("unbound", "versions"):
            self.arw["infos_label"].set_markup("\n".join(data1))
        else:
            self.arw["infos_label"].set_text("\n".join(data1))
        ftp.close()

    def search(self, widget):
        mac_search = self.arw["search_mac"].get_text().strip().lower()

        if mac_search:
            output = ""
            for user in self.controller.maclist:
                for mac in self.controller.maclist[user]:
                    if mac_search in mac:
                        output += user + " : " + mac + "\n"

        domain_search = self.arw["search_domain"].get_text().strip().lower()

        output = ""
        if domain_search:
            for group in self.controller.config['groups']:
                if domain_search in group:
                    output += _("group : %s \n") % (group)
                for domain in self.controller.config['groups'][group]['dest_domains']:
                    if domain_search in domain:
                        output += _("group : %s --> %s \n") % (group, domain)
            for rule in self.controller.config['rules']:
                if domain_search in rule:
                    output += _("rule : %s \n") % (rule)
                for domain in self.controller.config['rules'][rule]['dest_domains']:
                    if domain_search in domain:
                        output += _("rule : %s --> %s \n") % (rule, domain)

        self.arw["infos_label"].set_text(output)
