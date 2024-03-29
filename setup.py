#!/usr/bin/python3

#
# Confix 2.5.4
# Copyright (C) 2008-2012 GAF Software
# <https://sourceforge.net/projects/pdfbooklet>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import os
import re
import glob

"""
try :
    from setuptools import setup
    print "installation with setuptools"
except :
"""
import sys

# from distutils.core import setup
from setuptools import setup


sys.prefix = '/usr'


data_files=[('/usr/share/confix/data', glob.glob('confix/data/*.*')),
            ('/usr/share/confix/documentation', glob.glob('./documentation/*.*')),
            ('/usr/share/applications', ['confix/data/confix.desktop']),
            ('/usr/share/locale/fr/LC_MESSAGES', glob.glob('share/locale/fr/LC_MESSAGES/*.*')),
            ('/usr/share/pixmaps', ['confix/data/confix.png']),
            ('/usr/share/confix/icons/hicolor/scalable', ['confix/data/confix.svg'])]


setup(name='confix',
      version='2.5.4',
      author='GAF Software',
      author_email='Averell7 at sourceforge dot net',
      maintainer='Averell7',
      maintainer_email='Averell7 at sourceforge dot net',
      description='Configurator for Idefix',
      url='https://github.com/Averell7/idefix-configurator',
      license='GNU GPL-3',
      scripts=['bin/confix'],
      packages=['confix', 'confix.pyaes', 'confix.tldextract'],
      data_files=data_files
      #requires=['python-poppler'],          # for distutils
      #install_requires=['python-poppler']   # for setuptools  should work but does not. We can use setup.cfg instead
     )
