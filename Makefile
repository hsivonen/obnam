PYTHON = python

prefix = /usr/local
bindir = $(prefix)/bin

all: _obnam.so obnam.1

_obnam.so: _obnammodule.c
	if $(PYTHON) setup.py build > setup.log 2>&1; then \
            rm setup.log; else cat setup.log; exit 1; fi
	cp build/lib*/*.so .
	rm -rf build

obnam.1: obnam.1.in
	./obnam --generate-manpage=obnam.1.in > obnam.1

check: all
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm .coverage
	python blackboxtest
	fakeroot python blackboxtest
	
clean:
	rm -f _obnam.so obnamlib/*.pyc obnamlib/plugins/*.pyc test-plugins/*.pyc
	rm -f blackboxtest.log blackboxtest-obnam.log obnam.prof obnam.1
