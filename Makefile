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

odirect_read: odirect_read.c

obnam.1: obnam.docbook
	docbook2x-man obnam.docbook

odirect_read.1: odirect_read.docbook
	docbook2x-man odirect_read.docbook

check: all
	./test_odirect_read
	python testrun.py
	sh blackboxtests tests/*

clean:
	rm -rf *~ */*~ *.pyc *.pyo */*.pyc */*.pyo tmp.* odirect_read obnam.1


install: all
	install -d $(bindir)
	install cli.py $(bindir)/obnam
	install odirect_read $(bindir)
	install -d $(man1dir)
	install -m 0644 *.1 $(man1dir)
	install -d $(sitedir)/obnam
	install -m 0644 obnam/*.py $(sitedir)/obnam
	install -m 0644 uuid.py $(sitedir)
