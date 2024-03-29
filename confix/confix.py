﻿#!/usr/bin/env python
# coding: utf-8

# version 3.0.2 - keeps the device name
# version 3.0.1 - bug fix
# version 2.5.4 - adds dns servers for eth0; needs idefix update 2.5.8 to work.
# version 2.5.3 - bug fixes
# version 2.5.2 - bug fixes
# version 2.5.1 - bug fixes
# version 2.5.0 - fine tunes
# version 2.4.13 - Load connection - Don't execute operations which don't make sense on a FTP connection, outside Idefix
# version 2.4.12 - strict_end parameter added
# version 2.4.11 - If the configuration is invalid, automatically loads the last valid configuration
# version 2.4.10b- check the date of Idefix at startup - correct if necessary
# version 2.4.9 - control panel for services
# version 2.4.8 - Informations "connected users" allow to create user
# version 2.4.7 - export the three configuration files (idefix.json, idefix2_conf.json, confix.cfg)
# version 2.4.6 - improved create user assistant and first use assistant
# version 2.4.5 - password protection
# version 2.4.4 - bug fixes
# version 2.4.3 - Improve Informations/unbound log
# version 2.4.2 - Why...
# version 2.4.1 - first configuration
# version 2.4.0
# version 2.3.10 - restore from Idefix backups or FTP backups
# version 2.3.9 - Network summary
# version 2.3.8 - Warning when leaving the program, if user has not saved his changes
#                 Edit file added to the information tab
# version 2.3.7 - Idefix module automatically detected
# version 2.3.6 - Changes in connexion profiles are active immediately
# version 2.3.5 - groups repository is presented as a tree
# version 2.3.4 - Adds the "informations" tab
# version 2.3.3 - bug in assistant fixed - menu changed
# version 2.3.2 - Developper menu added
# version 2.3.1 - new idefix.json format
# version 2.1.0 - supports subusers
# version 2.0.0 - Supports Unbound

import http.client
import io
import json
import os
import sys
import zipfile
from collections import OrderedDict
from copy import deepcopy

sys.path.insert(0, os.path.dirname(__file__))

import gi
import time

from connection_information import Information
from ftp_client import ftp_connect, ftp_get, ftp_send, FTPError
from idefix2_config import Idefix2Config

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from groups_manager import GroupManager
from actions import DRAG_ACTION
from util import (
    AskForConfig, alert, showwarning, askyesno,
    EMPTY_STORE, SignalHandler, get_config_path, ip_address_test,
    ask_text, ask_choice, PasswordDialog, print_except)
from icons import (
    internet_full_icon, internet_filtered_icon, internet_denied_icon
)
from filter_rules import FilterRules
from proxy_group import ProxyGroup
from firewall import Firewall
from users import Users
from config_profile import ConfigProfile, requires_password, test_decrypt_config, encrypt_password, DEFAULT_KEY
from assistant import Assistant
from json_config import RestoreDialog, ExportJsonDialog, ImportJsonDialog

###########################################################################
# CONFIGURATION ###########################################################
###########################################################################
global version, future, idefix_domain
future = True  # Activate beta functions
version = "3.1.2"
idefix_domain = "idefix.admin"


gtk = Gtk
Pixbuf = GdkPixbuf.Pixbuf


def get_row(treestore, iter1):
    row = []
    for i in range(treestore.get_n_columns()):
        row.append(treestore.get_value(iter1, i))
    return row


