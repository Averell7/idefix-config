from gi.repository import Gtk

image = Gtk.Image()
image.set_from_file('./data/email-32.png')

email_icon = image.get_pixbuf()

image.set_from_file('./data/internet-32.gif')
internet_full_icon = image.get_pixbuf()

image.set_from_file('./data/internet-filtered-32.gif')
internet_filtered_icon = image.get_pixbuf()

image.set_from_file('./data/internet-clock-32.png')
internet_timed_icon = image.get_pixbuf()

image.set_from_file('./data/internet-disabled-32.gif')
internet_disabled_icon = image.get_pixbuf()

image.set_from_file('./data/internet-denied-32.gif')
internet_denied_icon = image.get_pixbuf()

image.set_from_file('./data/email-disabled-32.png')
email_disabled_icon = image.get_pixbuf()

image.set_from_file('./data/email-clock-32.png')
email_timed_icon = image.get_pixbuf()
