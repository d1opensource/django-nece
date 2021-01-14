# -*- coding: utf-8 -*-
from setuptools import setup


with open('README.rst', 'rb') as f:
    ld = f.read().decode('utf8')

long_description = ld.replace(ld[0:ld.find('nece?')], '')

version = '0.9'
description = "A content translation framework using Postgresql's jsonb" + \
    " field in the background"
url = 'https://github.com/polyconseil/django-nece'
download_url = '/'.join([url, 'tarball', version])

setup(
    name='django-nece',
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Can Mustafa Özdemir',
    author_email='canmustafaozdemir@gmail.com',
    maintainer="Polyconseil",
    maintainer_email="opensource+django-nece@polyconseil.fr",
    url=url,
    download_url=download_url,
    keywords=['translations', 'i18n', 'language', 'multilingual'],
    packages=['nece'],
    install_requires=[
        'Django>=1.9',
        'six>=1.10.0',
    ],
    extras_require={
        'psycopg2':  ['psycopg2>=2.8.1'],
        'psycopg2-binary': ['psycopg2-binary>=2.8.1'],
    },
    license='BSD License',
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Database",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Text Processing :: Linguistic",
    ],
)
