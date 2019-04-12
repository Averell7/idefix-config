import time

from gi.repository import Gdk, Gtk

from actions import DRAG_ACTION
from util import (
        askyesno, ask_text, EMPTY_STORE, get_config_path,
        format_comment, format_line, format_time, format_userline, format_domainline, format_name
)


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
        9 : dest_ip
        10 : destination
        11 : toggleButton (0/1) users [list/all]
        12 : toggleButton (0/1) destination [list/all]
        13 : toggleButton (0/1) [deny/allow]
        14 : checkbox    (0/1)  [off/on]
        15 : color1      (foreground)
        16 : color2      (background)
        """

        self.proxy_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, int, int, int, int, str,
                                         str)  #
        self.cell3 = Gtk.CellRendererText()
        self.check2 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check2.connect('toggled', self.controller.toggle_col14, self.proxy_store)
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

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell3, text=0, foreground=15, background=16)
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
            self.arw["proxy_users"].hide()
        else:
            self.proxy_store.set_value(self.controller.iter_proxy, 11, 0)
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
                                                              0, 1, 1, "#009900", "#ffffff"])

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
        new_name = data.get_text().strip()

        if self.proxy_user_has_any():
            return

        position = None

        if time.time() - self.mem_time < 1:  # dirty workaround to prevent two drags
            return
        self.mem_time = time.time()

        model = widget.get_model()

        path = data.get_text()
        try:
            iter_source = model.get_iter(path)
            values = [model.get_value(iter_source, i) for i in range(model.get_n_columns())]
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
                model.set_value(iter_dest, i, model.get_value(iter_source, i))
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
        if not proxy_iter:
            proxy_iter = self.controller.iter_proxy

        self.arw['proxy_users_store'].clear()

        # add users
        data1 = self.proxy_store[proxy_iter][5]  # user
        for name in self.proxy_store[proxy_iter][5].split('\n'):
            if name:
                iter = self.arw['proxy_users_store'].append()
                self.arw['proxy_users_store'].set_value(iter, 0, name)

        # add mac, if any
        data1 += self.proxy_store[proxy_iter][6]  # mac

        for name in self.proxy_store[proxy_iter][6].split('\n'):
            if name:
                iter = self.arw['proxy_users_store'].append()
                self.arw['proxy_users_store'].set_value(iter, 0, name)

        return data1

    def load_proxy_user(self, widget, event):

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
            self.arw["time_button_label"].set_text("All day\nand week")

        elif len(data1) > 8:
            try:
                tmp1 = data1.split()
                tmp2 = tmp1[1].split("-")
                days = tmp1[0].strip()
                time_from = tmp2[0].strip()
                time_to = tmp2[1].strip()
                button_text ='<span foreground="#008800" weight="bold" size="large">'
                button_text += days + "\n" + time_from + "-" + time_to + "</span>"
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
            #self.arw['toggle_proxy_user_open'].set_label(_("<b>All</b>"))
            #self.arw["toggle_proxy_user_open_button"].modify_bg(Gtk.StateType.NORMAL,
            #                                                    Gdk.Color(red=60535, green=60535, blue=0))

        else:
            self.arw["proxy_users_stack"].set_visible_child(self.arw["proxy_users_scroll_window"])
            self.arw["toggle_proxy_user_open_button"].set_image(self.controller.list_button)
            #self.arw["toggle_proxy_user_open"].set_label(_("<b>List</b>"))
            #self.arw["toggle_proxy_user_open_button"].modify_bg(Gtk.StateType.NORMAL, list_color)



        # set full access
        if self.proxy_store[self.controller.iter_proxy][12] == 1:
            self.arw["proxy_dest_stack"].set_visible_child(self.arw["proxy_dest_all"])
            self.arw["toggle_proxy_open_button"].set_image(self.controller.all2_button)
#            self.arw["toggle_proxy_open"].set_label(_("<b>All</b>"))
#            self.arw["toggle_proxy_open_button"].modify_bg(Gtk.StateType.NORMAL,
#                                                           Gdk.Color(red=60535, green=60535, blue=0))
        else:
            self.arw["toggle_proxy_open_button"].set_image(self.controller.list2_button)
#            self.arw["toggle_proxy_open"].set_label(_("<b>List</b>"))
#            self.arw["toggle_proxy_open_button"].modify_bg(Gtk.StateType.NORMAL, list_color)
            self.arw["proxy_dest_stack"].set_visible_child(self.arw["proxy_dest_grid"])


        # set allow/deny button
        if self.proxy_store[self.controller.iter_proxy][13] == 1:                             # TODO Chris : it would be better for translators to use properties,instead of markup, but I don't know how to do that in css.
            self.arw["toggle_proxy_allow_button"].set_image(self.controller.allow_button)
            message = _('<span foreground="#00aa00">All destinations \nallowed. </span>')
            self.arw["proxy_dest_all"].set_markup(message)
            self.arw["allow_deny_groups"].set_markup(_('<span foreground="#00aa00">Allowed Groups</span>'))
            self.arw["allow_deny_sites"].set_markup(_('<span foreground="#00aa00">Allowed Sites</span>'))
            #self.arw["toggle_proxy_allow"].set_label(_("<b>Allow</b>"))
            #self.arw["toggle_proxy_allow_button"].modify_bg(Gtk.StateType.NORMAL, Gdk.Color(red=0, green=60535, blue=0))

        else:
            self.arw["toggle_proxy_allow_button"].set_image(self.controller.deny_button)
            message = _('<span foreground="#ff0000"> All connections\nto Internet\nare prohibited. </span>')
            self.arw["proxy_dest_all"].set_markup(message)
            self.arw["allow_deny_groups"].set_markup(_('<span foreground="#ff0000">Denied Groups</span>'))
            self.arw["allow_deny_sites"].set_markup(_('<span foreground="#ff0000">Denied Sites</span>'))
            #self.arw["toggle_proxy_allow"].set_label(_("<b>Deny</b>"))
            #self.arw["toggle_proxy_allow_button"].modify_bg(Gtk.StateType.NORMAL, Gdk.Color(red=60535, green=0, blue=0))


        # if the first tab of permissions is empty, open the second
        x = self.arw["notebook2"].get_current_page()
        current_page = x

        groups_iter = self.arw['proxy_groups_store'].get_iter_first()
        has_groups = groups_iter is not None

        text_buffer = self.arw["proxy_dest"].get_buffer()
        (start_iter, end_iter) = text_buffer.get_bounds()
        dest_text = text_buffer.get_text(start_iter, end_iter, False)

        len1 = len(dest_text.strip())

        if not has_groups and len1 == 0:
            pass
        elif x == 0 and not has_groups:
            self.arw["notebook2"].set_current_page(1)
            current_page = 1
        elif x == 1 and len1 == 0:
            self.arw["notebook2"].set_current_page(0)
            current_page = 0

##        # Try to load the right chooser
##        # If the users list is active (red frame)
##        if self.arw['proxy_users_scroll_window'].get_style_context().has_class("chosen_list"):
##            self.arw["chooser"].set_model(self.controller.chooser_users_store)
##
##        # For destination
##        # Do not load the chooser if destination set to full access
##        elif self.proxy_store[self.controller.iter_proxy][12] == 1:
##            self.arw["chooser"].set_model(EMPTY_STORE)
##
##        # load the groups chooser if the "groups" tab is active.
##        elif current_page == 0:
##            self.arw["chooser"].set_model(self.controller.groups_store)
##        else:
##            self.arw["chooser"].set_model(EMPTY_STORE)

    def show_time_conditions_window(self, widget):
        self.arw["proxy_time_conditions"].show()
    def hide_time_conditions_window(self, widget):
        self.arw["proxy_time_conditions"].hide()

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
        data1 = self.controller.config["proxy"]
        keys = ["active", "action", "time_condition", "#comments", "user", "xxx", "dest_group", "dest_domain", "xxx",
                "destination"]
        for section in data1:
            if section[0:2] == "@_":  # generated sections must not be loaded
                continue
            out = [section]
            data2 = data1[section]
            # merge user and mac
            if "user" not in data2:
                if "users" in data2:
                    data2["user"] = data2["users"]
            else:
                if "users" in data2:
                    data2["user"] += data2["users"]
            # merge dest_domain and dest_ip
            if "dest_domain" not in data2:
                if "dest_ip" in data2:
                    data2["dest_domain"] = data2["dest_ip"]
            else:
                if "dest_ip" in data2:
                    data2["dest_domain"] += data2["dest_ip"]

            for key in keys:
                if key in data1[section]:
                    data = data1[section][key]

                    if key == 'time_condition':
                        # days = parse_date_format_from_squid(data[0].split(' ')[0])
                        days = data[0].split(' ')[0]
                        if len(data[0].split(' ')) > 1:
                            data = [days + ' ' + data[0].split(' ', 1)[1]]
                        else:
                            data = [days]

                    out.append("\n".join(data) + "\n")
                else:
                    out.append("")
            # check boxes and ToggleButtons
            if "any_user" in data1[section]:
                anyuser = data1[section]["any_user"]
            else:
                anyuser = 0
            out += [anyuser, 1, 1, 1, "#009900", "#ffffff"]

            self.proxy_store.append(out)

    def build_proxy_ini(self):

        out = ""
        for row in self.proxy_store:
            # add support for a time condition from evening to morning.
            # This requires to create two configurations.
            time_condition = row[3]
            time_condition_list = format_time(time_condition)
            i = 1
            index = ""
            for time_condition2 in time_condition_list:
                if len(time_condition_list) > 1:  # If the row is duplicated, we must create two different names
                    index = str(i)
                    i += 1
                out += "\n[%s%s]\n" % (row[0], index)
                out += format_comment(row[4])  # comments
                out += format_line("active", row[1])
                out += format_line("action", row[2])
                if row[11]:
                    out += "user = any\n"
                else:
                    out += format_userline("user", row[5])
                out += format_line("time_condition", time_condition2)
                if format_line("destination", row[10]) == "":
                    out += format_line("dest_group", row[7])
                    out += format_domainline("dest_domain", row[8])
                else:
                    out += format_line("destination", row[10])

        # add default permissions
        out += "\n[@_antivirus]\n"
        out += "active = on \n"
        out += "action = allow \n"
        out += "user = any \n"
        out += "dest_group = antivirus \n"

        with open(get_config_path("./tmp/proxy-users.ini"), "w", encoding="utf-8-sig", newline="\n") as f1:
            f1.write(out)


    def build_proxy_groups_ini(self):        # TODO Dysmas - add

        out = ""
        key = self.controller.config["groups"]
        for group in key:
            out += "\n[" + group + "]\n"
            for key2 in ["comments", "dest_domain", "dest_ip"]:
                if key2 in key[group]:
                    for line1 in key[group][key2]:
                        out += key2 + " = " + line1 + "\n"

        with open(get_config_path("./tmp/proxy-groups.ini"), "w", encoding="utf-8-sig", newline="\n") as f1:
            f1.write(out)