class Confix:
    cat_list = OrderedDict()
    iter_user = None
    iter_firewall = None
    iter_filter = None
    active_chooser = None

    def __init__(self, configname, config_password):

        # self.ftp_config = ftp_config
        # When set to true, the configuration is loaded and written from and to local files (development mode)
        self.load_locale = False
        self.mem_text = ""
        self.mem_time = 0
        self.block_signals = False
        # Load the glade file
        self.widgets = gtk.Builder()
        self.widgets.set_translation_domain("confix")
        self.widgets.add_from_file('./confix.glade')
        # create an array of all objects with their name as key
        ar_widgets = self.widgets.get_objects()
        self.arw = {}
        for z in ar_widgets:
            try:
                name = gtk.Buildable.get_name(z)
                self.arw[name] = z
                z.name = name
            except:
                pass

        # Assistant
        self.widgets2 = gtk.Builder()
        self.widgets2.set_translation_domain("confix")
        self.widgets2.add_from_file('./assistant.glade')
        # create an array of all objects with their name as key
        ar_widgets = self.widgets2.get_objects()
        self.arw2 = {}
        for z in ar_widgets:
            try:
                name = gtk.Buildable.get_name(z)
                self.arw2[name] = z
                z.name = name
            except:
                pass

        self.import_json = ImportJsonDialog(self.arw, self)
        # self.import_json_from_idefix = ImportJsonFromIdefix(self.arw, self)
        # self.import_json_from_ftp = ImportJsonFromFTP(self.arw, self)
        self.restore_dialog = RestoreDialog(self.arw, self)
        self.export_json = ExportJsonDialog(self.arw, self)
        self.offline = False

        self.arw["program_title"].set_text("Confix - Version " + version)
        window1 = self.arw["window1"]
        window1.show_all()
        window1.set_title(_("Confix"))
        #window1.connect("destroy", self.destroy)

        self.groups_manager = GroupManager(self.arw, self)


        if not future:
            for widget in ["scrolledwindow2", "toolbar3", "paned3", "box2"]:  # interface prévue pour le firewall
                self.arw[widget].hide()
            self.arw["firewall_disabled"].show()
        else :
            self.arw["firewall_disabled"].hide()

        # images for buttons
        image = Gtk.Image()
        image.set_from_file("./data/toggle_all.png")
        self.all_button = image
        image2 = Gtk.Image()
        image2.set_from_file("./data/toggle_list.png")
        self.list_button = image2
        image3 = Gtk.Image()
        image3.set_from_file("./data/toggle_allow.png")
        self.allow_button = image3
        image4 = Gtk.Image()
        image4.set_from_file("./data/toggle_deny.png")
        self.deny_button = image4
        image5 = Gtk.Image()

        image5.set_from_file("./data/toggle_all.png")
        self.all2_button = image5
        image6 = Gtk.Image()
        image6.set_from_file("./data/toggle_list.png")
        self.list2_button = image6

        # self.arw["button1"].set_image(self.blue_button)
        # self.arw["button1"].set_always_show_image(True)

        if config_password:
            kargs = {'password': config_password}
        else:
            kargs = {}
        self.profiles = ConfigProfile(self.arw, self, **kargs)
        # à garder $$ self.ftp_config = self.idefix_config['conf'][active_config]

        # set check boxes in menu
        self.block_signals = True
        self.arw['menu_autoload_check'].set_active(
            self.profiles.config['__options'].get('auto_load', 0) == '1'
        )
        self.block_signals = False

        # get the style from the css file and apply it
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path('./data/confix.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_USER)

        # autoconnect signals for self functions
        self.filter_rules = FilterRules(self.arw, self)
        self.proxy_group = ProxyGroup(self.arw, self)
        self.firewall = Firewall(self.arw, self)
        self.users = Users(self.arw, self)
        self.assistant = Assistant(self.arw, self.arw2, self)
        self.information = Information(self.arw, self)
        self.idefix2_config = Idefix2Config(self.arw, self)

        self.users_store = self.users.users_store
        self.filter_store = self.filter_rules.filter_store
        self.proxy_rules_store = self.filter_rules.proxy_rules_store
        self.groups_store = self.proxy_group.groups_store
        self.firewall_store = self.firewall.firewall_store

        self.signal_handler = SignalHandler([
            self, self.filter_rules, self.proxy_group, self.firewall, self.users, self.profiles, self.assistant,
            self.information, self.information.services, self.idefix2_config
        ])
        self.widgets.connect_signals(self.signal_handler)
        self.widgets2.connect_signals(self.signal_handler)

        # autosave textview buffers when typing (see also drag and drop below)
        # and when drag is received
        for textView in ["maclist",
                         "rule_dest", "filter_#comments",
                         "firewall_ports", "firewall_users", "firewall_comments"]:
            self.arw[textView].connect("key-release-event", self.update_tv)
            self.arw[textView].connect("drag-data-received", self.on_drag_data_received)

        self.config = OrderedDict()

        while Gtk.events_pending():
            Gtk.main_iteration()

        # load configuration
        if configname == "":                            # No connexion profile chosen
            self.ftp_config = None
        else:
            self.ftp_config = self.profiles.config[configname]
            ftp = self.open_connexion_profile()
        self.arw["configname"].set_text(configname)



        if self.load_locale:         # development environment
            self.arw['loading_window'].hide()
            if os.path.isfile(get_config_path("dev/idefix.json")):
                data_str = open(get_config_path("dev/idefix.json"), "r").read()
                try:
                    self.config = json.loads(data_str, object_pairs_hook=OrderedDict)
                    self.update()
                except:
                    alert("Unable to load configuration. Please import another one.")


        for category in ["firewall", "rules", "proxy-rules", "ports-rules", "ports", "groups"]:
            if category not in self.config:
                self.config[category] = OrderedDict()

        if "users" not in self.config:
            self.config["users"] = OrderedDict()


        if not future:
            # delete from config["firewall"] the generated lines
            todel = []
            for key in self.config["firewall"]:
                if key[0:2] == "__":
                    todel.append(key)
            for key in todel:
                del self.config["firewall"][key]

        # chooser

        # create a special store with users who have an Internet access
        # 0 - Name
        # 1 - Unused
        # 2 - Unused
        # 3 - True if sub user, False is user
        # 4 - True if category, False is user
        self.chooser_users_store = gtk.TreeStore(str, str, bool, bool)

        tvcolumn = gtk.TreeViewColumn(_('Groups Drag and Drop'), Gtk.CellRendererText(), text=0)
        self.arw["chooser"].append_column(tvcolumn)
        self.arw["chooser"].get_selection()
        self.proxy_group.set_group_store('proxy')
        # sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        tvcolumn = gtk.TreeViewColumn(_('Users Drag and Drop'), Gtk.CellRendererText(), text=0)
        self.arw["chooser1"].append_column(tvcolumn)
        self.arw["chooser1"].get_selection()
        self.arw["chooser1"].set_model(self.chooser_users_store)
        # sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        tvcolumn = gtk.TreeViewColumn(_('Firewall'), Gtk.CellRendererText(), text=0)
        self.arw["chooser2"].append_column(tvcolumn)
        # sel.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.arw["chooser2"].get_selection()

        self.empty_store = EMPTY_STORE

        for chooser in ["chooser", "chooser1", "chooser2"]:
            self.arw[chooser].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [],
                                                       DRAG_ACTION)
            self.arw[chooser].drag_source_add_text_targets()
            self.arw[chooser].connect("drag-data-get", self.chooser_drag_data_get)


        # drop for TextView
        # see above, the line : self.arw["proxy_group"].connect("drag-data-received", self.on_drag_data_received)

        # icons for users list

        (self.maclist, self.devicelist) = self.users.create_maclist()
        self.users.populate_users()
        self.filter_rules.populate_rules()
        self.populate_ports()
        self.populate_groups()
        self.populate_users_chooser()
        self.firewall.populate_firewall()
        self.set_check_boxes()
        self.set_colors()
        self.profiles.list_configuration_profiles()
        self.assistant.disable_simulated_user()     # In case the previous user has not disabled simulation before shutting down


        # Assistants
        # manage requests uses the model of the first tab
        self.arw2["manage_request_tree"].set_model(self.users.users_store)
        self.tvcolumn = gtk.TreeViewColumn(_('Users'), self.users.cell, text=0)
        self.arw2["manage_request_tree"].append_column(self.tvcolumn)

        if not self.profiles.config_found:
            self.assistant.show_assistant_first()

        # user defined options
        checkbox_config = self.profiles.config['__options'].get('checkbox_config', 0) == '1'
        if checkbox_config:
            self.filter_rules.set_gui('check')

        filter_tab = self.profiles.config['__options'].get('filter_tab', 0) == '1'
        if filter_tab:
            self.arw['notebook3'].set_current_page(1)

        password_option = self.profiles.config['__options'].get('password')
        if password_option:
            self.arw['option_password_check'].set_active(True)
            self.arw['option_password_entry'].set_text(config_password)

        developper_menu = self.profiles.config['__options'].get('developper_menu', 0) == '1'
        if developper_menu is False:
            self.arw['developper_menu'].set_sensitive(False)
            self.arw['developper_menu'].set_visible(False)

        advanced_filter = self.profiles.config['__options'].get('advanced_filter', 0 ) == '1'
        self.arw['filter_rules_box'].set_visible(advanced_filter)

        auto_load = self.profiles.config['__options'].get('auto_load', 0) == '1'
        if auto_load:
            last_config = self.profiles.config['__options'].get('last_config')
            if last_config:
                configname = last_config
                if configname:
                    self.ftp_config = self.profiles.config[configname]
                    if self.open_connexion_profile(configname):
                        self.arw["configname"].set_text(configname)
                    else:
                        self.arw["configname"].set_text("---")

    def ask_for_profile(self, widget = None):
        # Refresh available configurations?

        config_dialog = AskForConfig(self.profiles.config)
        result = config_dialog.run()
        if not result:
            return
        configname, eth = result

        if self.offline == True:                  # if an offline configuration is open, offer to save it
            alert("TODO : Do you want to save your changes, before opening another configuration?")
            # TODO : finish this dialog
            self.offline = False


        self.ftp_config = self.profiles.config[configname]
        if not self.profiles.config['__options']:
            self.profiles.config['__options'] = {}
        self.profiles.config['__options']["last_config"] = configname
        self.profiles.profile_save_config()
        if self.open_connexion_profile(configname, eth):
            self.arw["configname"].set_text(configname + "- eth" + str(eth))
            self.arw["save_button1"].set_sensitive(True)
            self.arw["save_button2"].set_sensitive(True)
        else:
            self.arw["configname"].set_text("---")
            self.arw["save_button1"].set_sensitive(False)
            self.arw["save_button2"].set_sensitive(False)

    def find_good_backup(self):
        """Find a good backup from Idefix"""

        # Download list of available back ups
        try:
            backup_list = json.loads(self.information.get_infos('list_backups'))
            backup_list.sort(reverse=True)
        except:
            backup_list = []

        for backup in backup_list:
            # Download the zip file and extract it
            filedata = self.information.get_infos('get_backup ' + backup, result='result.zip')
            backup_f = io.BytesIO()
            backup_f.write(filedata)
            backup_f.seek(0)
            try:
                zf = zipfile.ZipFile(backup_f)
            except zipfile.BadZipFile as e:
                print("Error extracting backup", backup, e)
                continue

            # Try load configuration from the file
            if self.restore_dialog.load_from_backup(zf, type=['permissions'], show_warning=True):
                print("Error loading backup", backup)
                continue
            else:
                showwarning(
                    _("Restore Backup"),
                    _("Restored from backup %s") % backup
                )

                self.load_connection()
                return

        self.ftp.close()
        # No good backups were found
        return alert("Unable to load configuration. Please import another one.")

    def open_connexion_profile(self, configname="", eth = 1):

        print("open connexion profile")
        self.mymac = None
        self.arw['loading_window'].show()
        while Gtk.events_pending():
            Gtk.main_iteration()
        # ftp connect
        ftp1 = self.ftp_config
        self.ftp = ftp_connect(ftp1["server"], ftp1["login"], ftp1["pass"], self)
        self.arw['loading_window'].hide()

        if not self.ftp:
            # alert(_("Could not connect to %s (%s). \nVerify your cables or your configuration.") % (ftp1["server"], configname))
            return False
        else:
            # retrieve files by ftp

            if eth == 1:
                configfile = "idefix3.json"
            elif eth == 2:
                configfile = "idefix3_2.json"
            elif eth == 3:
                configfile = "idefix3_3.json"
            data0 = ftp_get(self.ftp, configfile, json=True)
            self.opened_configuration = [configfile, "eth" + str(eth)]
            self.active_config_text = data0
            if data0:
                try:
                    self.config = json.loads(data0, object_pairs_hook=OrderedDict)
                    self.update()
                    self.update_gui()
                except:
                    print_except()
                    # Try load a backup configuration
                    if askyesno(_("Corrupted Configuration"), _('Your configuration is corrupted. Search for backup?')):
                        return self.find_good_backup()
                    else:
                        self.config = OrderedDict()
                        self.load_defaults()
                self.ftp.close()
            else:
                self.load_defaults()

            if self.load_connection(configname):
                return True

    def load_connection(self, configname = ""):
        global idefix_domain
        print("load connexion")
        ftp1 = self.ftp_config
        if (ftp1["server"] == idefix_domain or
            ip_address_test(ftp1["server"])):                 # If we are connected directly to an Idefix module
            self.connection_type = "idefix"
            for name in ["save_button1", "save_button2"]:
                self.arw[name].set_label("Send configuraton to Idefix")
            ip = ftp1["server"]
            try:
                h1 = http.client.HTTPConnection(ip, timeout=10)
                h1.connect()
                print("load connexion2")
                try:
                    h1.request("GET", "/network-info.php")
                    res = h1.getresponse()
                    if res.status == 200:
                        data1 = res.read().decode("cp850")
                        content = json.loads(data1)
                        self.myip = content["client"]["ip"]
                        self.mymac = content["client"]["mac"]
                        self.myidefix = True
                        if self.mymac in self.maclist:
                            self.myaccount = self.maclist[self.mymac]
                        else:
                            self.myaccount = _("unknown")
                except FTPError:
                    info = print_except(True)
                    message = ""
                    for line in info.split("\n"):
                        if "error" in line.lower():
                            message += line + "\n"
                    alert("could not get network-info.php")

                self.arw["configname"].set_text(configname)        # set the name of the profile in the gui
                # TODO : at this point, configname is empty !
                while Gtk.events_pending():
                    Gtk.main_iteration()
                self.assistant.refresh_detect_list()


                # Check if the date is correct and if not, update it
                t1 = time.time()
                try:
                    self.information.check_date()
                except:
                    print("Error when checking date")
                delta = int(time.time() - t1)
                print("self.information.check_date() : ", str(delta))
                print("load connexion3c")
            except FTPError:
                info = print_except(True)
                message = ""
                for line in info.split("\n"):
                    if "error" in line.lower():
                        message += line + "\n"
                alert("Impossible to join " + ip + "\n\n" + message)
        else:
            self.connection_type = "internet"
            for name in ["save_button1", "save_button2"]:
                self.arw[name].set_label("Send configuraton to FTP Server")

        # Check our mac address exists
        print("self.check_mac_and_create_config()")
        self.check_mac_and_create_config()

        # For the "Experiment user permissionhs" Assistant
        if hasattr(self,"myaccount"):
            self.arw2["my_account"].set_text(self.myaccount)

        return True

    def check_mac_and_create_config(self):
        """Check if there is a configuration for the user's mac address and optionally create a new configuration
        for them"""
        print("check_mac")
        if not self.mymac or self.mymac in self.maclist:
            return

        # Mac Address does not yet exist, ask the user to create a configuration
        self.arw["your_mac_address_label"].set_text(self.mymac)
        self.arw['user_mac_address_dialog'].show()
        response = self.arw['user_mac_address_dialog'].run()
        self.arw['user_mac_address_dialog'].hide()
        if response == Gtk.ResponseType.YES:
            # Create default configuration
            rule = ask_text(self.arw['window1'], _("Enter name for configuration"))
            if not rule:
                rule = 'default'

            # Pre fill in details in the first-run assistant
            self.assistant.show_assistant_create_pre_enter(
                rule,
                self.mymac,
                rule
            )

            """
            self.arw['newly_created_summary'].show()
            self.arw['newly_created_summary'].run()
            self.arw['newly_created_summary'].hide()

            # Jump to the created rule
            self.arw['notebook3'].set_current_page(1)
            self.proxy_users.select_rule(rule)
            """

        elif response == Gtk.ResponseType.APPLY:
            # Show the assistant
            self.assistant.show_assistant_create_with_mac(self.mymac)

    def update_gui(self):
        self.profiles.list_configuration_profiles()
        (self.maclist, self.devicelist) = self.users.create_maclist()
        self.users.populate_users()
        self.filter_rules.populate_rules()
        self.populate_ports()
        self.populate_groups()
        self.populate_users_chooser()
        #self.firewall.populate_firewall()
        self.set_check_boxes()
        self.set_colors()

    def load_defaults(self, widget = None):
        response = askyesno(_("No user data"),
                            _("There is no user data present. \nDo you want to create standard categories ?"))
        if response == 1:
            if os.path.isfile("./defaults/idefix3-default.json"):
                data_str = open("./defaults/idefix3-default.json", "r").read()
                self.config = json.loads(data_str, object_pairs_hook=OrderedDict)
                self.update_gui()
                self.set_colors()




    def open_config(self, widget):
        self.import_json.run(offline=True)

    def save_config(self, widget):
        self.export_json.run(configpath=self.restore_dialog.configpath, offline=True, to_json=True)

    def save_config_as(self, widget):
        self.export_json.run(offline=True, to_json=True)

    def import_config(self, widget):
        self.restore_dialog.run(source='local')

    def import_config_from_idefix_backup(self, widget):
        self.restore_dialog.run(source='idefix')

    def import_config_from_ftp_backup(self, widget):
        self.restore_dialog.run(source='ftp')

    def export_config(self, widget):
        offline = self.profiles.config['__options'].get('developper_menu', 0) == '1'
        self.export_json.run(offline=offline)

    def show_help_colors(self, widget):
        self.arw2["help_colors_window"].show()

    def hide_help_colors(self, widget):
        self.arw2["help_colors_window"].hide()

    def show_manage_groups(self, widget):
        self.groups_manager.show()

    def show_filter_helper(self, widget):
        self.arw["system_window"].show()

    def show_about(self, widget):
        self.arw["about_window"].show()

    def close_about(self, *args):
        self.arw['about_window'].hide()

    """ Load interface """

    def populate_ports(self):
        self.firewall.populate_ports()

    def populate_groups(self):
        self.groups_store.clear()
        data1 = self.config["groups"]
        for key in data1:
            tooltip = "\n".join(data1[key].get('dest_domains', ''))
            self.groups_store.append([key, tooltip])

    def populate_users_chooser(self) :
        self.chooser_users_store.clear()
        for row in self.users_store:
            category = row[0]
            if row[6] or row[7]:  # Add category only if Internet access is enabled
                iter1 = self.chooser_users_store.append(None, [category, "", False, True])
                for child in row.iterchildren():  # write users
                    user = child[0]
                    child_iter = self.chooser_users_store.append(iter1, [user, "", False, False])
                    for subchild in child.iterchildren():
                        subuser = subchild[0]
                        self.chooser_users_store.append(child_iter, [subuser, "", True, False])

    def set_check_boxes(self):
        for row in self.filter_store:
            if row[1].strip().lower() == "off":
                row[14] = 0
            if row[2].strip().lower() == "deny":
                row[13] = 0


        for row in self.firewall_store:
            if row[1].strip().lower() == "off":
                row[14] = 0
            if row[2].strip().lower() == "drop":
                row[13] = 0

            # if row[10].strip().lower() == "any" :
            #     row[12] = 1
            # else:
            #     row[12] = 0

    def set_colors(self):
        global iconx
        # col 13 = allow/deny state; col 15 = text color
        # col 14 = on/off state; col 15 = text color
        stores = [
            self.filter_store, self.firewall_store, self.filter_rules.proxy_rules_store,
            self.filter_rules.port_rules_store
        ]

        for store in stores:
            for row in store:
                if row[13] == 1:  # allow
                    row[15] = "#009900"  # green
                else:  # deny
                    row[15] = "#ff0000"  # red

                if row[14] == 0:  # off
                    row[15] = "#bbbbbb"  # grey

                if row[12] == 1:  # any  destination
                    row[16] = "#ffff88"  # yellow background

                if row[0][0:2] == "__":
                    row[16] = "#fbfbff"  # light grey background

        for row in self.users_store:
            """
            0 : section (level 1)  - user (level 2) - sub user (level 3)
            1 : options (text)
            2 : reserved [email time conditions]
            3 : reserved [internet time conditions]
            4 : email (1/0)
            5 : internet access (1/0)
            6 : filtered (1/0)
            7 : open (1/0)
            8 :
            9 : color 1
            10 : color 2
            11 : icon 1
            12 : icon 2
            """
            # yellow background for open Internet access
            if row[5] == 1 and (row[7] == 1):
                row[10] = "#ffff88"
            else:
                row[10] = "#ffffff"

            # icons for email and Internet access

