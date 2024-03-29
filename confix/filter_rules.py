import time
from gi.repository import Gdk, Gtk

from actions import DRAG_ACTION
from util import (
    askyesno, ask_text, format_name,
    showwarning, cleanhtml)


# 3 - rules
class FilterRules:
    mem_time = 0
    block_signals = False

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.arw["filter_users"].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [], DRAG_ACTION)
        self.arw['filter_users'].drag_source_add_text_targets()
        self.arw['filter_users'].connect("drag-data-get", self.filter_rules_data_get)
        self.arw['filter_users'].drag_dest_set(Gtk.DestDefaults.DROP, [], DRAG_ACTION)
        self.arw['filter_users'].drag_dest_add_text_targets()
        self.arw['filter_users'].connect("drag-data-received", self.update_filter_user_list_view)

        """
        0 : section
        1 : active     (off/on)
        2 : action     (deny/allow)
        3 : time_condition
        4 : #comments
        5 : user
        6 : mac
        7 : dest_group
        8 : dest_domains
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
        20 : checkbox strict_end (0/1)
        """

        self.filter_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, int, int, int, int,
                                          str, str, str, str, int, int)  #

        self.proxy_rules_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, int, int, int,
                                               int, str, str, str, str, int, int)  #

        self.port_rules_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, int, int, int,
                                              int, str, str, str, str, int, int)  #

        self._active_store = 'dns'

        self.cell3 = Gtk.CellRendererText()
        self.check2 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check2.connect('toggled', self.toggle_col14, self.filter_store)
        # Test pour Daniel
        self.check3 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check3.connect('toggled', self.toggle_col5, self.filter_store)
        self.check4 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check4.connect('toggled', self.toggle_col12, self.filter_store)
        self.check5 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check5.connect('toggled', self.toggle_col13_proxy, self.filter_store)

        self.treeview3 = self.arw["treeview3"]
        self.treeview3.set_model(self.filter_store)
        self.treeview3.connect("button-press-event", self.load_filter_user)

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
        for scroll in ['filter_users', 'chooser1']:
            ctx = self.arw[scroll].get_style_context()
            ctx.add_class('chosen_list1')

        self.switch_gui()

    @property
    def current_store(self):
        """Returns the currently selected store"""
        if self._active_store == 'dns':
            return self.filter_store
        elif self._active_store == 'proxy':
            return self.proxy_rules_store
        elif self._active_store == 'port':
            return self.port_rules_store

    def update_selected_filter_option(self, *args):
        """Update which current store"""
        if self.arw['dns_filter_rules_option'].get_active():
            self._active_store = 'dns'
            self.controller.proxy_group.set_group_store('proxy')
        elif self.arw['proxy_filter_rules_option'].get_active():
            self._active_store = 'proxy'
            self.controller.proxy_group.set_group_store('proxy')
        elif self.arw['port_filter_rules_option'].get_active():
            self._active_store = 'port'
            self.controller.proxy_group.set_group_store('port')

        self.treeview3.set_model(self.current_store)
        self.arw['filter_users_store'].clear()
        self.arw['rule_dest'].get_buffer().set_text("")
        self.arw['proxy_groups_store'].clear()
        self.arw["filter_users"].show()
        self.arw["proxy_group"].show()
        self.arw["rule_dest"].show()
        self.toggle_col13_proxy(None)
        self.load_filter_user2()

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
            for button in ["toggle_filter_user_open_button", "toggle_filter_open_button", "toggle_filter_allow_button"]:
                self.arw[button].show()
            self.arw["filter_users_box"].set_size_request(300,100)
        else:
            # checkboxes interface
            for col in (1,2,3):
                self.arw["treeview3"].get_column(col).set_visible(True)
            for button in ["toggle_filter_user_open_button", "toggle_filter_open_button", "toggle_filter_allow_button"]:
                self.arw[button].hide()
            self.arw["filter_users_box"].set_size_request(550,100)







    def toggle_col12(self, widget, a=0, b= 0):              # TODO test Daniel, et aussi les autres dessous
        # callback of the open access button in filter tab.
        # col 12 = open access state; col 16 = background color

        treestore = self.current_store
        if treestore.get_value(self.controller.iter_filter, 12) == 0:
            treestore.set_value(self.controller.iter_filter, 12, 1)
            treestore.set_value(self.controller.iter_filter, 10, "any")
            treestore.set_value(self.controller.iter_filter, 16, "#ffff88")
        else:
            treestore.set_value(self.controller.iter_filter, 12, 0)
            treestore.set_value(self.controller.iter_filter, 10, "")
            treestore.set_value(self.controller.iter_filter, 16, "#ffffff")
            #self.arw["toggle_filter_open_button"].set_image(self.controller.red_button)
        self.load_filter_user2()

    def toggle_col5(self, widget, a=0, b= 0):
        """Toggle any user or specific users"""
        if self.current_store.get_value(self.controller.iter_filter, 11) == 0:
            self.current_store.set_value(self.controller.iter_filter, 11, 1)
            markup = self.current_store.get_value(self.controller.iter_filter, 0)
            self.current_store.set_value(self.controller.iter_filter, 0, "<i>" + markup + "</i>")
            self.arw["filter_users"].hide()
        else:
            self.current_store.set_value(self.controller.iter_filter, 11, 0)
            markup = self.current_store.get_value(self.controller.iter_filter, 0)
            markup = markup.replace("<i>", "")
            markup = markup.replace("</i>", "")
            self.current_store.set_value(self.controller.iter_filter, 0, markup)
            self.arw["filter_users"].show()
        self.update_filter_user_list()

        self.load_filter_user2()

    def toggle_col13_proxy(self, widget, a=0, b= 0):
        # callback of the allow/deny button in filter tab.
        # col 13 = allow/deny state; col 15 = text color

        treestore = self.current_store
        if self.controller.iter_filter and treestore.iter_is_valid(self.controller.iter_filter):
            data = treestore[self.controller.iter_filter]
        else:
            data = None

        if not data or data[13] == 0:
            if data:
                treestore.set_value(self.controller.iter_filter, 13, 1)
                treestore.set_value(self.controller.iter_filter, 2, "allow")
                treestore.set_value(self.controller.iter_filter, 15, "#009900")
            self.arw["allow_deny_groups"].set_text("Allowed Groups")
            self.arw["allow_deny_sites"].set_text("Allowed Sites")
        else:
            treestore.set_value(self.controller.iter_filter, 13, 0)
            treestore.set_value(self.controller.iter_filter, 2, "deny")
            treestore.set_value(self.controller.iter_filter, 15, "#f00000")
            self.arw["allow_deny_groups"].set_text("Denied Groups")
            self.arw["allow_deny_sites"].set_text("Denied Sites")

        self.load_filter_user2()


    def toggle_col14(self, cellrenderer, row, _old_treestore):
        treestore = self.current_store
        # callback of the on/off checkbox in filter tab.
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

        #self.populate_rules()


    def add_rule_below(self, widget):
        # add rule in the filter tab
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        x = ask_text(self.arw["window1"], _("Name of the new rule :"), "")
        if x is None:
            return
        else:
            # name = format_name(x)
            name = x
            iter1 = self.current_store.insert_after(node,
                                                    [name, "on", "allow", "", "", "", "", "", "", "", "", 0,
                                                    0, 1, 1, "#009900", "#ffffff", "", "", 0, 0])

    def delete_rule(self, widget):
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        name = model.get_value(node, 0)
        if askyesno("Remove filter rule", "Do you want to remove %s?" % name):
            self.current_store.remove(node)

    def edit_rule(self, widget):
        (model, node) = self.arw["treeview3"].get_selection().get_selected()
        name = model.get_value(node, 0)
        x = ask_text(self.arw["window1"], "Name of the rule :", cleanhtml(name))
        if x is None:
            return
        else:
            # x = format_name(x)
            # Set format:
            if model.get_value(node, 1) == 'off':
                x = '<s>' + x + '</s>'
            self.current_store.set(node, [0], [x])

    def filter_user_has_any(self):
        """Return True if the filter user has any in the list of rules"""
        text = self.current_store.get_value(self.controller.iter_filter, 5)
        if not text:
            return False
        return 'any' in text.split('\n')

    def delete_filter_user(self, widget):
        model, iter = self.arw['filter_users'].get_selection().get_selected()
        name = model.get_value(iter, 0).strip()

        value = self.current_store.get_value(self.controller.iter_filter, 5)
        if not value:
            names = []
        else:
            names = value.split('\n')
        if name not in names:
            return

        res = askyesno(_("Remove user"), _("Do you want to remove user %s?") % name)
        if not res:
            return

        names.remove(name)

        self.current_store.set_value(self.controller.iter_filter, 5, '\n'.join(names))
        self.update_filter_user_list()

    def update_filter_user_list_view(self, widget, ctx, x, y, data, info, etime):
        """Add a user or a group to the list"""
        # called by the drag_data_received signal
        # TODO name should be changed, because it is not clear

        parts = data.get_text().split("#")
        new_name = parts[0].strip()

        if self.filter_user_has_any():
            return

        if not parts[1] or parts[1] != "chooser1":      # if data does not come from the right chooser, return
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
            self.current_store.set_value(self.controller.iter_filter, 5, '\n'.join(names))
            return

        names = self.current_store.get_value(self.controller.iter_filter, 5).split('\n')
        if new_name in names:
            return
        names.append(new_name)
        self.current_store.set_value(self.controller.iter_filter, 5, '\n'.join(names))
        self.update_filter_user_list(self.controller.iter_filter)

    def filter_user_select(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                self.arw["filter_users_menu"].popup(None, None, None, None, event.button, event.time)

    def update_filter_user_list(self, proxy_iter=None):
        """ (re)create the users list from the store """
        # called when something is changed in the store
        if not proxy_iter:
            proxy_iter = self.controller.iter_filter

        self.arw['filter_users_store'].clear()

        if not proxy_iter:
            return

        # add users
        users = self.current_store[proxy_iter][5]  # user
        if not users:
            return None

        for name in users.split('\n'):
            if name:
                iter = self.arw['filter_users_store'].append()
                self.arw['filter_users_store'].set_value(iter, 0, name)

        # add mac, if any
        users += self.current_store[proxy_iter][6]  # mac

        for name in self.current_store[proxy_iter][6].split('\n'):
            if name:
                iter = self.arw['filter_users_store'].append()
                self.arw['filter_users_store'].set_value(iter, 0, name)

        return users

    def load_filter_user(self, widget, event):

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
            iter1 = self.current_store.get_iter(path[0])
        else:
            model, iter1 = self.arw["treeview3"].get_selection().get_selected()
            if not iter1:
                return

        """# debug
        i = 0
        row = self.filter_store[iter1]
        try :
            for i in range(20):
                print(i, " = ", row[i])
        except:
            pass
        """

        self.controller.iter_filter = iter1

        # time conditions
        data1 = self.current_store[iter1][3].strip()
        if data1 == "":
            self.arw["filter_time_condition_days"].set_text("")
            self.arw["filter_time_condition_from"].set_text("")
            self.arw["filter_time_condition_to"].set_text("")
            self.arw["time_button_label"].set_text(_("All day\nand week"))

        elif ' ' in data1:
            try:
                tmp1 = data1.split()
                tmp2 = tmp1[1].split("-")
                days = tmp1[0].strip()
                human_days = self.convert_days_to_local(days)
                time_from = tmp2[0].strip()
                time_to = tmp2[1].strip()
                if self.current_store[self.controller.iter_filter][13] == 1:      # change colour for deny or allow
                    color = 'foreground="#008800"'
                else :
                    color = 'foreground="#ee0000"'
                button_text = '<span ' + color + ' weight="bold" >'    # size="large" deleted
                button_text += human_days + '\n  <span size="large">' + time_from + "-" + time_to + "</span></span>"
                self.arw["filter_time_condition_days"].set_text(days)
                self.arw["filter_time_condition_from"].set_text(time_from)
                self.arw["filter_time_condition_to"].set_text(time_to)
                self.arw["time_button_label"].set_markup(button_text)

            except:
                print("Error handling time condition :", data1)
        else:
            print("Invalid time :", data1)

        self.arw["filter_#comments"].get_buffer().set_text(self.current_store[iter1][4])
        self.arw['filter_time_strict_end_checkbox'].set_active(self.current_store[iter1][20])

        self.update_filter_user_list(iter1)
        self.controller.proxy_group.update_proxy_group_list(iter1)

        # add dest_domains
        data1 = self.current_store[iter1][8]  # dest_domains
        # add dest_ip, if any
        data1 += self.current_store[iter1][9]  # dest_ip
        self.arw["rule_dest"].get_buffer().set_text(data1)
        self.load_filter_user2()

    def load_filter_user2(self):
        # used by the function above, and by the buttons of the filter tab
        list_color = Gdk.Color(red=50535, green=50535, blue=60535)

        if self.controller.iter_filter and self.current_store.iter_is_valid(self.controller.iter_filter):
            data = self.current_store[self.controller.iter_filter]
        else:
            data = None

        if data and data[11] == 1:
            self.arw["filter_users_stack"].set_visible_child(self.arw["filter_users_all"])
            x = self.arw["toggle_filter_user_open_button"]
            self.arw["toggle_filter_user_open_button"].set_image(self.controller.all_button)

        else:
            self.arw["filter_users_stack"].set_visible_child(self.arw["filter_users_scroll_window"])
            self.arw["toggle_filter_user_open_button"].set_image(self.controller.list_button)


        # set full access
        if data and data[12] == 1:
            self.arw["rule_dest_stack"].set_visible_child(self.arw["rule_dest_all"])
            self.arw["toggle_filter_open_button"].set_image(self.controller.all2_button)

        else:
            self.arw["toggle_filter_open_button"].set_image(self.controller.list2_button)
            self.arw["rule_dest_stack"].set_visible_child(self.arw["rule_dest_grid"])


        # set allow/deny button
        if data and data[13] == 1:
            self.arw["toggle_filter_allow_button"].set_image(self.controller.allow_button)
            message = '<span foreground="#00aa00">' + _("All destinations \nallowed.") +  '</span>'
            self.arw["rule_dest_all"].set_markup(message)
            self.arw["allow_deny_groups"].set_markup('<span foreground="#00aa00">' + _("Allowed Groups") +  '</span>')
            self.arw["allow_deny_sites"].set_markup('<span foreground="#00aa00">' + _("Allowed Sites") +  '</span>')

        else:
            self.arw["toggle_filter_allow_button"].set_image(self.controller.deny_button)
            message = '<span foreground="#ff0000">' + _("All connections\nto Internet\nare prohibited.") +  '</span>'
            self.arw["rule_dest_all"].set_markup(message)
            self.arw["allow_deny_groups"].set_markup('<span foreground="#ff0000">' + _("Denied Groups") +  '</span>')
            self.arw["allow_deny_sites"].set_markup('<span foreground="#ff0000">' + _("Denied Sites") +  '</span>')

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
        # Get the current time condition
        time_condition = self.current_store[self.controller.iter_filter][3]
        self.arw['filter_time_condition_days'].set_text('')
        self.arw['filter_time_condition_from'].set_text('')
        self.arw['filter_time_condition_to'].set_text('')
        self.arw['filter_time_strict_end_checkbox'].set_active(False)

        if self.controller.iter_filter:
            self.arw['filter_time_strict_end_checkbox'].set_active(self.current_store[self.controller.iter_filter][20])

        if time_condition:
            splitted = time_condition.split(' ')
            self.update_time_days(text=splitted[0])
            from_time, to_time = splitted[1].split('-')
            self.arw['filter_time_condition_from'].set_text(from_time)
            self.arw['filter_time_condition_to'].set_text(to_time)
        else:
            self.update_time_days(text='')

        self.update_time_checkbox()

        self.arw["filter_time_conditions"].show()

    def hide_time_conditions_window(self, widget):
        self.arw["filter_time_conditions"].hide()
        self.load_filter_user("", "")

    def update_time_resort(self, widget, *args):
        widget.set_text(''.join(sorted(filter(lambda x: x.isdigit(), widget.get_text()))))

    def update_time_days(self, widget=None, text=None, *args):
        """Update the checkboxes based on the user's input"""

        if text is None:
            text = widget.get_text()

        self.block_signals = True
        for n in range(1, 8):
            self.arw['time_checkbutton' + str(n)].set_active(False)

        for char in text:
            try:
                n = int(char)
            except ValueError:
                continue

            checkbox = self.arw.get('time_checkbutton' + str(n))
            if checkbox:
                checkbox.set_active(True)

        self.block_signals = False

    def update_time_checkbox(self, widget=None):
        """Update the text box based on the checkboxes"""
        if self.block_signals:
            return

        text = ''

        for n in range(1, 8):
            if self.arw['time_checkbutton' + str(n)].get_active():
                text += str(n)

        self.arw['filter_time_condition_days'].set_text(text)

    def save_time_conditions_window(self, widget):
        time_condition = self.arw["filter_time_condition_days"].get_text() + " "
        if time_condition.strip() == "":
            time_condition = "1234567 "

        time_condition += self.arw["filter_time_condition_from"].get_text().strip() + "-"
        time_condition += self.arw["filter_time_condition_to"].get_text().strip()
        if time_condition == "1234567 -":
            time_condition = ""

        if self.arw['filter_time_strict_end_checkbox'].get_active():
            self.current_store[self.controller.iter_filter][20] = 1
        else:
            self.current_store[self.controller.iter_filter][20] = 0

        self.current_store[self.controller.iter_filter][3] = time_condition

        self.arw["filter_time_conditions"].hide()
        self.load_filter_user("", "")

    def filter_profile_select(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                self.arw["filter_profiles_menu"].popup(None, None, None, None, event.button, event.time)

    def filter_rules_data_get(self, treeview, drag_context, data, info, time):
        (model, iter1) = treeview.get_selection().get_selected()
        if iter1:
            path = model.get_string_from_iter(iter1)
            data.set_text(path, -1)

    def select_rule(self, rulename):
        """Select a rule by its name"""
        for rule in self.current_store:
            if rule[0] == rulename:
                self.arw['treeview3'].set_cursor(rule.path)
                self.load_filter_user(event=None, widget=None)
                return

    def populate_rules(self):
        self.populate_filter_rules(self.filter_store, self.controller.config['rules'])
        if 'proxy-rules' in self.controller.config:
            self.populate_filter_rules(self.proxy_rules_store, self.controller.config['proxy-rules'])
        if 'ports-rules' in self.controller.config:
            self.populate_filter_rules(self.port_rules_store, self.controller.config['ports-rules'])

    def populate_filter_rules(self, store, data1):
        store.clear()
        keys = ["active", "action", "time_condition", "#comments",
                "users", "",
                "dest_groups", "dest_domains", "", "",
                "any_user", "any_destination", "allow_deny"]
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
                        if isinstance(data, list):
                            if len(data) == 0:
                                data = ""
                            else:
                                data = data[0]           # TODO version 3
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
                    out.append('')
            # check boxes and ToggleButtons
##            if "any_user" in data2:
##                anyuser = data1[section]["any_user"]
##            else:
##                anyuser = 0
            out += [1, "#009900", "#ffffff", "", "", 0, 0]

            if not out[11]:
                out[11] = 0
            if not out[12]:
                out[12] = 0
            if not out[13]:
                out[13] = 0

            if data2.get("active") == 'off':
                out[14] = 0
            else:
                out[14] = 1

            if 'strict_end' in data2 and data2['strict_end']:
                out[20] = 1

            store.append(out)

