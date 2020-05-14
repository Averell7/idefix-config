import io
import json
import os
import sys
import zipfile
from collections import OrderedDict

from gi.repository import Gtk

from connection_information import Information
from ftp_client import ftp_connect, ftp_get, ftp_send
from util import get_config_path, alert, showwarning


class ImportJsonDialog:

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.file_filter = Gtk.FileFilter()
        self.file_filter.add_pattern('*.json')
        self.configpath = ""

    def run(self, offline=False):
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
            self.controller.config = config
            self.controller.update()
            self.update_gui()
            if offline:
                self.controller.offline = True
                # close ftp connection
                try:
                    self.controller.ftp.close()
                except:
                    pass
                # disable the save button
                self.controller.arw["save_button1"].set_sensitive(False)
                self.controller.arw["save_button2"].set_sensitive(False)
                self.controller.arw["configname"].set_text(configname)
        dialog.destroy()

    def update_gui(self):
        self.controller.maclist = self.controller.users.create_maclist()
        self.controller.users.populate_users()
        self.controller.proxy_users.populate_proxy()
        # self.controller.populate_ports()
        self.controller.populate_groups()
        self.controller.populate_users_chooser()
        # self.controller.firewall.populate_firewall()
        self.controller.set_check_boxes()
        self.controller.set_colors()