##            if row[3]:
##                row[12] = internet_timed_icon
##            elif not row[5]:
##                row[12] = internet_denied_icon

            if row[7]:
                row[12] = internet_full_icon
            elif row[6]:
                row[12] = internet_filtered_icon
            else:
                row[12] = internet_denied_icon


    """Actions"""



    def toggle_col13(self, cellrenderer, row, treestore, name):       # unused
        # callback of ?
        # col 13 = allow/deny state; col 15 = text color

        if treestore[row][13] == 0:
            treestore[row][13] = 1
            if name == "proxy":
                treestore[row][2] = "allow"
            elif name == "firewall":
                treestore[row][2] = "ACCEPT"
            treestore[row][15] = "#009900"
        else:
            treestore[row][13] = 0
            if name == "proxy":
                treestore[row][2] = "deny"
            elif name == "firewall":
                treestore[row][2] = "DROP"
            treestore[row][15] = "#ff0000"

    def update_tv(self, text_view, event=None, a=None, b=None, c=None, text=""):

        text_buffer = text_view.get_buffer()
        (start_iter, end_iter) = text_buffer.get_bounds()
        text1 = text_buffer.get_text(start_iter, end_iter, False) + text
        widget = text_view

        if widget.name == "rule_dest":
            self.filter_rules.current_store.set(self.iter_filter, 8, text1)
        elif widget.name == "filter_#comments":
            self.filter_rules.current_store.set(self.iter_filter, 4, text1)

        elif widget.name == "firewall_ports":
            self.firewall_store.set(self.iter_firewall, 3, text1)
        elif widget.name == "firewall_users":
            self.firewall_store.set(self.iter_firewall, 6, text1)
        elif widget.name == "firewall_comments":
            self.firewall_store.set(self.iter_firewall, 5, text1)

        elif widget.name == "maclist":
            devicedata = text1.split("\n")  # create list
            # get usr name
            (model, node) = self.arw["treeview1"].get_selection().get_selected()
            name = model.get_value(node, 0)
            self.maclist[name] = devicedata
            self.devicelist[name] = []
            i = 1
            for devicedef in devicedata:
                if devicedef.strip().startswith("#"):   # comment
                     continue   # not supported by the new config
                elif "#" in devicedef:
                    (device, thismac) = devicedef.split("#", 1)
                    self.devicelist[name].append([thismac,device])
                elif ip_address_test(devicedef):
                    self.devicelist[name].append([devicedef, "device" + str(i)])
                    i += 1


        """
        elif widget.name == "maclist":
            mac_addresses = text1.split("\n")  # create list
            # get usr name
            (model, node) = self.arw["treeview1"].get_selection().get_selected()
            name = model.get_value(node, 0)
            self.maclist[name] = mac_addresses
        """
    def update_check(self, widget):
        # Updates the stores according to the settings of the check buttons

        if self.block_signals:
            return
        # proxy
        if widget.name == "proxy_full_access":
            if widget.get_active():
                self.filter_store[self.iter_filter][10] = "any"
                self.arw["paned2"].set_sensitive(False)
            else:
                self.filter_store[self.iter_filter][10] = ""
                self.arw["paned2"].set_sensitive(True)
        # users
        elif widget.name == "internet_email":
            if widget.get_active():
                self.users_store[self.iter_user][4] = 1
            else:
                self.users_store[self.iter_user][4] = 0

        elif widget.name == "internet_filtered":
            if widget.get_active():
                self.users_store[self.iter_user][6] = 1
                self.arw["internet_open"].set_active(False)
                self.users_store[self.iter_user][7] = 0
            else:
                self.users_store[self.iter_user][6] = 0

        elif widget.name == "internet_open":
            if widget.get_active():
                self.users_store[self.iter_user][7] = 1
                self.arw["internet_filtered"].set_active(False)
                self.users_store[self.iter_user][6] = 0     # internet filtered disabled
                self.users_store[self.iter_user][4] = 1     # email enabled
                #self.arw["internet_email"].set_active(True)
            else:
                self.users_store[self.iter_user][7] = 0


        self.populate_users_chooser()
        self.set_colors()
        # Update the time conditions frames
