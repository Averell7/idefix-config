#!/usr/bin/env python
# coding: utf-8

# version 0.19.1  - Github

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import Gio, GLib
from gi.repository import cairo
gtk = Gtk

from collections import defaultdict, OrderedDict
import os, io, sys, time, re
from ftplib import FTP
from myconfigparser import myConfigParser

DRAG_ACTION = Gdk.DragAction.COPY

###########################################################################
# LOCALISATION ############################################################
###########################################################################
import gettext
import locale
import elib_intl3
elib_intl3.install("idefix", "share/locale")

def _(string) :
    return string


###########################################################################
# CONFIGURATION ###########################################################
###########################################################################

global ftp_active_config
ftp_active_config = "dev"




def printExcept() :
    a,b,c = sys.exc_info()
    for d in traceback.format_exception(a,b,c) :
        print(d, end=' ')

def bool_test(value) :
    if isinstance(value, str) :
        try :
            value = int(value)
        except :
            if value.strip().lower() == "true" :
                return True
            else :
                return False

    return bool(value)

def alert(message, type = 0) :

        dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING,
                                     Gtk.ButtonsType.CLOSE , message)
        dialog.run()
        dialog.destroy()

def showwarning(title, message) :
    """
      GTK_MESSAGE_INFO,
      GTK_MESSAGE_WARNING,
      GTK_MESSAGE_QUESTION,
      GTK_MESSAGE_ERROR,
      GTK_MESSAGE_OTHER
    """

    resetTransform_b = False

    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL , Gtk.MessageType.WARNING,
                                 Gtk.ButtonsType.CLOSE , title)

    dialog.format_secondary_text(message)
    if "transformWindow" in app.arw :
        app.arw["transformWindow"].set_keep_above(False)
        resetTransform_b = True
    dialog.set_keep_above(True)
    dialog.run()
    dialog.destroy()
    if resetTransform_b == True :
        app.arw["transformWindow"].set_keep_above(True)


def askyesno(title, string) :


    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL , Gtk.MessageType.QUESTION,
                               Gtk.ButtonsType.NONE, title)
    dialog.add_button(Gtk.STOCK_YES, True)
    dialog.add_button(Gtk.STOCK_NO, False)
    dialog.format_secondary_text(string)
    dialog.set_keep_above(True)
    rep = dialog.run()
    dialog.destroy()
    return rep

def ask_text(parent, message, default=''):
    """
    Display a dialog with a text entry.
    Returns the text, or None if canceled.
    """
    d = Gtk.MessageDialog(parent,
                          Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                          Gtk.MessageType.QUESTION,
                          Gtk.ButtonsType.OK_CANCEL,
                          message)
    entry = Gtk.Entry()
    entry.set_text(default)
    entry.show()
    d.vbox.pack_end(entry, True, True, 0)
    entry.connect('activate', lambda _: d.response(Gtk.ResponseType.OK))
    d.set_default_response(Gtk.ResponseType.OK)

    r = d.run()
    text = entry.get_text()
    if sys.version_info[0] == 2 :
        text = text.decode('utf8')
    d.destroy()
    if r == Gtk.ResponseType.OK:
        return text
    else:
        return None




def ftp_connect(server, login, password) :
    global ftp1

    if password[0:1] == "%" :
        hysteresis = ""
        i = 0
        for deplacement in password :
            if i % 2 == 1 :
                hysteresis += deplacement
            i += 1
        password = hysteresis

    try :
        ftp = FTP(server)     # connect to host, default port
        ftp.login(login, password)
        if "local" in ftp1 :
            ftp.cwd("idefix")
        return ftp
    except :
        print ("Unable to connect to ftp server with : %s / %s" % (login, password))


def ftp_get(ftp, filename, utime = None, required = True, basedir = "") :

    if utime :
        utime -= time.timezone
    try :
        x = ftp.sendcmd('MDTM '+ filename)          # verify that the file exists on the server
        try :
            f1 = io.BytesIO()
            ftp.retrbinary('RETR ' + filename, f1.write)     # get the file
            data1 = f1.getvalue()
            f1.close()
            return data1.decode("utf-8-sig").split("\n")
        except :
                print("could not get " + filename)
    except :
        if required :
            print("We got an error with %s. Is it present on the server?" % filename)






def ftp_send(ftp, filepath, directory = None, dest_name = None) :

    if directory :
        ftp.cwd(directory)               # change into subdirectory
    if not dest_name :
        dest_name = os.path.split(filepath)[1]

    if os.path.isfile(filepath) :
        with open(filepath,'rb') as f1 :               # file to send
            ftp.storbinary('STOR ' + dest_name, f1)     # send the file
    else :
        print(filepath + " not found")


    #print( ftp.retrlines('LIST'))
    if directory :
        ftp.cwd('..')               # return to house directory




