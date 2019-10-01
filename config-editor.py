#!/usr/bin/env python
# coding: utf-8

# version 0.1.0


import glob
import io
import json
import os
import sys
import time
from copy import deepcopy
from collections import OrderedDict
from ftplib import FTP, all_errors as FTPError

import gi

from groups_manager import GroupManager

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from myconfigparser import myConfigParser
#from actions import DRAG_ACTION
from util import (
    AskForConfig, alert, showwarning, askyesno,
    EMPTY_STORE, SignalHandler, get_config_path, write_default_config,
    ip_address_test
)
#from icons import (
#    internet_full_icon, internet_filtered_icon, internet_denied_icon,
#    internet_timed_icon, email_icon, email_timed_icon
#)
#from proxy_users import ProxyUsers
#from proxy_group import ProxyGroup
#from firewall import Firewall
#from users import Users
from config_profile import ConfigProfile
#from assistant import Assistant
from json_config import ImportJsonDialog, ExportJsonDialog

###########################################################################
# CONFIGURATION ###########################################################
###########################################################################
global version
version = "0.1.0"

def ftp_connect(server, login, password):
    global ftp1

    if password[0:1] == "%":
        hysteresis = ""
        i = 0
        for deplacement in password:
            if i % 2 == 1:
                hysteresis += deplacement
            i += 1
        password = hysteresis

    try:
        ftp = FTP(server, timeout=15)  # connect to host, default port
        ftp.login(login, password)
        if ftp1['mode'][0] == 'local':
                ftp.cwd("idefix")
        return ftp
    except FTPError as e:
        print("Unable to connect to ftp server with : %s / %s. \nError: %s" % (login, password, e))



def ftp_get(ftp, filename, directory="", required=True, json=False):
    if not ftp:
        print(_("No ftp connection"))
        return False

    # verify that the file exists on the server
    try:
        x = ftp.mlsd(directory)
        if not filename in ([n[0] for n in x]):
            if required:
                print(_("We got an error with %s. Is it present on the server?" % filename))
            return False
    except:
        if not filename in ftp.nlst(directory):  # deprecated, but vsftpd does non support mlsd (used in idefix.py)
            if required:
                print(_("We got an error with %s. Is it present on the server?" % filename))
            return False


    try:
        f1 = io.BytesIO()
        ftp.retrbinary('RETR ' + filename, f1.write)  # get the file
        data1 = f1.getvalue()
        f1.close()
        print(filename, _("received OK."))
        if json :           # returns string
            return data1.decode("ascii")
        else :              # returns list
            return data1.decode("utf-8-sig").split("\n")
    except FTPError:
        print(_("could not get ") + filename)


def ftp_send(ftp, filepath, directory=None, dest_name=None):
    if directory:
        ftp.cwd(directory)  # change into subdirectory
    if not dest_name:
        dest_name = os.path.split(filepath)[1]

    if os.path.isfile(get_config_path(filepath)):
        with open(get_config_path(filepath), 'rb') as f1:  # file to send
            ftp.storbinary('STOR ' + dest_name, f1)  # send the file
    else:
        message = filepath + " not found"
        print(message)
        return message

    # print( ftp.retrlines('LIST'))
    if directory:
        ftp.cwd('..')  # return to house directory
    return True


def get_row(treestore, iter1):
    row = []
    for i in range(treestore.get_n_columns()):
        row.append(treestore.get_value(iter1, i))
    return row