class RestoreDialog:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller
        self.configpath = ''
        self.file_filter = Gtk.FileFilter()
        self.file_filter.add_pattern('*.zip')

    def run(self, source='local', offline=False, type=None):
        """ Run the restore dialog to select which files to restore. If type is specified then import those types
        without asking the user. Type can either be a string or an array. Source can be local for local files,
         ftp for ftp files or idefix for files on idefix"""

        if not offline:
            if not hasattr(self.controller, 'ftp') or not self.controller.ftp:
                alert(_(
                    "You cannot Restore a configuration without a connexion. \nIf you want to work offline, \nuse «Open Configuration on disk...» \nin the developper menu"))
                return

        zf = None
        path_prefix = ''

        if source == 'local':
            # Ask the user to select a file to restore

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
                try:
                    zf = zipfile.ZipFile(self.configpath)
                except zipfile.BadZipFile:
                    alert(_("Zip file could not be read"))
                path_prefix = ''
                dialog.destroy()
            else:
                dialog.destroy()
                self.arw['restore_config_dialog'].hide()
                return

        elif source == 'ftp':
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
                backup_list.sort(reverse=True)
                self.arw["backups_list_store"].clear()
                for backup in backup_list:
                    self.arw["backups_list_store"].append([backup])
                response = self.arw["backup_restore"].run()
            else:
                alert(_("Could not get FTP connection"))
                response = Gtk.ResponseType.CANCEL

            if response == Gtk.ResponseType.OK:
                (model, node) = self.arw["backups_list_tree"].get_selection().get_selected()
                name = model.get_value(node, 0)
                backupfiledata = (ftp_get(ftp, name))
                backup_f = io.BytesIO()
                backup_f.write(backupfiledata)
                backup_f.seek(0)
                try:
                    zf = zipfile.ZipFile(backup_f)
                except zipfile.BadZipFile:
                    alert(_("Zip file could not be read"))

                path_prefix = 'home/rock64/idefix/'
                self.arw["backup_restore"].hide()
            else:
                self.arw["backup_restore"].hide()
                self.arw['restore_config_dialog'].hide()
                return

        elif source == 'idefix':
            # get the list of backups present in Idefix

            x = Information.get_infos(self, "list_backups")
            backup_list = json.loads(x)
            backup_list.sort(reverse=True)

            self.arw["backups_list_store"].clear()

            for backup in backup_list:
                self.arw["backups_list_store"].append([backup])
            response = self.arw["backup_restore"].run()

            if response == Gtk.ResponseType.OK:
                (model, node) = self.arw["backups_list_tree"].get_selection().get_selected()
                name = model.get_value(node, 0)

                backupfiledata = (Information.get_infos(self, "get_backup " + name, result="result.zip"))
                backup_f = io.BytesIO()
                backup_f.write(backupfiledata)
                backup_f.seek(0)
                try:
                    zf = zipfile.ZipFile(backup_f)
                except zipfile.BadZipFile as e:
                    alert(_("Zip file could not be read"))
                path_prefix = 'home/rock64/idefix/'
                self.arw["backup_restore"].hide()
            else:
                self.arw["backup_restore"].hide()
                self.arw['restore_config_dialog'].hide()
                return
        else:
            self.arw["backup_restore"].hide()
            self.arw['restore_config_dialog'].hide()
            return

        if not zf:
            self.arw['restore_config_dialog'].hide()
            return

        self.arw['restore_config_permission_check'].set_active(False)
        self.arw['restore_config_network_check'].set_active(False)
        self.arw['restore_config_confix_check'].set_active(False)

        if type:
            response = Gtk.ResponseType.OK
            if 'permissions' in type:
                self.arw['restore_config_permission_check'].set_active(True)
            if 'network' in type:
                self.arw['restore_config_network_check'].set_active(True)
            if 'restore_config_confix_check' in type:
                self.arw['restore_config_confix_check'].set_active(True)

        else:
            response = self.arw['restore_config_dialog'].run()

        if response != Gtk.ResponseType.OK:
            self.arw['restore_config_dialog'].hide()
            return

        import_permissions = self.arw['restore_config_permission_check'].get_active()
        import_network = self.arw['restore_config_network_check'].get_active()
        import_confix = self.arw['restore_config_confix_check'].get_active()

        if not import_confix and not import_network and not import_permissions:
            alert(_("You must choose at least one option to restore"))
            self.arw['restore_config_dialog'].hide()
            return

        skip_confix = ''
        skip_network = ''
        skip_permissions = ''

        if import_permissions:
            try:
                data1 = zf.open(path_prefix + "idefix.json").read().decode("cp850")
            except KeyError:
                skip_permissions = _("Permissions file does not exist in backup")
            else:
                config = json.loads(
                    data1,
                    object_pairs_hook=OrderedDict
                )
                self.controller.config = config

        if import_network:
            try:
                data1 = zf.open(path_prefix + "idefix2_conf.json").read().decode("cp850").replace('\r\n', '\n')
            except KeyError:
                skip_network = _("Network file does not exist in backup")
            else:
                ftp1 = self.controller.ftp_config
                ftp = ftp_connect(ftp1["server"], ftp1["login"], ftp1["pass"])
                tmp_file = get_config_path('tmp_idefix2_conf.json')
                with open(tmp_file, 'w') as f:
                    f.write(data1)
                ftp_send(ftp, filepath=tmp_file, dest_name="idefix2_conf.json")
                command_f = io.BytesIO()
                command_f.write(bytes("restore_config", "utf-8"))
                command_f.seek(0)
                # send command
                ftp.storlines('STOR trigger', command_f)
                ftp.close()
                os.unlink(tmp_file)

        if import_confix:
            try:
                data1 = zf.open(path_prefix + "confix.cfg").read().decode("cp850")
            except KeyError:
                skip_confix = _("Connections file not exist in backup")
            else:
                with open(self.controller.profiles.filename, 'w') as f:
                    f.write(data1)

        self.controller.update()
        self.update_gui()

        if skip_permissions or skip_network or skip_confix:
            msg = ''
            if skip_permissions:
                msg += skip_permissions + '\n'
            if skip_network:
                msg += skip_network + '\n'
            if skip_confix:
                msg += skip_confix + '\n'

            showwarning(_("Some files were not restored"), msg)

        if offline:
            configname = os.path.split(self.configpath)[1]
            self.controller.offline = True
            # close ftp connection
            try:
                self.controller.ftp.close()
            except:
                pass
            # disable the save button
            self.controller.arw["save_button1"].set_sensitive(False)
            self.controller.arw["save_button2"].set_sensitive(False)
            self.controller.arw["configname"].set_text(configname)

        self.arw['restore_config_dialog'].hide()
        if import_confix and not skip_confix:
            alert(_("Please restart Confix to use your restored profiles"))
            sys.exit(1)

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

    def run(self, configpath=None, offline=False, to_json=False):
        """Export the configuration either as a zip file if to_json=False or as a json file if to_json=True"""

        if not configpath:
            dialog = Gtk.FileChooserDialog(
                _("Export Config"),
                self.arw['window1'],
                Gtk.FileChooserAction.SAVE,
                (_("Export"), Gtk.ResponseType.ACCEPT),
            )
            file_filter = Gtk.FileFilter()
            if to_json:
                file_filter.add_pattern('*.json')
            else:
                file_filter.add_pattern('*.zip')
            dialog.set_filter(file_filter)

            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                configpath = dialog.get_filename()
            dialog.destroy()

        config2 = self.controller.rebuild_config()
        config2_str = json.dumps(config2, indent=3)

        if to_json:
            f1 = open(configpath, "w", newline="\n")
            f1.write(config2_str)
            f1.close()
        else:
            zf = zipfile.ZipFile(os.path.splitext(configpath)[0] + ".zip", 'w')
            try:
                x = Information.get_infos(self, "get_conf")
                conf_list = json.loads(x)
                zf.writestr("idefix2_conf.json", conf_list["idefix2_conf.json"])
            except TypeError:
                if offline:
                    print("No connection, skipping idefix2_conf.json")
                else:
                    alert(_("Cannot retrieve network configuration from Idefix"))
                    return

            zf.writestr("idefix.json", config2_str)
            zf.write(get_config_path('confix.cfg'), 'confix.cfg')
            zf.close()
        alert(_("Configuration saved"))
