from setuptools import setup, find_packages

requirements = [
    'peewee>=2.2.5',
]

setup(
    name='peewee-lockdown',
    author='Jason Horman',
    author_email='jhorman@gmail.com',
    version='1.0.0',
    url='http://github.com/jhorman/peewee-lockdown/',
    description='Secures peewee models',
    packages=find_packages(),
    zip_safe=False,
    platforms='any',
    install_requires=requirements,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)