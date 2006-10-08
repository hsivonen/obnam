all:

check:
	python testrun.py
	sh blackboxtests tests/*

clean:
	rm -rf *~ *.pyc *.pyo wibbrlib/*.pyc wibbrlib/*.pyo tmp.*