class Idefix :

    def __init__(self):

        global cp, ftp1
        # Load the glade file
        self.widgets = gtk.Builder()
        self.widgets.add_from_file('./idefix-config.glade')
        # create an array of all objects with their name as key
        arWidgets = self.widgets.get_objects()
        self.arw = {}
        for z in arWidgets :
            try :
                name = gtk.Buildable.get_name(z)
                self.arw[name]= z
                z.name = name
            except :
                pass

        window1 = self.arw["window1"]
        window1.show_all()
        window1.set_title("Test program")
        window1.connect("destroy", self.destroy)

        #autoconnect signals for self functions
        self.widgets.connect_signals(self)

        # ftp connect
        self.idefix_config = cp.read("./idefix-config.cfg", "conf")         # $$
        ftp1 = self.idefix_config["conf"][ftp_active_config]
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])

        # retrieve common files from server
        if not "local" in ftp1 :
            ftp.cwd("common")
        data1 = ftp_get(ftp, "firewall-ports.ini")
        data2 = ftp_get(ftp, "proxy-groups.ini")
        if not "local" in ftp1 :
            ftp.cwd("..")

        # retrieve perso files from server
        data3 = ftp_get(ftp, "users.ini")
        data4 = ftp_get(ftp, "firewall-users.ini")
        data5 = ftp_get(ftp, "proxy-users.ini")

        ftp.close()

        self.config = cp.read(data3, "mac", comments = True, isdata = True)
        self.config = cp.read(data4, "firewall", merge = self.config, comments = True, isdata = True)
        self.config = cp.read(data5, "proxy", merge = self.config, comments = True, isdata = True)
        self.config = cp.read(data1, "ports", merge = self.config, comments = True, isdata = True)
        self.config = cp.read(data2, "groups", merge = self.config, comments = True, isdata = True)


        # retrieve common files from server
##        self.idefix_config = cp.read("./idefix-config.cfg", "conf")         # $$
##        ftp1 = self.idefix_config["conf"]["ftp-common"]
##        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
##        ftp.cwd("common")
##        for file1 in ["firewall-ports.ini", "proxy-groups.ini"] :
##            ftp_get(ftp, file1, basedir = "./tmp/")
##        ftp.close()




##        self.config = cp.read("./tmp/users.ini", "mac", comments = True)
##        self.config = cp.read("./tmp/firewall-users.ini", "firewall", merge = self.config, comments = True)
##        self.config = cp.read("./tmp/proxy-users.ini", "proxy", merge = self.config, comments = True)
##        self.config = cp.read("./tmp/firewall-ports.ini", "ports", merge = self.config, comments = True)
##        self.config = cp.read("./tmp/proxy-groups.ini", "groups", merge = self.config, comments = True)


        self.maclist = {}
        data1 = self.config["mac"]
        for section in data1 :
            for user in data1[section] :
                self.maclist[user] = data1[section][user]

        # delete from config["firewall"] the generated lines
        todel = []
        for key in self.config["firewall"] :
            if key[0:2] == "__" :
                todel.append(key)
        for key in todel :
            del self.config["firewall"][key]


        # Trees
        # 1 - users
        """
        0 : section (level 1)  - user (level 2)
        1 : options (text)
        2 : reserved
        3 : reserved
        4 : email (1/0)
        5 : internet access (1/0)
        6 : filtered (1/0)
        7 : open (1/0)
        8 : full (1/0)
        """
        # section / user
        self.users_store = gtk.TreeStore(str,str,str, str, int, int, int, int, int) #

        self.treeview1 = self.arw["treeview1"]
        self.treeview1.set_model(self.users_store)

        self.cell = gtk.CellRendererText()
        self.cellpb = gtk.CellRendererPixbuf()


        self.tvcolumn = gtk.TreeViewColumn(_('Filename'))
        self.treeview1.connect("button-press-event", self.load_user)

        self.tvcolumn.pack_start(self.cellpb, False)
        self.tvcolumn.pack_start(self.cell, False)
##        self.tvcolumn.add_attribute(self.cell, "cell-background", 5)
##        self.tvcolumn.add_attribute(self.cell, "foreground", 7)
##        self.tvcolumn.add_attribute(self.cell, "weight", 8)
        self.tvcolumn.add_attribute(self.cell, "text", 0)
