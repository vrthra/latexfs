import setuptools
with open('README.md') as f:
    long_description = f.read()

setuptools.setup(
        name='latexmount',
        version='0.6',
        author='Rahul Gopinath',
        author_email='rahul@gopinath.org',
        description='A FUSE mount that shows individual sections of a latex file as separate files',
        long_description=long_description,
        url='http://github.com/vrthra/latexmount',
        packages=['latexmount'],
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Operating System :: POSIX",
            "Topic :: System :: Filesystems",
            "Topic :: Fun"
            ],
        )
