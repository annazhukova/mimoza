#!/usr/local/bin/python2.7
# -*- coding: UTF-8 -*-
import logging
import os
import cgi
import cgitb
from os.path import dirname, abspath
import sys

import libsbml

from sbml_generalization.generalization.sbml_generalizer import generalize_model
from mod_sbml.onto import parse_simple
from mod_sbml.annotation.chebi.chebi_serializer import get_chebi
from sbml_vis.mimoza_path import *
from sbml_vis.html.html_t_generator import create_thanks_for_uploading_html, generate_generalization_finished_html

cgitb.enable()
# Windows needs stdio set for binary mode.
try:
    import msvcrt

    msvcrt.setmode(0, os.O_BINARY)  # stdin  = 0
    msvcrt.setmode(1, os.O_BINARY)  # stdout = 1
except ImportError:
    pass

form = cgi.FieldStorage()
sbml = form['sbml'].value
m_dir_id = form['dir'].value

print('''Content-Type: text/html;charset=utf-8


        <html lang="en">

          <head>
             <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
             <meta http-equiv="Pragma" content="no-cache" />
             <meta http-equiv="Expires" content="0" />
             <link media="all" href="http://mimoza.bordeaux.inria.fr/lib/modelmap/modelmap.min.css" type="text/css" rel="stylesheet" />
             <link rel="stylesheet" type="text/css" href="http://mimoza.bordeaux.inria.fr/lib/FullWidthTabs/component.min.css" />
             <link rel="stylesheet" type="text/css" href="http://mimoza.bordeaux.inria.fr/lib/FullWidthTabs/demo.min.css" />
             <link media="all" href="http://mimoza.bordeaux.inria.fr/lib/jquery/jquery-ui.min.css" type="text/css" rel="stylesheet" />

             <link href="http://mimoza.bordeaux.inria.fr/lib/modelmap/fav.ico" type="image/x-icon" rel="shortcut icon" />

             <script src="http://mimoza.bordeaux.inria.fr/lib/jquery/jquery-2.1.4.min.js" type="text/javascript"></script>
             <script src="http://mimoza.bordeaux.inria.fr/lib/jquery/jquery-ui.min.js" type="text/javascript"></script>
             <title>Generalizing...</title>
          </head>

          <body>
          <br/>
          <p class="centre">Please, be patient while we are generalizing your model...</p>
          <br/>
          <img class="img-centre" src="http://mimoza.bordeaux.inria.fr/lib/modelmap/method.gif" id="img" />
          <div id="hidden" style="visibility:hidden;height:0px;">''')

sys.stdout.flush()
url = '%s/%s/index.html' % (MIMOZA_URL, m_dir_id)
directory = os.path.join('..', 'html', m_dir_id)

log_file = os.path.join(directory, 'log.log')
logging.basicConfig(level=logging.INFO, format='%(message)s', filename=log_file)

try:
    logging.info('calling model_generalisation library')
    reader = libsbml.SBMLReader()
    input_document = reader.readSBML(sbml)
    input_model = input_document.getModel()
    m_id = input_model.getId()

    sbml_directory = dirname(abspath(sbml))
    groups_sbml = os.path.join(sbml_directory, '%s_with_groups.xml' % m_id)

    if not os.path.exists(groups_sbml):
        chebi = parse_simple(get_chebi())
        gen_sbml = os.path.join(sbml_directory, '%s_generalized.xml' % m_id)
        r_id2g_id, s_id2gr_id, species_id2chebi_id, ub_sps = generalize_model(sbml, chebi, groups_sbml, gen_sbml)
    create_thanks_for_uploading_html(m_id, input_model.getName(), '../html', m_dir_id,
                                     MIMOZA_URL, 'comp.html', generate_generalization_finished_html)

except Exception as e:
    logging.info(e)
    url = MIMOZA_ERROR_URL

sys.stdout.flush()

print('''</div>
          </body>
          <script type="text/javascript">
                window.location = "%s"
          </script>
        </html>''' % url)
sys.stdout.flush()