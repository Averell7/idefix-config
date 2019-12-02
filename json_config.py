import json
import shutil
import os
from collections import OrderedDict

from gi.repository import Gtk

from util import get_config_path, alert


class ImportJsonDialog:

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.file_filter = Gtk.FileFilter()
        self.file_filter.add_pattern('*.json')
        self.configpath = ""

    def run(self, offline = False):
        if not hasattr(self.controller, 'ftp') or not self.controller.ftp:
            alert(_("You cannot Restore a configuration without a connexion. \nIf you want to work offline, \nuse «Open Configuration on disk...» \nin the devlopper menu"))
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

