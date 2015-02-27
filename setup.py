#!/usr/bin/env python
from setuptools import setup

setup(
    name='scrapyjs',
    version='0.1',
    url='https://github.com/scrapinghub/scrapyjs',
    description='JavaScript support for Scrapy using Splash',
    long_description=open('README.rst').read(),
    author='Scrapinghub Inc.',
    maintainer='Mikhail Korobov',
    maintainer_email='kmike84@gmail.com',
    license='MIT License',
    packages=['scrapyjs'],
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Framework :: Scrapy',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    requires=['scrapy'],
)