##        self.tvcolumn.add_attribute(self.cellpb, "stock_id", 6)

        #self.tvcolumn1 = gtk.TreeViewColumn(_('Restore'), self.check, active=3)
        #self.tvcolumn2 = gtk.TreeViewColumn(_('Test'), self.test, text=3)
        #self.tvcolumn = gtk.TreeViewColumn(_('Yes'), self.cell, text=0, background=2)
        self.treeview1.append_column(self.tvcolumn)
        #self.treeview1.append_column(self.tvcolumn1)
        self.populate_users()

        # 2 - firewall
        """
        0 : section
        1 :"active",
        2 : "action",
        3 : "ports",
        4 : "time_condition",
        5 : "#comments",
        6 : "user",
        7 : "mac",
        8 :
        9 :
        10 : (int)
        11 : (int)
        12 : (int)
        13 : checkbox1   (0/1)
        14 : checkbox2   (0/1)
        15 : color1


        """

        self.firewall_store = gtk.ListStore(str,str,str, str, str, str,str,str, str, str, int, int, int, int, int, str) #
        self.cell2 = gtk.CellRendererText()

        self.check3 = gtk.CellRendererToggle(activatable = True)
        #self.check.set_property('xalign', 0.0)
        self.check3.connect( 'toggled', self.toggle_col13, self.firewall_store )
        self.check4 = gtk.CellRendererToggle(activatable = True, xalign = 0.5)
        self.check4.connect( 'toggled', self.toggle_col14, self.firewall_store )

        self.treeview2 = self.arw["treeview2"]
        self.treeview2.set_model(self.firewall_store)
        self.treeview2.connect("button-press-event", self.firewall_user)

        self.tvcolumn = gtk.TreeViewColumn(_('Key'), self.cell2, text = 0)
        #self.tvcolumn.pack_start(self.cell2, False)
        #self.tvcolumn.add_attribute(self.cell2, "text", 0)
        self.treeview2.append_column(self.tvcolumn)

        self.tvcolumn = gtk.TreeViewColumn(_('Accept/Drop'), self.check3, active = 13)
        self.treeview2.append_column(self.tvcolumn)

        self.tvcolumn = gtk.TreeViewColumn(_('On/Off'), self.check4, active = 14)
        self.treeview2.append_column(self.tvcolumn)

##        self.tvcolumn = gtk.TreeViewColumn(_('Value'), self.check )
##        #self.tvcolumn.pack_start(self.check, False)
##        #self.tvcolumn.add_attribute(self.check, "text", 1)
##        self.treeview2.append_column(self.tvcolumn)
##        # self.tvcolumn1 = gtk.TreeViewColumn(_('Restore'), self.check, active=3)


        # 3 - proxy
        """
        0 : section
        1 : active
        2 : action
        3 : time_condition
        4 : #comments
        5 : user
        6 : mac
        7 : dest_group
        8 : dest_domain
        9 : dest_ip
        10 : ""
        11 : ""
        12 : ""
        13 : checkbox1   (0/1)
        14 : checkbox2   (0/1)
        15 : color1
        16 : color2
        """
        self.proxy_store = gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, str, str, int, int, str, str) #
        self.cell3 = gtk.CellRendererText()
        self.check1 = gtk.CellRendererToggle(activatable = True)
        self.check1.connect( 'toggled', self.toggle_col13, self.proxy_store )
        self.check2 = gtk.CellRendererToggle(activatable = True, xalign = 0.5)
        self.check2.connect( 'toggled', self.toggle_col14, self.proxy_store )


        self.treeview3 = self.arw["treeview3"]
        self.treeview3.set_model(self.proxy_store)
        self.treeview3.connect("button-press-event", self.proxy_user)


        self.tvcolumn = gtk.TreeViewColumn(_('Key'), self.cell3, text = 0, foreground = 15)
        self.treeview3.append_column(self.tvcolumn)

        self.tvcolumn = gtk.TreeViewColumn(_('Allow/deny'), self.check1, active = 13)
        self.treeview3.append_column(self.tvcolumn)

        self.tvcolumn = gtk.TreeViewColumn(_('On/Off'), self.check2, active = 14)
        self.treeview3.append_column(self.tvcolumn)

        # chooser

        self.tvcolumn = gtk.TreeViewColumn(_('---'), self.cell, text = 0)
        self.arw["chooser"].append_column(self.tvcolumn)
        sel = self.arw["chooser"].get_selection()
        ## sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.tvcolumn = gtk.TreeViewColumn(_('---'), self.cell, text = 0)
        self.arw["chooser2"].append_column(self.tvcolumn)
        sel = self.arw["chooser2"].get_selection()
        ## sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.ports_store = gtk.ListStore(str) #
        self.groups_store = gtk.ListStore(str) #

        self.empty_store = gtk.ListStore(str) #

