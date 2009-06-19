# Makefile for Obnam
# Copyright (C) 2006-2009  Lars Wirzenius <liw@liw.fi>
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

CC = gcc
CFLAGS = -D_GNU_SOURCE

PYTHON = python

all: _obnam.so

_obnam.so: _obnammodule.c
	if $(PYTHON) setup.py build > setup.log 2>&1; then \
	    rm setup.log; else cat setup.log; exit 1; fi
	cp build/lib*/*.so .
	rm -rf build

.PHONY: check
check: all check-test-modules check-unittests check-licenses check-blackbox

.PHONY: check-test-modules
check-test-modules:
	bzr ls --versioned --kind=file | grep '\.py$$' | \
		xargs ./check-has-test-module

.PHONY: check-unittests
check-unittests:
	$(PYTHON) -m CoverageTestRunner
	rm -f .coverage

.PHONY: check-licenses
check-licenses:
	bzr ls --versioned --kind=file | \
	    grep -Fxv -f check-license-exceptions | \
	    xargs ./check-license

.PHONY: check-blackbox
check-blackbox:
	./blackboxtest

.PHONY: clean
clean:
	rm -rf *~ */*~ *.pyc *.pyo */*.pyc */*.pyo tmp.* *,cover */*,cover build
	rm -f obnam.1 obnamfs.1 .coverage *.so
