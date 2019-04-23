import time

from gi.repository import Gtk, Gdk
from gi.repository.GdkPixbuf import Pixbuf

from actions import DRAG_ACTION
from icons import (
    internet_filtered_icon, internet_full_icon
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
        # section / user
        self.users_store = Gtk.TreeStore(str, str, str, str, int, int, int, int, int, str, str, Pixbuf, Pixbuf)  #

        self.treeview1 = self.arw["treeview1"]
        self.treeview1.set_model(self.users_store)
        self.arw['select_user_tree_view'].set_model(self.users_store)

        self.cell = Gtk.CellRendererText()
        self.cellpb = Gtk.CellRendererPixbuf(xalign=0.0)
        self.cellpb2 = Gtk.CellRendererPixbuf(xalign=0.0)

        self.tvcolumn = Gtk.TreeViewColumn(_('Filename'))
        self.treeview1.connect("button-press-event", self.load_user)

        self.tvcolumn.pack_start(self.cell, False)
        self.tvcolumn.pack_start(self.cellpb, False)
        self.tvcolumn.pack_start(self.cellpb2, False)
        self.tvcolumn.add_attribute(self.cell, "background", 10)
        # self.tvcolumn.add_attribute(self.cell, "foreground", 9)
        # self.tvcolumn.add_attribute(self.cell, "weight", 8)
        self.tvcolumn.add_attribute(self.cell, "text", 0)
        self.tvcolumn.add_attribute(self.cellpb, "pixbuf", 11)
        self.tvcolumn.add_attribute(self.cellpb2, "pixbuf", 12)

        # self.tvcolumn1 = gtk.TreeViewColumn(_('Restore'), self.check, active=3)
        # self.tvcolumn2 = gtk.TreeViewColumn(_('Test'), self.test, text=3)
        # self.tvcolumn = gtk.TreeViewColumn(_('Yes'), self.cell, text=0, background=2)
        self.treeview1.append_column(self.tvcolumn)
        # self.treeview1.append_column(self.tvcolumn1)

        # drag and drop for users tree
        self.arw["treeview1"].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [],
                                                       DRAG_ACTION)
        self.arw["treeview1"].drag_source_add_text_targets()
        self.arw["treeview1"].connect("drag-data-get", self.users_drag_data_get)

        self.arw["treeview1"].drag_dest_set(Gtk.DestDefaults.DROP, [], DRAG_ACTION)
        self.arw["treeview1"].drag_dest_add_text_targets()
        self.arw["treeview1"].connect("drag-data-received", self.users_drag_data_received)

    def populate_users(self):
        self.users_store.clear()
        data1 = self.controller.config["users"]

        # Email, Internet, Filtered, Open
        options_list = [0, 0, 0, 0, 0]
        for section in data1:

            options_list[0] = data1[section].get('@_email', [0])[0] == '1'
            options_list[1] = data1[section].get('@_internet', ['none'])[0] != 'none'
            options_list[2] = data1[section].get('@_internet', [''])[0] == 'filtered'
            options_list[3] = data1[section].get('@_internet', [''])[0] == 'open'

            internet_time_condition = data1[section].get("@_internet_time_condition", [''])[0]
            if internet_time_condition:
                days = internet_time_condition.split(' ')[0]
                # days = parse_date_format_from_squid(days)

                if len(internet_time_condition.split(' ')) > 1:
                    internet_time_condition = days + ' ' + internet_time_condition.split(' ', 1)[1]
                else:
                    internet_time_condition = days

            email_time_condition = data1[section].get("@_email_time_condition", [''])[0]
            if email_time_condition:
                days = email_time_condition.split(' ')[0]
                # days = parse_date_format_from_squid(days)

                if len(email_time_condition.split(' ')) > 1:
                    email_time_condition = days + ' ' + email_time_condition.split(' ', 1)[1]
                else:
                    email_time_condition = days

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
                    self.users_store.append(node, [user, "", "", "", 0, 0, 0, 0, 0, "", "#ffffff", None, None])

    def load_user(self, widget, event, iternew=None):
        """ loads data in right pane when a category or a user is selected in the tree"""

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
            self.arw["internet_email"].set_active(self.users_store[iter1][4] or self.users_store[iter1][7])
            self.arw["internet_access"].set_active(self.users_store[iter1][5])
            self.arw["internet_filtered"].set_active(self.users_store[iter1][6])
            self.arw["internet_open"].set_active(self.users_store[iter1][7])
            # adapt the right click menu
            self.arw["menu_add_above"].hide()
            self.arw["menu_add_below"].hide()
            self.arw["menu_add_user"].show()
            self.arw["menu_add_cat"].show()
            self.arw["menu_move_user"].hide()
            self.arw["menu_rename_user"].hide()
            self.arw["menu_rename_cat"].show()
            self.arw["simulate_user"].hide()

            self.arw['email_time_condition'].set_sensitive(
                self.users_store[self.controller.iter_user][4] or self.users_store[self.controller.iter_user][7]
            )

            self.arw['internet_time_condition'].set_sensitive(
                self.users_store[self.controller.iter_user][5] and self.users_store[self.controller.iter_user][7]
            )

            # time conditions internet
            data1 = self.users_store[iter1][3].strip()
            if not data1:
                self.arw["users_time_days_internet"].set_text("")
                self.arw["users_time_from_internet"].set_text("")
                self.arw["users_time_to_internet"].set_text("")
            elif len(data1) > 8:
                try:
                    tmp1 = data1.split()
                    tmp2 = tmp1[1].split("-")
                    days = tmp1[0].strip()
                    time_from = tmp2[0].strip()
                    time_to = tmp2[1].strip()

                    self.arw["users_time_days_internet"].set_text(days)
                    self.arw["users_time_from_internet"].set_text(time_from)
                    self.arw["users_time_to_internet"].set_text(time_to)
                except IndexError:
                    print("Error handling time condition :", data1)
            else:
                print("Invalid time :", data1)

            # time conditions email
            data1 = self.users_store[iter1][2].strip()
            if not data1:
                self.arw["users_time_days_email"].set_text("")
                self.arw["users_time_from_email"].set_text("")
                self.arw["users_time_to_email"].set_text("")
            elif len(data1) > 8:
                try:
                    tmp1 = data1.split()
                    tmp2 = tmp1[1].split("-")
                    days = tmp1[0].strip()
                    time_from = tmp2[0].strip()
                    time_to = tmp2[1].strip()

                    self.arw["users_time_days_email"].set_text(days)
                    self.arw["users_time_from_email"].set_text(time_from)
                    self.arw["users_time_to_email"].set_text(time_to)
                except IndexError:
                    print("Error handling time condition :", data1)
            else:
                print("Invalid time :", data1)

        elif level == 2:  # user level

            self.arw["users_stack"].set_visible_child(self.arw["user_summary_frame"])
            # adapt the right click menu
            self.arw["menu_add_above"].show()
            self.arw["menu_add_below"].show()
            self.arw["menu_add_user"].hide()
            self.arw["menu_add_cat"].hide()
            self.arw["menu_move_user"].show()
            self.arw["menu_rename_user"].show()
            self.arw["menu_rename_cat"].hide()
            self.arw["simulate_user"].show()

            username = self.users_store[iter1][0]
            buffer = self.arw["maclist"].get_buffer()
            if username in self.controller.maclist:
                data1 = "\n".join(self.controller.maclist[username])
                buffer.set_text(data1)
            else:
                buffer.set_text("")
                if not iternew:
                    alert("No mac address for this user !")

            self.user_summary(username)

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

    def ask_user_dialog(self, level, text = ""):
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
        return False

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

    def add_new_user(self, widget, mode=None):
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
            else:
                if mode == "above":
                    iternew = self.users_store.insert_before(None, node,
                                                             [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])
                else:
                    iternew = self.users_store.insert_after(None, node,
                                                            [name, "", "", "", 0, 0, 0, 0, 0, "", "", None, None])
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

    def rename_user(self, widget):
        (model, node) = self.arw["treeview1"].get_selection().get_selected()
        name = model.get_value(node, 0)
        x = ask_text(self.arw["window1"], "Name of the user :", name)
        if x is None:
            return
        else:
            # Rename all existing entries in the proxy_store
            for item in self.controller.proxy_store:
                users = item[5].split('\n')
                if name in users:
                    i = users.index(name)
                    users[i] = x
                self.controller.proxy_store.set_value(item.iter, 5, '\n'.join(users))
                #self.controller.load_proxy_user(self.arw['treeview3'], event=None)
            # update the mac list
            self.controller.maclist[x] = self.controller.maclist[name]
            del self.controller.maclist[name]

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

        node = self.cat_list[cat]
        self.users_store.append(node, row)
        self.users_store.remove(self.controller.iter_user)

        # self.users_store.move_after(self.controller.iter_user, node)       # serait plus élégant mais ne marche pas



    def check_addresses(self, widget):
        buffer = self.arw['maclist'].get_buffer()
        (start_iter, end_iter) = buffer.get_bounds()
        value = buffer.get_text(start_iter, end_iter, False)

        OK = True
        for v in value.split('\n'):
            if v.startswith("#"):
                continue
            if not mac_address_test(v) and not ip_address_test(v):
                showwarning(_("Address Invalid"), _("The address \n%s\n entered is not valid") % v)
                OK = False
        if OK:
            showwarning(_("Addresses OK"), _("All addresses are valid"))

    def confirm_select_user_popup(self, widget):
        self.arw['select_user_popup'].hide()

        model, iter = self.arw['select_user_tree_view'].get_selection().get_selected()
        target_user = model.get_value(iter, 0).strip()
        current_user = model.get_value(self.controller.iter_user, 0).strip()

        if target_user == current_user:
            return

        self.enable_simulated_user(current_user, target_user)

    def cancel_select_user_popup(self, widget):
        self.arw['select_user_popup'].hide()

    def simulate_user_toggled(self, widget):
        if self.block_signals:
            return

        if widget.get_active():
            self.arw['select_user_popup'].show()
        else:
            self.disable_simulated_user()

    def enable_simulated_user(self, user, target_user):
        """Add -@ to user and add +@ to target_user"""

        mac_list = []

        for mac in self.controller.maclist[user]:
            mac_list.append(mac)

        # Update the user to ignore previous set addresses
        self.controller.maclist[user] = ['-@' + mac for mac in mac_list]
        self.controller.maclist[user].append(
            "+@11:11:11:11:11:11")  # add a dummy address, to prevent errors created by a user without a valid address

        self.controller.maclist[target_user].extend(['+@' + mac for mac in mac_list])
        self.arw["maclist"].get_buffer().set_text('\n'.join(self.controller.maclist[user]))
        self.user_summary(user)

    def disable_simulated_user(self):
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

        current_user = self.users_store.get_value(self.controller.iter_user, 0).strip()
        self.arw["maclist"].get_buffer().set_text(
            '\n'.join(self.controller.maclist[current_user])
        )
        if user:
            self.user_summary(user)

    """ User Summary """

    def user_summary(self, user1):

        parent_iter = self.users_store.iter_parent(self.controller.iter_user)
        if not parent_iter:
            parent_iter = self.controller.iter_user

        self.arw['user_summary_frame_label'].set_label(_("Summary For ") + user1)

        if user1 not in self.controller.maclist:
            self.arw['maclist'].get_buffer().set_text(
                _("# No mac address for this user")
            )

