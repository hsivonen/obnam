#!/usr/bin/python

from distutils.core import setup

setup(name='obnam',
      version='0.9.3',
      description='Backup software',
      author='Lars Wirzenius',
      author_email='liw@liw.fi',
      url='http://braawi.org/obnam.html',
      packages=['obnamlib'],
      scripts=['obnam'],
     )
