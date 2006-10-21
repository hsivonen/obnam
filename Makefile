all:

check:
	python testrun.py
	sh blackboxtests tests/*

clean:
	rm -rf *~ */*~ *.pyc *.pyo */*.pyc */*.pyo tmp.*
