build:
	python3 setup.py sdist

upload:
	python -m twine upload dist/*

clean:
	rm -rf build dist
