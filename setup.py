import os
from setuptools import setup, find_packages
from glob import glob

# Get version number
here = os.path.abspath(os.path.dirname(__file__))
version_path = os.path.join(here, "mcstasscript", "_version.py")
version = {}
with open(version_path) as fp:
    exec(fp.read(), version)
found_version = version['__version__']
print("Version read from file:", found_version)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
     name='McStasScript',
     version=found_version,
     author="Mads Bertelsen",
     author_email="Mads.Bertelsen@ess.eu",
     description="A python scripting interface for McStas",
     include_package_data=True,
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/PaNOSC-ViNYL/McStasScript",
     install_requires=['numpy', 'matplotlib', 'PyYAML', 'ipywidgets', 'libpyvinyl'],
     packages=find_packages(),
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: GNU General Public License (GPL)",
         "Operating System :: OS Independent",
         "Topic :: Scientific/Engineering"
     ],
 )
