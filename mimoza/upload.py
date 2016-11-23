#!/usr/local/bin/python2.7
# -*- coding: UTF-8 -*-

import cgi
import logging
import os
import cgitb
from shutil import copytree
import sys
import base64

import libsbml

from sbml_vis.html.html_t_generator import create_thanks_for_uploading_html, generate_uploaded_generalized_sbml_html
from sbml_vis.file.md5_checker import check_md5
from sbml_vis.mimoza_path import *
from sbml_generalization.sbml.sbml_helper import check_for_groups, SBO_CHEMICAL_MACROMOLECULE, GROUP_TYPE_UBIQUITOUS

ALREADY_EXISTS = 1
OK = 0
NOT_MODEL = 2
ALREADY_GENERALIZED = 3


LIB = '../html/lib'

cgitb.enable()

# Windows needs stdio set for binary mode.
try:
    import msvcrt

    msvcrt.setmode(0, os.O_BINARY)  # stdin  = 0
    msvcrt.setmode(1, os.O_BINARY)  # stdout = 1
except ImportError:
    pass


# Generator to buffer file chunks
def file_buffer(f, chunk_size=10000):
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk


def upload_file():
    form = cgi.FieldStorage()
    # A nested FieldStorage instance holds the file
    file_item = form['file_input']
    # Test if the file was uploaded
    if file_item.filename:
        # strip leading path from file name to avoid directory traversal attacks
        file_name = os.path.basename(file_item.filename)
        safe_fn = base64.urlsafe_b64encode(file_name)
        sfn = "%s" % safe_fn
        i = 0
        while os.path.exists(os.path.join('..', 'uploads', sfn)):
            sfn = '%s_%d' % (safe_fn, i)
            i += 1
        f_path = os.path.join('..', 'uploads', sfn)
        f = open(f_path, 'wb', 10000)
        # Read the file in chunks
        for chunk in file_buffer(file_item.file):
            f.write(chunk)
        f.close()
        return process_file(f_path)
    else:
        return NOT_MODEL, None


def process_file(sbml_file):
    reader = libsbml.SBMLReader()
    doc = reader.readSBML(sbml_file)
    model = doc.getModel()
    if not model:
        return NOT_MODEL, None
    model_id = model.getId()
    if not model_id:
        sbml_name = os.path.splitext(os.path.basename(sbml_file))[0]
        model.setId(sbml_name)
        model_id = sbml_name

    m_id = check_md5(sbml_file)
    directory = os.path.join('..', 'html', m_id)
    if os.path.exists(directory):
        if os.path.exists(os.path.join(directory, 'index.html')):
            return ALREADY_EXISTS, (model_id, m_id)
    else:
        os.makedirs(directory)
        copytree(LIB, os.path.join(directory, 'lib'))

    log_file = None
    try:
        log_file = os.path.join(directory, 'log.log')
        with open(log_file, "w+"):
            pass
    except:
        pass
    logging.basicConfig(level=logging.INFO, format='%(message)s', filename=log_file)

    if check_for_groups(sbml_file, SBO_CHEMICAL_MACROMOLECULE, GROUP_TYPE_UBIQUITOUS):
        new_sbml_file = os.path.join(directory, '%s_with_groups.xml' % model_id)
        if sbml_file != new_sbml_file:
            if not libsbml.writeSBMLToFile(doc, new_sbml_file):
                return NOT_MODEL, None
            os.remove(sbml_file)
        return ALREADY_GENERALIZED, (model_id, model.getName(), m_id)

    new_sbml_file = os.path.join(directory, '%s.xml' % model_id)
    if sbml_file != new_sbml_file:
        if not libsbml.writeSBMLToFile(doc, new_sbml_file):
            return NOT_MODEL, None
        os.remove(sbml_file)
    return OK, (model_id, model.getName(), m_id)

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
            <title>Checking...</title>
          </head>

          <body>
          <p class="info">We are checking your model now...</p>
          <img class="img-centre" src="http://mimoza.bordeaux.inria.fr/lib/modelmap/loader.gif" id="img" />
          <div id="hidden" style="visibility:hidden;height:0px;">''')
sys.stdout.flush()

result, args = upload_file()
url = MIMOZA_UPLOAD_ERROR_URL

if OK == result:
    (m_id, m_name, m_dir_id) = args
    create_thanks_for_uploading_html(m_id, m_name, '../html', m_dir_id, MIMOZA_URL, 'comp.html', groups_suffix='')
    url = '%s/%s/index.html' % (MIMOZA_URL, m_dir_id)
elif ALREADY_EXISTS == result:
    model_id, m_dir_id = args
    url = '%s/%s/index.html' % (MIMOZA_URL, m_dir_id)
elif ALREADY_GENERALIZED == result:
    (m_id, m_name, m_dir_id) = args
    create_thanks_for_uploading_html(m_id, m_name, '../html', m_dir_id, MIMOZA_URL, 'comp.html',
                                     generate_uploaded_generalized_sbml_html)
    url = '%s/%s/index.html' % (MIMOZA_URL, m_dir_id)


print('''</div>
          </body>
          <script type="text/javascript">
                window.location = "%s"
          </script>
        </html>''' % url)
sys.stdout.flush()