class editor:
    def __init__(self, configname = "", config_password = None):

        self.load_locale = False

        #data_str = open("./new-idefix.json", "r").read()
        #data_str = open("./toto", "r").read()
        #self.config = json.loads(data_str, object_pairs_hook=OrderedDict)

        # Load the glade file
        self.widgets = Gtk.Builder()
        self.widgets.set_translation_domain("confix")
        self.widgets.add_from_file('./config-editor.glade')
        # create an array of all objects with their name as key
        ar_widgets = self.widgets.get_objects()
        self.arw = {}
        for z in ar_widgets:
            try:
                name = Gtk.Buildable.get_name(z)
                self.arw[name] = z
                z.name = name
            except:
                pass
        self.widgets.connect_signals(self)

        window1 = self.arw["window1"]
        window1.show_all()
        window1.set_title("Json Editor")
        window1.connect("destroy", self.destroy)


        if config_password:
            kargs = {'password': config_password}
        else:
            kargs = {}
        self.profiles = ConfigProfile(self.arw, self, **kargs)
        self.idefix_config = self.profiles.config

        # load configuration
        if configname == "":                            # No connexion profile chosen
            self.ftp_config = None
        else:
            self.ftp_config = self.idefix_config['conf'][configname]
            ftp = self.open_connexion_profile()
        self.arw["configname"].set_text(configname)



        if self.load_locale:         # development environment
            self.arw['loading_window'].hide()
            if os.path.isfile(get_config_path("dev\idefix.json")):
                data_str = open(get_config_path("dev\idefix.json"), "r").read()
                try:
                    self.config = json.loads(data_str, object_pairs_hook=OrderedDict)
                    self.update()
                except:
                    alert("Unable to load configuration. Please import another one.")

        # config tree
        self.model = Gtk.TreeStore(str, str);
        view = self.arw['treeview1']
        #view.set_size_request(400, 620);
        cell_renderer = Gtk.CellRendererText();
        view.append_column(Gtk.TreeViewColumn('Tree', cell_renderer, text=0));
        view.append_column(Gtk.TreeViewColumn('Values', cell_renderer, text=1));
        view.set_model(self.model);

        # unbound config tree
        self.unbound_model = Gtk.TreeStore(str, str);
        view = self.arw['unbound_tree']
        #view.set_size_request(400, 620);
        cell_renderer = Gtk.CellRendererText();
        view.append_column(Gtk.TreeViewColumn('Tree', cell_renderer, text=0));
        view.append_column(Gtk.TreeViewColumn('Values', cell_renderer, text=1));
        view.set_model(self.unbound_model);


        #self.populate_tree(self.config, self.model )


    def destroy(self, widget=None, donnees=None):
        print("Évènement destroy survenu.")
        Gtk.main_quit()
        return (True)


    def ask_for_profile(self, widget = None):
        config_dialog = AskForConfig(idefix_config)
        configname = config_dialog.run()
        self.arw["configname"].set_text(configname)
        self.ftp_config = self.idefix_config['conf'][configname]
        if not idefix_config['conf'].get('__options'):
            idefix_config['conf']['__options'] = {}
        idefix_config['conf']['__options']["last_config"] = configname
        parser.write(idefix_config['conf'], get_config_path('confix.cfg'))

        self.open_connexion_profile()


    def open_connexion_profile(self):
        global ftp1

        ftp1 = self.ftp_config
        if ftp1['mode'][0] == 'dev':          # development mode - no ftp connection
            self.load_locale = True
            config_file = get_config_path("dev/idefix.json")
            if os.path.isfile(config_file):
                with open(config_file) as f1:
                    self.config = json.loads(f1.read(), object_pairs_hook=OrderedDict)
                    self.update()
                    self.update_gui()
            else:
                self.load_defaults()

            return

        # ftp connect
        if ftp1['mode'][0] == 'local':
            self.local_control = True

        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])


        if not ftp:

            if askyesno(_("Update Configuration"), _("Could not connect to FTP. Edit Configuration?")):
                self.profiles.profile_open_window()

                def restart(*args):
                    askyesno(_("Restart"), _("Please restart idefix to use new configuration"))
                    sys.exit(0)

                self.profiles.window.connect('hide', restart)
                print("restart system")
                self.profiles.list_configuration_profiles()
                return
            else:
                return
        else:
            # retrieve files by ftp
            data0 = ftp_get(ftp, "idefix.json", json  = True)
            data1 = ftp_get(ftp, "unbound.json", json  = True)

            if data0 :
                try:
                    self.config = json.loads(data0, object_pairs_hook=OrderedDict)
                    self.populate_tree(self.config, self.model)
                except:
                    alert("Unable to load configuration. Please import another one.")
            if data1 :
                try:
                    self.config2 = json.loads(data1, object_pairs_hook=OrderedDict)
                    self.populate_tree(self.config2, self.unbound_model)
                except:
                    pass   # non critical

            ftp.close()


    def populate_tree(self, dict1, model) :
        # This function displays a dictionary in a Treeview. It may be used to display
        # a directory tree, but non only
        dir_list = []
        i = 0

        dir_list.append([dict1, None]); #// stores the directory list as queue
        nodes = {};
        nodes[0] = None
        model.clear()

        while(len(dir_list)>0) :
            (dict1, node) = dir_list.pop(0) #// get the first entry in queue
            #//echo "folder = $dir\n";
            i += 1
            for key in dict1:
                val = dict1[key]
                if isinstance(val, dict) or isinstance(val, OrderedDict) : #// is it a dictionary?
                    newnode = model.append(node, [key,""]);
                    dir_list.append([val, newnode]);  #// yes, queue it in the dir list
                else :

                    val = repr(val)

                    newnode = model.append(node, [key,val])


    def show_selected(self, widget, *args) :

        global selected_path
        sel = widget.get_selection()
        model, iter1 = sel.get_selected()
        self.selected_iter = iter1
        if not iter1:
            return
        key1 = model.get_value(iter1,0)
        val1 = model.get_value(iter1,1)
        try:
            val2 = eval(val1)
        except:
            val2 = val1

        if isinstance(val2, list) :
            val3 = "\n".join(val2)
            self.arw["textview1"].get_buffer().set_text(val3)
            self.datatype = "list"
        else :
            self.arw["textview1"].get_buffer().set_text(str(val1))
            self.datatype = "string"


    def open_config(self, widget):
        self.file_filter = Gtk.FileFilter()
        self.file_filter.add_pattern('*.json')
        dialog = Gtk.FileChooserDialog(
            _("Import Config"),
            self.arw['window1'],
            Gtk.FileChooserAction.OPEN,
            (_("Import"), Gtk.ResponseType.ACCEPT),
        )
        dialog.set_filter(self.file_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.config = json.load(
                open(dialog.get_filename(), 'r'),
                object_pairs_hook=OrderedDict
            )
        self.populate_tree(self.config, self.model)
        dialog.destroy()

    def save_config(self, widget) :

        out = OrderedDict()
        for row in self.model:
            if row.iterchildren():
                out[row[0]] =OrderedDict()
                self.walk_model(row, out[row[0]])

        with open("toto", "w") as f1:
            f1.write(json.dumps(out, indent = 3))



    def walk_model(self, row, level):
        for child in row.iterchildren():
            xx = child.iterchildren()

            if child.iterchildren():
                if child[1] != "":
                    try:
                        val = eval(child[1])
                    except:
                        val = child[1]
                    level[child[0]] = val
                else :
                    level[child[0]] = OrderedDict()
                    self.walk_model(child, level[child[0]])

    def update_tv(self, text_view, event=None, a=None, b=None, c=None, text=""):
        text_buffer = text_view.get_buffer()
        (start_iter, end_iter) = text_buffer.get_bounds()
        text1 = text_buffer.get_text(start_iter, end_iter, False)
        if self.datatype == "list":
            ext1 = repr(text1.split("\n"))
        self.model.set(self.selected_iter, 1, text1)

    def find_string(self,*args) :
        string_s = self.arw["find_entry"].get_text().strip()
        message = find_in_dict(self.config,string_s)
        buf1 = self.arw['find_TV'].get_buffer()
        buf1.set_text(message)




class Confix:
    cat_list = {}
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
        self.local_control = False  # will be set to True if the connection with Idefix is direct
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
        self.export_json = ExportJsonDialog(self.arw, self)

        self.arw["program_title"].set_text("Confix - Version " + version)
        window1 = self.arw["window1"]
        window1.show_all()
        window1.set_title(_("Confix"))
        window1.connect("destroy", self.destroy)

        window2 = self.arw2["assistant1"]

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

        # get the style from the css file and apply it
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path('./data/confix.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_USER)

        # autoconnect signals for self functions
        self.proxy_users = ProxyUsers(self.arw, self)
        self.proxy_group = ProxyGroup(self.arw, self)
        self.firewall = Firewall(self.arw, self)
        self.users = Users(self.arw, self)
        self.assistant = Assistant(self.arw, self.arw2, self)

        if config_password:
            kargs = {'password': config_password}
        else:
            kargs = {}
        self.profiles = ConfigProfile(self.arw, self, **kargs)
        self.idefix_config = self.profiles.config
        # à garder $$ self.ftp_config = self.idefix_config['conf'][active_config]

        self.users_store = self.users.users_store
        self.filter_store = self.proxy_users.filter_store
        self.groups_store = self.proxy_group.groups_store
        self.firewall_store = self.firewall.firewall_store

        self.signal_handler = SignalHandler([
            self, self.proxy_users, self.proxy_group, self.firewall, self.users, self.profiles, self.assistant
        ])
        self.widgets.connect_signals(self.signal_handler)
        self.widgets2.connect_signals(self.signal_handler)

        # autosave textview buffers when typing (see also drag and drop below)
        # and when drag is received
        for textView in ["maclist",
                         "proxy_dest", "proxy_#comments",
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
            self.ftp_config = self.idefix_config['conf'][configname]
            ftp = self.open_connexion_profile()
        self.arw["configname"].set_text(configname)



        if self.load_locale:         # development environment
            self.arw['loading_window'].hide()
            if os.path.isfile(get_config_path("dev\idefix.json")):
                data_str = open(get_config_path("dev\idefix.json"), "r").read()
                try:
                    self.config = json.loads(data_str, object_pairs_hook=OrderedDict)
                    self.update()
                except:
                    alert("Unable to load configuration. Please import another one.")


        for category in ["firewall", "rules", "ports", "groups"]:
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

        self.tvcolumn = gtk.TreeViewColumn(_('Groups Drag and Drop'), self.users.cell, text=0)
        self.arw["chooser"].append_column(self.tvcolumn)
        self.arw["chooser"].get_selection()
        self.chooser_sort = Gtk.TreeModelSort.sort_new_with_model(self.groups_store)
        self.chooser_sort.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.arw["chooser"].set_model(self.chooser_sort)
        # sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.tvcolumn = gtk.TreeViewColumn(_('Users Drag and Drop'), self.users.cell, text=0)
        self.arw["chooser1"].append_column(self.tvcolumn)
        self.arw["chooser1"].get_selection()
        self.arw["chooser1"].set_model(self.chooser_users_store)
        # sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.tvcolumn = gtk.TreeViewColumn(_('Firewall'), self.users.cell, text=0)
        self.arw["chooser2"].append_column(self.tvcolumn)
        self.arw["chooser2"].get_selection()
        # sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.ports_store = gtk.ListStore(str)  #
        self.empty_store = EMPTY_STORE

        for chooser in ["chooser", "chooser1", "chooser2"]:
            self.arw[chooser].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [],
                                                       DRAG_ACTION)
            self.arw[chooser].drag_source_add_text_targets()
            self.arw[chooser].connect("drag-data-get", self.chooser_drag_data_get)

        # list of inifiles

        self.inifiles_store = gtk.ListStore(str, str)
        self.tvcolumn = gtk.TreeViewColumn(_('---'), self.users.cell, text=0)
        self.arw["inifiles_list"].append_column(self.tvcolumn)
        self.arw["inifiles_list"].connect("button-press-event", self.load_file)
        self.arw["inifiles_list"].set_model(self.inifiles_store)

        # drop for TextView
        # see above, the line : self.arw["proxy_group"].connect("drag-data-received", self.on_drag_data_received)

        # icons for users list

        self.maclist = self.users.create_maclist()
        self.users.populate_users()
        self.proxy_users.populate_proxy()
        self.populate_ports()
        self.populate_groups()
        self.populate_users_chooser()
        self.firewall.populate_firewall()
        self.set_check_boxes()
        self.set_colors()
        self.load_ini_files()
        self.profiles.list_configuration_profiles()
        self.load_chooser("")
        self.assistant.disable_simulated_user()     # In case the previous user has not disabled simulation before shutting down


        # user defined options
        checkbox_config = idefix_config['conf'].get('__options', {}).get('checkbox_config', [0])[0] == '1'
        if checkbox_config:
            self.proxy_users.set_gui('check')

        filter_tab = idefix_config['conf'].get('__options', {}).get('filter_tab', [0])[0] == '1'
        if filter_tab:
            self.arw['notebook3'].set_current_page(1)

        auto_load = idefix_config['conf'].get('__options', {}).get('auto_load', [0])[0] == '1'
        if auto_load:
            last_config = idefix_config['conf'].get('__options', {}).get('last_config')
            if last_config:
                configname = last_config[0]
                if configname:
                    self.ftp_config = self.idefix_config['conf'][configname]
                    self.open_connexion_profile()
                    self.arw["configname"].set_text(configname)

    def ask_for_profile(self, widget = None):
        config_dialog = AskForConfig(idefix_config)
        configname = config_dialog.run()
        self.arw["configname"].set_text(configname)
        self.ftp_config = self.idefix_config['conf'][configname]
        if not idefix_config['conf'].get('__options'):
            idefix_config['conf']['__options'] = {}
        idefix_config['conf']['__options']["last_config"] = configname
        parser.write(idefix_config['conf'], get_config_path('confix.cfg'))

        self.open_connexion_profile()


    def open_connexion_profile(self):
        global ftp1

        ftp1 = self.ftp_config
        if ftp1['mode'][0] == 'dev':          # development mode - no ftp connection
            self.load_locale = True
            config_file = get_config_path("dev/idefix.json")
            if os.path.isfile(config_file):
                with open(config_file) as f1:
                    self.config = json.loads(f1.read(), object_pairs_hook=OrderedDict)
                    self.update()
                    self.update_gui()
            else:
                self.load_defaults()

            return

        # ftp connect
        if ftp1['mode'][0] == 'local':
            self.local_control = True

        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])


        if not ftp:
            # x = ConfigProfile(self.arw, self)
            # x.profile_open_window()

            if askyesno(_("Update Configuration"), _("Could not connect to FTP. Edit Configuration?")):
                self.profiles.profile_open_window()

                def restart(*args):
                    askyesno(_("Restart"), _("Please restart idefix to use new configuration"))
                    sys.exit(0)

                self.profiles.window.connect('hide', restart)
                print("restart system")
                self.profiles.list_configuration_profiles()
                return
            else:
                return
        else:
            # retrieve files by ftp
            data0 = ftp_get(ftp, "idefix.json", json  = True)
            if data0 == False:                                               # TODO - compatibility
                data0 = ftp_get(ftp, "idefix-config.json", json  = True)
            if data0 :
                try:
                    self.config = json.loads(data0, object_pairs_hook=OrderedDict)
                    self.update()
                    self.update_gui()
                except:
                    alert("Unable to load configuration. Please import another one.")
                ftp.close()
                self.update_gui()

        self.update()

    def update_gui(self):
        self.maclist = self.users.create_maclist()
        self.users.populate_users()
        self.proxy_users.populate_proxy()
        #self.populate_ports()
        self.populate_groups()
        self.populate_users_chooser()
        #self.firewall.populate_firewall()
        self.set_check_boxes()
        self.set_colors()

    def load_defaults(self, widget = None):
        response = askyesno(_("No user data"),
                            _("There is no user data present. \nDo you want to create standard categories ?"))
        if response == 1:
            if os.path.isfile("./confix-default.json"):
                data_str = open("./confix-default.json", "r").read()
                self.config = json.loads(data_str, object_pairs_hook=OrderedDict)
                self.update_gui()
                self.set_colors()




    def open_config(self, widget):
        self.import_json.run()

    def save_config(self, widget):
        self.export_json.run()

    def show_help(self, widget):
        self.arw2["help_window"].show()

    def hide_help(self, widget):
        self.arw2["help_window"].hide()

    def show_manage_groups(self, widget):
        self.groups_manager.show()

    def show_filter_helper(self, widget):
        self.arw["system_window"].show()

    def show_about(self, widget):
        self.arw["about_window"].show()

    def import_ini_files(self):
        # This function is presently unused

        if not self.load_locale:
            print("WARNING ! unable to get idefix.json.\n Loading ini files")

            # retrieve common files by ftp
            if ftp1['mode'][0] != 'local':
                ftp.cwd("common")
            data1 = ftp_get(ftp, "firewall-ports.ini")
            data2 = ftp_get(ftp, "proxy-groups.ini")
            if ftp1['mode'][0] != 'local':
                ftp.cwd("..")

            # make a local copy for debug purpose
            f1 = open(get_config_path("./tmp/firewall-ports.ini"), "w", encoding="utf-8-sig")
            f1.write("\n".join(data1))
            f1.close()
            f1 = open(get_config_path("./tmp/proxy-groups.ini"), "w", encoding="utf-8-sig")
            f1.write("\n".join(data2))
            f1.close()

            # retrieve perso files by ftp
            data3 = ftp_get(ftp, "users.ini")
            data4 = ftp_get(ftp, "firewall-users.ini")
            data5 = ftp_get(ftp, "proxy-users.ini")

            ftp.close()

            if data1 is None:
                print("WARNING ! unable to get firewall-ports.ini.")
            if data2 is None:
                print("WARNING ! unable to get proxy-groups.ini.")
            if data3 is None:
                print("WARNING ! unable to get users.ini.")
            if data4 is None:
                print("WARNING ! unable to get users.ini.")
            if data5 is None:
                print("WARNING ! unable to get proxy-users.ini.")

            self.config = parser.read(data3, "users", comments=True, isdata=True)
            self.config = parser.read(data4, "firewall", merge=self.config, comments=True, isdata=True)
            self.config = parser.read(data5, "rules", merge=self.config, comments=True, isdata=True)
            self.config = parser.read(data1, "ports", merge=self.config, comments=True, isdata=True)
            self.config = parser.read(data2, "groups", merge=self.config, comments=True, isdata=True)
        else:

            self.config = parser.read(
                get_config_path("./tmp/users.ini"), "users", merge=self.config, comments=True
            )
            self.config = parser.read(
                get_config_path("./tmp/firewall-users.ini"), "firewall", merge=self.config, comments=True
            )
            self.config = parser.read(
                get_config_path("./tmp/proxy-users.ini"), "rules", merge=self.config, comments=True
            )
            self.config = parser.read(
                get_config_path("./tmp/firewall-ports.ini"), "ports", merge=self.config, comments=True
            )
            self.config = parser.read(
                get_config_path("./tmp/proxy-groups.ini"), "groups", merge=self.config, comments=True
            )



    """ Load interface """

    def populate_ports(self):
        self.ports_store.clear()
        data1 = self.config["ports"]
        for key in data1:
            self.ports_store.append([key])

    def populate_groups(self):
        self.groups_store.clear()
        data1 = self.config["groups"]
        for key in data1:
            tooltip = "\n".join(data1[key].get('dest_domain', ''))
            if data1[key].get('dest_ip', ''):
                if tooltip:
                    tooltip += '\n'
                tooltip += "\n".join(data1[key].get('dest_ip', ''))
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
            if row[10].strip().lower() == "any":
                row[12] = 1
            else:
                row[12] = 0

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
        for store in [self.filter_store, self.firewall_store]:
            for row in store:
                if row[13] == 1:  # allow
                    row[15] = "#009900"  # green
                else:  # deny
                    row[15] = "#ff0000"  # red

                if row[14] == 0:  # off
                    row[15] = "#bbbbbb"  # grey

                if row[12] == 1:  # any
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

            if row[3]:
                row[12] = internet_timed_icon
            elif not row[5]:
                row[12] = internet_denied_icon

            elif row[7]:
                row[12] = internet_full_icon
            elif row[6]:
                row[12] = internet_filtered_icon
            else:
                row[12] = None

