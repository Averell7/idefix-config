import io
import os
import subprocess
import time
import re
import http.client
import json
import ipaddress

from ftp_client import ftp_connect, ftp_get
from util import showwarning, find_idefix
from gi.repository import Gdk, Gtk

# version 2.3.19 - Edit files added


class ExportDiagnosticDialog:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        #self.file_filter = Gtk.FileFilter()
        #self.file_filter.add_pattern('*.json')

    def run(self, data1, configpath = None ):
        if not configpath:
            dialog = Gtk.FileChooserDialog(
                _("Export Config"),
                self.arw['window1'],
                Gtk.FileChooserAction.SAVE,
                (_("Export"), Gtk.ResponseType.ACCEPT),
            )
            #dialog.set_filter(self.file_filter)

            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                configpath =    dialog.get_filename()
            dialog.destroy()

        f1 = open(configpath, "wb")
        f1.write(data1)
        f1.close()

class Information:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller


    def getmac(self, widget):

        message = ""
        if os.name == "nt":
            getmac_txt = subprocess.check_output(["getmac", "-v"]).decode("cp850")
            x = getmac_txt.replace("\r", "").split("\n")

            for line in x:
                x = line.strip()
                if x[0:3] == "===":
                    x = x[0:60]
                x = x.replace(" ", "  ")
                #x = re.sub("(\s)", "§", x)
                message += x + "\n"
        else:
            pass  # TODO : code for Linux and Mac

        # find Idefix and display network settings
        (ip, content) = find_idefix()
        if content:

            message += "\n\nfound Idefix at " + ip
            network = json.loads(content)
            message += _("\n\n     Local port (eth1) IP : ") + network["idefix"]["eth1"]
            message += _("\n     Local port (eth1) Netmask : ") + network["idefix"]["netmask1"]
            message += _("\n     Local port (eth1) active : ") + network["idefix"]["link_eth1"]
            message += _("\n\n     Internet port (eth0) IP : ") + network["idefix"]["eth0"]
            message += _("\n     Internet port (eth0) Netmask : ") + network["idefix"]["netmask0"]
            message += _("\n     Internet port (eth0) active : ") + network["idefix"]["link_eth0"]

            wan = ipaddress.ip_interface(network["idefix"]["eth0"] + "/" + network["idefix"]["netmask0"])
            lan = ipaddress.ip_interface(network["idefix"]["eth1"] + "/" + network["idefix"]["netmask1"])

            if lan.network.overlaps(wan.network):
                message += "\n\nWARNING !!!  WARNING !!!  WARNING !!!  WARNING !!! \n Both subnets overlap !\nIdefix cannot work"

            supervix = "http://" + ip + ":10080/visu-donnees-systeme.php"

            # verify Idefix Internet connection
            command_f = io.BytesIO()
            command_f.write(b'ping')

            # delete data in "result" file
            ftp1 = self.controller.ftp_config
            ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
            self.ftp = ftp
            ftp.storlines('STOR result', command_f)    # the pointer is at the end of the file, so nothing will be written
            command_f.seek(0)
            ftp.storlines('STOR trigger', command_f)
            self.arw["infos_spinner"].start()
            self.spin(True)
            self.arw["infos_spinner"].stop()
            result = ftp_get(ftp, "result")
            result = "\n".join(result)
            message += "\n\nInternet connexion : \n" + result
            ftp.close()
        else:
            message += "\n\nIdefix not found ! "




        dialog = Gtk.Dialog()
        dialog.set_transient_for(self.arw['window1'])
        dialog.add_button(_("Launch Idefix interface"), Gtk.ResponseType.APPLY)
        dialog.add_button(_("Close"), Gtk.ResponseType.CANCEL)
        label = Gtk.Label(message)
        dialog.get_content_area().add(label)
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result == Gtk.ResponseType.APPLY:
            os.startfile(supervix)






    def spin(self, progress = False):
        # insure that the spinner runs for the required time
        time1 = time.time()
        for i in range(30):     # set absolute maximum to 30 seconds
            while time.time() < time1 + i:
                while Gtk.events_pending():
                        Gtk.main_iteration()
            if progress:
                result = ftp_get(self.ftp, "result")
                result = "\n".join(result)
                # escape characters incompatible with pango markup
                result = result.replace("&", "&amp;")
                result = result.replace(">", "&gt;")
                result = result.replace("<", "&lt;")

                self.arw["infos_label"].set_markup(result)
            status =  ftp_get(self.ftp, "trigger")
            if status[0] == "ready":
                break
