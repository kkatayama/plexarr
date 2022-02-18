import setuptools


with open('README.md') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name='plexarr',
    version='1.1.47',
    author='Teddy Katayama',
    author_email='katayama@udel.edu',
    description='Unofficial Python Wrapper for the Plex, Sonarr, Radarr, and Bazarr API with Added Features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kkatayama/filenames',
    packages=setuptools.find_packages(),
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
)
