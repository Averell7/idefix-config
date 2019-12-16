import io
import subprocess
import time

from ftp_client import ftp_connect, ftp_get
from util import showwarning


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


    def spin(self, delay):
        # insure that the spinner runs for the required time
        time1 = time.time()
        while time.time() < time1 + delay:
            while Gtk.events_pending():
                    Gtk.main_iteration()
        return True


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
                self.arw["infos_spinner"].start()

        if command in ("ping"):
            self.spin(4)
        elif command in ("all"):
            self.spin(6)
        else:
            self.spin(2)
        self.arw["infos_spinner"].stop()
        data1 = ftp_get(ftp, "result")
        if command == "all":
            dialog = ExportDiagnosticDialog(self.arw, self)
            dialog.run("\n".join(data1).encode("utf8"))
        else:
            self.arw["infos_label"].set_markup("\n".join(data1))
        ftp.close()

    def search(self, widget):
        mac_search = self.arw["search_mac"].get_text().strip().lower()

        if mac_search != "":
            output = ""
            for user in self.controller.maclist:
                for mac in self.controller.maclist[user]:
                    if mac_search in mac:
                        output += user + " : " + mac + "\n"

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

        self.arw["infos_label"].set_text(output)