##        while Gtk.events_pending():
##            Gtk.main_iteration()


        return True


    def idefix_infos(self, widget):
        action = widget.name
        if action == "show_technical_data":
            command = self.arw["infos_technical"].get_active_id().replace("info_", "")
        elif action == "linux_command":
            command = "linux " + self.arw["linux_command_entry"].get_text()
        else:
            command = action.replace("infos_", "")

        if command in["unbound", "squid"]:
            command += " " + self.controller.myip

        command_f = io.BytesIO()
        command_f.write(bytes(command, "utf-8"))
        command_f.seek(0)
        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        self.ftp = ftp
        ftp.storlines('STOR trigger', command_f)
        self.arw["infos_spinner"].start()

        if command in ("ping"):
            self.spin(True)
        elif command in ("all"):
            self.spin()
        elif command in ("versions"):
                self.spin(True)
        elif command.startswith("linux"):
            self.spin()
        else:
            self.spin()
        self.arw["infos_spinner"].stop()
        result = ftp_get(ftp, "result")
        result = "\n".join(result)
        if command == "all":
            dialog = ExportDiagnosticDialog(self.arw, self)
            dialog.run(result.encode("utf8"))
        else:
            # escape characters incompatible with pango markup
            result = result.replace("&", "&amp;")
            result = result.replace(">", "&gt;")
            result = result.replace("<", "&lt;")

            # set colors
            if command.startswith("unbound"):
                result2 = result.split("\n")
                result3 = ""
                for line in result2:
                    if "no match" in line :
                        line = '<span foreground="blue">' + line.strip() + "</span>"
                    elif "denied" in line :
                        line = '<span foreground="red">' + line.strip() + "</span>"
                    elif "allowed" in line :
                        line = '<span foreground="green">' + line.strip() + "</span>"
                    if "validation failure" in line :
                        line = '<span background="#ff9999">' + line.strip().replace("<", "&lt;").replace(">", "&gt;") + "</span>\n"
                    result3 += line + "\n"
                result = result3
            elif command == "mac":
                result2 = result.split("\n")
                result3 = ""
                for line in result2:
                    if "expired" in line :
                        line = '<span foreground="red">' + line.strip() + "</span>"
                    elif "active" in line :
                        line = '<span foreground="green">' + line.strip() + "</span>"
                    result3 += line +"\n"
                result = result3

            self.arw["infos_label"].set_markup(result)

        ftp.close()


    def edit_file(self, widget):

        filename = widget.name.replace("file_", "")
        if filename == "eth0":
            full_path = "/etc/network/interfaces.d/eth0"
        elif filename == "eth1":
            full_path = "/etc/network/interfaces.d/eth1"
        elif filename == "idefix.conf":
            full_path = "/etc/idefix/idefix.conf"
        elif filename == "idefix2_conf":
            full_path = "/etc/idefix/idefix2_conf.json"
        elif filename == "ddclient.conf":
            full_path = "/etc/ddclient.conf"

        self.edited_file = full_path

        command_f = io.BytesIO()
        command_f.write(b"linux cat " + bytes(full_path, "utf-8"))

        # delete data in "result" file
        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        ftp.storlines('STOR result', command_f)    # the pointer is at the end of the file, so nothing will be written
        command_f.seek(0)
        ftp.storlines('STOR trigger', command_f)
        self.arw["infos_spinner"].start()
        self.spin(True)
        self.arw["infos_spinner"].stop()

        data1 = ftp_get(ftp, "result")

        self.arw["editor_textview"].get_buffer().set_text("\n".join(data1))

        ftp.close()

    def save_file(self, widget):
        text_buffer = self.arw["editor_textview"].get_buffer()
        (start_iter, end_iter) = text_buffer.get_bounds()
        full_text = text_buffer.get_text(start_iter, end_iter, False)
        command_f = io.BytesIO()
        command_f.write(bytes(full_text, "utf-8")) #.replace(b'\r\n', b'\n'))
        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        command_f.seek(0)
        ftp.storbinary('STOR buffer', command_f)
        command_f = io.BytesIO()
        command_f.write(bytes("linux cp /home/rock64/idefix/buffer " + self.edited_file, "utf-8"))
        command_f.seek(0)
        ftp.storbinary('STOR trigger', command_f)



    def update_display(self, widget):
        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        data1 = ftp_get(ftp, "result")
        self.arw["infos_label"].set_markup("\n".join(data1))
        ftp.close()

    def open_editor(self, widget):
        self.arw["informations_stack"].set_visible_child(self.arw["editor_box"])

    def close_editor(self, widget):
        self.arw["informations_stack"].set_visible_child(self.arw["informations_box"])

    def load_eth0(self, widget):
        self.idefix_edit("", commandline = "cat /etc/idefix/idefix2_conf.json")

    def search(self, widget):
        mac_search = self.arw["search_mac"].get_text().strip().lower()

        output1 = ""
        if mac_search != "":
            for user in self.controller.maclist:
                for mac in self.controller.maclist[user]:
                    if mac_search in mac:
                        output1 += user + " : " + mac + "\n"

        domain_search = self.arw["search_domain"].get_text().strip().lower()

        output = ""
        if domain_search != "":
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

        self.arw["infos_label"].set_text(output1 + "\n\n" + output)