##        self.arw["proxy_group"].drag_dest_add_text_targets()
##        self.arw["proxy_group"].drag_dest_set(Gtk.DestDefaults.ALL, [], DRAG_ACTION)
##        self.arw["proxy_group"].connect("drag-data-received", self.on_drag_data_received)

        for chooser in["chooser", "chooser2"] :

            self.arw[chooser].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [],
                DRAG_ACTION)
            self.arw[chooser].drag_source_add_text_targets()
            self.arw[chooser].connect("drag-data-get", self.chooser_drag_data_get)


        self.populate_firewall()
        self.populate_proxy()
        self.populate_ports()
        self.populate_groups()
        self.set_check_boxes()
        self.set_colors()



    def __________load_interface____________ () :
        pass


    def format_list(self, listtext, prefix) :
        # add a key (example : "user = ") at the beginning of each line of a text
        if len(listtext.strip()) == 0 :
            return ""
        temp1 = listtext.split("\n")
        data1 = ""
        for line1 in temp1 :
            data1 += prefix + line1 + "\n"
        return data1

    def populate_users(self):
        self.users_store.clear()
        data1 = self.config["mac"]
        options = ["", "", "", "", "email", "internet access", "filtered", "open", "full"]
        for section in data1 :
            if "option" in data1[section] :
                options_list = []
                for i in [4,5,6,7,8] :
                    if options[i] in data1[section]["option"] :
                        options_list.append(1)
                    else :
                        options_list.append(0)
            else :
                options_list = [0,0,0,0,0]
            node = self.users_store.append(None, [section, "", "", ""] + options_list)
            for user in data1[section] :
                if user in ["option"] :
                    continue
                else :
                    node2 = self.users_store.append(node, [user, "", "", "", 0, 0, 0, 0, 0])

    def populate_firewall(self):
        self.firewall_store.clear()
        data1 = self.config["firewall"]
        keys = ["active", "action", "ports", "time_condition", "#comments", "user", "mac"]
        for section in data1 :
            data2 = [section]
            for key in keys :
                if key in data1[section] :
                    data2.append("\n".join(data1[section][key]))
                else :
                    data2.append("")
            data2 += ["", "",1, 1, 1]   # reserved
            data2 += [1, 1, "#009900"]  # check boxes dans colors
            node = self.firewall_store.append(data2)


    def populate_proxy(self):
        self.proxy_store.clear()
        data1 = self.config["proxy"]
        keys = ["active", "action", "time_condition", "#comments", "user", "xxx", "dest_group", "dest_domain", "xxx", "destination", "", ""]
        for section in data1 :
            out = [section]
            data2 = data1[section]
            # merge user and mac
            if not "user" in data2 :
                if "mac" in data2 :
                    data2["user"] = data2["mac"]
            else :
                if "mac" in data2 :
                    data2["user"] += data2["mac"]
            # merge dest_domain and dest_ip
            if not "dest_domain" in data2 :
                if "dest_ip" in data2 :
                    data2["dest_domain"] = data2["dest_ip"]
            else :
                if "dest_ip" in data2 :
                    data2["dest_domain"] += data2["dest_ip"]



            for key in keys :
                if key in data1[section] :
                    out.append("\n".join(data1[section][key]))
                else :
                    out.append("")
            # check boxes
            out += [1,1,"#009900", ""]

            node = self.proxy_store.append(out)

    def populate_ports(self) :
        self.ports_store.clear()
        data1 = self.config["ports"]
        for key in data1 :
            self.ports_store.append([key])

    def populate_groups(self) :
        self.groups_store.clear()
        data1 = self.config["groups"]
        for key in data1 :
            self.groups_store.append([key])



    def set_check_boxes(self) :
        for row in self.proxy_store :
            if row[1].strip().lower() == "off" :
                row[14] = 0
            if row[2].strip().lower() == "deny" :
                row[13] = 0

    def set_colors(self) :
        # col 13 = allow/deny state; col 15 = text color
        # col 14 = on/off state; col 15 = text color
        for row in self.proxy_store :
            if row[13] == 1 :
                row[15] = "#009900"
            else :
                row[15] = "#ff0000"

            if row[14] == 0 :
                row[15] = "#aaaaaa"


    def load_user(self, widget, event) :
        # loads data in right pane when a category or a user is selected in the tree
        pos = widget.get_path_at_pos(event.x, event.y)
        if pos == None :    # click outside a valid line
            return
        iter1 = self.users_store.get_iter(pos[0])
        self.iter_user = iter1
        if pos == None :
            return
        level =  pos[0].get_depth()


