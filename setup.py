from setuptools import setup

#with open('README.rst') as README:
#    long_description = README.read()
#    long_description = long_description[long_description.index('Description'):]

setup(name='wos',
      version='0.1',
      description='Web of Science client using API v3.',
#      long_description=long_description,
      install_requires=['suds'],
      url='http://github.com/enricobacis/wos',
      author='Enrico Bacis',
      author_email='enrico.bacis@gmail.com',
      license='MIT',
      packages=['wos'],
      keywords='wos isi web of science knowledge api client')