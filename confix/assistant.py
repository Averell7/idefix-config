import http.client
import ipaddress
import json
import re
import webbrowser

from gi.repository import Gtk, GObject

# import requests
import http_client as requests
from ftp_client import FTPError, ftp_connect
from util import mac_address_test, ip_address_test, showwarning, ask_text, print_except


class Assistant:
    mem_time = 0
    editing_iter = None
    request_help_label_text = ''
    first_use_label_text = ''

    def __init__(self, arw, arw2, controller):
        self.arw = arw
        self.arw2 = arw2
        self.controller = controller
        self.block_signals = False

        self.arw2['create_user_window'].set_transient_for(self.arw['window1'])
        self.arw2['create_user_stack'].set_visible_child_name('0')
        self.request_help_label_text = self.arw2['assistant_request_help_label'].get_label()
        self.first_use_label_text = self.arw2['first_use_found_label'].get_label()

        """
        self.arw2["assistant_create_user"].set_forward_page_func(self.forward_func)

        # During development
        for name in ["proxy_rules2", "manage_request"]:
            self.arw2["assistant_create_user"].set_page_complete(self.arw2[name], True)
        """

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
        self.arw2["assistant_proxy_rules"].set_model(self.controller.filter_rules.filter_store)

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

        for tree in ["experiment_dest"]:
            self.treeview1 = self.arw2[tree]
            self.treeview1.set_model(self.controller.users.users_store)

        self.cell = Gtk.CellRendererText()
        self.tvcolumn = Gtk.TreeViewColumn(_('User'), self.cell, text=0)
        self.arw2["experiment_dest"].append_column(self.tvcolumn)

    def show_assistant_create_with_mac(self, mac_address):
        self.show_assistant_create()
        self.arw2['new_user_mac'].get_buffer().set_text(mac_address + '\n')
        self.refresh_assistant_flow(page=1)

    def show_assistant_create_pre_enter(self, name, mac_address, filter):
        self.show_assistant_create()
        self.arw2['new_user_mac'].get_buffer().set_text(mac_address + '\n')
        self.arw2['new_user_entry'].set_text(name)
        self.arw2['requested_user_entry'].set_text(filter)
        self.arw2['check_full'].set_active(True)
        self.check_user_data(widget=None, nosuccess=True)
        self.refresh_assistant_flow(page=3)

    def show_assistant_create(self, widget = None):
        self.arw2['create_user_window'].show()
        # self.arw2["assistant_create_user"].show()
        # self.arw2["assistant_create_user"].set_keep_above(True)
        self.reset_assistant()

    def show_assistant_experiment(self, widget = None):
        self.arw2["assistant_experiment"].show()
        self.arw2["assistant_experiment"].set_keep_above(True)

    def show_assistant_first(self, widget=None):
        self.arw2['first_use_assistant'].set_current_page(0)
        self.arw2["first_use_assistant"].show()
        self.arw2["first_use_assistant"].set_keep_above(True)

    def cancel(self, widget, a=None):
        # self.arw2["assistant_create_user"].hide()
        self.arw2["assistant_experiment"].hide()
        self.arw2['first_use_assistant'].hide()
        self.arw2['create_user_window'].hide()
        self.reset_assistant()

    def remove_user_request(self, username):
        """Remove a user request"""
        if self.controller.ftp_config and ip_address_test(self.controller.ftp_config["server"]):
            ip = self.controller.ftp_config["server"]
            requests.get(ip, '/request_account_json.php', {
                'usercode': username,
                'reset': 'true',
            }, timeout=15)

        # Remove user from the list
        iter = None
        for row in self.arw2['requests_liststore']:
            if row[0] == username:
                iter = row.iter
                break

        if iter:
            self.arw2['requests_liststore'].remove(iter)

    def refresh_detect_list(self, widget=None):
        """Refresh the account requests"""

        if self.controller.ftp_config and ip_address_test(self.controller.ftp_config["server"]):
            ip = self.controller.ftp_config["server"]
            try:
                h1 = http.client.HTTPConnection(ip, timeout=10)
                h1.connect()
                h1.request("GET", "/request_account.json")
                res = h1.getresponse()
                self.arw2['requests_liststore'].clear()
                if res.status == 200:
                    data1 = res.read().decode("cp850")
                    try:                               # this feature is not critical and should not block Confix
                        requests = json.loads(data1)
                    except:
                        print_except()
                        print("WARNING : there is a problem with the request_account.json file")
                        return
                    if len(requests["account"]) > 0:   # necessary, because if the dictionary is empty,
                                                       # json encodes [] instead of {}, and this will create the error :
                                                       # list object has no attribute "items"
                        for mac, user in requests["account"].items():
                            self.arw2["requests_liststore"].append([user, mac])
                return
            except FTPError:
                print("No ftp connection")
        elif not widget:
            return

        showwarning(_("Not Connected"), _("Please connect to idefix first"))

    def create_user_deny_next(self, *args):
        """Make the next button not sensitive"""
        self.arw2['create_user_next_button'].set_sensitive(False)

    def create_user_allow_next(self, *args):
        """Make the next button sensitive"""
        self.arw2['create_user_next_button'].set_sensitive(True)

    def change_create_assistant_option(self, *args):
        """Automatically swap to the correct option on page 0 if user selects the text box"""
        self.arw2['create_user_radio'].set_active(True)

    def validate_page(self, page_number):
        """Check to see if the next button can be pressed"""
        self.create_user_deny_next()
        self.arw2['create_user_finish_button'].set_sensitive(False)
        self.arw2['create_user_finish_button'].set_label(_("Finish"))
        self.arw2['create_user_next_button'].set_label(_("Next"))

        # Show the back button unless we are on page 1
        self.arw2['create_user_back_button'].set_sensitive(page_number > 0)

        if page_number == 0:
            if not self.arw2['account_request_radio'].get_active():
                if self.arw2['new_user_entry1'].get_text():
                    self.create_user_allow_next()
            else:
                (model, node) = self.arw2["requests"].get_selection().get_selected()
                if node:
                    self.create_user_allow_next()
        elif page_number == 2:
            if self.arw2['manage_requests_radio2'].get_active():
                model, node = self.arw2['manage_request_tree'].get_selection().get_selected()
                if node and model.iter_parent(node):
                    self.create_user_allow_next()
            elif self.arw2['requested_user_entry'].get_text():
                self.create_user_allow_next()
        elif page_number == 6:
            self.arw2['create_user_finish_button'].set_sensitive(True)
            self.arw2['create_user_finish_button'].set_label(_("Save & Close"))
            self.arw2['create_user_next_button'].set_label(_("Save & New"))
            self.create_user_allow_next()

            # Build the summary
            label = self.username + ''
            if self.arw2['manage_requests_radio'].get_active():
                label += _(' (New User)')
            else:
                label += _(' (Adding to Existing User)')
            self.arw2['summary_name_label'].set_label(label)

            self.arw2['summary_mac_label'].set_label(self.mac_address)

            internet = _('Open (Allow all traffic)')
            if self.arw2['check_nothing'].get_active():
                internet = _('No Internet Access')
            elif self.arw2['check_filter'].get_active():
                internet = _('Filtered Internet')
            self.arw2['summary_internet_label'].set_label(internet)

            rules = []
            if self.arw2['proxy_rule_radio1'].get_active():
                rules.append(self.username + _(' (New Rule)'))
            for row in self.controller.filter_store:
                if row[19] and (not row[11]):
                    rules.append(row[0])
            self.arw2['summary_filter_label'].set_label('\n'.join(rules))

            category = None
            for row1 in self.categories_store:
                if row1[3] == 1:
                    category = row1[0]
                    break
            if not category:
                category = _('Default')
            self.arw2['summary_category_label'].set_label(category)

        else:
            self.create_user_allow_next()

    def request_assistant_next_page(self, widget=None, page_number=None):
        """Triggers if the 'next' button is pushed"""
        if not page_number:
            page_number = int(self.arw2['create_user_stack'].get_visible_child_name())

        if page_number == 0:
            if self.arw2['account_request_radio'].get_active():
                # If the user has selected an account request then store the mac address and name
                # and jump to page 2 (manage_request)
                (model, node) = self.arw2["requests"].get_selection().get_selected()
                if not node:
                    return
                name = model.get_value(node, 0)
                self.mac_address = model.get_value(node, 1)
                self.arw2["requested_user_entry"].set_text(name)
                page_number = 2
            else:
                # Otherwise show page 1 (new_user)
                self.arw2["new_user_entry"].set_text(self.arw2["new_user_entry1"].get_text())
                page_number = 1
        elif page_number == 1:
            # Step1: Make sure that the mc addresses have been added to the list
            self.add_address(widget=None, allowempty=True)
            # Step2: Check that all the data is valid
            if self.check_user_data(None, nosuccess=True):
                page_number = 3
            else:
                return
        elif page_number == 2:
            # manage the requested account
            if self.arw2['manage_requests_radio2'].get_active():
                # Existing user
                model, node = self.arw2['manage_request_tree'].get_selection().get_selected()
                if not node:
                    showwarning(_("Select a user"), _("You must select an existing user"))
                    return
                elif not model.iter_parent(node):
                    showwarning(_("Select a user"), _("You must select a user rather than a category"))
                    return
                self.username = model.get_value(node, 0)
                page_number = 6
            else:
                self.username = self.arw2["requested_user_entry"].get_text()
                page_number = 3
        elif page_number == 3:
            if not self.arw2['check_filter'].get_active():
                # Jump to confirmation page
                page_number = 6
            else:
                page_number += 1
        elif page_number == 6:
            self.finalise_create_user("", hide_assistant=False)
            page_number = 0
        else:
            page_number += 1

        self.arw2['create_user_stack'].set_visible_child_name(str(page_number))
        self.arw2['create_user_next_button'].set_sensitive(False)
        self.validate_page(page_number)

    def request_assistant_back_page(self, widget=None):
        """Triggers if the 'back' button is pushed"""
        page_number = int(self.arw2['create_user_stack'].get_visible_child_name())

        if page_number == 1 or page_number == 2:
            page_number = 0
        elif page_number == 3:
            if not self.arw2['account_request_radio'].get_active():
                # If this is a new user go back to mac address
                page_number = 1
            else:
                page_number -= 1
        elif page_number == 6:
            # Check if the user has created a new rule or is using an existing rule
            if self.arw2['manage_requests_radio'].get_active():
                # Check to see if internet access is filtered or not. If it is go back one page otherwise
                # jump back to the firewall page
                if not self.arw2['check_filter'].get_active():
                    page_number = 3
                else:
                    page_number -= 1
            else:
                # User chose an existing rule so show them the manage request page again
                page_number = 0
        else:
            page_number -= 1

        if page_number < 0:
            page_number = 0

        self.arw2['create_user_stack'].set_visible_child_name(str(page_number))
        self.validate_page(page_number)

    def request_assistant_finish_page(self, widget=None):
        """Triggers if the 'finish' button is pushed"""
        page_number = int(self.arw2['create_user_stack'].get_visible_child_name())
        if page_number == 6:
            self.finalise_create_user("", hide_assistant=True)
        else:
            # Go to summary
            self.arw2['create_user_stack'].set_visible_child_name('6')

    def refresh_assistant_flow(self, page=None):
        """Manage the page flow of the create user assistant."""
        self.arw2['create_user_stack'].set_visible_child_name(str(page))
        self.validate_page(page)

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
        # self.arw2["assistant_create_user"].set_page_complete(self.arw2["firewall_permissions"], True)
        self.update_categories_list()

    def update_categories_list(self,widget = None):
        """ updates the list of categories which correspond to the choices for email, web etc. """
        self.categories_store.clear()
        webfilter = self.arw2["check_filter"].get_active()
        webfull = self.arw2["check_full"].get_active()

        # get category
        for row in self.controller.users_store:
            if (row[6] == webfilter and row[7] == webfull):
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
        # self.arw2["assistant_create_user"].set_page_complete(self.arw2["proxy_rules"], True)
        pass

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

    def add_address(self, widget=None, allowempty=False):
        address = self.get_mac_address(allowempty=allowempty)
        if address:
            self.reset_mac_address()
            self.arw2["new_user_mac"].get_buffer().insert_at_cursor(address + "\n")

    def check_addresses(self, widget, nowarning=False, nosuccess=False):
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
                if not nowarning:
                    showwarning(_("Address Invalid"), _("The address \n%s\n entered is not valid") % v)
                OK = False
        if OK:
            if not nowarning and not nosuccess:
                showwarning(_("Addresses OK"), _("All addresses are valid"))
            return True

    def check_user_data(self, widget, a=None, nowarning=False, nosuccess=False):
        # started by the button in the assistant

        self.username = self.arw2["new_user_entry"].get_text()
        mac_address = self.get_mac_address(True)  # True will prevent an error message if the six entries are empty
                                                        # because user has clicked on "Add another address"
        if mac_address == False:  # If address invalid let user correct
            self.create_user_deny_next()
            return

        if not self.arw2["new_user_entry"].get_text():
            if not nowarning:
                showwarning(_("Name must be given"),
                            _("You must set a name for this user"))
            return

        x = self.check_addresses("", nowarning=nowarning, nosuccess=nosuccess)
        if x == False:
            self.create_user_deny_next()
            return

        x = self.controller.users.does_user_exist(self.username)
        if x == True:
            if not nowarning:
                showwarning(_("Name already used"),
                            _("The name %s is already in use.\nPlease choose another one.") % self.username)
            self.create_user_deny_next()
            return
        self.create_user_allow_next()
        # prepare the following page
        message = _("%s will have a filtered Web access.\nDo you want to create a specific access rule for him ?" % self.username)
        self.arw2["label_specific_rule"].set_label(message)

        buffer = self.arw2['new_user_mac'].get_buffer()
        start_iter, end_iter = buffer.get_bounds()
        self.mac_address = buffer.get_text(start_iter, end_iter, False)
        return True

    def choose_rules(self, widget, row):
        """ controls the toggle buttons column """
        self.controller.filter_store[row][19] = not self.controller.filter_store[row][19]

    def create_user(self, category, username, mac, enable_email=0, enable_internet=0, enable_filter=0, enable_open=0):
        """Adds a new user to the users store.
            category = category name
            username = user (level 2)

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
        # TODO : create category if needed

        category_iter = None
        for row in self.controller.users_store:
            if row[0] == category:
                category_iter = row.iter

        iternew = self.controller.users_store.insert(
            category_iter, 1, [
                username, "", "", "",
                enable_email, enable_internet, enable_filter, enable_open,
                0, "", "#ffffff", None, None
            ]
        )
        self.controller.maclist[username] = mac.split('\n')

        self.controller.devicelist[username] = []
        i = 1
        for mac1 in mac.split('\n'):
            self.controller.devicelist[username].append([mac1, "device" + str(i)])
            i += 1
        self.controller.set_colors()
        return iternew

    def create_internet_filter(self, username, users, active=True, allow=True, all_users=False, all_destinations=False):
        """Create a new entry in the filer store"""
        return self.controller.filter_store.insert(
            -1,
            [username, "on" if active else "off", "allow" if allow else "deny", "", "",
             '\n'.join(users), "", "", "", "", "", all_users, all_destinations, allow, active,
             "#009900", "#ffffff", "", "", 0, 0])

    def finalise_create_user(self, widget, hide_assistant=True):

        # Remove the user from the request list
        if self.arw2['account_request_radio'].get_active():
            self.remove_user_request(self.username)

        if self.arw2['manage_requests_radio2'].get_active():
            # This is an existing user, all we do is add the mac addresses
            # to their user
            if self.username not in self.controller.maclist:
                self.controller.maclist[self.username] = []
            if self.username not in self.controller.devicelist:
                self.controller.devicelist[self.username] = []

            self.controller.maclist[self.username].extend(self.mac_address.split('\n'))
            self.controller.filter_rules.load_filter_user(None, None)
            if hide_assistant:
                self.arw2["create_user_window"].hide()
            self.reset_assistant()

            # If connected, then save
            if self.controller.ftp_config:
                # Save config
                self.controller.build_files()

            return
        else:
            # create user
            # get the selected category
            category = None
            for row1 in self.categories_store:
                if row1[3] == 1:
                    category = row1[0]
                    string1 = row1[2]
                    break

            if not category:
                # If there is no category, choose the best matching one based on the user rules
                # this should only happen if a default configuration has not been used
                if self.arw2['check_full'].get_active():
                    look_category = 'Internet ouvert'
                    filtered = False
                    open = True
                elif self.arw2['check_filter'].get_active():
                    look_category = 'Internet filtré'
                    filtered = True
                    open = False
                else:
                    look_category = 'internet fermé'
                    filtered = False
                    open = False

                for row1 in self.categories_store:
                    if row1[0] == look_category:
                        category = look_category
                        break

                # if default does not exist, create it
                if not category:
                    # Create a new default category
                    self.controller.users_store.append(
                        None, [look_category, "", "", "", 0, 0, filtered, open, 0, "", "", None, None]
                    )
                    category = look_category

            iternew = self.create_user(category, self.username, self.mac_address)

        # Proxy config
        iter1 = None
        memiter = None

        # create rule
        if self.arw2["proxy_rule_radio1"].get_active() == 1:
            iter1 = self.create_internet_filter(self.username, [self.username], active=True, allow=True)

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
        self.controller.filter_rules.load_filter_user(None, None)

        # if Web filter is not selected, show the first tab with the new user selected and close the assistant
        if self.arw2["proxy_rule_radio2"].get_active() == 1:
            model = self.controller.users_store
            iterparent = model.iter_parent(iternew)
            if iterparent:
                path1 = model.get_path(iterparent)
                self.arw["treeview1"].expand_row(path1, True)
            sel = self.arw["treeview1"].get_selection()
            sel.select_iter(iternew)
            self.arw["notebook3"].set_current_page(0)
            self.controller.users.load_user("", "", iternew)
        else:
            self.arw["notebook3"].set_current_page(1)

        if hide_assistant:
            self.arw2["create_user_window"].hide()
        self.reset_assistant()

        # If connected, then save
        if self.controller.ftp_config:
            # Save config
            self.controller.build_files("")

    def reset_assistant(self, widget = None):
        self.arw2['create_user_finish_button'].set_label(_("Finish"))
        self.arw2['create_user_next_button'].set_label(_("Next"))

        self.arw2['create_user_stack'].set_visible_child_name('0')
        self.arw2['create_user_back_button'].set_sensitive(False)
        self.arw2['create_user_finish_button'].set_sensitive(False)
        self.arw2['create_user_next_button'].set_sensitive(False)

        self.reset_mac_address()
        self.arw2['account_request_radio'].set_active(True)
        self.arw2['manage_requests_radio'].set_active(True)
        self.arw2['proxy_rule_radio1'].set_active(True)
        for entry in [
            "new_user_entry", "new_user_entry1",
            "mac_A", "mac_B", "mac_C", "mac_D", "mac_E", "mac_F",
            "requested_user_entry"
        ]:
            self.arw2[entry].set_text("")
        for textview in ["new_user_mac"]:
            self.arw2[textview].get_buffer().set_text("")
        for checkbox in ["check_nothing", "check_filter", "check_full"]:
            self.arw2[checkbox].set_active(False)
        self.arw2['check_nothing'].set_active(True)
        if self.controller.ftp_config and ip_address_test(self.controller.ftp_config["server"]):
            website = 'http://' + self.controller.ftp_config['server'] + '/request_account_json.php'
            self.arw2['assistant_request_help_label'].set_label(self.request_help_label_text % website)
        else:
            self.arw2['assistant_request_help_label'].set_label(_("You must be connected to idefix to see this list"))


    """ Experiment user permissions """

    def get_target_user(self,widget, event = None):
        path = widget.get_path_at_pos(event.x, event.y)
        iter1 = self.controller.users.users_store.get_iter(path[0])
        self.target_name = self.controller.users.users_store[iter1][0]
        #self.arw2["my_account"].set_text(self.controller.myaccount)
        self.arw2["target_name"].set_text(self.target_name)

    def start_simulate_user(self, widget):
        """ called by the toggle button in the Asssistant """
        if self.controller.myaccount == self.target_name:
            showwarning(_("Incvalid configuration"), _("You cannot experiment yourself! \n Please choose another user."))
            widget.set_active(False)
            return
        self.enable_simulated_user(self.controller.myaccount, self.target_name)


    def simulate_user_titlebar_toggled(self,widget):
        """ called by the toggle button in the title bar. Disables experimentation, and show the normal status bar """
        if not self.arw["experiment_user_toggle"].get_active():
            self.disable_simulated_user(self.controller.myaccount)
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
        self.arw2["assistant_experiment"].hide()

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

    def connect_idefix(self, password='admin'):
        """Check if idefix connects"""
        model, iter = self.arw2['idefix_select_view'].get_selection().get_selected()

        idefix_ip = model.get_value(iter, 0)

        print("Trying", idefix_ip)
        connection = ftp_connect(idefix_ip, 'idefix', password)
        if not connection:
            # Prompt for password again
            password = ask_text(self.arw2['first_use_assistant'], _("Enter idefix ftp password"), password=True)
            if not password:
                # Show the selection dialog
                self.arw2['first_use_assistant'].set_current_page(2)
                self.arw2['first_use_assistant'].commit()
                return
            return self.connect_idefix(password)

        self.arw2['first_use_found_label'].set_label(self.first_use_label_text % idefix_ip)

        # Write the configuration
        self.controller.profiles.config = {
            '__options': {
                'auto_load': 1,
                'last_config': 'default'
            }
        }

        self.controller.profiles.profiles_store.append(
            ['default', 'local', 'idefix', password, model.get_value(iter, 0)]
        )

        self.controller.profiles.profile_save_config()
        self.controller.profiles.refresh_saved_profiles()
        self.controller.ftp_config = self.controller.profiles.config['default']

        # Load next page
        self.arw2['first_use_assistant'].set_current_page(4)
        self.arw2['first_use_assistant'].commit()
        data = self.controller.information.get_infos('ftp', decode_json=True)
        if data and (data.get('ftp') != "" or data.get('ftp') != "" or data.get('ftp') != ""):
            # Show page 4 with populated data
            self.arw2['first_use_assistant'].set_current_page(5)
            self.arw2['first_use_assistant'].commit()
            self.arw2['ftp_config_name'].set_text("Idefix in the cloud")
            self.arw2['ftp_config_host'].set_text(data.get('ftp'))
            self.arw2['ftp_config_login'].set_text(data.get('login'))
            self.arw2['ftp_config_password'].set_text(data.get('password'))
        else:
            self.finish_first_configuration()

    def finish_first_configuration(self):
        """Open connection profile and hide the assistant"""
        self.controller.update_gui()
        self.controller.profiles.refresh_saved_profiles()
        self.controller.profiles.profile_save_config()
        self.arw["configname"].set_text("default")
        self.arw2['first_use_assistant'].hide()
        self.controller.open_connexion_profile()
    def cancel_configuration(self, *args):
        self.arw2['first_use_assistant'].set_current_page(0)
        self.arw2['first_use_assistant'].hide()

    def start_finding_idefix(self):
        found = self.controller.information.find_idefix()
        self.arw2['finding_idefix'].hide()
        if not found:
            # Warn the user that idefix was not found
            showwarning(
                _("Idefix Not Found"),
                _("Idefix was not detected. Please make sure it is connected to this computer and try again"),
                msgtype=4
            )
            self.arw2['first_use_assistant'].set_current_page(0)
            return

        self.arw2['idefix_store'].clear()
        ip_iter = None
        for (ip, content) in found:
            network = json.loads(content)
            ip_iter = self.arw2['idefix_store'].append()
            self.arw2['idefix_store'].set_value(ip_iter, 0, ip)

            if network["idefix"].get("eth0", "") != "" and network["idefix"].get("eth1", "") != "":
                wan = ipaddress.ip_interface(network["idefix"]["eth0"] + "/" + network["idefix"]["netmask0"])
                lan = ipaddress.ip_interface(network["idefix"]["eth1"] + "/" + network["idefix"]["netmask1"])
                if lan.network.overlaps(wan.network):
                    # Warn the user
                    response = self.arw2['idefix_conflict_dialog'].run()
                    if response == Gtk.ResponseType.ACCEPT:
                        # Launch the browser if the user wants
                        webbrowser.open('http://' + ip + ':10080/config-reseau.php')

                    self.arw2['idefix_conflict_dialog'].hide()

                    self.arw2['first_use_assistant'].set_current_page(0)
                    self.arw2['first_use_assistant'].commit()
                    return

        if len(found) > 1:
            # Show selection page
            self.arw2['first_use_assistant'].set_current_page(2)
            self.arw2['first_use_assistant'].commit()
        else:
            # Go straight to connection profile
            self.arw2['idefix_select_view'].get_selection().select_iter(ip_iter)
            self.arw2['first_use_assistant'].set_current_page(3)
            self.arw2['first_use_assistant'].commit()

    def on_configuration_page_change(self, widget, page_widget):
        """Called on page changing for first time assistant"""
        page = widget.get_current_page()

        if page == 1:
            # Pop up dialog
            self.arw2['finding_idefix'].show_all()
            while Gtk.events_pending():
                Gtk.main_iteration()
            GObject.timeout_add(5, self.start_finding_idefix)

        elif page == 3:
            # Idefix config was selected
            model, iter = self.arw2['idefix_select_view'].get_selection().get_selected()
            if not iter:
                showwarning(_("Please select"), _("Please select an Idefix to configure"))
                self.arw2['first_use_assistant'].set_current_page(2)
                return
            self.arw2['first_use_assistant'].commit()
            self.connect_idefix()

    def finish_configuration(self, *args):
        if not self.arw2['ftp_config_name'].get_text():
            showwarning(_("Invalid Name"), _("Please enter a name"))
            self.arw2['first_use_assistant'].set_current_page(5)
            return

        self.controller.profiles.profiles_store.append([
            self.arw2['ftp_config_name'].get_text(),
            'remote',
            self.arw2['ftp_config_login'].get_text(),
            self.arw2['ftp_config_password'].get_text(),
            self.arw2['ftp_config_host'].get_text()
        ])
        self.controller.profiles.profile_save_config()
        self.controller.profiles.refresh_saved_profiles()
        self.finish_first_configuration()

    def auto_find_mac_address(self, widget=None):
        """Automatically determine the MAC Address"""

        # Step1: We submit to request_account_json.php
        code = self.arw2["new_user_entry"].get_text()

        # If we don't have an active configuration, try to use the default
        # server ip.
        host = '192.168.84.184'
        if self.controller.ftp_config and self.controller.ftp_config.get('server'):
            host = self.controller.ftp_config['server']

        response = requests.post(host, '/request_account_json.php', {
            'usercode': code,
            'reset': '',
        }, timeout=15)

        if not response:
            showwarning(_('Could not detect'), _("Could not contact the idefix server"))
            return

        response = requests.get(host, '/request_account.json', timeout=15)
        if not response:
            showwarning(_('Could not detect'), _("Could not contact the idefix server"))
            return
        else:
            data = json.loads(response)

        for mac, user in data['account'].items():
            if user == code:
                # Retrieve the mac address
                self.arw2['new_user_mac'].get_buffer().set_text(mac)
                self.check_user_data(widget=None)
                return

        showwarning(_('Could not detect'), _("Could not find the MAC address"))
        return
