###############################################################################
# Plexarr Setup                                                               #
###############################################################################

import setuptools
from pathlib import Path


# -- Read Files -- #
long_description = Path('README.md').read_text()
required = Path('requirements.txt').read_text().splitlines()

setuptools.setup(
    name='plexarr',
    version='1.1.366',
    author='Teddy Katayama',
    author_email='katayama@udel.edu',
    description='Unofficial Python Wrapper for the Plex, Sonarr, Radarr, and Bazarr API with Added Features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kkatayama/filenames',
    packages=setuptools.find_packages(),
    # packages=['plexarr'],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=required,
    include_package_data=True
)