##            if row[4]:
##                if row[2]:
##                    row[11] = email_timed_icon
##                else:
##                    row[11] = email_icon
##            else:
##                row[11] = None

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

        if widget.name == "proxy_dest":
            self.filter_store.set(self.iter_filter, 8, text1)
        elif widget.name == "proxy_#comments":
            self.filter_store.set(self.iter_filter, 4, text1)

        elif widget.name == "firewall_ports":
            self.firewall_store.set(self.iter_firewall, 3, text1)
        elif widget.name == "firewall_users":
            self.firewall_store.set(self.iter_firewall, 6, text1)
        elif widget.name == "firewall_comments":
            self.firewall_store.set(self.iter_firewall, 5, text1)

        elif widget.name == "maclist":
            mac_addresses = text1.split("\n")  # create list
            # get usr name
            (model, node) = self.arw["treeview1"].get_selection().get_selected()
            name = model.get_value(node, 0)
            self.maclist[name] = mac_addresses

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
##        elif widget.name == "internet_access":
##            if widget.get_active():
##                self.users_store[self.iter_user][5] = 1
##                if self.arw["internet_filtered"].get_active():
##                    self.users_store[self.iter_user][6] = 1
##                else:
##                    self.users_store[self.iter_user][6] = 0
##                if self.arw["internet_open"].get_active():
##                    self.users_store[self.iter_user][7] = 1
##                    self.arw["internet_email"].set_active(True)
##                else:
##                    self.users_store[self.iter_user][7] = 0
##            else:
##                self.users_store[self.iter_user][5] = 0

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

        self.set_colors()
        self.populate_users_chooser()

        # Update the time conditions frames
