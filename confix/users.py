import time

from gi.repository import Gtk, Gdk
from gi.repository.GdkPixbuf import Pixbuf

from actions import DRAG_ACTION
from icons import (
    internet_filtered_icon, internet_full_icon, internet_denied_icon
)
from util import alert, ask_text, showwarning, askyesno, mac_address_test, ip_address_test


class Users:
    mem_time = 0
    cat_list = {}
    iter_user = None
    block_signals = False

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        # 1 - users
        """
        0 : section (level 1)  - user (level 2)  - sub user (level 3)
        1 : options (text)    TODO : probably no longer used, verify
        2 : email time condition
        3 : internet time condition
        4 : email (1/0)
        5 : internet access (1/0)  # no longer used
        6 : filtered (1/0)
        7 : open (1/0)
        8 : reserved (int)
        9 :  reserved (str)
        10 : background color
        11 : icon 1
        12 : icon 2
        """
        # section / user
        self.users_store = Gtk.TreeStore(str, str, str, str, int, int, int, int, int, str, str, Pixbuf, Pixbuf)  #

        self.treeview1 = self.arw["treeview1"]
        self.treeview1.set_model(self.users_store)

        self.cell = Gtk.CellRendererText()
        self.cellpb = Gtk.CellRendererPixbuf(xalign=0.0)
        self.cellpb2 = Gtk.CellRendererPixbuf(xalign=0.0)

        self.tvcolumn = Gtk.TreeViewColumn(_('Filename'))
        self.treeview1.connect("button-press-event", self.load_user)

        self.tvcolumn.pack_start(self.cell, False)
        self.tvcolumn.pack_start(self.cellpb, False)
        self.tvcolumn.pack_start(self.cellpb2, False)
        self.tvcolumn.add_attribute(self.cell, "background", 10)
        self.tvcolumn.add_attribute(self.cell, "text", 0)
        self.tvcolumn.add_attribute(self.cellpb, "pixbuf", 11)
        self.tvcolumn.add_attribute(self.cellpb2, "pixbuf", 12)

        self.treeview1.append_column(self.tvcolumn)

        # drag and drop for users tree
        self.arw["treeview1"].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [],
                                                       DRAG_ACTION)
        self.arw["treeview1"].drag_source_add_text_targets()
        self.arw["treeview1"].connect("drag-data-get", self.users_drag_data_get)

        self.arw["treeview1"].drag_dest_set(Gtk.DestDefaults.DROP, [], DRAG_ACTION)
        self.arw["treeview1"].drag_dest_add_text_targets()
        self.arw["treeview1"].connect("drag-data-received", self.users_drag_data_received)

        self.users_store.connect('row-changed', lambda *args: self.controller.populate_users_chooser())
        self.users_store.connect('row-deleted', lambda *args: self.controller.populate_users_chooser())
        self.users_store.connect('rows-reordered', lambda *args: self.controller.populate_users_chooser())
        self.users_store.connect('row-inserted', lambda *args: self.controller.populate_users_chooser())

    def create_maclist(self):
        maclist = {}
        devicelist = {}
        data1 = self.controller.config["users"]
        for section in data1:
            for user in data1[section]:
                if user.startswith("@_"):
                    continue
                maclist[user] = []
                devicelist[user] = []                              # better adapted to version 3
                devices =  list(data1[section][user]["devices"])
                for device in devices:
                    #maclist[user].append(data1[section][user]["devices"][device]["mac"] + " # " + device)
                    # En cours
                    thismac = data1[section][user]["devices"][device]["mac"]
                    maclist[user].append(thismac)
                    devicelist[user].append([thismac,device])
                if "subusers" in data1[section][user]:
                    for subuser in data1[section][user]["subusers"]:
                        maclist[subuser] = [data1[section][user]["subusers"][subuser]]

                for macs in data1[section][user]:
                    if macs.startswith('-@') or macs.startswith('+@'):
                        self.block_signals = True
                        self.arw['experiment_user_toggle'].set_active(True)
                        self.block_signals = False
        # reverse search
        temp1 = {}
        for user, macs in maclist.items():
            for mac in macs:
                mac = mac.split("#")[0].strip()
                if mac != "":
                    temp1[mac] = user
        maclist.update(temp1)

        return (maclist, devicelist)


    def populate_users(self):
        self.users_store.clear()
        data1 = self.controller.config["users"]

        # Email, Internet, Filtered, Open
        options_list = [0, 0, 0, 0, 0]
        for section in data1:


            options_list[1] = data1[section].get('@_internet', ['none']) != 'none'
            options_list[2] = data1[section].get('@_internet', ['']) == 'filtered'
            options_list[3] = data1[section].get('@_internet', ['']) == 'open'

            """
            internet_time_condition = data1[section].get("@_internet_time_condition", [''])
            if internet_time_condition:
                days = internet_time_condition.split(' ')[0]
                # days = parse_date_format_from_squid(days)

                if len(internet_time_condition.split(' ')) > 1:
                    internet_time_condition = days + ' ' + internet_time_condition.split(' ', 1)[1]
                else:
                    internet_time_condition = days

            email_time_condition = data1[section].get("@_email_time_condition", [''])
            if email_time_condition:
                days = email_time_condition.split(' ')[0]
                # days = parse_date_format_from_squid(days)

                if len(email_time_condition.split(' ')) > 1:
                    email_time_condition = days + ' ' + email_time_condition.split(' ', 1)[1]
                else:
                    email_time_condition = days
            """
            email_time_condition = ""
            internet_time_condition = ""

            # add section
            node = self.users_store.append(None,
                                           [section, "", email_time_condition,
                                            internet_time_condition] + options_list + ["", "#ffffff", None,
                                                                                       None])
            # N.B. : icons are set in the set_colors function
            # keep memory of the nodes, it will be used for changing the category of a user
            # (function change_category below)
            self.cat_list[section] = node

            # add users for this section
            for user in data1[section]:
                if not user.startswith('@_'):
                    user_iter = self.users_store.append(
                        node,
                        [user, "", "", "", 0, 0, 0, 0, 0, "", "#ffffff", None, None]
                    )

                    # check if any sub users have been defined
                    if "subusers" in data1[section][user]:
                        for subuser in data1[section][user].get('subusers').keys():
                            self.users_store.append(
                                user_iter,
                                [subuser, "", "", "", 0, 0, 0, 0, 0, "", "#ffffff", None, None]
                            )

    def load_user(self, widget, event, iternew=None):
        """ loads data in right pane when a category or a user is selected in the tree"""


        if not isinstance(event, str) and event.button != 1:    # don't load data when right click is used
            return

        self.controller.block_signals = True
        self.block_signals = True  # to prevent the execution of update_check wich causes errors

        if iternew:
            iter1 = iternew
            level = 2
        else:

            path = widget.get_path_at_pos(event.x, event.y)
            if path is None:  # click outside a valid line
                # if click outside the list, unselect all. It is good to view the global configuration
                #  with the colors, otherwise, there is always a line masked by the cursor.
                sel = self.arw["treeview1"].get_selection()
                sel.unselect_all()
                return

            iter1 = self.users_store.get_iter(path[0])
            level = path[0].get_depth()

        self.controller.iter_user = iter1

        if level == 1:  # category level
            self.arw["users_stack"].set_visible_child(self.arw["vbox2"])

            # set internet rights in the check boxes and radio list
            # self.arw["internet_email"].set_active(self.users_store[iter1][4] or self.users_store[iter1][7])
            self.arw["internet_filtered"].set_active(self.users_store[iter1][6])
            self.arw["internet_open"].set_active(self.users_store[iter1][7])
            # adapt the right click menu
            self.arw["menu_add_above"].hide()
            self.arw["menu_add_below"].hide()
            self.arw["menu_add_user"].show()
            self.arw["menu_add_cat"].show()
            self.arw["menu_move_user"].hide()
            self.arw["menu_rename_user"].hide()
            self.arw["menu_add_subuser"].hide()
            self.arw["menu_rename_cat"].show()


        elif level in (2, 3):  # user / sub user level

            self.arw["users_stack"].set_visible_child(self.arw["user_summary_frame"])
            # adapt the right click menu
            self.arw["menu_add_above"].show()
            self.arw["menu_add_below"].show()
            self.arw["menu_add_user"].hide()
            self.arw["menu_add_cat"].hide()
            self.arw["menu_move_user"].show()
            self.arw["menu_rename_user"].show()
            self.arw["menu_rename_cat"].hide()
            self.arw["menu_add_subuser"].show()

            # fill the mac address frame
            username = self.users_store[iter1][0]
            buffer = self.arw["maclist"].get_buffer()
            if username in self.controller.devicelist:
                devices = self.controller.devicelist[username]
                #macaddr = self.controller.maclist[username]
                if not devices or (devices[0][0] == False) or (devices[0][0] == ""):
                    buffer.set_text("")
                    alert(_("No valid mac address for this user1 !"))
                else:
                    #if not isinstance(macaddr, list):     # This may happen if the subuser name and the Identifier are identical
                    #    macaddr = [macaddr]
                    device_str = []
                    for mac, name in devices:
                        device_str.append(name + "  #  " + mac)
                    data1 = "\n".join(device_str)
                    buffer.set_text(data1)
            else:
                buffer.set_text("")
                if not iternew:
                    alert(_("No mac address for this user2 !"))

            # adapt the title of the frame for user/subuser
            if level == 3:
                self.arw['user_summary_label'].set_label(_("Identifier"))         # subuser
            else:
                self.arw['user_summary_label'].set_label(_("Mac Address(es)"))     # user

            # fill the user summary
            self.user_summary(username, level)

            # get data in lists for this user
        self.block_signals = False
        self.controller.block_signals = False

    def manage_users(self, widget, event=None):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                submenu = Gtk.Menu()
                submenu.show()
                for row in self.users_store:
                    cat = row[0]
                    commandes = Gtk.MenuItem(cat)
                    submenu.append(commandes)
                    # commandes.connect("activate", self.change_category, cat)       # works only with a right click, hence replaced by the following
                    commandes.connect("button-press-event", self.change_category, cat)

                    commandes.show()

                self.arw["menu_move_user"].set_submenu(submenu)
                self.arw["users_menu"].popup(None, None, None, None, event.button, event.time)
        return

    def ask_user_dialog(self, level, text=""):
        if level == 1:
            new = _("Name of the new category")
        else:
            new = _("Name of the new user")

        return ask_text(self.arw["window1"], new, text)

    def does_user_exist(self, name):
        """Check if the user exists or not"""
        name = name.strip().lower()
        for row in self.users_store:
            for child in row.iterchildren():
                existing_name = child[0].strip().lower()
                if existing_name == name:
                    return True
                for subchild in child.iterchildren():
                    existing_name = subchild[0].strip().lower()
                    if existing_name == name:
                        return True
        return False

    def add_subuser(self, widget):
        """Adds a new sub user to the selected user"""
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        level = model.get_path(node).get_depth()
        if level == 1:  # category selected
            return
        elif level == 3:  # sub user selected, get parent
            node = model.iter_parent(node)

        name = self.ask_user_dialog(2)
        if name:
            if self.does_user_exist(name):
                showwarning(_("User Exists"), _("Username exists"))
                return

        iternew = self.users_store.insert(node, 1, [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])

        self.controller.populate_users_chooser()
        # open the right tab to allow entering the address
        self.arw["treeview1"].expand_row(model.get_path(iternew), True)
        sel = self.arw["treeview1"].get_selection()
        sel.select_iter(iternew)
        self.load_user("", "", iternew)

    def add_user_above(self, widget):
        self.add_new_user(widget, "above")

    def add_user_below(self, widget):
        # used by the right click menu and by the add button
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        level = model.get_path(node).get_depth()
        if level == 1:
            self.add_new_category(widget)
        else:
            self.add_new_user(widget)

    def add_new_user(self, widget, mode=None, parent=None):
        """ adds a new user under the category selected, or below the user selected """
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        level = model.get_path(node).get_depth()
        name = self.ask_user_dialog(2)
        if name:
            if self.does_user_exist(name):
                showwarning(_("User Exists"), _("Username exists"))
                return

            if level == 1:  # if a category is selected, insert below it
                iternew = self.users_store.insert(node, 1, [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])
                path = model.get_path(node)
                self.arw["treeview1"].expand_row(path, True)  # open the path to allow entering the adress
            elif level == 2:  # A user is selected
                if mode == "above":
                    iternew = self.users_store.insert_before(None, node,
                                                             [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])
                else:
                    iternew = self.users_store.insert_after(None, node,
                                                            [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])
            else:
                return

            self.controller.populate_users_chooser()
            # open the right tab to allow entering the address
            sel = self.arw["treeview1"].get_selection()
            sel.select_iter(iternew)
            self.load_user("", "", iternew)
            self.arw["notebook5"].set_current_page(1)
            showwarning(_("Enter address"), _("Please, enter the Mac or IP address for this user"))

    def does_category_exist(self, name):
        """Check if the category exists or not"""
        name = name.strip().lower()
        for row in self.users_store:
            existing_name = row[0].strip().lower()
            if existing_name == name:
                return True
        return False

    def add_new_category(self, widget):
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        if node is None:
            level = 1
        else:
            level = model.get_path(node).get_depth()
        name = self.ask_user_dialog(level)
        if name:
            if self.does_category_exist(name):
                showwarning(_("Category Exists"), _("The category name already exists"))
                return
            self.users_store.insert_after(None, node, [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])

    def delete_user(self, widget):
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        name = model.get_value(node, 0)
        if model.iter_has_child(node):
            res = askyesno("Remove user", "Do you want to remove category %s?" % name)
        else:
            res = askyesno("Remove user", "Do you want to remove user %s?" % name)
        if res:
            self.users_store.remove(node)

            # User should be removed from the maclist too
            if name in self.controller.maclist:
                del self.controller.maclist[name]

            # Remove user from the filter_store
            for item in self.controller.filter_store:
                users = (item[5] or '').split('\n')
                try:
                    users.remove(name)
                except ValueError:
                    continue
                self.controller.filter_store.set_value(item.iter, 5, '\n'.join(users))

            # Refresh the proxy users list
            self.controller.filter_rules.update_filter_user_list()

    def rename_user(self, widget):
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        name = model.get_value(node, 0)
        x = ask_text(self.arw["window1"], "Name of the user :", name)
        if x is None:
            return
        else:
            # Rename all existing entries in the filter_store
            for item in self.controller.filter_store:
                users = (item[5] or '').split('\n')
                if name in users:
                    i = users.index(name)
                    users[i] = x
                self.controller.filter_store.set_value(item.iter, 5, '\n'.join(users))
                # self.controller.load_filter_user(self.arw['treeview3'], event=None)
            # update the mac list and the devices list
            self.controller.maclist[x] = self.controller.maclist[name]
            del self.controller.maclist[name]
            self.controller.devicelist[x] = self.controller.devicelist[name]
            del self.controller.devicelist[name]

            # Refresh the proxy users list
            self.controller.filter_rules.update_filter_user_list()

            self.users_store.set(node, [0], [x])

    def rename_category(self, widget):
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        name = model.get_value(node, 0)
        x = self.ask_user_dialog(1, name)

        if x is None:
            return
        else:
            self.users_store.set(node, [0], [x])

    def change_category(self, widget, void, cat):

        # get user data
        row = []
        for i in range(self.users_store.get_n_columns()):
            row.append(self.users_store.get_value(self.controller.iter_user, i))

        # subusers
        sub_users = []
        model = self.users_store
        child = model.iter_children(self.controller.iter_user)
        while child:
            childrow = []
            for i in range(model.get_n_columns()):
                childrow.append(model.get_value(child, i))
            sub_users.append(childrow)
            child = model.iter_next(child)


        node = self.cat_list[cat]
        iter_new = self.users_store.append(node, row)
        for subuser in sub_users:
            model.append(iter_new, subuser)

        self.users_store.remove(self.controller.iter_user)

        # self.users_store.move_after(self.controller.iter_user, node)       # serait plus élégant mais ne marche pas

    def mac_address_fullscreen(self, widget):
        if widget.get_active():
            # value doesn't really matter, it will be limited by the Height request property in Glade of the Gtk Box
            # for the filters
            self.arw['user_summary_paned'].set_position(800)
        else:
            # resets it back to original position
            self.arw['user_summary_paned'].set_position(-1)

    def check_addresses(self, widget):
        buffer = self.arw['maclist'].get_buffer()
        (start_iter, end_iter) = buffer.get_bounds()
        value = buffer.get_text(start_iter, end_iter, False)

        OK = True
        for v in value.split('\n'):
            if v.startswith("#"):
                continue
            if v.strip() == "":
                continue
            if not mac_address_test(v) and not ip_address_test(v):
                showwarning(_("Address Invalid"), _("The address \n%s\n entered is not valid") % v)
                OK = False
        if OK:
            showwarning(_("Addresses OK"), _("All addresses are valid"))



    """ User Summary """

    def user_summary(self, user1, level):

        parent_iter = self.users_store.iter_parent(self.controller.iter_user)
        if level == 3:
            parent_iter = self.users_store.iter_parent(parent_iter)
        if not parent_iter:
            parent_iter = self.controller.iter_user

        self.arw['user_summary_frame_label'].set_label(_("Summary For ") + user1)

        if user1 not in self.controller.maclist:
            self.arw['maclist'].get_buffer().set_text(
                _("# No mac address for this user3")
            )

        internet_filtered = self.users_store.get_value(parent_iter, 6)
        internet_open = self.users_store.get_value(parent_iter, 7)

        if internet_filtered:
            self.arw['user_summary_internet_icon'].set_from_pixbuf(internet_filtered_icon)
            self.arw["user_summary_category_label"].set_markup(_("<b><span color='green' size='x-large'>Access to Internet is limited for this user</span></b>"))
            self.arw["user_summary_tree_view"].show()
            self.arw["user_summary_footnote"].show()
        elif internet_open:
            self.arw['user_summary_internet_icon'].set_from_pixbuf(internet_full_icon)
            self.arw["user_summary_category_label"].set_markup(_("<b><span color='blue' size='x-large'>This user has full Internet access</span></b>"))
            self.arw["user_summary_tree_view"].hide()
            self.arw["user_summary_footnote"].hide()
        else:
            self.arw['user_summary_internet_icon'].set_from_pixbuf(internet_denied_icon)
            self.arw["user_summary_category_label"].set_markup(_("<b><span color='red' size='x-large'>This user has no Internet access</span></b>"))
            self.arw["user_summary_tree_view"].hide()
            self.arw["user_summary_footnote"].hide()

        store = self.arw['user_summary_tree_store']
        store.clear()

        # firewall permissions

        # 0 - name
        # 1 - time conditions
        # 2 - icon1
        # 3 - icon2
        # 4 - text colour
        # 5 - strikethrough
        # 6 - proxy row reference
        for row in self.controller.firewall_store:
            users = row[6].split("\n")
            print(users)
            for userx in users:
                if userx.strip() == user1:
                    parent_iter = store.append(None)
                    store.set_value(parent_iter, 0, row[0])
                    store.set_value(parent_iter, 1, row[4])

                    store.set_value(parent_iter, 5, row[1] == 'no')

                    if row[2] == 'deny':
                        store.set_value(parent_iter, 4, 'red')
                        colour = 'red'
                    else:
                        store.set_value(parent_iter, 4, 'green')
                        colour = 'green'

                    for port in row[3].split('\n'):
                        child_iter = store.append(parent_iter)
                        store.set_value(child_iter, 0, port)
                        store.set_value(child_iter, 4, colour)

        # Internet filter

        # 0 : section
        # 1 : active     (off/on)
        # 2 : action     (deny/allow)
        # 3 : time_condition
        # 4 : #comments
        # 5 : user
        # 6 : mac
        # 7 : dest_group
        # 8 : dest_domains
        # 11 : toggleButton (0/1) users [list/all]
        # 12 : toggleButton (0/1) destination [list/all]
        # 13 : toggleButton (0/1) [deny/allow]
        # 14 : checkbox    (0/1)  [off/on]
        # 15 : color1      (foreground)
        # 16 : color2      (background)
        # 19 : chekbox assistant (0/1)

        i = 0
        for row in self.controller.filter_store:
            if not row[5]:
                users = [""]
            else:
                users = row[5].strip().split("\n")

            for userx in users:

                if userx.strip() == user1 or row[11] == 1:
                    parent_iter = store.append(None)
                    if row[11]:
                        name = '<i>' + row[0] + '</i>'
                    else:
                        name = row[0]
                    store.set_value(parent_iter, 0, name)
                    store.set_value(parent_iter, 1, row[3])

                    store.set_value(parent_iter, 5, row[1] == 'no')

                    if row[13]:                                     # if the rule denies, the line is red
                        store.set_value(parent_iter, 4, 'green')
                        colour = 'green'
                    else:
                        store.set_value(parent_iter, 4, 'red')
                        colour = 'red'

                    if row[12]:
                        if colour != 'red':
                            store.set_value(parent_iter, 2, internet_full_icon)
                            store.set_value(parent_iter, 4, 'blue')
                            colour = 'blue'
                        else:
                            store.set_value(parent_iter, 2, internet_denied_icon)
                            store.set_value(parent_iter, 4, 'red')
                            colour = 'red'

                    elif not (internet_filtered or internet_open):
                        store.set_value(parent_iter, 4, 'red')
                        colour = 'red'
                        store.set_value(parent_iter, 2, internet_denied_icon)
                    else:
                        store.set_value(parent_iter, 2, internet_filtered_icon)

                    if row[1].strip() == 'on':
                        store.set_value(parent_iter, 5, False)
                    else:
                        store.set_value(parent_iter, 4, 'gray')
                        store.set_value(parent_iter, 5, True)
                        colour = 'gray'

                    for domain in row[8].strip().split('\n'):
                        child_iter = store.append(parent_iter)
                        if row[11]:
                            domain = '<i>' + domain + '</i>'
                        store.set_value(child_iter, 0, domain)
                        store.set_value(child_iter, 6, i)
                        store.set_value(child_iter, 4, colour)

                    store.set_value(parent_iter, 6, i)

            i += 1

    def summary_warning(self, widget=None, event=None):

        if event.get_keyval()[1] in range(65360, 65370):  # allow direction keys
            return
        message = _("The user summary is not editable. \n See the Internet Filter tab.")
        showwarning(_("Not editable"), message, 2)


    def load_user_config(self, widget, event, iternew=None):
        """ When user clicks on a line of the summary, selects the right rule in proxy tab, and displays this tab"""

        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                store = self.arw['user_summary_tree_store']
                if iternew:
                    iter1 = iternew
                    level = 2
                else:
                    path = widget.get_path_at_pos(event.x, event.y)
                    if path is None:  # click outside a valid line
                        return
                    iter1 = store.get_iter(path[0])
                    text = store[iter1][6]
                    print(text)
                    sel = self.arw["treeview3"].get_selection()
                    sel.select_path(int(text))
                    self.arw["notebook3"].set_current_page(1)
                    self.controller.filter_rules.load_filter_user(None, None)



    """ Drag and Drop """

    def users_drag_data_get(self, treeview, drag_context, data, info, time):

        (model, iter1) = treeview.get_selection().get_selected()
        if iter1:
            path = model.get_string_from_iter(iter1)
            data.set_text(path, -1)

    def users_drag_data_received(self, treeview, drag_context, x, y, data, info, etime):

        if time.time() - self.mem_time < 1:  # dirty workaround to prevent two drags
            return
        self.mem_time = time.time()
        path = data.get_text()
        source_level = len(path.split(":"))
        model = treeview.get_model()
        iter_source = model.get_iter(path)

        # if level == 1:
        #    print("moving categories not yet implemented")
        #    return

        # create the row to insert
        row = []
        for i in range(model.get_n_columns()):
            row.append(model.get_value(iter_source, i))

        sub_users = []

        if source_level == 2:  # user
            child = model.iter_children(iter_source)
            while child:
                childrow = []
                for i in range(model.get_n_columns()):
                    childrow.append(model.get_value(child, i))
                sub_users.append(childrow)
                child = model.iter_next(child)

        drop_info = treeview.get_dest_row_at_pos(x, y)
        iter_dest = None

        if source_level == 1:
            # Move an entire Category
            path1, position = drop_info
            iter1 = model.get_iter(path1)

            # Always ensure top level
            if not model.iter_has_child(iter1):
                iter1 = model.iter_parent(iter1)

            if (position == Gtk.TreeViewDropPosition.BEFORE
                    or position == Gtk.TreeViewDropPosition.BEFORE):
                iter_dest = model.insert_before(None, iter1, row)
            else:
                iter_dest = model.insert_after(None, iter1, row)

            child_iter = model.iter_children(iter_source)

            # Move users
            while child_iter:
                child_row = []
                for i in range(model.get_n_columns()):
                    child_row.append(model.get_value(child_iter, i))
                child_iter = model.iter_next(child_iter)

            model.remove(iter_source)
        else:
            if drop_info:
                path1, position = drop_info
                dest_level = path1.get_depth()
                iter1 = model.get_iter(path1)

                if dest_level == 1:
                    # print("drop on category")
                    new_iter = model.append(iter1, row)
                    model.remove(iter_source)
                elif (position == Gtk.TreeViewDropPosition.BEFORE
                      or position == Gtk.TreeViewDropPosition.BEFORE):
                    new_iter = model.insert_before(None, iter1, row)
                    model.remove(iter_source)
                    print("BEFORE")
                else:
                    new_iter = model.insert_after(None, iter1, row)
                    model.remove(iter_source)

                for subuser in sub_users:
                    model.append(new_iter, subuser)

                iter_dest = new_iter
            else:
                iter_dest = model.append([data])

        if iter_dest:
            self.arw['treeview1'].get_selection().select_iter(iter_dest)

    #        if drag_context.get_actions() == Gdk.DragAction.MOVE:
    #            drag_context.finish(True, True, etime)
