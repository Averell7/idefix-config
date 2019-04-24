import time

from gi.repository import Gdk, Gtk

from myconfigparser import myConfigParser,myTextParser
from util import askyesno, ask_text, mac_address_test, showwarning
import re


class Assistant:
    mem_time = 0
    editing_iter = None

    def __init__(self, arw2, controller):
        self.arw2 = arw2
        self.controller = controller
        self.block_signals = False
        self.arw2["assistant1"].set_forward_page_func(self.forward_func)
        # open file with long texts for the assistant
        parser = myTextParser()
        self.longtexts = parser.read("./assistant-texts.txt")
        # load texts in the interface
        # labels
        for label in ["assistant_user_page1"]:
            label1 = label + ".fr"
            if label1 in self.longtexts:
                self.arw2[label].set_text(self.longtexts[label1])


        # Listview
        self.categories_store = Gtk.ListStore(str,Gtk.TreeIter,str,int)
        self.arw2["assistant_categories"].set_model(self.categories_store)

        self.cell = Gtk.CellRendererText()
        self.radio = Gtk.CellRendererToggle(activatable=True, radio = True, xalign=0.5)
        self.radio.connect('toggled', self.categories_radio_toggle)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell, text=0, foreground=15, background=16)
        self.tvcolumn.set_fixed_width(220)
        self.arw2["assistant_categories"].append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('---'), self.radio, active=3)
        self.arw2["assistant_categories"].append_column(self.tvcolumn)


        # Listview
        self.arw2["assistant_proxy_rules"].set_model(self.controller.proxy_users.proxy_store)

        self.cell = Gtk.CellRendererText()
        self.check = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check.connect('toggled', self.choose_rules)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell, text=0, foreground=15, background=16)
        self.tvcolumn.set_fixed_width(220)
        self.arw2["assistant_proxy_rules"].append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('---'), self.check, active=19)
        self.arw2["assistant_proxy_rules"].append_column(self.tvcolumn)
        self.arw2["assistant_proxy_rules"].hide()




    def show_assistant(self, widget = None):
        self.arw2["assistant1"].show()
        self.arw2["assistant1"].set_keep_above(True)

    def cancel (self, widget, a = None):
        self.arw2["assistant1"].hide()

    def forward_func(self, page):
        """ manage the page flow, depending of the choices made by the user """
        if page == 0 :       # useful for development, to go easily to the developped page
            return page + 1
        elif (  page == 2    # if no proxy rules are necessary
                and self.arw2["check_filter"].get_active() == 0
             ):
            return 4   # summary page
        elif ( page == 3     # if a rule specific for this user is choosed, skip existent rules page
               and self.arw2["radio_specific_rule"].get_active() == 1
              ):
            return 4  # summary page
        else:
            return page + 1

    def assistant_check_nothing(self, widget):
        self.block_signals = True
        if self.arw2["check_nothing"].get_active() == 1:
            for check in ["email", "filter", "full"]:
                self.arw2["check_" + check].set_active(False)
                self.arw2["check_" + check].set_sensitive(False)
        else:
            for check in ["email", "filter", "full"]:
                self.arw2["check_" + check].set_sensitive(True)
        self.block_signals = False

    def assistant_check_filter(self, widget):
        if self.block_signals:
            return
        if self.arw2["check_filter"].get_active() == 1:
            self.arw2["check_full"].set_active(False)

    def assistant_check_full(self, widget):
        if self.block_signals:
            return
        if self.arw2["check_full"].get_active() == 1:
            self.arw2["check_filter"].set_active(False)
            self.arw2["check_email"].set_active(True)



    def ass_new_user(self, widget, a = None):
        self.arw2["assistant1"].set_page_complete(self.arw2["new_user"], True)

    def ass_firewall_permissions(self, widget, event = None):
        self.arw2["assistant1"].set_page_complete(self.arw2["firewall_permissions"], True)
        self.update_categories_list()

    def update_categories_list(self,widget = None):
        """ updates the list of categories which correspond to the choices for email, web etc. """
        self.categories_store.clear()
        email = self.arw2["check_email"].get_active()
        webfilter = self.arw2["check_filter"].get_active()
        webfull = self.arw2["check_full"].get_active()
        if webfilter or webfull:
            web = True
        else:
            web = False

        # get category
        for row in self.controller.users_store:
            if (row[4] == email
                and row[5] == web
                and row[6] == webfilter
                and row[7] == webfull):
                iter1 = row.iter
                path1 = row.path.to_string()
                name = row[0]
                iternew = self.categories_store.append()
                self.categories_store.set_value(iternew,0,name)
                self.categories_store.set_value(iternew,2,path1)
                self.categories_store.set_value(iternew,3,0)
        try:
            self.categories_store[0][3] = 1
        except:
            pass

    def categories_radio_toggle(self, widget, row):
        """ controls the toggle buttons column """
        for row1 in self.categories_store:
            row1[3] = 0
        self.categories_store[row][3] = 1

    def ass_new_user_rules(self, widget, event = None):
        # activated when the user changes the radio buttons of the page 4 of the assistant
        self.arw2["assistant1"].set_page_complete(self.arw2["proxy_rules"], True)
        # hide the list, if useless
        if self.arw2["radio_specific_rule"].get_active():
            self.arw2["assistant_proxy_rules"].hide()
        else:
            self.arw2["assistant_proxy_rules"].show()

    def get_mac_address(self):
        mac = []
        for index in["A", "B", "C", "D", "E", "F"]:
            value = self.arw2["mac_" + index].get_text().lower()
            x = re.search("[0-9a-f]{2}", value)
            if not x:
                showwarning(_("Error"), _("Invalid Mac address, please correct and retry"))
                return False

            mac.append(value)
        mac = ":".join(mac)
        return mac

    def reset_mac_address(self):
        for index in["A", "B", "C", "D", "E", "F"]:
            self.arw2["mac_" + index].set_text("")


    def check_mac_address(self, widget, a = None):
        mac = self.get_mac_address()
        x = mac_address_test(mac)
        print(x)

    def add_address(self, widget = None):
        address = self.get_mac_address()
        if address:
            self.reset_mac_address()
            self.arw2["new_user_mac"].get_buffer().insert_at_cursor(address + "\n")


    def choose_rules(self, widget, row):
        """ controls the toggle buttons column """
        self.controller.proxy_store[row][19] = not self.controller.proxy_store[row][19]

    def summary(self, widget):
        username = self.arw2["new_user_entry"].get_text()
        mac_address = self.get_mac_address()



        # TODO : create category if needed
        """
        0 : section (level 1)  - user (level 2)
        1 : options (text)    TODO : probably no longer used, verify
        2 : email time condition
        3 : internet time condition
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
        # create user
        # get the selected category
        for row1 in self.categories_store:
            if row1[3] == 1:
                category = row1[0]
                print(category)
                path1 = row1[2]
                print(path1)
                break
        iter1 = self.controller.users_store.get_iter_from_string(path1)
        iternew = self.controller.users_store.insert(iter1, 1,
                        [username, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])
        self.controller.maclist[username] = [mac_address]
        self.controller.set_colors()

        if self.arw2["check_filter"].get_active() == 0:
            sel = self.controller.arw["treeview1"].get_selection()
            sel.select_iter(iter1)
            self.controller.arw["notebook3"].set_current_page(0)
            self.arw2["assistant1"].hide()
            return


        # Proxy config
        if self.arw2["radio_specific_rule"].get_active() == 1:
            # create rule
            iter1 = self.controller.proxy_store.insert(-1,
                        [username, "on", "allow", "", "", username, "", "", "", "", "", 0, 0, 1, 1, "#009900", "#ffffff", "", "", 0, 0])
            # select rule
            sel = self.controller.arw["treeview3"].get_selection()
            sel.select_iter(iter1)
            self.controller.proxy_users.load_proxy_user(None, None)
            self.controller.arw["notebook3"].set_current_page(1)
            # add user
            #iter1 = self.controller.arw['proxy_users_store'].append()
            #self.controller.arw['proxy_users_store'].set_value(iter1, 0, username)
            #self.controller.update_tv(self.arw[")
            # show page


            self.arw2["assistant1"].hide()

        if self.arw2["radio_existent_rule"].get_active() == 1:
            # create rule
            iter1 = self.controller.proxy_store.insert(-1,
                        [username, "on", "allow", "", "", username, "", "", "", "", "", 0, 0, 1, 1, "#009900", "#ffffff", "", "", 0, 0])
            # select rule
            sel = self.controller.arw["treeview3"].get_selection()
            sel.select_iter(iter1)
            self.controller.proxy_users.load_proxy_user(None, None)
            self.controller.arw["notebook3"].set_current_page(1)
            # add user
            #iter1 = self.controller.arw['proxy_users_store'].append()
            #self.controller.arw['proxy_users_store'].set_value(iter1, 0, username)
            #self.controller.update_tv(self.arw[")
            # show page


            self.arw2["assistant1"].hide()
        self.reset_assistant()


    def reset_assistant(self, widget = None):
        self.reset_mac_address()
        for entry in ["new_user_entry"]:
            self.arw2[entry].set_text("")
        for textview in ["new_user_mac"]:
            self.arw2[textview].get_buffer().set_text("")
        for checkbox in ["check_nothing", "check_email", "check_filter", "check_full"]:
            self.arw2[checkbox].set_active(False)
        for page in ["new_user", "firewall_permissions"]:
            self.arw2["assistant1"].set_page_complete(self.arw2[page], False)



