import time

from gi.repository import Gdk, Gtk

from actions import DRAG_ACTION
from util import (
    askyesno, ask_text, get_config_path,
    format_comment, format_line, format_time, format_userline, format_domainline, format_name,
    showwarning)


# 3 - proxy
class ProxyUsers:
    mem_time = 0

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.arw["proxy_users"].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [], DRAG_ACTION)
        self.arw['proxy_users'].drag_source_add_text_targets()
        self.arw['proxy_users'].connect("drag-data-get", self.proxy_users_data_get)
        self.arw['proxy_users'].drag_dest_set(Gtk.DestDefaults.DROP, [], DRAG_ACTION)
        self.arw['proxy_users'].drag_dest_add_text_targets()
        self.arw['proxy_users'].connect("drag-data-received", self.update_proxy_user_list_view)

        """
        0 : section
        1 : active     (off/on)
        2 : action     (deny/allow)
        3 : time_condition
        4 : #comments
        5 : user
        6 : mac
        7 : dest_group
        8 : dest_domain
        9 : (previously : dest_ip. No longer used)
        10 : (previously : destination. No longer used)
        11 : toggleButton (0/1) users [list/all]
        12 : toggleButton (0/1) destination [list/all]
        13 : toggleButton (0/1) [deny/allow]
        14 : checkbox    (0/1)  [off/on]
        15 : color1      (foreground)
        16 : color2      (background)
        17 : reserved (str)
        18 : reserved (str)
        19 : chekbox assistant (0/1)
        20 : reserved (0/1)
        """

        self.proxy_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, int, int, int, int, str,
                                         str, str, str, int, int)  #
        self.cell3 = Gtk.CellRendererText()
        self.check2 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check2.connect('toggled', self.toggle_col14, self.proxy_store)
        # Test pour Daniel
        self.check3 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check3.connect('toggled', self.toggle_col5, self.proxy_store)
        self.check4 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check4.connect('toggled', self.toggle_col12, self.proxy_store)
        self.check5 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check5.connect('toggled', self.toggle_col13_proxy, self.proxy_store)

        self.treeview3 = self.arw["treeview3"]
        self.treeview3.set_model(self.proxy_store)
        self.treeview3.connect("button-press-event", self.load_proxy_user)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell3, markup=0, foreground=15, background=16)
        self.tvcolumn.set_fixed_width(220)
        self.treeview3.append_column(self.tvcolumn)

        self.tvcolumn = Gtk.TreeViewColumn(_('Users\nList/All'), self.check3, active=11)
        self.treeview3.append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('Dest.\nList/All'), self.check4, active=12)
        self.treeview3.append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('Allow/\nDeny'), self.check5, active=13)
        self.treeview3.append_column(self.tvcolumn)
        self.tvcolumn = Gtk.TreeViewColumn(_('On/Off'), self.check2, active=14)
        self.treeview3.append_column(self.tvcolumn)

        self.switch_gui()

    def switch_gui(self,widget = None):

        if widget == None:
            gui = "buttons"
        else:
            if self.arw["switch_gui"].get_active() == 0 :
                gui = "buttons"
            else:
                gui ="check"
        self.set_gui(gui)

    def set_gui(self, gui):
        # button interface
        if gui == "buttons":
            for col in (1,2,3):
                self.arw["treeview3"].get_column(col).set_visible(False)
            for button in ["toggle_proxy_user_open_button", "toggle_proxy_open_button", "toggle_proxy_allow_button"]:
                self.arw[button].show()
            self.arw["proxy_users_box"].set_size_request(300,100)
        else:
            # checkboxes interface
            for col in (1,2,3):
                self.arw["treeview3"].get_column(col).set_visible(True)
            for button in ["toggle_proxy_user_open_button", "toggle_proxy_open_button", "toggle_proxy_allow_button"]:
                self.arw[button].hide()
            self.arw["proxy_users_box"].set_size_request(470,100)







    def toggle_col12(self, widget, a=0, b= 0):              # TODO test Daniel, et aussi les autres dessous
        # callback of the open access button in proxy tab.
        # col 12 = open access state; col 16 = background color

        treestore = self.proxy_store
        if treestore.get_value(self.controller.iter_proxy, 12) == 0:
            treestore.set_value(self.controller.iter_proxy, 12, 1)
            treestore.set_value(self.controller.iter_proxy, 10, "any")
            treestore.set_value(self.controller.iter_proxy, 16, "#ffff88")
        else:
            treestore.set_value(self.controller.iter_proxy, 12, 0)
            treestore.set_value(self.controller.iter_proxy, 10, "")
            treestore.set_value(self.controller.iter_proxy, 16, "#ffffff")
            #self.arw["toggle_proxy_open_button"].set_image(self.controller.red_button)
        self.load_proxy_user2()

    def toggle_col5(self, widget, a=0, b= 0):
        """Toggle any user or specific users"""
        if self.proxy_store.get_value(self.controller.iter_proxy, 11) == 0:
            self.proxy_store.set_value(self.controller.iter_proxy, 11, 1)
            markup = self.proxy_store.get_value(self.controller.iter_proxy, 0)
            self.proxy_store.set_value(self.controller.iter_proxy, 0, "<i>" + markup + "</i>")
            self.arw["proxy_users"].hide()
        else:
            self.proxy_store.set_value(self.controller.iter_proxy, 11, 0)
            markup = self.proxy_store.get_value(self.controller.iter_proxy, 0)
            markup = markup.replace("<i>", "")
            markup = markup.replace("</i>", "")
            self.proxy_store.set_value(self.controller.iter_proxy, 0, markup)
            self.arw["proxy_users"].show()
        self.update_proxy_user_list()

        self.load_proxy_user2()

    def toggle_col13_proxy(self, widget, a=0, b= 0):
        # callback of the allow/deny button in proxy tab.
        # col 13 = allow/deny state; col 15 = text color

        treestore = self.proxy_store
        if treestore.get_value(self.controller.iter_proxy, 13) == 0:
            treestore.set_value(self.controller.iter_proxy, 13, 1)
            treestore.set_value(self.controller.iter_proxy, 2, "allow")
            treestore.set_value(self.controller.iter_proxy, 15, "#009900")
            self.arw["allow_deny_groups"].set_text("Allowed Groups")
            self.arw["allow_deny_sites"].set_text("Allowed Sites")
        else:
            treestore.set_value(self.controller.iter_proxy, 13, 0)
            treestore.set_value(self.controller.iter_proxy, 2, "deny")
            treestore.set_value(self.controller.iter_proxy, 15, "#f00000")
            self.arw["allow_deny_groups"].set_text("Denied Groups")
            self.arw["allow_deny_sites"].set_text("Denied Sites")

        self.load_proxy_user2()


    def toggle_col14(self, cellrenderer, row, treestore):
        # callback of the on/off checkbox in proxy tab.
        # col 14 = on/off state; col 15 = text color
        if treestore[row][14] == 0:
            treestore[row][14] = 1
            treestore[row][1] = "on"
            markup = treestore[row][0]
            markup = markup.replace("<s>", "")
            treestore[row][0] = markup.replace("</s>", "")

            if treestore[row][13] == 1:
                treestore[row][15] = "#009900"
            else:
                treestore[row][15] = "#ff0000"
        else:
            treestore[row][14] = 0
            treestore[row][1] = "off"
            treestore[row][15] = "#bbbbbb"
            markup = treestore[row][0]
            treestore[row][0] = "<s>" + markup + "</s>"

        #self.populate_proxy()


    def add_rule_below(self, widget):
        # add rule in the proxy tab
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        x = ask_text(self.arw["window1"], "Name of the new rule :", "")
        if x is None:
            return
        else:
            name = format_name(x)
            iter1 = self.controller.proxy_store.insert_after(node,
                                                             [name, "on", "allow", "", "", "", "", "", "", "", "", 0,
                                                              0, 1, 1, "#009900", "#ffffff", "", "", 0, 0])

    def delete_rule(self, widget):
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        name = model.get_value(node, 0)
        if askyesno("Remove filter rule", "Do you want to remove %s?" % name):
            self.controller.proxy_store.remove(node)

    def edit_rule(self, widget):
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        name = model.get_value(node, 0)
        x = ask_text(self.arw["window1"], "Name of the rule :", name)
        if x is None:
            return
        else:
            x = format_name(x)
            self.controller.proxy_store.set(node, [0], [x])


    def proxy_user_has_any(self):
        """Return True if the proxy user has any"""
        return 'any' in self.proxy_store.get_value(self.controller.iter_proxy, 5).split('\n')

    def delete_proxy_user(self, widget):
        model, iter = self.arw['proxy_users'].get_selection().get_selected()
        name = model.get_value(iter, 0).strip()

        names = self.proxy_store.get_value(self.controller.iter_proxy, 5).split('\n')
        if name not in names:
            return

        res = askyesno("Remove user", "Do you want to remove user %s?" % name)
        if not res:
            return

        names.remove(name)

        self.proxy_store.set_value(self.controller.iter_proxy, 5, '\n'.join(names))
        self.update_proxy_user_list()

    def update_proxy_user_list_view(self, widget, ctx, x, y, data, info, etime):
        """Add a user or a group to the list"""
        # called by the drag_data_received signal
        # TODO name should be changed, because it is not clear

        new_name = data.get_text().split("#")[0].strip()

        if self.proxy_user_has_any():
            return

        if not data.get_text().split("#")[1] == "chooser1":      # if data does not come from the right chooser, return
            return

        model, iter = self.arw['chooser1'].get_selection().get_selected()

        if time.time() - self.mem_time < 1:  # dirty workaround to prevent two drags
            return
        self.mem_time = time.time()

        if model.get_value(iter, 3):
            # This is a category, not a user so show a warning and do nothing
            showwarning(_("Not Supported"), _("Choosing a category is not yet supported"))
            return

        position = None

        model = widget.get_model()
        data1 = data.get_text().split("#")
        path = data1[0]
        if len(data1) == 2 :
            source_model = self.arw[data1[1]].get_model()
        else:
            source_model = model

        try:
            iter_source = source_model.get_iter(path)
            values = [source_model.get_value(iter_source, i) for i in range(model.get_n_columns())]
        except TypeError:
            iter_source = None
            values = None

        dest = widget.get_dest_row_at_pos(x, y)
        if dest:
            drop_path, position = dest
            iter1 = model.get_iter(drop_path)

            if (position == Gtk.TreeViewDropPosition.BEFORE
                    or position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE):
                iter_dest = model.insert_before(iter1, ['' for x in range(model.get_n_columns())])
            else:
                iter_dest = model.insert_after(iter1, ['' for x in range(model.get_n_columns())])
        else:
            iter_dest = model.insert(-1)

        if iter_source:
            for i in range(model.get_n_columns()):
                model.set_value(iter_dest, i, values[i])
            if source_model == model:       # move row in the list
                model.remove(iter_source)
            names = [name[0] for name in model]
            self.proxy_store.set_value(self.controller.iter_proxy, 5, '\n'.join(names))
            return

        names = self.proxy_store.get_value(self.controller.iter_proxy, 5).split('\n')
        if new_name in names:
            return
        names.append(new_name)
        self.proxy_store.set_value(self.controller.iter_proxy, 5, '\n'.join(names))
        self.update_proxy_user_list(self.controller.iter_proxy)

    def proxy_user_select(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                self.arw["proxy_users_menu"].popup(None, None, None, None, event.button, event.time)

    def update_proxy_user_list(self, proxy_iter=None):
        """ (re)create the users list from the store """
        # called when something is changed in the store
        if not proxy_iter:
            proxy_iter = self.controller.iter_proxy

        self.arw['proxy_users_store'].clear()

        # add users
        users = self.proxy_store[proxy_iter][5]  # user
        if not users:
            return None

        for name in users.split('\n'):
            if name:
                iter = self.arw['proxy_users_store'].append()
                self.arw['proxy_users_store'].set_value(iter, 0, name)

        # add mac, if any
        users += self.proxy_store[proxy_iter][6]  # mac

        for name in self.proxy_store[proxy_iter][6].split('\n'):
            if name:
                iter = self.arw['proxy_users_store'].append()
                self.arw['proxy_users_store'].set_value(iter, 0, name)

        return users

    def load_proxy_user(self, widget, event):

        human_days = ""
        # Loads user data when a user is selected in the list
        if event:
            path = widget.get_path_at_pos(event.x, event.y)
            if path is None:  # if click outside the list, unselect all.
                # It is good to view the global configurations with the colors,
                # otherwise, the cursor always masks one line.
                sel = self.arw["treeview3"].get_selection()
                sel.unselect_all()
                return
            iter1 = self.proxy_store.get_iter(path[0])
        else:
            model, iter1 = self.arw["treeview3"].get_selection().get_selected()
            if not iter1:
                return

        """# debug
        i = 0
        row = self.proxy_store[iter1]
        try :
            for i in range(20):
                print(i, " = ", row[i])
        except:
            pass
        """

        self.controller.iter_proxy = iter1

        # time conditions
        data1 = self.proxy_store[iter1][3].strip()
        if data1 == "":
            self.arw["proxy_time_condition_days"].set_text("")
            self.arw["proxy_time_condition_from"].set_text("")
            self.arw["proxy_time_condition_to"].set_text("")
            self.arw["time_button_label"].set_text(_("All day\nand week"))

        elif len(data1) > 8:
            try:
                tmp1 = data1.split()
                tmp2 = tmp1[1].split("-")
                days = tmp1[0].strip()
                human_days = self.convert_days_to_local(days)
                time_from = tmp2[0].strip()
                time_to = tmp2[1].strip()
                if self.proxy_store[self.controller.iter_proxy][13] == 1:      # change colour for deny or allow
                    color =  'foreground="#008800"'
                else :
                    color = 'foreground="#ee0000"'
                button_text ='<span ' + color + ' weight="bold" >'    # size="large" deleted
                button_text += human_days + '\n  <span size="large">' + time_from + "-" + time_to + "</span></span>"
                self.arw["proxy_time_condition_days"].set_text(days)
                self.arw["proxy_time_condition_from"].set_text(time_from)
                self.arw["proxy_time_condition_to"].set_text(time_to)
                self.arw["time_button_label"].set_markup(button_text)

            except:
                print("Error handling time condition :", data1)
        else:
            print("Invalid time :", data1)

        self.arw["proxy_#comments"].get_buffer().set_text(self.proxy_store[iter1][4])

        self.update_proxy_user_list(iter1)
        self.controller.proxy_group.update_proxy_group_list(iter1)

        # add dest_domains
        data1 = self.proxy_store[iter1][8]  # dest_domain
        # add dest_ip, if any
        data1 += self.proxy_store[iter1][9]  # dest_ip
        self.arw["proxy_dest"].get_buffer().set_text(data1)
        self.load_proxy_user2()

    def load_proxy_user2(self):
        # used by the function above, and by the buttons of the proxy tab
        list_color = Gdk.Color(red=50535, green=50535, blue=60535)

        if self.proxy_store[self.controller.iter_proxy][11] == 1:
            self.arw["proxy_users_stack"].set_visible_child(self.arw["proxy_users_all"])
            x = self.arw["toggle_proxy_user_open_button"]
            self.arw["toggle_proxy_user_open_button"].set_image(self.controller.all_button)

        else:
            self.arw["proxy_users_stack"].set_visible_child(self.arw["proxy_users_scroll_window"])
            self.arw["toggle_proxy_user_open_button"].set_image(self.controller.list_button)


        # set full access
        if self.proxy_store[self.controller.iter_proxy][12] == 1:
            self.arw["proxy_dest_stack"].set_visible_child(self.arw["proxy_dest_all"])
            self.arw["toggle_proxy_open_button"].set_image(self.controller.all2_button)

        else:
            self.arw["toggle_proxy_open_button"].set_image(self.controller.list2_button)
            self.arw["proxy_dest_stack"].set_visible_child(self.arw["proxy_dest_grid"])


        # set allow/deny button
        if self.proxy_store[self.controller.iter_proxy][13] == 1:
            self.arw["toggle_proxy_allow_button"].set_image(self.controller.allow_button)
            message = '<span foreground="#00aa00">' + _("All destinations \nallowed.") +  '</span>'
            self.arw["proxy_dest_all"].set_markup(message)
            self.arw["allow_deny_groups"].set_markup('<span foreground="#00aa00">' + _("Allowed Groups") +  '</span>')
            self.arw["allow_deny_sites"].set_markup('<span foreground="#00aa00">' + _("Allowed Sites") +  '</span>')

        else:
            self.arw["toggle_proxy_allow_button"].set_image(self.controller.deny_button)
            message = '<span foreground="#ff0000">' + _("All connections\nto Internet\nare prohibited.") +  '</span>'
            self.arw["proxy_dest_all"].set_markup(message)
            self.arw["allow_deny_groups"].set_markup('<span foreground="#ff0000">' + _("Denied Groups") +  '</span>')
            self.arw["allow_deny_sites"].set_markup('<span foreground="#ff0000">' + _("Denied Sites") +  '</span>')

        # TODO : what is the use of the following code, which does nothing ?
        groups_iter = self.arw['proxy_groups_store'].get_iter_first()
        has_groups = groups_iter is not None

        text_buffer = self.arw["proxy_dest"].get_buffer()
        (start_iter, end_iter) = text_buffer.get_bounds()
        dest_text = text_buffer.get_text(start_iter, end_iter, False)
        pass

    def convert_days_to_local(self, days):
        locale = _("Mo,Tu,We,Th,Fr,Sa,Su").split(",")
        days_locale = []
        for day in days:
            days_locale.append(locale[int(day) - 1])
        days_locale = " ".join(days_locale)
        return days_locale


    def expand_users_view(self, widget):
        if widget.get_active():
            self.arw['expand_permissions_toggle'].set_active(False)
            self.arw['internet_filter_paned'].set_position(10000)
        else:
            self.arw['internet_filter_paned'].set_position(self.arw['internet_filter_paned'].get_allocated_height() / 2)

    def expand_permissions_view(self, widget):
        if widget.get_active():
            self.arw['expand_users_toggle'].set_active(False)
            self.arw['internet_filter_paned'].set_position(1)
        else:
            self.arw['internet_filter_paned'].set_position(self.arw['internet_filter_paned'].get_allocated_height() / 2)

    def show_time_conditions_window(self, widget):
        self.arw["proxy_time_conditions"].show()
    def hide_time_conditions_window(self, widget):
        self.arw["proxy_time_conditions"].hide()
        self.load_proxy_user("","")

    def proxy_profile_select(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                self.arw["proxy_profiles_menu"].popup(None, None, None, None, event.button, event.time)

    def proxy_users_data_get(self, treeview, drag_context, data, info, time):
        (model, iter1) = treeview.get_selection().get_selected()
        if iter1:
            path = model.get_string_from_iter(iter1)
            data.set_text(path, -1)

    def populate_proxy(self):
        self.proxy_store.clear()
        data1 = self.controller.config["rules"]
        keys = ["active", "action", "time_condition", "#comments",
                "users", "",
                "dest_groups", "dest_domains", "", "",
                "any_user", "any_destination", "allow_deny" ]
        for section in data1:
            if section[0:2] == "@_":  # generated sections must not be loaded
                continue

            data2 = data1[section]
            if data2.get("any_user"):
                name = '<i>' + section + '</i>'
            else:
                name = section
            if data2.get("active") == 'off':
                 name = "<s>" + name + "</s>"
            out = [name]

            for key in keys:
                if key in data1[section]:
                    data = data1[section][key]

                    if key == 'time_condition':
                        # days = parse_date_format_from_squid(data[0].split(' ')[0])
                        days = data.split(' ')[0]
                        if len(data.split(' ')) > 1:
                            data = days + ' ' + data.split(' ', 1)[1]
                        else:
                            data = days

                    if isinstance(data, list):
                        out.append("\n".join(data) + "\n")
                    else:
                        out.append(data)
                else:
                    out.append("")
            # check boxes and ToggleButtons
##            if "any_user" in data2:
##                anyuser = data1[section]["any_user"]
##            else:
##                anyuser = 0
            out += [1, "#009900", "#ffffff", "", "", 0, 0]

            self.proxy_store.append(out)

