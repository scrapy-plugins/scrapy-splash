#!/usr/bin/env python
from setuptools import setup

setup(
    name='scrapy-splash',
    version='0.7',
    url='https://github.com/scrapy-plugins/scrapy-splash',
    description='JavaScript support for Scrapy using Splash',
    long_description=open('README.rst').read() + "\n\n" + open("CHANGES.rst").read(),
    author='Scrapy developers',
    maintainer='Mikhail Korobov',
    maintainer_email='kmike84@gmail.com',
    license='BSD',
    packages=['scrapy_splash'],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Framework :: Scrapy',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    requires=['scrapy', 'six'],
)