##        email_time_conditions = self.users_store.get_value(parent_iter, 2)
##        internet_time_conditions = self.users_store.get_value(parent_iter, 3)
##        email_enabled = self.users_store.get_value(parent_iter, 4)
##        internet_enabled = self.users_store.get_value(parent_iter, 5)
##        internet_filtered = self.users_store.get_value(parent_iter, 6)
##        internet_open = self.users_store.get_value(parent_iter, 7)
##
##        if not email_enabled:
##            self.arw['user_summary_email_icon'].set_from_pixbuf(email_disabled_icon)
##        else:
##            self.arw['user_summary_email_icon'].set_from_pixbuf(email_icon)
##
##        if not internet_enabled:
##            self.arw['user_summary_internet_icon'].set_from_pixbuf(internet_disabled_icon)
##        elif internet_filtered:
##            self.arw['user_summary_internet_icon'].set_from_pixbuf(internet_filtered_icon)
##        elif internet_open:
##            self.arw['user_summary_internet_icon'].set_from_pixbuf(internet_full_icon)
##
##        # internet time conditions
##        if internet_time_conditions:
##            self.arw['user_summary_internet_time_conditions'].set_label(internet_time_conditions)
##        else:
##            self.arw['user_summary_internet_time_conditions'].set_label("")
##
##        # email time conditions
##        if email_time_conditions:
##            self.arw['user_summary_email_time_conditions'].set_label(email_time_conditions)
##        else:
##            self.arw['user_summary_email_time_conditions'].set_label("")

        store = self.arw['user_summary_tree_store']
        store.clear()

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

        i = 0
        for row in self.controller.proxy_store:
            users = row[5].split("\n")
            for userx in users:
                if userx.strip() == user1:
                    parent_iter = store.append(None)
                    store.set_value(parent_iter, 0, row[0])
                    store.set_value(parent_iter, 1, row[3])

                    store.set_value(parent_iter, 5, row[1] == 'no')

                    if row[2] == 'deny':
                        store.set_value(parent_iter, 4, 'red')
                        colour = 'red'
                    else:
                        store.set_value(parent_iter, 4, 'green')
                        colour = 'green'

                    if row[8] == 'any':
                        store.set_value(parent_iter, 2, internet_full_icon)
                        colour = 'blue'
                    else:
                        store.set_value(parent_iter, 2, internet_filtered_icon)

                    for domain in row[8].split('\n'):
                        child_iter = store.append(parent_iter)
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
                    self.controller.proxy_users.load_proxy_user(None, None)



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

        drop_info = treeview.get_dest_row_at_pos(x, y)

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
                model.insert_after(iter_dest, None, child_row)
                child_iter = model.iter_next(child_iter)

            model.remove(iter_source)
        else:
            if drop_info:
                path1, position = drop_info
                dest_level = path1.get_depth()
                iter1 = model.get_iter(path1)

                if dest_level == 1:
                    # print("drop on category")
                    model.append(iter1, row)
                    model.remove(iter_source)
                elif (position == Gtk.TreeViewDropPosition.BEFORE
                      or position == Gtk.TreeViewDropPosition.BEFORE):
                    model.insert_before(None, iter1, row)
                    model.remove(iter_source)
                    print("BEFORE")
                else:
                    model.insert_after(None, iter1, row)
                    model.remove(iter_source)
            else:
                model.append([data])

    #        if drag_context.get_actions() == Gdk.DragAction.MOVE:
    #            drag_context.finish(True, True, etime)