##        (model, node) = self.arw["treeview1"].get_selection().get_selected()


        if level == 1 :         # category level
            self.arw["notebook5"].set_current_page(0)

            # set internet rights in the check boxes and radio list
            self.arw["internet_email"].set_active(self.users_store[iter1][4])
            self.arw["internet_access"].set_active(self.users_store[iter1][5])
            self.arw["internet_filtered"].set_active(self.users_store[iter1][6])
            self.arw["internet_open"].set_active(self.users_store[iter1][7])
            self.arw["internet_full"].set_active(self.users_store[iter1][8])
          # TODO :          self.arw["internet_email"].set_active(True)


        elif level == 2 :         # user level
            self.arw["notebook5"].set_current_page(2)

            username = self.users_store[iter1][0]
            buffer = self.arw["maclist"].get_buffer()
            if username in self.maclist :
                data1 = "\n".join(self.maclist[username])
                buffer.set_text(data1)
            else :
                buffer.set_text("")
                alert("No mac address for this user !")
            self.user_summary(username)

            # get data in lists for this user


    def firewall_user(self, widget, event) :
        # Loads user data when a user is selected in the list
        path = widget.get_path_at_pos(event.x, event.y)
        iter1 = self.firewall_store.get_iter(path[0])
        self.iter_firewall = iter1

        keys = ["section", "active", "action", "ports", "time_condition", "#comments"]
        for i in [2, 4, 5] :
            self.arw["entry_" + keys[i]].set_text(self.firewall_store[iter1][i])

        # add ports
        data1 = self.format_list(self.firewall_store[iter1][3], "") # dest_group
        self.arw["firewall_ports"].get_buffer().set_text(data1)

        # add users
        data1 = self.format_list(self.firewall_store[iter1][6], "")
        # add mac, if any
        data1 += self.format_list(self.firewall_store[iter1][7], "")
        buffer = self.arw["firewall_users"].get_buffer()
        buffer.set_text(data1)


    def proxy_user(self, widget, event) :
        # Loads user data when a user is selected in the list
        path = widget.get_path_at_pos(event.x, event.y)
        if path == None :
            return
        iter1 = self.proxy_store.get_iter(path[0])
        self.iter_proxy =iter1
        data1 = ""
        self.arw["proxy_time_condition"].set_text(self.proxy_store[iter1][3])
        self.arw["proxy_#comments"].get_buffer().set_text(self.proxy_store[iter1][4])

        # add users
        data1 = self.format_list(self.proxy_store[iter1][5], "")  # user
        # add mac, if any
        data1 += self.format_list(self.proxy_store[iter1][6], "")  # mac
        buffer = self.arw["proxy_users"].get_buffer()
        buffer.set_text(data1)

        # add groups
        data1 = self.format_list(self.proxy_store[iter1][7], "") # dest_group
        self.arw["proxy_group"].get_buffer().set_text(data1)
        # add dest_domains
        data1 = self.format_list(self.proxy_store[iter1][8], "") # dest_domain
        # add dest_ip, if any
        data1 += self.format_list(self.proxy_store[iter1][9], "") # dest_ip
        self.arw["proxy_dest"].get_buffer().set_text(data1)

        # set full access
        self.arw["proxy_full_access"].set_active(False)
        self.arw["paned2"].set_sensitive(True)
        if self.proxy_store[iter1][10] == "any" :
            self.arw["proxy_full_access"].set_active(True)
            self.arw["paned2"].set_sensitive(False)

    def _____________actions_______________() :
        pass

    def toggle_col13(self, cellrenderer, row, treestore) :
        # callback of the allow/deny checkbox in proxy tab.
        # col 13 = allow/deny state; col 15 = text color
        if treestore[row][13] == 0 :
            treestore[row][13] = 1
            treestore[row][2] = "allow"
            treestore[row][15] = "#009900"
        else :
            treestore[row][13] = 0
            treestore[row][2] = "deny"
            treestore[row][15] = "#ff0000"

    def toggle_col14(self, cellrenderer, row, treestore) :
        # callback of the on/off checkbox in proxy tab.
        # col 14 = on/off state; col 15 = text color
        if treestore[row][14] == 0 :
            treestore[row][14] = 1
            treestore[row][1] = "on"
            if treestore[row][13] == 1:
                treestore[row][15] = "#009900"
            else :
                treestore[row][15] = "#ff0000"
        else :
            treestore[row][14] = 0
            treestore[row][1] = "off"
            treestore[row][15] = "#aaaaaa"

    def update_tv(self, widget, event) :

        TextBuffer = widget.get_buffer()
        (start_iter, end_iter) = TextBuffer.get_bounds()
        text = TextBuffer.get_text(start_iter, end_iter, False)

        if widget.name == "proxy_group" :
            self.proxy_store.set(self.iter_proxy, 7, text)
        elif widget.name == "proxy_dest" :
            self.proxy_store.set(self.iter_proxy, 8, text)
        elif widget.name == "proxy_users" :
            self.proxy_store.set(self.iter_proxy, 5, text)

        elif widget.name == "firewall_ports" :
            self.firewall_store.set(self.iter_firewall, 3, text)
        elif widget.name == "firewall_users" :
            self.firewall_store.set(self.iter_firewall, 6, text)

        elif widget.name == "maclist" :
            mac_addresses = text.split("\n")           # create list
            # get usr name
            (model, node) = self.arw["treeview1"].get_selection().get_selected()
            name = model.get_value(node,0)
            self.maclist[name] = mac_addresses


    def update_check(self, widget) :
        # proxy
        if widget.name == "proxy_full_access" :
            if widget.get_active() == True :
                self.proxy_store[self.iter_proxy][10] = "any"
                self.arw["paned2"].set_sensitive(False)
            else :
                self.proxy_store[self.iter_proxy][10] = ""
                self.arw["paned2"].set_sensitive(True)
        # users
        elif widget.name == "internet_email" :
            if widget.get_active() == True :
                self.users_store[self.iter_user][4] = 1
            else :
                self.users_store[self.iter_user][4] = 0
        elif widget.name == "internet_access" :
            if widget.get_active() == True :
                self.users_store[self.iter_user][5] = 1
                self.arw["box_internet"].show()
            else :
                self.users_store[self.iter_user][5] = 0
                self.arw["box_internet"].hide()
        elif widget.name == "internet_filtered" :
            if widget.get_active() == True :
                self.users_store[self.iter_user][6] = 1
            else :
                self.users_store[self.iter_user][6] = 0

        elif widget.name == "internet_open" :
            if widget.get_active() == True :
                self.users_store[self.iter_user][7] = 1
            else :
                self.users_store[self.iter_user][7] = 0
        elif widget.name == "internet_full" :
            if widget.get_active() == True :
                self.users_store[self.iter_user][8] = 1
            else :
                self.users_store[self.iter_user][8] = 0


    def rappel_toggled_col2(self, a, b, c) :
        return

    def rappel_toggled_col3(self, a, b, c) :
        return

    def test1(self, widget, a = "") :
        print ("test1", repr(a))

    def load_chooser(self, widget, event = None, data = None) :

        if data == None :  # cela sert-il à quelque chose ???

            if widget.name in [ "proxy_users"] :
                self.arw["chooser"].set_model(self.users_store)
            elif widget.name == "firewall_users":
                self.arw["chooser2"].set_model(self.users_store)
            elif widget.name in [ "proxy_group"] :
                self.arw["chooser"].set_model(self.groups_store)
            elif widget.name in [ "firewall_ports"] :
                self.arw["chooser2"].set_model(self.ports_store)

            else :
                self.arw["chooser"].set_model(self.empty_store)
                self.arw["chooser2"].set_model(self.empty_store)
        else :
            print("===>", repr(data))





    def general_chooser_answer(self, *params) :

        widget = self.chooser_widget_source
        widget_type = magutils.widget_type(widget)

        if widget_type == "GtkEntry" :
            response = get_sel_row_data(self.arw["treeview8"], 0, 0)
            widget.set_text(response)

            temp1 = widget.name.split("@")
            category_s = temp1[0]
            field_s = temp1[1]

            if category_s in ["central", "peripheral"] :
                configuration = self.database_structure_active[1]
                self.config[category_s][configuration][field_s] = response
                self.load_database_tree()

            elif category_s == "xtabs" :
                configuration = self.search_active
                self.config["xtabs"][configuration][field_s] = response

            elif category_s == "inversion" :
                configuration = self.inversion_active
                self.config["inversion"][configuration][field_s] = response

            elif category_s == "combobox" :
                configuration = self.combobox_active
                self.config["combobox"][configuration][field_s] = response

            elif category_s == "details" :
                configuration = self.details_active
                self.config["details"][configuration][field_s] = response

            elif category_s == "popup" :
                configuration = self.popup_active
                self.config["popup"][configuration][field_s] = response


        elif widget_type == "GtkTreeView" :
            if widget.name == "treeview6" :     # Search lists
                (row,col,treeview) = self.search_edit_cell
                response = get_sel_row_data(self.arw["treeview8"], 0, 0)
                self.edit_list_search("",row,response,col, treeview)

            elif widget.name == "treeview5" :       # Result lists
                (row,col,treeview) = self.search_edit_cell
                response = get_sel_row_data(self.arw["treeview8"], 0, 0)
                self.edit_list_search("",row,response,col, treeview)

    def ________________user_management________________________() :
        pass

    def add_user_above(self) :
        # not implemented
        pass
    def manage_users(self, widget, dummy = "") :
        # not implemented
        pass

    def add_user_below(self, widget) :
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        x = ask_text(self.arw["window1"], "Name of the new user :", "")
        if x == None :
            return
        else :
            self.users_store.insert_after(None, node, [x, "", "", "", 0, 0, 0, 0, 0])

    def delete_user(self, widget) :
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        self.users_store.remove(node)

    def edit_user(self, widget) :
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        name = model.get_value(node,0)
        x = ask_text(self.arw["window1"], "Name of the user :", name)
        if x == None :
            return
        else :
            self.users_store.set(node, [0], [x])

    def add_user_below2(self, widget) :
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        x = ask_text(self.arw["window1"], "Name of the new user :", "")
        if x == None :
            return
        else :
            self.proxy_store.insert_after(node, [x, "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, "", "" ])

    def delete_user2(self, widget) :
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        self.proxy_store.remove(node)

    def edit_user2(self, widget) :
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        name = model.get_value(node,0)
        x = ask_text(self.arw["window1"], "Name of the user :", name)
        if x == None :
            return
        else :
            self.proxy_store.set(node, [0], [x])



    def add_user_below3(self, widget) :
        (model, node) = self.arw["treeview2"].get_selection().get_selected()
        x = ask_text(self.arw["window1"], "Name of the new user :", "")
        if x == None :
            return
        else :
            self.firewall_store.insert_after(node, [x, "", "", "", "", "", "", "", "", "", 0, 0])

    def delete_user3(self, widget) :
        (model, node) = self.arw["treeview2"].get_selection().get_selected()
        self.firewall_store.remove(node)

    def edit_user3(self, widget) :
        (model, node) = self.arw["treeview2"].get_selection().get_selected()
        name = model.get_value(node,0)
        x = ask_text(self.arw["window1"], "Name of the user :", name)
        if x == None :
            return
        else :
            self.firewall_store.set(node, [0], [x])


    def check_addresses(self, widget) :
        print("check_addresses not yet implemented")


    def ________________user_summary________________________() :
        pass


    def user_summary(self, user1) :

        if not user1 in self.maclist :
            out = "User %s has no mac address !" % user1
        else :
            out = "Mac address(es) for user %s : \n" % user1
            out += "\n".join(self.maclist[user1])

        out += "\nAccès Internet : \n"

        for row in self.users_store :
            mem = "\n[%s]\n" % row[0]      # section
            # write options
            options = ["", "", "", "", "email", "internet access", "filtered", "open", "full"]
            for i in [4,5,6,7,8] :
                if row[i] == 1 :
                    mem += "option = " + options[i] + "\n"
            for child in row.iterchildren() :     # write users and macaddress
                user = child[0]
                if user1 == user :
                    out += mem + "\n\n"
                    mem = ""



##        for row in self.proxy_store :
##            out += "\n[%s]\n" % row[0]
##            out += self.format_line("", row[4])      # comments
##            out += self.format_line("active", row[1])
##            out += self.format_line("action", row[2])
##            out += self.format_line("time_condition", row[3])
##            out += self.format_userline("user", row[5])
##            out += self.format_line("dest_group", row[7])
##            out += self.format_line("destination", row[10])
##            out += self.format_domainline("dest_domain", row[8])

        self.arw["user_summary"].get_buffer().set_text(out)



    def ________________drag_and_drop________________________() :
        pass

    def chooser_drag_data_get(self, treeview, drag_context , data, info, time) :

        (model, node) = treeview.get_selection().get_selected()
        if node :
            text = model.get_value(node,0) + "\n"
            data.set_text(text, -1)

    def on_drag_data_received(self, widget, drag_context, x,y, data,info, time):
            text = data.get_text()
            print("Received text: %s" % text)

    def ______________output____________() :
        pass

    def format_line(self, key, line1) :
        text = ""
        if key != "" :
            key += " = "
        for value in line1.split("\n") :
            if value.strip() != "" :
                text += key + value + "\n"
        return text

    def format_userline(self, dummy, line1) :
        # separate domains and ips
        text = ""
        for value in line1.split("\n") :
            if value.strip() != "" :
                if len(re.findall("[:]", value)) == 5 :  # five : means this is a mac address
                    # TODO  check that the mac address is valid
                    key = "mac"
                else : key = "user"
                text += key + " = " + value + "\n"
        return text


    def format_domainline(self, dummy, line1) :
        # separate domains and ips
        text = ""
        for value in line1.split("\n") :
            if value.strip() != "" :
                if len(re.findall("[a-zA-Z]", value)) == 0 :  # no alphabetical characters, it is an IP address
                    # TODO  check that the ip address is valid
                    key = "dest_ip"
                else : key = "dest_domain"
                text += key + " = " + value + "\n"
        return text

    def format_directive(self, list1) :
        out = "action = " + list1[0] + "\n"
        for line in list1[1:] :
            out += "ports = " + line + "\n"
        return out + "\n"


    def build_files (self, widget) :
        # launched by the GO button
        self.build_users()
        self.build_proxy_ini()
        self.build_firewall_ini()
        self.ftp_upload()


    def build_users(self) :
        out = ""
        for row in self.users_store :
            out += "\n[%s]\n" % row[0]      # section
            # write options
            options = ["", "", "", "", "email", "internet access", "filtered", "open", "full"]
            for i in [4,5,6,7,8] :
                if row[i] == 1 :
                    out += "option = " + options[i] + "\n"
            for child in row.iterchildren() :     # write users and macaddress
                user = child[0]
                if not user in self.maclist :
                    alert("User %s has no mac address !" % user)
                else :
                    macaddress = self.maclist[user]
                    for address in macaddress :
                        out += user + " = " + address + "\n"

        with open("./tmp/users.ini", "w", encoding = "utf-8-sig") as f1 :
            f1.write(out)



    def build_proxy_ini (self) :

        out = ""
        for row in self.proxy_store :
            out += "\n[%s]\n" % row[0]
            out += self.format_line("", row[4])      # comments
            out += self.format_line("active", row[1])
            out += self.format_line("action", row[2])
            out += self.format_line("time_condition", row[3])
            out += self.format_userline("user", row[5])
            out += self.format_line("dest_group", row[7])
            out += self.format_line("destination", row[10])
            out += self.format_domainline("dest_domain", row[8])


        with open("./tmp/proxy-users.ini", "w", encoding = "utf-8-sig") as f1 :
            f1.write(out)


    def build_firewall_ini (self) :
        out = ""
        #"active", "action", "ports", "time_condition", "#comments", "user", "mac"

        for row in self.firewall_store :
            tmp1 = ""
            tmp1 += "\n[%s]\n" % row[0]
            tmp1 += self.format_line("#comments", row[5])
            tmp1 += self.format_line("active", row[1])
            tmp1 += self.format_line("action", row[2])
            tmp1 += self.format_line("ports", row[3])
            tmp1 += self.format_line("time_condition", row[4])
            tmp1 += self.format_line("user", row[6])
            tmp1 += self.format_line("mac", row[7])
            #print(tmp1)
            out += tmp1

        out2 = ""       # data from the users tree
        """
        0 : section (level 1)  - user (level 2)
        1 : options (text) (no longer used)
        2 : reserved
        3 : reserved
        4 : email (1/0)
        5 : internet access (1/0)
        6 : filtered (1/0)
        7 : open (1/0)
        8 : full (1/0)
        """
        for row in self.users_store :
            #print(row[0], row[1], row[2])
            out2 += "\n[__%s]\n" % row[0]
            # set the command lines for the categories
            option = row[1].split("|")

            myoptions = ["ACCEPT"]
            if row[4] == 1 :
                myoptions.append("email")
            if row[5] == 1 :
                if row[6] == 1:
                    myoptions.append("ftp")
                elif row[7] == 1:
                    myoptions.append("http")
                    if not "email" in myoptions :
                        myoptions.append("email")
                elif row[8] == 1:
                    myoptions.append("any")

            if len(myoptions) > 1 :
                out2 += self.format_directive(myoptions)
            else :
                out2 += self.format_directive(["DROP", "any"])

            for b in row.iterchildren() :
                out2 += "user = " + b[0] +"\n"

        with open("./tmp/firewall-users.ini", "w", encoding = "utf-8-sig") as f1 :
            f1.write(out2)
            f1.write("\n#####################################\n")
            f1.write(out)


    def ftp_upload(self) :
        ftp1 = self.idefix_config["conf"][ftp_active_config]
        ftp = ftp_connect(ftp1["server"][0], ftp1["login"][0], ftp1["pass"][0])
        for file1 in ["./tmp/users.ini", "./tmp/firewall-users.ini", "./tmp/proxy-users.ini"] :
            ftp_send(ftp, file1)
            print(file1, "envoyé")
        ftp.close()

        # TODO : message to indicate upload was successful
        print("Upload OK")


    def destroy(self, widget=None, donnees=None):
        print ("Évènement destroy survenu.")
        gtk.main_quit()
        return(True)


if __name__ == "__main__":
    global win, cp, conf
    cp = myConfigParser()
    win = Idefix()
    gtk.main()
