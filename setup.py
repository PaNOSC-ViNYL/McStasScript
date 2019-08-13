import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
     name='McStasScript',
     version='0.0.10',
     author="Mads Bertelsen",
     author_email="Mads.Bertelsen@esss.se",
     description="A python scripting interface for McStas",
     include_package_data=True,
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/PaNOSC-ViNYL/McStasScript",
     install_requires=['numpy', 'matplotlib'],
     packages=setuptools.find_packages(),
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: GNU General Public License (GPL)",
         "Operating System :: OS Independent",
     ],
 )
