# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='flood-mapper',
    version='0.1.0',
    author='Fifi ADODO',
    author_email='fidel999@yahoo.fr', 
    description='An automated tool for flood mapping using Google Earth Engine SAR and Sentinel-2 imagery.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/fadodo/flood_mapper', 
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Remote Sensing',
    ],
    python_requires='>=3.8',
    install_requires=[
        'earthengine-api',
        'geemap',
        'numpy',
        'matplotlib',
        'Pillow', # Often a dependency for geemap/matplotlib if not already present
    ],
    entry_points={
        'console_scripts': [
            'run-flood-mapping=scripts.run_flood_mapping:main',
        ],
    },
)
