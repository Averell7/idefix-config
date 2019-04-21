import time

from gi.repository import Gdk, Gtk

from myconfigparser import myConfigParser,myTextParser
from util import askyesno, ask_text, mac_address_test


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
        self.arw2["assistant_proxy_rules"].set_model(self.controller.proxy_users.proxy_store)

        self.cell = Gtk.CellRendererText()
        self.check = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check.connect('toggled', self.choose_rules)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell, text=0, foreground=15, background=16)
        self.tvcolumn.set_fixed_width(220)
        self.arw2["assistant_proxy_rules"].append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('---'), self.check, active=19)
        self.arw2["assistant_proxy_rules"].append_column(self.tvcolumn)




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
            return 5   # summary page
        elif ( page == 3     # if a rule specific for this user is choosed, skip existent rules page
               and self.arw2["radio_specific_rule"].get_active() == 1
              ):
            return 5  # summary page
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
            self.arw2["check_full"].set_sensitive(False)
        else:
            self.arw2["check_full"].set_sensitive(True)

    def assistant_check_full(self, widget):
        if self.block_signals:
            return
        if self.arw2["check_full"].get_active() == 1:
            self.arw2["check_filter"].set_active(False)
            self.arw2["check_filter"].set_sensitive(False)
        else:
            self.arw2["check_filter"].set_sensitive(True)




    def add_address(self, widget = None):
        return

    def ass_new_user(self, widget, a = None):
        self.arw2["assistant1"].set_page_complete(self.arw2["new_user"], True)

    def ass_firewall_permissions(self, widget, event = None):
        self.arw2["assistant1"].set_page_complete(self.arw2["firewall_permissions"], True)

    def ass_firewalll_permissions(self, widget, event = None):
        pass

    def ass_new_user_rules(self, widget, event = None):
        self.arw2["assistant1"].set_page_complete(self.arw2["proxy_rules"], True)

    def get_mac_address(self):
        mac = []
        for index in["A", "B", "C", "D", "E", "F"]:
            mac.append(self.arw2["mac_" + index].get_text())
        mac = ":".join(mac)
        return mac

    def check_mac_address(self, widget, a = None):
        mac = self.get_mac_address()
        print(mac)
        x = mac_address_test(mac)
        print(x)


    def choose_rules(self, widget, row):

        self.controller.proxy_store[row][19] = not self.controller.proxy_store[row][19]
##        if self.controller.proxy_store[row][19] == 0:
##            self.controller.proxy_store[row][19] = 1
##        else:
##            self.controller.proxy_store[row][19] = 0





    def summary(self, widget):
        username = self.arw2["new_user_entry"].get_text()
        mac_address = self.get_mac_address()
        # firewall permissions

        if self.arw2["radio_nothing"].get_active() == 1:
            email = 0
            web = 0
            webfilter = 0
            webfull = 0
        elif self.arw2["radio_email"].get_active() == 1:
            email = 1
            web = 0
            webfilter = 0
            webfull = 0
        elif self.arw2["radio_webonly"].get_active() == 1:
            email = 0
            web = 1
            webfilter = 1
            webfull = 0
        elif self.arw2["radio_filter"].get_active() == 1:
            email = 1
            web = 1
            webfilter = 1
            webfull = 0
        elif self.arw2["radio_full"].get_active() == 1:
            email = 1
            web = 1
            webfilter = 0
            webfull = 1


        # get category
        for row in self.controller.users_store:
            if (row[4] == email
                and row[5] == web
                and row[6] == webfilter
                and row[7] == webfull):
                iter1 = row.iter
                break

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
        iternew = self.controller.users_store.insert(iter1, 1,
                        [username, "", "", "", email, web, webfilter, webfull, 0, "", "", None, None])
        self.controller.maclist[username] = [mac_address]
        self.controller.set_colors()

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



