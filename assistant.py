from gi.repository import Gtk

import re

from gi.repository import Gtk

from util import mac_address_test, ip_address_test, showwarning


class Assistant:
    mem_time = 0
    editing_iter = None

    def __init__(self, arw, arw2, controller):
        self.arw = arw
        self.arw2 = arw2
        self.controller = controller
        self.block_signals = False
        self.arw2["assistant1"].set_forward_page_func(self.forward_func)

        # Listview
        self.categories_store = Gtk.ListStore(str,Gtk.TreeIter,str,int)
        self.arw2["assistant_categories"].set_model(self.categories_store)

        self.cell = Gtk.CellRendererText()
        self.radio = Gtk.CellRendererToggle(activatable=True, radio = True, xalign=0.5)
        self.radio.connect('toggled', self.categories_radio_toggle)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell, text=0)
        self.tvcolumn.set_fixed_width(220)
        self.arw2["assistant_categories"].append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('---'), self.radio, active=3)
        self.arw2["assistant_categories"].append_column(self.tvcolumn)


        # Listview
        self.arw2["assistant_proxy_rules"].set_model(self.controller.proxy_users.filter_store)

        self.cell = Gtk.CellRendererText()
        self.check = Gtk.CellRendererToggle(xalign=0.5)
        self.check.connect('toggled', self.choose_rules)

        def render_name(col, cell, model, iter, *args):
            cell.set_property('foreground', model.get_value(iter, 15))
            cell.set_property('background', model.get_value(iter, 16))
            text = model.get_value(iter, 0)
            if model.get_value(iter, 11):
                text = '<i>' + text + '</i>'
            cell.set_property('markup', text)

        def render_check(col, cell, model, iter, *args):
            all_rule = model.get_value(iter, 11)
            cell.set_active(True if all_rule else model.get_value(iter, 19))
            cell.set_activatable(not all_rule)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell)
        self.tvcolumn.set_cell_data_func(self.cell, render_name)
        self.tvcolumn.set_fixed_width(220)
        self.arw2["assistant_proxy_rules"].append_column(self.tvcolumn)

        self.tvcolumn = Gtk.TreeViewColumn(_('---'), self.check)
        self.tvcolumn.set_cell_data_func(self.check, render_check)

        self.arw2["assistant_proxy_rules"].append_column(self.tvcolumn)


        # Treeview for experiment user permissions

        for tree in ["experiment_source", "experiment_dest"]:
            self.treeview1 = self.arw2[tree]
            self.treeview1.set_model(self.controller.users.users_store)

        self.cell = Gtk.CellRendererText()
        self.tvcolumn = Gtk.TreeViewColumn(_('You'), self.cell, text=0)
        self.arw2["experiment_source"].append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('User'), self.cell, text=0)
        self.arw2["experiment_dest"].append_column(self.tvcolumn)






    def show_assistant(self, widget = None):
        self.arw2["assistant1"].show()
        self.arw2["assistant1"].set_keep_above(True)

    def cancel (self, widget, a = None):
        self.arw2["assistant1"].hide()

    def forward_func(self, page):
        """ manage the page flow, depending of the choices made by the user """

        if page == 0 :
            if self.arw2["ass_create_user_check"].get_active():
                return 1
            elif self.arw2["ass_experiment_check"].get_active():
                return 5
        elif (  page == 2    # if no proxy rules are necessary
                and self.arw2["check_filter"].get_active() == 0
             ):
            return 4   # summary page
        elif page == 4:
            self.summary("")
            return 0

        else:
            return page + 1

    def assistant_check_nothing(self, widget):
        self.block_signals = True
        if self.arw2["check_nothing"].get_active() == 1:
            for check in ["filter", "full"]:
                self.arw2["check_" + check].set_active(False)

        self.block_signals = False

    def assistant_check_filter(self, widget):
        if self.block_signals:
            return
        if self.arw2["check_filter"].get_active() == 1:
            self.arw2["check_nothing"].set_active(False)
            self.arw2["check_full"].set_active(False)

    def assistant_check_full(self, widget):
        if self.block_signals:
            return
        if self.arw2["check_full"].get_active() == 1:
            self.arw2["check_nothing"].set_active(False)
            self.arw2["check_filter"].set_active(False)

    def ass_firewall_permissions(self, widget, event = None):
        self.arw2["assistant1"].set_page_complete(self.arw2["firewall_permissions"], True)
        self.update_categories_list()

    def update_categories_list(self,widget = None):
        """ updates the list of categories which correspond to the choices for email, web etc. """
        self.categories_store.clear()
        webfilter = self.arw2["check_filter"].get_active()
        webfull = self.arw2["check_full"].get_active()
        if webfilter or webfull:
            web = True
        else:
            web = False

        # get category
        for row in self.controller.users_store:
            if (row[5] == web
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

    def get_mac_address(self, allowempty = False):
        mac = []
        MacError = False
        for index in["A", "B", "C", "D", "E", "F"]:
            value = self.arw2["mac_" + index].get_text().lower()
            x = re.search("[0-9a-f]{2}", value)
            if not x:
                MacError = True
            mac.append(value)
        mac = ":".join(mac)
        if mac == ":::::":       # empty address
            if allowempty:
                return ""
        if MacError:
            showwarning(_("Error"), _("Invalid Mac address, please correct and retry"))
            return False
        return mac

    def reset_mac_address(self):
        for index in["A", "B", "C", "D", "E", "F"]:
            self.arw2["mac_" + index].set_text("")

    def add_address(self, widget = None):
        address = self.get_mac_address()
        if address:
            self.reset_mac_address()
            self.arw2["new_user_mac"].get_buffer().insert_at_cursor(address + "\n")

    def check_addresses(self, widget):
        buffer = self.arw2['new_user_mac'].get_buffer()
        (start_iter, end_iter) = buffer.get_bounds()
        value = buffer.get_text(start_iter, end_iter, False)

        OK = True
        for v in value.split('\n'):
            if v.strip() == "":
                continue
            if v.startswith("#"):
                continue
            if not mac_address_test(v) and not ip_address_test(v):
                showwarning(_("Address Invalid"), _("The address \n%s\n entered is not valid") % v)
                OK = False
        if OK:
            showwarning(_("Addresses OK"), _("All addresses are valid"))
            return True

    def check_user_data(self, widget, a = None):
        # started by the button in the assistant

        self.username = self.arw2["new_user_entry"].get_text()
        self.mac_address = self.get_mac_address(True)        # True will prevent an error message if the six entries are empty
                                                        # because user has clicked on "Add another address"
        if self.mac_address == False:                             # If address invalid let user correct
            return

        x = self.check_addresses("")
        if x == False:
            return

        x = self.controller.users.does_user_exist(self.username)
        if x == True:
            showwarning(_("Name already used"), _("The name %s is already in use.\nPlease choose another one.") % self.username)
            return
        self.arw2["assistant1"].set_page_complete(self.arw2["new_user"], True)
        # prepare the following page
        self.arw2["check_specific_rule"].set_label(_("Create a specific access rule for %s") % self.username)


    def choose_rules(self, widget, row):
        """ controls the toggle buttons column """
        self.controller.filter_store[row][19] = not self.controller.filter_store[row][19]

    def summary(self, widget):


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
        9 :
        10 : background color
        11 : icon 1
        12 : icon 2
        """
        # create user
        # get the selected category
        for row1 in self.categories_store:
            if row1[3] == 1:
                category = row1[0]
                string1 = row1[2]
                break
        iter1 = self.controller.users_store.get_iter_from_string(string1)
        iternew = self.controller.users_store.insert(iter1, 1,
                        [self.username, "", "", "", 0, 0, 0, 0, 0, "", "#ffffff", None, None])
        self.controller.maclist[self.username] = [self.mac_address]
        self.controller.set_colors()

        # if Web filter is not selected, show the first tab with the new user selected and close the assistant
        if self.arw2["check_filter"].get_active() == 0:
            model = self.controller.users_store
            iterparent = model.iter_parent(iternew)
            path1 = model.get_path(iterparent)
            self.arw["treeview1"].expand_row(path1, True)
            sel = self.arw["treeview1"].get_selection()
            sel.select_iter(iternew)
            self.arw["notebook3"].set_current_page(0)
            self.controller.users.load_user("","", iternew)
            self.arw2["assistant1"].hide()
            return


        # Proxy config
        iter1 = None
        memiter = None

        # create rule
        if self.arw2["check_specific_rule"].get_active() == 1:
            iter1 = self.controller.filter_store.insert(-1,
                        [self.username, "on", "allow", "", "", self.username, "", "", "", "", "", 0, 0, 1, 1, "#009900", "#ffffff", "", "", 0, 0])

        # Add the user to the chosen rules
        for row in self.controller.filter_store:
            if row[19] and (not row[11]):       # if selected, but is not a general rule (all users)
                # add user to users list
                row[5] += "\n" + self.username
                memiter= row.iter

        # select rule
        if not iter1:           # if no new rule was created, we will open the last general rule applied to this user
            iter1 = memiter

        sel = self.arw["treeview3"].get_selection()
        if iter1:
            sel.select_iter(iter1)
        self.controller.proxy_users.load_proxy_user(None, None)
        self.arw["notebook3"].set_current_page(1)
        self.arw2["assistant1"].hide()
        self.reset_assistant()


    def reset_assistant(self, widget = None):
        self.reset_mac_address()
        for entry in ["new_user_entry"]:
            self.arw2[entry].set_text("")
        for textview in ["new_user_mac"]:
            self.arw2[textview].get_buffer().set_text("")
        for checkbox in ["check_nothing", "check_filter", "check_full"]:
            self.arw2[checkbox].set_active(False)
        for page in ["new_user", "firewall_permissions"]:
            self.arw2["assistant1"].set_page_complete(self.arw2[page], False)


    """ Experiment user permissions """

    def get_current_user(self,widget, event = None):
        path = widget.get_path_at_pos(event.x, event.y)
        iter1 = self.controller.users.users_store.get_iter(path[0])
        self.current_name = self.controller.users.users_store[iter1][0]
        self.arw2["current_name"].set_text(self.current_name)

    def get_target_user(self,widget, event = None):
        path = widget.get_path_at_pos(event.x, event.y)
        iter1 = self.controller.users.users_store.get_iter(path[0])
        self.target_name = self.controller.users.users_store[iter1][0]
        self.arw2["target_name"].set_text(self.target_name)

    def start_simulate_user(self, widget):
        """ called by the toggle button in the Asssistant """
        if self.current_name == self.target_name:
            showwarning(_("Incvalid configuration"), _("You cannot experiment yourself! \n Please choose another user."))
            widget.set_active(False)
            return
        self.enable_simulated_user(self.current_name, self.target_name)


    def simulate_user_titlebar_toggled(self,widget):
        """ called by the toggle button in the title bar. Disables experimentation, and show the normal status bar """
        if not self.arw["experiment_user_toggle"].get_active():
            self.disable_simulated_user(self.current_name)
            # Toggle the indicator in the title bar
            self.arw["titlebar_stack"].set_visible_child(self.arw["titlebar_standard"])
            self.arw["experiment_user_toggle"].set_active(False)

    def enable_simulated_user(self, user, target_user):
        """Add -@ to user and add +@ to target_user"""

        mac_list = []
        self.disable_simulated_user()        # clean up
        for mac in self.controller.maclist[user]:
            mac_list.append(mac)

        # Update the user to ignore previous set addresses
        self.controller.maclist[user] = ['-@' + mac for mac in mac_list]
        self.controller.maclist[user].append(
            "+@11:11:11:11:11:11")  # add a dummy address, to prevent errors created by a user without a valid address

        self.controller.maclist[target_user].extend(['+@' + mac for mac in mac_list])
        self.arw["maclist"].get_buffer().set_text('\n'.join(self.controller.maclist[user]))

        # Toggle the indicator in the title bar
        self.arw["titlebar_stack"].set_visible_child(self.arw["titlebar_experiment"])
        self.arw["experiment_user_toggle"].set_active(True)
        self.arw["experiment_username"].set_text(target_user)
        self.arw2["assistant1"].hide()

    def disable_simulated_user(self, current_user = None):
        """Remove -@ and +@ prefixes from all users"""
        user = None
        for user in self.controller.maclist:
            maclist = self.controller.maclist[user]
            updated_macs = []
            for mac in maclist:
                if mac.startswith('-@'):  # Enable old addresses
                    updated_macs.append(mac[2:])
                elif not mac.startswith('+@'):  # Remove added addresses completely
                    updated_macs.append(mac)
            self.controller.maclist[user] = updated_macs

        if current_user:
            self.arw["maclist"].get_buffer().set_text(
                '\n'.join(self.controller.maclist[current_user])
        )
        #if user:
        #    self.controller.users.user_summary(user)