##        self.arw['email_time_condition'].set_sensitive(
##            self.users_store[self.iter_user][4] or self.users_store[self.iter_user][7]
##            )
##        self.arw['internet_time_condition'].set_sensitive(self.users_store[self.iter_user][7])

    def update_time(self, widget):
        if widget.name in ["users_time_days_email", "users_time_from_email", "users_time_to_email"]:
            time_condition = self.arw["users_time_days_email"].get_text() + " "
            if time_condition.strip() == "":
                time_condition = "1234567 "
            time_condition += self.arw["users_time_from_email"].get_text().strip() + "-"
            time_condition += self.arw["users_time_to_email"].get_text().strip()
            if time_condition == "1234567 -":
                time_condition = ""
            self.users_store[self.iter_user][2] = time_condition
            self.set_colors()

        if widget.name in ["users_time_days_internet", "users_time_from_internet", "users_time_to_internet"]:
            time_condition = self.arw["users_time_days_internet"].get_text() + " "
            if time_condition.strip() == "":
                time_condition = "1234567 "
            time_condition += self.arw["users_time_from_internet"].get_text().strip() + "-"
            time_condition += self.arw["users_time_to_internet"].get_text().strip()
            if time_condition == "1234567 -":
                time_condition = ""
            self.users_store[self.iter_user][3] = time_condition
            self.set_colors()

        if widget.name in ["firewall_time_days", "firewall_time_from", "firewall_time_to"]:
            # time_condition = self.arw["users_time_days"].get_text() + " "
            time_condition = self.arw["firewall_time_from"].get_text().strip() + "-"
            time_condition += self.arw["firewall_time_to"].get_text().strip()
            if time_condition.strip() == "-":
                time_condition = ""
            self.firewall_store[self.iter_firewall][4] = time_condition

    def treeview_expand(self, widget):
        if widget.get_active() == 1:
            self.arw["treeview1"].expand_all()
        else:
            self.arw["treeview1"].collapse_all()

    def on_permissions_tab_change(self, widget, a, page):
        # launched by the switch page signal of notebook2
        #
        if page == 0:
            self.arw["chooser"].set_model(self.groups_store)
            self.active_chooser = 'proxy_group'
        else:
            self.arw["chooser"].set_model(self.empty_store)
            self.active_chooser = None

    """ Options Management """

    def cancel_options(self, widget):
        self.arw['options_window'].hide()

    def save_options(self, widget):
        if self.block_signals:
            return

        if self.arw['option_password_check'].get_active() and not self.arw['option_password_entry'].get_text():
            showwarning(_("No Password"), _("Please enter a password"))
            return

        gui_check = self.arw['option_checkbox_gui_check'].get_active()
        filter_tab = self.arw['option_filter_tab_check'].get_active()
        auto_load = self.arw['menu_autoload_check'].get_active()
        developper_menu = self.arw['option_developper_check'].get_active()
        advanced_filter = self.arw['option_advanced_filter_check'].get_active()

        self.profiles.config['__options'] = {
            'checkbox_config': '1' if gui_check else '0',
            'filter_tab': '1' if filter_tab else '0',
            'auto_load': '1' if auto_load else '0',
            'developper_menu': '1' if developper_menu else '0',
            'advanced_filter': '1' if advanced_filter else '0',
        }

        if self.arw['option_password_check'].get_active():
            self.profiles.config['__options']['password'] = encrypt_password(
                self.arw['option_password_entry'].get_text(),
                self.arw['option_password_entry'].get_text()
            )
            self.profiles.password = self.arw['option_password_entry'].get_text()
        else:
            self.profiles.password = DEFAULT_KEY
            self.arw['option_password_entry'].set_text('')

        if gui_check:
            self.filter_rules.set_gui('check')
        else:
            self.filter_rules.set_gui('buttons')

        self.arw['developper_menu'].set_sensitive(developper_menu)
        self.arw['developper_menu'].set_visible(developper_menu)

        self.arw['filter_rules_box'].set_visible(advanced_filter)

        # Save to config
        self.profiles.profile_save_config()
        self.arw['options_window'].hide()

    def show_options(self, widget):
        # Get options
        self.arw['option_checkbox_gui_check'].set_active(
            self.profiles.config['__options'].get('checkbox_config', 0) == '1'
        )
        self.arw['option_filter_tab_check'].set_active(
            self.profiles.config['__options'].get('filter_tab', 0) == '1'
        )
        self.arw['option_developper_check'].set_active(
            self.profiles.config['__options'].get('developper_menu', 0) == '1'
        )
        self.arw['option_advanced_filter_check'].set_active(
            self.profiles.config['__options'].get('advanced_filter', 0) == '1'
        )

        self.arw['options_window'].show_all()

    def toggle_password_entry(self, widget):
        self.arw['option_password_entry'].set_sensitive(widget.get_active())

    """ User Management """

    def show_debug_window(self, widget) :
        self.arw["system_window"].show_all()

    def hide_debug_window(self,widget):
        self.arw["system_window"].hide()


    """ View """

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, etime):
        # Used in TextViews for Drag and Drop
        text1 = data.get_text()
        self.mem_time = time.time()
        self.update_tv(widget, text=text1)

    def chooser_drag_data_get(self, treeview, drag_context, data, info, time):

        (model, node) = treeview.get_selection().get_selected()
        if node:
            text = model.get_path(node).to_string()
            text += "#" + treeview.name
            data.set_text(text, -1)
            #sel = treeview.get_selection()
            #treeview.set_row_drag_data(sel, model, node)  Not a treeview function

    def chooser_show_context(self, widget, event):
        """Show the context menu on right click (if applicable)"""
        if event.type != Gdk.EventType.BUTTON_RELEASE or event.button != 3:
            return
        self.arw["chooser_proxy_groups_menu"].popup(None, None, None, None, event.button, event.time)


    """ Output """

    def build_files(self, widget):
        # launched by the GO button

        f1 = open(get_config_path("idefix3.json"), "w", newline = "\n")
        config3 = self.rebuild_config3()
        self.active_config_text = json.dumps(config3, indent = 3)      # update the copy in memory of the config, used to detect changes and remind the user to save.
        json.dump(config3, f1, indent = 3)
        f1.close()

        if not self.load_locale:  # send the files by FTP. Load_locale is the development mode, where files are read and written only on the local disk
            self.ftp_upload(dest_name=self.opened_configuration[0])

    def format_row(self, row) :
        # used by rebuild_config
        if not row:
            return
        tmp = row.strip().split("\n")
        tmp2 = []
        for value in tmp:                    # clean list
            if value in tmp2:
                continue
            tmp2.append(value)
        return tmp2


    def format_domain_row(self, row) :
        # used by rebuild_config
        x = row.strip().split("\n")
        y = []
        for domain in x:
            # Correct classical syntax errors
            domain = domain.strip()
            if domain.startswith("."):
                domain = "*" + domain
            if domain.endswith("."):
                domain = domain[:-1]
            if domain.startswith("*") and (not domain[1:2] == "."):
                domain = "*." + domain[1:]
            y.append(domain)
        return y

    def rebuild_config(self) :
        config2 = OrderedDict()
        for section in ["users", "rules", "proxy-rules", "ports-rules", "groups", "ports"]:
            config2[section] = OrderedDict()
        config2["version"] = self.config.get("version")

        # users store
        for row in self.users_store:
            config2["users"][row[0]] = OrderedDict()
            if row[6]:
                internet = 'filtered'
            elif row[7]:
                internet = 'open'
            else:
                internet = 'none'
            config2["users"][row[0]]['@_internet'] = internet

            for child in row.iterchildren():  # write users and macaddress
                user = child[0]
                mac = []
                if user not in self.maclist:
                    alert(_("User %s has no mac address !") % user)
                else:
                    macaddress = self.maclist[user]
                    for address in macaddress:
                        mac.append(address.lower())

                subusers = OrderedDict()

                for subchild in child.iterchildren():
                    submac = []
                    if subchild[0] in self.maclist:
                        submac = self.maclist[subchild[0]]
                        password = ""
                        if not isinstance(submac, list):            # This may happen if the subuser name and the Identifier are identical
                            submac = [submac]
                        for line in submac:
                            if line.strip() == "":
                                continue
                            if line.strip().startswith("#"):
                                continue
                            else:
                                password = line.split("#")[0]       # support inline comments
                                password = password.strip()

                        subusers[subchild[0]] = password


                config2["users"][row[0]][user] = OrderedDict()
                config2["users"][row[0]][user]["mac"] = mac
                if subusers:
                    config2["users"][row[0]][user]["subusers"] = subusers
                pass

        # dns filter rules store
        rule_stores = [
            ('rules', self.filter_store),
            ('proxy-rules', self.filter_rules.proxy_rules_store),
            ('ports-rules', self.filter_rules.port_rules_store)
        ]
        for rule_name, store in rule_stores:
            for row in store:
                name = row[0]
                for code in["<i>", "</i>", "<s>", "</s>"]:  # remove codes which are only for display
                    name = name.replace(code, "")
                config2[rule_name][name] = OrderedDict()
                config2[rule_name][name]["active"] = row[1]
                config2[rule_name][name]["action"] = row[2]
                config2[rule_name][name]["time_condition"] = row[3]
                config2[rule_name][name]["comments"] = row[4]
                config2[rule_name][name]["users"] = self.format_row(row[5])
                config2[rule_name][name]["dest_groups"] = self.format_row(row[7])
                config2[rule_name][name]["dest_domains"] = self.format_domain_row(row[8])
                config2[rule_name][name]["any_user"] = row[11]
                config2[rule_name][name]["any_destination"] = row[12]
                config2[rule_name][name]["allow_deny"] = row[13]
                config2[rule_name][name]['strict_end'] = row[20] == 1

        for row in self.firewall_store:
            config2["firewall"][row[0]] = OrderedDict()

        # groups store
        for row in self.groups_store:
            config2['groups'][row[0]] = OrderedDict()
            domains = []
            ip = []

            for line in self.format_domain_row(row[1]):
                if ip_address_test(line):
                    ip.append(line)
                else:
                    domains.append(line)

            if domains:
                config2['groups'][row[0]]['dest_domains'] = domains

            if ip:
                config2['groups'][row[0]]['dest_ip'] = ip

        # ports store
        for row in self.proxy_group.ports_store:
            config2['ports'][row[0]] = OrderedDict()
            ports = []
            for line in self.format_domain_row(row[1]):
                ports.append(line)

            config2['ports'][row[0]]['port'] = ports

        return config2

    def rebuild_config3(self) :
        config2 = OrderedDict()
        for section in ["users", "rules", "proxy-rules", "ports-rules", "groups", "ports"]:
            config2[section] = OrderedDict()
        version = self.config.get("version")
        if version == 25:
            version = 30
        config2["version"] = version
        # users store
        for row in self.users_store:
            config2["users"][row[0]] = OrderedDict()
            if row[6]:
                internet = 'filtered'
            elif row[7]:
                internet = 'open'
            else:
                internet = 'none'
            config2["users"][row[0]]['@_internet'] = internet

            for child in row.iterchildren():  # write users and macaddress
                user = child[0]
                devices = OrderedDict()
                if user not in self.maclist:
                    alert(_("User %s has no mac address !") % user)
                else:
                    devicedata = self.devicelist[user]
                    i = 1
                    for (address, devicename) in devicedata:
                        address = address.strip()
                        devicename = devicename.strip()
                        if address == "":
                            continue
                        if devicename.startswith("#"):
                            active = 0
                            address = address[1:]
                        else:
                            active = 1

                        address = address.replace("\t", "").strip()
                        devices[devicename] = OrderedDict()
                        devices[devicename]["mac"] = address.lower()
                        devices[devicename]["active"] = active
                        i += 1

                subusers = OrderedDict()

                for subchild in child.iterchildren():
                    submac = []
                    if subchild[0] in self.maclist:
                        submac = self.maclist[subchild[0]]
                        password = ""
                        if not isinstance(submac, list):            # This may happen if the subuser name and the Identifier are identical
                            submac = [submac]
                        for line in submac:
                            if line.strip() == "":
                                continue
                            if line.strip().startswith("#"):
                                continue
                            else:
                                password = line.split("#")[0]       # support inline comments
                                password = password.strip()

                        subusers[subchild[0]] = password


                config2["users"][row[0]][user] = OrderedDict()
                config2["users"][row[0]][user]["devices"] = devices
                if subusers:
                    config2["users"][row[0]][user]["subusers"] = subusers
                pass

        # dns filter rules store
        rule_stores = [
            ('rules', self.filter_store),
            ('proxy-rules', self.filter_rules.proxy_rules_store),
            ('ports-rules', self.filter_rules.port_rules_store)
        ]
        for rule_name, store in rule_stores:
            for row in store:
                name = row[0]
                for code in["<i>", "</i>", "<s>", "</s>"]:  # remove codes which are only for display
                    name = name.replace(code, "")
                name = name.replace("_", " ")           # the flask application does not support _ in names
                config2[rule_name][name] = OrderedDict()
                config2[rule_name][name]["active"] = row[1]
                if row[3] != "":
                    config2[rule_name][name]["time_condition"] = [row[3]]
                else:
                    config2[rule_name][name]["time_condition"] = []
                config2[rule_name][name]["comments"] = row[4]
                config2[rule_name][name]["users"] = self.format_row(row[5])
                config2[rule_name][name]["dest_groups"] = self.format_row(row[7])
                config2[rule_name][name]["dest_domains"] = self.format_domain_row(row[8])
                config2[rule_name][name]["any_user"] = row[11]
                config2[rule_name][name]["any_destination"] = row[12]
                config2[rule_name][name]["allow_deny"] = row[13]
                config2[rule_name][name]['strict_end'] = row[20] == 1

        for row in self.firewall_store:
            config2["firewall"][row[0]] = OrderedDict()

        # groups store
        for row in self.groups_store:
            config2['groups'][row[0]] = OrderedDict()
            domains = []
            ip = []

            for line in self.format_domain_row(row[1]):
                if ip_address_test(line):
                    ip.append(line)
                else:
                    domains.append(line)

            if domains:
                config2['groups'][row[0]]['dest_domains'] = domains

            if ip:
                config2['groups'][row[0]]['dest_ip'] = ip

        # ports store
        for row in self.proxy_group.ports_store:
            config2['ports'][row[0]] = OrderedDict()
            ports = []
            for line in self.format_domain_row(row[1]):
                ports.append(line)

            config2['ports'][row[0]]['port'] = ports

        return config2

    def ftp_upload(self, uploadlist=None, message=True, dest_name = None):
        ftp1 = self.ftp_config
        msg = ""
        OK = True
        ftp = ftp_connect(ftp1["server"], ftp1["login"], ftp1["pass"])
        if ftp is None:
            msg += _("No FTP connexion")
            return
        if uploadlist is None:
            uploadlist = ["./idefix3.json"]
        for file1 in uploadlist:
            ret = ftp_send(ftp, get_config_path(file1), dest_name=dest_name)
            if dest_name:
                out_name = dest_name
            else:
                out_name = file1
            if ret == True :
                msg += out_name + _(" sent\n")
            else :
                msg += ret
                OK = False
        ftp.close()

        if OK :
            title = "Upload OK"
        else :
            title ="ERRORS in upload"
        print(msg)

        if message:
            showwarning(title, msg, 1)


    def destroy(self, widget=None, donnees=None):
        # are the changes saved ?
        if hasattr(self, "active_config_text"):
            present_config = self.rebuild_config3()
            present_config = json.dumps(present_config, indent = 3)
            if present_config != self.active_config_text:
                open("debug1.txt", "w").write(self.active_config_text)
                open("debug2.txt", "w").write(present_config)
                dialog = Gtk.Dialog()
                dialog.set_transient_for(self.arw['window1'])
                dialog.add_button(_("Save and Quit"), Gtk.ResponseType.APPLY)
                dialog.add_button(_("Quit without saving"), Gtk.ResponseType.CANCEL)
                label = Gtk.Label(_("Data has been changed. \nDo you want to save your changes ?"))
                dialog.get_content_area().add(label)
                dialog.show_all()
                result = dialog.run()
                dialog.hide()
                if result == Gtk.ResponseType.APPLY:
                     self.build_files("")


        self.arw["window1"].destroy()
        gtk.main_quit()
        return (True)

    def update(self):
        if self.config.get("version") == None:
            self.config["version"] = 1
        elif self.config.get("version") == "2.2":
            self.config["version"] = 22
        elif self.config.get("version") == "2.3":
            self.config["version"] = 23


        config2 = deepcopy(self.config)
        #print("update called", self.config.get("version"))

        if config2["version"] < 22:

            if not "rules" in config2:
                config2["rules"] = config2["proxy"]
                del config2["proxy"]

            for rule in config2["rules"]:
                x = config2["rules"][rule]
                for key in ("user", "dest_group", "dest_domain"):
                    if key in x:
                        x[key + "s"] = x[key]
                        del x[key]
                for key in ["active", "time_condition", "comments"]:
                    if isinstance(x[key], list):
                        x[key] = x[key][0]

                if not x["active"] in ["on", "off"]:
                     x["active"] = "on"
                if not x["action"] in ["allow", "deny"]:
                     x["action"] = "allow"
                x["time_condition"] = ""
            config2["version"] = 22

        if config2["version"] < 23:
            # users
            for cat1 in config2["users"]:
                for user1 in config2["users"][cat1]:
                    if user1.startswith("@_"):
                        continue
                    if isinstance(config2["users"][cat1][user1], list):
                        macaddress = deepcopy(config2["users"][cat1][user1])    # list
                        config2["users"][cat1][user1] = OrderedDict()
                        config2["users"][cat1][user1]["mac"] = macaddress
            config2["version"] = 23


        if config2["version"] < 25:
            for group in config2["groups"]:
                x = config2["groups"][group]
                for key in ["dest_domain"]:
                    if key in x:
                        x[key + "s"] = x[key]
                        del x[key]
            config2["version"] = 25

        self.config = config2


if __name__ == "__main__":
    global win, parser, configname, load_locale

    # Get the configuration
    if len(sys.argv) > 1:  # if the config is indicated on the command line
        if len(sys.argv[1].strip()) > 0:
            configname = sys.argv[1]
    else:
        configname = ""

    password = ""

    if requires_password(configname):
        dialog = PasswordDialog()
        password = dialog.run()
        while password:
            if test_decrypt_config(configname, password):
                break
            showwarning(_("Password"), _("Entered password is incorrect"))
            password = dialog.run()

        if not password:
            showwarning(_("Cancelling"), _("No password entered, quitting"))
            sys.exit(1)

        dialog.destroy()

    win = Confix(configname, password)
    gtk.main()
