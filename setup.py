from setuptools import setup, find_packages

setup(
    name='flood_mapper',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'earthengine-api',
        'geemap',
        'numpy',
        'matplotlib',
        'google-api-python-client', 
        'google-auth-httplib2',     
        'google-auth-oauthlib',     
        'pytest',                   
    ],
    entry_points={
        'console_scripts': [
            'run_flood_mapping=scripts.run_flood_mapping:main',
        ],
    },
    author='Fifi ADODO', 
    author_email='fidel999@yahoo.fr', 
    description='A Python package for rapid flood mapping using Sentinel-1 SAR and/or Sentinel-2 optical satellite data with Google Earth Engine.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/fadodo/flood_mapper', 
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Image Processing',
        'Topic :: Environmental :: GIS',
    ],
    python_requires='>=3.8',
)