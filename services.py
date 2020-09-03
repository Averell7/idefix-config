import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class ServicesPanel:
    def __init__(self, arw, controller, connection):
        self.arw = arw
        self.controller = controller
        self.connection = connection
        self.window = self.arw['services_window']
        self.spinner = self.arw['services_panel_spinner']
        self.store = self.arw['services_store']
        self.list = self.arw['services_tree']
        self.list.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

    def refresh_services(self, _=None):
        """Get the latest status for the services"""

        self.spinner.start()
        # self.spinner.show()
        result = self.connection.get_infos('services2')
        self.store.clear()
        for name, status in json.loads(result).items():
            if 'running' in status:
                colour = 'green'
            else:
                colour = 'red'

            self.store.append((name, status, colour))

        self.spinner.stop()
        # Parse

    def show_services(self, _=None):
        self.arw['services_window'].show()
        self.refresh_services()

    def close_services_panel(self, widget):
        self.window.hide()

    def start_selected_service(self, widget):
        self.spinner.start()
        model, paths = self.list.get_selection().get_selected_rows()
        for path in paths:
            service_name = model.get_value(model.get_iter(path), 0)
            self.connection.get_infos('service %s start' % service_name)

        self.refresh_services()
        self.spinner.stop()

    def stop_selected_service(self, widget):
        self.spinner.start()
        model, paths = self.list.get_selection().get_selected_rows()
        for path in paths:
            service_name = model.get_value(model.get_iter(path), 0)
            self.connection.get_infos('service %s stop' % service_name)

        self.refresh_services()
        self.spinner.stop()
