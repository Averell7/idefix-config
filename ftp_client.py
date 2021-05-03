import io
import os
from ftplib import FTP, all_errors as FTPError

from util import alert, get_config_path, print_except


def ftp_connect(server, login, password, controller = None):
    global ftp1

    if password[0:1] == "%":
        hysteresis = ""
        i = 0
        for deplacement in password:
            if i % 2 == 1:
                hysteresis += deplacement
            i += 1
        password = hysteresis

    try:
        ftp = FTP(server, timeout=15)  # connect to host, default port
        ftp.login(login, password)
        # for (name, properties) in ftp.mlsd():     # would be better, but the ftp server of Idefix does not support the command
        #    if name == "idefix" and properties['type'] == "dir":
        if "idefix" in ftp.nlst():
            ftp.cwd("idefix")
            if controller:
                controller.idefix_module = True
        else:
            if controller:
                controller.idefix_module = False
        return ftp
    except OSError as e:
        alert(_("Cannot connect to %s. Host not found") % server)
    except FTPError as e:
        alert(_("Cannot connect to %s. Reason: %s") % e)
        print("Unable to connect to ftp server with : %s / %s. \nError: %s" % (login, password, e))


def ftp_get(ftp, filename, directory="", required=True, json=False):
    if not ftp:
        print(_("No ftp connection"))
        return False

    # verify that the file exists on the server
    try:
        x = ftp.mlsd(directory)
        if not filename in ([n[0] for n in x]):
            if required:
                print(_("We got an error with %s. Is it present on the server?" % filename))
            return False
    except:
        if not filename in ftp.nlst(directory):  # deprecated, but vsftpd does non support mlsd (used in idefix.py)
            if required:
                print(_("We got an error with %s. Is it present on the server?" % filename))
            return False

    try:
        f1 = io.BytesIO()
        ftp.retrbinary('RETR ' + filename, f1.write)  # get the file
        data1 = f1.getvalue()
        f1.close()
        if json:  # returns string
            return data1.decode("ascii")
        else:  # returns list
            try:
                return data1.decode("utf-8-sig")
            except:
                return data1

    except FTPError:
        print(_("could not get ") + filename)
    except:
        print_except()
        return False

def ftp_send(ftp, filepath, directory=None, dest_name=None):
    if directory:
        ftp.cwd(directory)  # change into subdirectory
    if not dest_name:
        dest_name = os.path.split(filepath)[1]

    if os.path.isfile(get_config_path(filepath)):
        with open(get_config_path(filepath), 'rb') as f1:  # file to send
            ftp.storbinary('STOR ' + dest_name, f1)  # send the file
    else:
        message = filepath + " not found"
        print(message)
        return message

    # print( ftp.retrlines('LIST'))
    if directory:
        ftp.cwd('..')  # return to house directory
    return True
