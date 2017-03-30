import os
from distutils.core import setup

setup(name='sbml_vis',
      description='SBML zoomable visualization utilities.',
      long_description=open('README.md').read(),
      author='Anna Zhukova',
      author_email='zhutchok@gmail.com',
      url='https://github.com/annazhukova/mimoza',
      version='0.1',
      packages=['sbml_vis'],
      package_data={'sbml_vis': [os.path.join('html', 'templates', '*.html'),
                                 os.path.join('converter', '*.py'),
                                 os.path.join('file', '*.py'),
                                 os.path.join('graph', '*.py'),
                                 os.path.join('graph', '*', '*.py'),
                                 os.path.join('html', '*.py'),
                                 os.path.join('..', 'main.py'),
                                 os.path.join('..', 'lib', '*'),
                                 os.path.join('..', 'lib', '*', '*'),
                                 os.path.join('..', 'lib', '*', '*', '*'),
                                 os.path.join('..', 'lib', '*', '*', '*', '*')]},
      include_package_data=True,
      platform=['MacOS', 'Linux', 'Windows'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Topic :: Scientific/Engineering :: Bio-Informatics',
          'Topic :: Scientific/Engineering :: Visualization',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      download_url='https://github.com/annazhukova/mimoza/archive/0.1.zip',
      requires=['sympy', 'geojson', 'jinja2', 'mod_sbml', 'tarjan', 'sbml_generalization',
                'libsbgnpy', 'tulip-python', 'python-libsbml-experimental', 'pandas', 'urllib3']
      )
