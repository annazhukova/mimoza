#!/usr/local/bin/python2.7
# -*- coding: UTF-8 -*-

import logging
import os
import cgi
import cgitb
import sys

import libsbml

try:
    from sbml_vis.converter.sbgn_helper import save_as_sbgn
    sbgn_export_available = True
except ImportError:
    sbgn_export_available = False

from sbml_vis.converter.sbml_manager import parse_layout_sbml, LoPlError, save_as_layout_sbml
from sbml_vis.file.serializer import serialize
from sbml_vis.converter.sbml2tlp import import_sbml
from sbml_vis.mimoza_path import *
from sbml_vis.converter.tulip_graph2geojson import graph2geojson
from mod_sbml.onto import parse_simple
from mod_sbml.annotation.chebi.chebi_serializer import get_chebi


cgitb.enable()
# Windows needs stdio set for binary mode.
try:
    import msvcrt
    msvcrt.setmode(0, os.O_BINARY)  # stdin  = 0
    msvcrt.setmode(1, os.O_BINARY)  # stdout = 1
except ImportError:
    pass

form = cgi.FieldStorage()
groups_sbml = form['sbml'].value
gen_sbml = form['gen_sbml'].value
groups_sbgn = form['sbgn'].value
gen_sbgn = form['gen_sbgn'].value
m_dir_id = form['dir'].value
directory = '../html/%s/' % m_dir_id
log_file = '%s/log.log' % directory
logging.basicConfig(level=logging.INFO, format='%(message)s', filename=log_file)

print '''Content-Type: text/html;charset=utf-8


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
            <title>Visualizing...</title>
          </head>

          <body>
          <br/>
          <p class="centre">We are visualizing your model now...</p>
          <br/>
          <img class="img-centre" src="http://mimoza.bordeaux.inria.fr/lib/modelmap/ajax-loader.gif" id="img" />
          <div id="hidden" style="visibility:hidden;height:0px;">'''

sys.stdout.flush()

temp = os.dup(sys.stdout.fileno())
try:
    url = '/%s/comp.html' % m_dir_id

    if not os.path.exists(os.path.join('..', m_dir_id, 'comp.html')):
        chebi = parse_simple(get_chebi())
        reader = libsbml.SBMLReader()
        input_document = reader.readSBML(groups_sbml)
        input_model = input_document.getModel()

        # sbml -> tulip graph
        logging.info('sbml -> tlp')
        graph, c_id2info, c_id2outs, chebi, ub_sps = import_sbml(input_model, groups_sbml)

        try:
            n2xy = parse_layout_sbml(groups_sbml)
        except LoPlError:
            n2xy = None

        fc, (n2lo, e2lo), hidden_c_ids, c_id_hidden_ubs = graph2geojson(c_id2info, c_id2outs, graph, n2xy, onto=chebi)
        c_id2out_c_id = {}
        for c_id, info in c_id2info.iteritems():
            if c_id not in fc:
                continue
            _, _, (_, out_c_id) = info
            if out_c_id and out_c_id in fc:
                c_id2out_c_id[c_id] = out_c_id

        if not n2xy or gen_sbml:
            groups_document = reader.readSBML(groups_sbml)
            groups_model = groups_document.getModel()
            gen_document = reader.readSBML(gen_sbml)
            gen_model = gen_document.getModel()
            save_as_layout_sbml(groups_model, gen_model, groups_sbml, gen_sbml, n2lo, ub_sps)

        if sbgn_export_available:
            logging.info('exporting as SBGN...')
            try:
                groups_document = reader.readSBML(groups_sbml)
                groups_model = groups_document.getModel()
                save_as_sbgn(n2lo, e2lo, groups_model, groups_sbgn)
                logging.info('   exported as SBGN %s' % groups_sbgn)
                if gen_sbml:
                    gen_document = reader.readSBML(gen_sbml)
                    gen_model = gen_document.getModel()
                    save_as_sbgn(n2lo, e2lo, gen_model, gen_sbgn)
                    logging.info('   exported as SBGN %s' % gen_sbgn)
            except Exception as e:
                logging.info(e.message)

        serialize(directory, m_dir_id, input_model, fc, c_id2out_c_id, hidden_c_ids, c_id_hidden_ubs,
                  groups_sbml)

except Exception as e:
    logging.info(e.message)
    url = MIMOZA_ERROR_URL

sys.stdout.flush()

print '''</div>
          </body>
          <script type="text/javascript">
                window.location = "%s"
          </script>
        </html>''' % url
sys.stdout.flush()