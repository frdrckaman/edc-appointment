# -*- coding: utf-8 -*-
import os
from setuptools import setup
from setuptools import find_packages
from os.path import join, abspath, normpath, dirname


with open(join(dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

with open(join(dirname(__file__), 'VERSION')) as f:
    VERSION = f.read()

# allow setup.py to be run from any path
os.chdir(normpath(join(abspath(__file__), os.pardir)))

setup(
    name='edc-appointment',
    version=VERSION,
    author=u'Erik van Widenfelt',
    author_email='ew2789@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    url='http://github/clinicedc/edc-appointment',
    license='GPL license, see LICENSE',
    description='Appointment module for clinicedc/edc projects',
    long_description=README,
    zip_safe=False,
    keywords='django appointments research clinical trials',
    install_requires=[
        'edc-dashboard',
        'edc-facility',
        'edc_form_validators',
        'edc-identifier',
        'edc-metadata',
        'edc-metadata-rules',
        'edc-model',
        'edc-model-admin',
        'edc-sites',
        'edc-timepoint',
        'edc-utils',
        'edc-visit-schedule',
        'edc-offstudy',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    python_requires=">=3.7",
)
