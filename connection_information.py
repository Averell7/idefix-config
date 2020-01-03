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

        # clear data
        for widget in ["network_summary_label1", "network_summary_label2", "network_summary_label3"]:
            self.arw[widget].set_text("")
        self.arw["network_summary"].show()
        message = ""
        self.arw["network_summary_spinner"].start()
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
            self.arw["network_summary_label1"].set_text(message)
            while Gtk.events_pending():
                        Gtk.main_iteration()
        else:
            pass  # TODO : code for Linux and Mac

        # find Idefix and display network settings
        (ip, content) = find_idefix()
        if content:

            message = "<b>found Idefix at " + ip + "</b>"
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
                message += "\n\n<b>WARNING !!!  WARNING !!!  WARNING !!!  WARNING !!! \n Both subnets overlap !\nIdefix cannot work</b>"

            supervix = "http://" + ip + ":10080/visu-donnees-systeme.php"
            self.arw["network_summary_label2"].set_markup(message)
            while Gtk.events_pending():
                        Gtk.main_iteration()

            # verify Idefix Internet connection
            ping_data = get_infos("ping")
            self.arw["network_summary_spinner"].stop()
            if ping_data:
                message = "\n\nInternet connexion : \n" + result
            else:
                message = "Open a connection for this Idefix, and resend the command.\n"
                message += "It will then be able to test if Idefix Internet connection is working."
            self.arw["network_summary_label3"].set_markup(message)
        else:
            message += "<b>Idefix not found ! </b>"
            self.arw["network_summary_label2"].set_markup(message)


    def get_infos(self, command, result = "result", progress = False, json = False):
        # get infos from Idefix. The process is :
        #  - write a command in the 'trigger' file
        #  - the command is processed by Idefix, and the result is written in the 'result' file
        #  - the 'result' file is read, and data returned.
        #  - if json is set, then the data is first decoded
        #  - if progress is set, data is sent every second
        #  @spin : the spin object
        #  @ progress : a label object




        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        if not ftp:
            return False
        self.ftp = ftp

        command_f = io.BytesIO()
        ftp.storlines('STOR ' + result, command_f)       # delete data in result file

        command_f.write(bytes(command, "utf-8"))
        command_f.seek(0)
        # send command
        ftp.storlines('STOR trigger', command_f)

        # wait until Idefix has finished the job
        time1 = time.time()
        for i in range(60):     # set absolute maximum to 60 seconds
            while time.time() < time1 + i:
                while Gtk.events_pending():               # necessary to have the spinner work
                        Gtk.main_iteration()
            if progress:
                data1 = ftp_get(ftp, result)
                # escape characters incompatible with pango markup
                data1 = data1.replace("&", "&amp;")
                data1 = data1.replace(">", "&gt;")
                data1 = data1.replace("<", "&lt;")
                progress.set_markup(data1)

            status =  ftp_get(self.ftp, "trigger")
            if status == "ready":
                break

        data1 = ftp_get(ftp, result)
        ftp.close()
        return data1


    def idefix_infos(self, widget):
        if isinstance(widget, str):
            action = widget
        else:
            action = widget.name

        if action in ["unbound", "squid", "users"]:
            display_label = self.arw["infos_label"]
            spinner = self.arw["infos_spinner"]
        else:
            display_label = self.arw["infos_label2"]
            spinner = self.arw["infos_spinner2"]
            self.arw["display2_stack"].set_visible_child(self.arw["infos_page2_1"])


        if action == "linux_command":                                          # launched by the Go button
            command = "linux " + self.arw["linux_command_entry"].get_text()      # get command from the entry
        else:
            command = action.replace("infos_", "")

        if command in["unbound", "squid"]:
            command += " " + self.controller.myip

        spinner.start()
        if command in ("versions"):
            result = self.get_infos(command, progress=display_label)
        elif command in("all"):
            result = self.get_infos(command, result='result.zip')
        else:
            result = self.get_infos(command)
        spinner.stop()

        if command == "all":
            dialog = ExportDiagnosticDialog(self.arw, self)
            dialog.run(result)
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

            display_label.set_markup(result)

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


    def update_display(self, widget):
        ftp1 = self.controller.ftp_config
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        data1 = ftp_get(ftp, "result")
        self.arw["infos_label"].set_markup(data1)
        ftp.close()


    """ File editor   """

    def edit_file(self, widget):

        self.arw["display2_stack"].set_visible_child(self.arw["infos_page2_2"])
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

        data1 = self.get_infos("linux cat " + full_path)
        self.arw["editor_textview"].get_buffer().set_text(data1)


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


    def open_editor(self, widget):
        self.arw["informations_stack"].set_visible_child(self.arw["editor_box"])

    def close_editor(self, widget):
        self.arw["informations_stack"].set_visible_child(self.arw["informations_box"])