##        self.arw['email_time_condition'].set_sensitive(
##            self.users_store[self.iter_user][4] or self.users_store[self.iter_user][7]
##            )
##        self.arw['internet_time_condition'].set_sensitive(self.users_store[self.iter_user][7])

    def update_time(self, widget, x=None):
        # TODO  this function is not very well written.
        if widget.name in ["proxy_time_condition_days", "proxy_time_condition_from", "proxy_time_condition_to"]:
            time_condition = self.arw["proxy_time_condition_days"].get_text() + " "
            if time_condition.strip() == "":
                time_condition = "1234567 "
            time_condition += self.arw["proxy_time_condition_from"].get_text().strip() + "-"
            time_condition += self.arw["proxy_time_condition_to"].get_text().strip()
            if time_condition == "1234567 -":
                time_condition = ""
            self.filter_store[self.iter_filter][3] = time_condition

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


    def load_chooser(self, widget, event=None):          # TODO no longer used
        for scroll in ['proxy_users_scroll_window', 'chooser1_frame'] :
            ctx = self.arw[scroll].get_style_context()
            ctx.add_class('chosen_list1')

        for scroll in ['proxy_group_scroll_window', 'chooser_frame'] :
            ctx = self.arw[scroll].get_style_context()
            ctx.add_class('chosen_list')

        return

        if widget.name in ["filter_users"]:
            self.active_chooser = 'filter_users'
            self.arw["chooser"].set_model(self.chooser_users_store)
            ctx = self.arw['proxy_users_scroll_window'].get_style_context()
            ctx.add_class('chosen_list')

            ctx = self.arw['proxy_group_scroll_window'].get_style_context()
            ctx.remove_class('chosen_list')
        elif widget.name == "firewall_users":
            self.arw["chooser2"].set_model(self.users_store)
        elif widget.name in ["proxy_group"]:
            self.active_chooser = 'proxy_group'
            self.arw["chooser"].set_model(self.groups_store)
            ctx = self.arw['proxy_group_scroll_window'].get_style_context()
            ctx.add_class('chosen_list')

            ctx = self.arw['proxy_users_scroll_window'].get_style_context()
            ctx.remove_class('chosen_list')
        elif widget.name in ["firewall_ports"]:
            self.arw["chooser2"].set_model(self.ports_store)

        else:
            self.arw["chooser"].set_model(self.empty_store)
            self.arw["chooser2"].set_model(self.empty_store)
            self.active_chooser = None

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
        gui_check = self.arw['option_checkbox_gui_check'].get_active()
        filter_tab = self.arw['option_filter_tab_check'].get_active()
        auto_load = self.arw['option_autoload_check'].get_active()

        idefix_config['conf']['__options'] = {
            'checkbox_config': ['1' if gui_check else '0'],
            'filter_tab': ['1' if filter_tab else '0'],
            'auto_load': ['1' if auto_load else '0'],
        }

        if gui_check:
            self.proxy_users.set_gui('check')
        else:
            self.proxy_users.set_gui('buttons')

        # Save to config
        parser.write(idefix_config['conf'], get_config_path('confix.cfg'))
        self.arw['options_window'].hide()

    def show_options(self, widget):
        # Get options
        self.arw['option_checkbox_gui_check'].set_active(
            idefix_config['conf'].get('__options', {}).get('checkbox_config', [0])[0] == '1'
        )
        self.arw['option_filter_tab_check'].set_active(
            idefix_config['conf'].get('__options', {}).get('filter_tab', [0])[0] == '1'
        )
        self.arw['option_autoload_check'].set_active(
            idefix_config['conf'].get('__options', {}).get('auto_load', [0])[0] == '1'
        )
        self.arw['options_window'].show_all()

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

    def load_ini_files(self):
        for path in glob.glob(get_config_path("./tmp/") + "*.ini"):
            filename = os.path.split(path)[1]
            self.inifiles_store.append([filename, path])
        #self.load_log_files()

    def load_log_files(self) :
        ftp1 = self.ftp_config
        if ftp1['mode'][0] == 'local':
            ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        ftp.cwd("..")
        ftp.cwd("..")
        ftp.cwd("..")
        ftp.cwd("var")
        ftp.cwd("log")
        f1 = open(get_config_path("./tmp/syslog"), "wb")
        filename = "syslog"
        ftp.retrbinary('RETR ' + filename, f1.write)  # get the file
        self.inifiles_store.append([filename, get_config_path("./tmp/syslog")])

        ftp.cwd("squid")
        self.f1 = open(get_config_path("./tmp/squid.log"), "w")
        filename = "access.log"
        ftp.retrlines('RETR ' + filename, self.filter_squid_log)  # get the file
        self.inifiles_store.append([filename, get_config_path("./tmp/squid.log")])
        self.f1.close()

    def filter_squid_log(self, line1):
        urlfilter = ["cloudfront.net", "agkn.net", "avast", "avcdn", "googleapis.com",
             "mozilla.org", "microsoft.com", "google.fr", "google.com", "youtube.com"]

        for url in urlfilter :
            if url in line1 :
               return

        line1 = line1.split()
        time1 = time.localtime(int(float(line1[0])))
        time1 = time.strftime("%a %d, %H:%M:%S", time1)

        self.f1.write(chr(9).join([time1, line1[2], line1[3], line1[6]]) + "\n")

    def load_file(self, widget, event):
        pos = widget.get_path_at_pos(event.x, event.y)
        if pos is None:  # click outside a valid line
            return
        iter1 = self.inifiles_store.get_iter(pos[0])
        path = self.inifiles_store[iter1][1]
        f1 = open(get_config_path(path), "r", encoding="utf-8-sig")
        text = f1.read()
        f1.close()
        self.arw["inifiles_view"].get_buffer().set_text(text)

    """ Output """

    def build_files(self, widget):
        # launched by the GO button
        self.rebuild_config()
        self.build_users()
        self.proxy_users.build_proxy_ini()
        self.proxy_users.build_proxy_groups_ini()
        #self.firewall.build_firewall_ini()
        self.build_unbound()

        f1 = open(get_config_path("idefix.json"), "w")
        config2 = self.rebuild_config()
        f1.write(json.dumps(config2, indent = 3))
        f1.close()

        if not self.load_locale:  # send the files by FTP. Load_locale is the development mode, where files are read and written only on the local disk
            self.ftp_upload()
        else:
            f1 = open(get_config_path("dev/idefix.json"), "w")
            f1.write(json.dumps(config2, indent = 3))
            f1.close()

        if self.local_control:  # if connected to Idefix, send the update signal
            f1 = open(get_config_path("./tmp/update"), "w")
            f1.close()
            self.ftp_upload([get_config_path("./tmp/update")], message=False)

    def build_users(self):
        out = ""
        check_duplicates = {}
        for row in self.users_store:
            out += "\n[%s]\n" % row[0]  # section

            # write users and macaddress

            for child in row.iterchildren():
                user = child[0]
                if user not in self.maclist:
                    alert("User %s has no mac address !" % user)
                else:
                    macaddress = self.maclist[user]
                    for address in macaddress:
                        if address.strip() == "":     # empty line
                            continue
                        if address.startswith("-@"):
                            continue
                        elif address.startswith("+@"):
                            address = address[2:]
                            print(address)
                        if address in check_duplicates:
                            message = _("WARNING ! address %s is used by %s and %s. Please, correct.") % (address, user, check_duplicates[address])
                            alert (message)
                        out += user + " = " + address + "\n"
                        check_duplicates[address] = user

        with open(get_config_path("./tmp/users.ini"), "w", encoding="utf-8-sig", newline="\n") as f1:
            f1.write(out)

    def build_unbound(self):
        config1 = deepcopy(self.config)

        def extract_data3 (data1) :
            # cette fonction extrait d'une liste les données utiles en éliminant les commentaires et renvoie la liste nettoyée
            # elle traite aussi les données additionnelles
            list1 = []
            additional = False
            for line1 in data1 :
                if isinstance(line1, OrderedDict):        # Additional data is given for this user
                    additional = line1
                else :
                    line1 = line1.split("#")[0]         # on élimine tout ce qui se trouve à partir du #
                    if line1.strip() == "":
                        continue
                    list1.append(line1.strip())         # on constitue la liste

            if additional:
                if"subusers" in additional:
                    data1 = additional["subusers"]
                    mac_data = {}
                    mac_data["_default"] = list1
                    for subuser in data1:
                        mac_data[data1[subuser][0]] = subuser
                    print(mac_data)
                    return mac_data

            return list1

        # create mac-user table
        mac_user = {}
        for cat in self.config["users"]:
          for username in self.config["users"][cat]:
            if username.startswith("@_"):
                continue
            data1 = extract_data3(self.config["users"][cat][username])
            if isinstance(data1, dict):       # sub-users present
                usernames = { "default" : username}
                for user1 in data1:
                    if user1 == "_default":
                        maclist = data1[user1]
                    else :
                        usernames[user1] = data1[user1]
            else :
                maclist = data1
                usernames = username

            for mac in maclist:
                mac = mac.lower()
                if len(mac) < 17:  # invalid mac address
                    continue
                mac_user[mac] = usernames
        del config1["users"]
        config1["mac_user"] = mac_user

        # walk rules
        for key in config1["rules"]:
            rule = config1["rules"][key]
            expanded_groups = []

            if rule.get("active") == "off":
                continue
            # time conditions
            if rule["time_condition"].strip() != "":
                print(rule["time_condition"])
                (week, hours) = rule["time_condition"].split()
                rule["time_condition"] = {}
                rule["time_condition"]["week"] = week
                (f,t) = hours.split("-")
                f = f.replace(":", "")
                t = t.replace(":", "")
                rule["time_condition"]["from"] = int(f)
                rule["time_condition"]["to"] = int(t)
            if rule.get("destination") == ["any"]:
                rule["domains_tree"] = {"*" : {}}
                continue
            # expand groups in a single list, and merge it with dest_domain and det_ip
            if rule["dest_domains"] != ['']:
                expanded_groups += rule["dest_domains"]
            if rule["dest_groups"] != ['']:
                for group in rule["dest_groups"]:
                    expanded_groups += self.config["groups"][group].get("dest_domains")
                    # TODO ajouter les IP


            # convert the domains list in a tree, which first level contains the extensions (com, net, fr, etc.)
            #                                     the second level contains the domains (google, microsoft, etc.)
            #                                     the third level, the subdomain, and so on.
            # When a domain begins with a dot (.), the last level will be "*"
            expanded_groups = extract_data3(expanded_groups)     # clean comments
            domains_tree = {}
            for domain in expanded_groups:
                if domain.startswith("."):
                    domain = "*" + domain
                data1 = domain.split(".")
                data1.reverse()

                base = domains_tree
                for i in range(len(data1)):
                    level = data1[i]
                    if not level in base:
                        base[level] = {}
                    base = base[level]

            rule["domains_tree"] = domains_tree
            rule["dest_domains"] = expanded_groups
            for section in ["dest_ip", "dest_groups", "dest_domains"]:
                if section in rule:
                    del rule[section]

        with open(get_config_path("./unbound-idefix.json"), "w") as f1:
            f1.write(json.dumps(config1, indent = 3))

    def format_row(self, row) :
        # used by rebuild_config
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
            if domain.startswith("."):
                domain = "*" + domain
            y.append(domain)
        return y

    def rebuild_config(self) :
        config2 = OrderedDict()
        for section in ["users", "rules", "groups"] :
            config2[section] = OrderedDict()
        #config2["ports"] = self.config["ports"]

        # users store
        for row in self.users_store :
            config2["users"][row[0]] = OrderedDict()
            if row[6]:
                internet = 'filtered'
            elif row[7]:
                internet = 'open'
            else:
                internet = 'none'
            config2["users"][row[0]]['@_internet'] = internet
            #config2["users"][row[0]]['@_email'] = [str(row[4])]         # TODO str should not be necessary.
            #config2["users"][row[0]]['@_email_time_condition'] = [row[2]]
            #config2["users"][row[0]]['@_internet_time_condition'] = [row[3]]

            for child in row.iterchildren():  # write users and macaddress
                user = child[0]
                mac = []
                if user not in self.maclist:
                    alert(_("User %s has no mac address !") % user)
                else:
                    macaddress = self.maclist[user]
                    for address in macaddress:
                        mac.append(address)

                subusers = {}

                for subchild in child.iterchildren():
                    submac = []
                    if subchild[0] in self.maclist:
                        submac = self.maclist[subchild[0]]
                    subusers[subchild[0]] = submac

                if subusers:
                    mac.append({'subusers': subusers})

                config2["users"][row[0]][user] = mac

        # proxy store
        for row in self.filter_store :
            name = row[0]
            for code in["<i>", "</i>", "<s>", "</s>"]:  # remove codes which are only for display
                name = name.replace(code, "")
            config2["rules"][name] = OrderedDict()
            config2["rules"][name]["active"] = row[1]
            config2["rules"][name]["action"] = row[2]
            config2["rules"][name]["time_condition"] = row[3]
            config2["rules"][name]["comments"] = row[4]
            config2["rules"][name]["user"] = self.format_row(row[5])
            config2["rules"][name]["destination"] = self.format_row(row[10])
            config2["rules"][name]["dest_group"] = self.format_row(row[7])
            config2["rules"][name]["dest_domain"] = self.format_domain_row(row[8])
            config2["rules"][name]["any_user"] = row[11]
            config2["rules"][name]["any_destination"] = row[12]
            config2["rules"][name]["allow_deny"] = row[13]

        for row in self.firewall_store:
            config2["firewall"][row[0]] = OrderedDict()

        # groups store
        for row in self.groups_store:
            config2['groups'][row[0]] = {}
            domains = []
            ip = []

            for line in self.format_domain_row(row[1]):
                if ip_address_test(line):
                    ip.append(line)
                else:
                    domains.append(line)

            if domains:
                config2['groups'][row[0]]['dest_domain'] = domains

            if ip:
                config2['groups'][row[0]]['dest_ip'] = ip

        return config2

    def ftp_upload(self, uploadlist=None, message=True):
        ftp1 = self.ftp_config
        msg = ""
        OK = True
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        if ftp is None:
            msg += _("No FTP connexion")
            return
        if uploadlist is None:
            uploadlist = [
                                "./idefix.json", "./unbound-idefix.json"
            ]
        for file1 in uploadlist:
            ret = ftp_send(ftp, get_config_path(file1))
            if ret == True :
                msg += file1 + _(" sent\n")
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
        print("Évènement destroy survenu.")
        gtk.main_quit()
        return (True)


    def update(self):

        config2 = deepcopy(self.config)
        if not "rules" in config2:
            config2["rules"] = config2["proxy"]
            del config2["proxy"]

        for rule in config2["rules"]:
            x = config2["rules"][rule]
            for key in ("user", "dest_group", "dest_domain"):
                if key in x:
                    x[key + "s"] = x[key]
                    del x[key]
            for key in ["active", "action", "time_condition", "comments"]:
                if isinstance(x[key], list):
                    x[key] = x[key][0]

        for group in config2["groups"]:
            x = config2["groups"][group]
            for key in ["dest_domain"]:
                if key in x:
                    x[key + "s"] = x[key]
                    del x[key]

        f1 = open("new-idefix.json", "w")
        f1.write(json.dumps(config2, indent = 3))
        f1.close()
        self.config = config2




if __name__ == "__main__":
    global win, parser, configname, load_locale

    parser = myConfigParser()
    idefix_config = parser.read(get_config_path('confix.cfg'), "conf")

    if not idefix_config:
        # Try write the default configuration
        path = write_default_config()
        idefix_config = parser.read(path, "conf")
        configname = 'default'

    # Get the configuration
    if len(sys.argv) > 1:  # if the config is indicated on the command line
        if len(sys.argv[1].strip()) > 0:
            configname = sys.argv[1]
    else:
        configname = ""
##    else:  # ask for config
##        config_dialog = AskForConfig(idefix_config)
##        configname = config_dialog.run()
##        #if not configname:
##        #    sys.exit()


    #dialog = PasswordDialog()
    #password = dialog.run()
    password = ""

    win = editor(configname, password)
    Gtk.main()
