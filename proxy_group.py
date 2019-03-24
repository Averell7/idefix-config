import time

from gi.repository import Gdk, Gtk

from actions import DRAG_ACTION
from util import askyesno, _


class ProxyGroup:
    mem_time = 0

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        self.arw["proxy_group"].enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [], DRAG_ACTION)
        self.arw['proxy_group'].drag_source_add_text_targets()
        self.arw['proxy_group'].connect("drag-data-get", self.proxy_group_data_get)
        self.arw['proxy_group'].drag_dest_set(Gtk.DestDefaults.DROP, [], DRAG_ACTION)
        self.arw['proxy_group'].drag_dest_add_text_targets()
        self.arw['proxy_group'].connect("drag-data-received", self.update_proxy_group_list_view)

    def proxy_group_data_get(self, treeview, drag_context, data, info, time):

        (model, iter1) = treeview.get_selection().get_selected()
        if iter1:
            path = model.get_string_from_iter(iter1)
            data.set_text(path, -1)
            print("DRAG", path)

    def proxy_group_select(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                self.arw["proxy_groups_menu"].popup(None, None, None, None, event.button, event.time)

    def update_proxy_group_list(self, proxy_iter=None):
        if not proxy_iter:
            proxy_iter = self.controller.iter_proxy

        self.arw['proxy_groups_store'].clear()
        for name in self.controller.iter_firewall[proxy_iter][7].split('\n'):
            if name:
                iter = self.arw['proxy_groups_store'].append()
                self.arw['proxy_groups_store'].set_value(iter, 0, name)
                try:
                    tooltip = "\n".join(self.controller.config['groups'][name].get('dest_domain', ''))
                except:
                    tooltip = _("(error)")
                self.arw['proxy_groups_store'].set_value(iter, 1, tooltip)

    def delete_proxy_group(self, widget):
        model, iter = self.arw['proxy_group'].get_selection().get_selected()
        name = model.get_value(iter, 0).strip()

        names = self.controller.proxy_users.proxy_store.get_value(self.controller.iter_proxy, 7).split('\n')
        if name not in names or name == 'any':
            return

        res = askyesno("Remove group", "Do you want to remove group %s?" % name)
        if not res:
            return

        names.remove(name)

        self.controller.proxy_users.proxy_store.set_value(self.controller.iter_proxy, 7, '\n'.join(names))
        self.update_proxy_group_list()

    def update_proxy_group_list_view(self, widget, ctx, x, y, data, info, etime):
        """Add a proxy group to the list"""

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
                model.set_value(iter_dest, i, values[i])
            model.remove(iter_source)
            names = [name[0] for name in model]
            self.controller.proxy_users.proxy_store.set_value(self.controller.iter_proxy, 7, '\n'.join(names))
            return

        new_name = data.get_text().strip()

        names = self.controller.proxy_users.proxy_store.get_value(self.controller.iter_proxy, 7).split('\n')
        if new_name in names:
            return
        names.append(new_name)
        self.controller.proxy_users.proxy_store.set_value(self.controller.iter_proxy, 7, '\n'.join(names))
        self.update_proxy_group_list(self.controller.iter_proxy)
