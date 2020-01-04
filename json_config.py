import json
import shutil
import os
import io
from collections import OrderedDict
import zipfile

from gi.repository import Gtk

from util import get_config_path, alert
from connection_information import Information
from ftp_client import ftp_connect, ftp_get


class ImportJsonDialog:

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.file_filter = Gtk.FileFilter()
        self.file_filter.add_pattern('*.json')
        self.configpath = ""

    def run(self, offline = False):
        if not offline:
            if not hasattr(self.controller, 'ftp') or not self.controller.ftp:
                alert(_("You cannot Restore a configuration without a connexion. \nIf you want to work offline, \nuse «Open Configuration on disk...» \nin the developper menu"))
                return
        dialog = Gtk.FileChooserDialog(
            _("Import Config"),
            self.arw['window1'],
            Gtk.FileChooserAction.OPEN,
            (_("Import"), Gtk.ResponseType.ACCEPT),
        )
        dialog.set_filter(self.file_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.configpath = dialog.get_filename()
            configname = os.path.split(self.configpath)[1]
            config = json.load(
                open(self.configpath, 'r'),
                object_pairs_hook=OrderedDict
            )

            if offline :
                # close ftp connection
                try:
                    self.controller.ftp.close()
                except:
                    pass
                # disable the save button
                self.controller.arw["save_button1"].set_sensitive(False)
                self.controller.arw["save_button2"].set_sensitive(False)
                self.controller.arw["configname"].set_text(configname)


            self.controller.config = config
            self.controller.update()
            self.update_gui()
        dialog.destroy()

    def update_gui(self):
        self.controller.maclist = self.controller.users.create_maclist()
        self.controller.users.populate_users()
        self.controller.proxy_users.populate_proxy()
        #self.controller.populate_ports()
        self.controller.populate_groups()
        self.controller.populate_users_chooser()
        #self.controller.firewall.populate_firewall()
        self.controller.set_check_boxes()
        self.controller.set_colors()


class ImportJsonFromIdefix:

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

    def run(self, offline = False):
        if not offline:
            if not hasattr(self.controller, 'ftp') or not self.controller.ftp:
                alert(_("You cannot Restore a configuration without a connexion. \nIf you want to work offline, \nuse «Open Configuration on disk...» \nin the developper menu"))
                return

        # get the list of backups present in Idefix
        x = Information.get_infos(self, "list_backups")
        backup_list = json.loads(x)
        backup_list.sort(reverse = True)
        self.arw["backups_list_store"].clear()
        for backup in backup_list:
            self.arw["backups_list_store"].append([backup])
        x = self.arw["backup_restore"].run()

        if x == 1:
            (model, node) = self.arw["backups_list_tree"].get_selection().get_selected()
            name = model.get_value(node, 0)
            backupfiledata = (Information.get_infos(self, "get_backup " + name, result="result.zip"))
            backup_f = io.BytesIO()
            backup_f.write(backupfiledata)
            backup_f.seek(0)
            zf = zipfile.ZipFile(backup_f)
            config_json = zf.open("home/rock64/idefix/idefix.json").read().decode("cp850")

            config = json.loads(config_json, object_pairs_hook=OrderedDict)
            self.controller.config = config
            self.controller.update()
            self.update_gui()

        self.arw["backup_restore"].hide()

        print("terminé")


    def update_gui(self):
        self.controller.maclist = self.controller.users.create_maclist()
        self.controller.users.populate_users()
        self.controller.proxy_users.populate_proxy()
        #self.controller.populate_ports()
        self.controller.populate_groups()
        self.controller.populate_users_chooser()
        #self.controller.firewall.populate_firewall()
        self.controller.set_check_boxes()
        self.controller.set_colors()


class ImportJsonFromFTP:

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

    def run(self, offline = False):
        if not offline:
            if not hasattr(self.controller, 'ftp') or not self.controller.ftp:
                alert(_("You cannot Restore a configuration without a connexion. \nIf you want to work offline, \nuse «Open Configuration on disk...» \nin the developper menu"))
                return

        # get the list of backups present on the ftp server
        # get Idefix ftp configuration
        if self.controller.idefix_module:
            ftp1 = json.loads(Information.get_infos(self, "ftp"))
            ftp = ftp_connect(ftp1["ftp"], ftp1["login"], ftp1["password"], self.controller)
        else:
            ftp1 = self.controller.ftp_config
            ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])

        if ftp:
            ftp.cwd("backup")
            backup_list = ftp.nlst()
            backup_list.sort(reverse = True)
            self.arw["backups_list_store"].clear()
            for backup in backup_list:
                self.arw["backups_list_store"].append([backup])
            x = self.arw["backup_restore"].run()

        if x == 1:
            (model, node) = self.arw["backups_list_tree"].get_selection().get_selected()
            name = model.get_value(node, 0)
            backupfiledata = (ftp_get(ftp, name))
            backup_f = io.BytesIO()
            backup_f.write(backupfiledata)
            backup_f.seek(0)
            zf = zipfile.ZipFile(backup_f)
            config_json = zf.open("home/rock64/idefix/idefix.json").read().decode("cp850")

            config = json.loads(config_json, object_pairs_hook=OrderedDict)
            self.controller.config = config
            self.controller.update()
            self.update_gui()

        self.arw["backup_restore"].hide()

        print("terminé")


    def update_gui(self):
        self.controller.maclist = self.controller.users.create_maclist()
        self.controller.users.populate_users()
        self.controller.proxy_users.populate_proxy()
        #self.controller.populate_ports()
        self.controller.populate_groups()
        self.controller.populate_users_chooser()
        #self.controller.firewall.populate_firewall()
        self.controller.set_check_boxes()
        self.controller.set_colors()


class ExportJsonDialog:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.file_filter = Gtk.FileFilter()
        self.file_filter.add_pattern('*.json')

    def run(self, configpath = None, offline = False):
        if not configpath:
            dialog = Gtk.FileChooserDialog(
                _("Export Config"),
                self.arw['window1'],
                Gtk.FileChooserAction.SAVE,
                (_("Export"), Gtk.ResponseType.ACCEPT),
            )
            dialog.set_filter(self.file_filter)

            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                configpath =    dialog.get_filename()
            dialog.destroy()

        f1 = open(configpath, "w", newline = "\n")
        config2 = self.controller.rebuild_config()
        f1.write(json.dumps(config2, indent = 3))
        f1.close()
        alert(_("Configuration saved"))

