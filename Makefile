# Makefile for Obnam
# Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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

CC = gcc
CFLAGS = -D_GNU_SOURCE

prefix = /usr/local
bindir = $(prefix)/bin
libdir = $(prefix)/lib
sharedir = $(prefix)/share
mandir = $(sharedir)/man
man1dir = $(mandir)/man1
pydir = $(libdir)/python2.4
sitedir = $(pydir)/site-packages

all: odirect_read obnam.1 odirect_read.1

version:
	./cli.py --version

odirect_read: odirect_read.c

obnam.1: obnam.docbook
	docbook2x-man obnam.docbook

odirect_read.1: odirect_read.docbook
	docbook2x-man odirect_read.docbook

check: all
	./test_odirect_read
	python testrun.py
	sh blackboxtests tests/*
	./check-options

coverage: all
	rm -f .coverage
	coverage.py -x testrun.py
	sh blackboxtests --use-coverage tests/*
	coverage.py -r -o /usr,/var,$(HOME)/bin,uuid,testrun | \
	awk '/%$$/ && $$(NF-2)!=$$(NF-1) {print $$0,"   ",$$(NF-2)-$$(NF-1)}'

clean:
	rm -f *~ */*~ *.pyc *.pyo */*.pyc */*.pyo tmp.* *,cover */*,cover
	rm -f obnam.1 odirect_read.1 odirect_read


install: all
	install -d $(bindir)
	install cli.py $(bindir)/obnam
	install odirect_read $(bindir)
	install -d $(man1dir)
	install -m 0644 *.1 $(man1dir)
	install -d $(sitedir)/obnam
	install -m 0644 obnam/*.py $(sitedir)/obnam
	python2.4 fixup-defaults.py \
	    --gpg-encrypt-to= \
	    --gpg-home= \
	    --gpg-sign-with= \
	    --odirect-read=odirect_read \
	    --odirect-pipe=odirect_pipe \
	    --ssh-key= \
	    --store= \
	    --host-id="socket.gethostname()" \
	    --cache= \
	    > $(sitedir)/obnam/defaultconfig.py
	install -m 0644 uuid.py $(sitedir)
