all:

check:
	python testrun.py
	sh blackboxtests tests/*

clean:
	rm -rf *~ wibbrlib/*~ *.pyc *.pyo wibbrlib/*.pyc wibbrlib/*.pyo tmp.*
