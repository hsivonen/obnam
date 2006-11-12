prefix = /usr/local
bindir = $(prefix)/bin
libdir = $(prefix)/lib
pydir = $(libdir)/python2.4
sitedir = $(pydir)/site-packages

all:

check:
	python testrun.py
	sh blackboxtests tests/*

clean:
	rm -rf *~ */*~ *.pyc *.pyo */*.pyc */*.pyo tmp.*


install:
	install -d $(bindir)
	install cli.py $(bindir)/obnam
	install -d $(sitedir)/obnam
	install -m 0644 obnam/*.py $(sitedir)/obnam
	install -m 0644 uuid.py $(sitedir)
