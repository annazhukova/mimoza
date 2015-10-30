import logging
import os
from os.path import dirname, abspath
from shutil import copytree

import libsbml

from sbml_vis.graph.color.color import color_by_id
from sbml_vis.graph.color.color import color
from sbml_vis.converter.tlp2geojson import DEFAULT_LAYER2MASK
from sbml_vis.graph.resize import REACTION_SIZE
from sbml_vis.converter.sbml2tlp import import_sbml
from sbml_vis.converter.tulip_graph2geojson import graph2geojson
from sbml_vis.file.md5_checker import check_md5
from sbml_vis.file.serializer import serialize, ABOUT_TAB, DOWNLOAD_TAB
from sbml_generalization.generalization.sbml_generalizer import generalize_model, ubiquitize_model
from mimoza.mimoza_path import MIMOZA_URL
import mimoza
from mod_sbml.onto import parse_simple
from mod_sbml.annotation.chebi.chebi_serializer import get_chebi
from sbml_vis.converter.sbgn_helper import save_as_sbgn
from sbml_generalization.sbml.sbml_helper import check_for_groups, SBO_CHEMICAL_MACROMOLECULE, GROUP_TYPE_UBIQUITOUS
from sbml_vis.converter.sbml_manager import parse_layout_sbml, LoPlError, save_as_layout_sbml
from sbml_vis.graph.transformation_manager import scale

__author__ = 'anna'


def get_lib():
    return os.path.join(os.path.dirname(os.path.abspath(mimoza.mimoza_path.__file__)), '..', 'lib')


def process_sbml(sbml, verbose, ub_ch_ids=None, path=None, generalize=True, log_file=None,
                 id2mask=None, layer2mask=DEFAULT_LAYER2MASK, tab2html=None, title=None,
                 id2color=None, tabs={ABOUT_TAB, DOWNLOAD_TAB}, info='', invisible_layers=None):
    reader = libsbml.SBMLReader()
    doc = reader.readSBML(sbml)
    model = doc.getModel()
    if not model:
        raise Exception("The model should be in SBML format")
    model_id = model.getId()
    if not model_id:
        sbml_name = os.path.splitext(os.path.basename(sbml))[0]
        model.setId(sbml_name)
        model_id = sbml_name
    m_id = path if path else check_md5(sbml)
    sbml_dir = dirname(abspath(sbml))
    directory = os.path.join(sbml_dir, m_id)
    if not os.path.exists(directory):
        os.makedirs(directory)
    lib_path = os.path.join(directory, 'lib')
    if not os.path.exists(lib_path):
        copytree(get_lib(), lib_path)
    if verbose:
        logging.captureWarnings(True)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s',
                            datefmt="%Y-%m-%d %H:%M:%S", filename=log_file)
        logging.captureWarnings(True)
    groups_sbml = os.path.join(directory, '%s_with_groups.xml' % model_id)
    gen_sbml = os.path.join(directory, '%s_generalized.xml' % model_id)
    if check_for_groups(sbml, SBO_CHEMICAL_MACROMOLECULE, GROUP_TYPE_UBIQUITOUS):
        if sbml != groups_sbml:
            if not libsbml.SBMLWriter().writeSBMLToFile(doc, groups_sbml):
                raise Exception("Could not write your model to %s" % groups_sbml)
    else:
        chebi = parse_simple(get_chebi())
        if generalize:
            logging.info('Generalizing the model...')
            generalize_model(groups_sbml, gen_sbml, sbml, chebi, ub_chebi_ids=ub_ch_ids)
        else:
            gen_sbml = None
            logging.info('Ubiquitizing the model...')
            ubiquitize_model(groups_sbml, sbml, chebi, ub_chebi_ids=ub_ch_ids)

    reader = libsbml.SBMLReader()
    input_document = reader.readSBML(groups_sbml)
    input_model = input_document.getModel()

    root, c_id2info, c_id2outs, chebi, ub_sps = import_sbml(input_model, groups_sbml)

    c_id2out_c_id = {}
    for c_id, c_info in c_id2info.iteritems():
        _, _, (_, out_c_id) = c_info
        if out_c_id:
            c_id2out_c_id[c_id] = out_c_id
    try:
        n2xy = parse_layout_sbml(sbml)
        if n2xy:
            logging.info('Found layout in the model...')
            r_size = next((n2xy[r.getId()][1][0] for r in input_model.getListOfReactions() if r.getId() in n2xy), None)
            if r_size:
                scale_factor = REACTION_SIZE / r_size
                if scale_factor != 1:
                    keys = n2xy.keys()
                    for n_id in keys:
                        value = n2xy[n_id]
                        if isinstance(value, dict):
                            value = {r_id: (scale(xy, scale_factor), scale(wh, scale_factor))
                                     for (r_id, (xy, wh)) in value.iteritems()}
                        else:
                            xy, wh = value
                            value = scale(xy, scale_factor), scale(wh, scale_factor)
                        n2xy[n_id] = value
    except LoPlError:
        n2xy = None
    fc, (n2lo, e2lo), hidden_c_ids, c_id_hidden_ubs = \
        graph2geojson(c_id2info, c_id2outs, root, n2xy, id2mask=id2mask, onto=chebi,
                      colorer=color if not id2color else lambda graph: color_by_id(graph, id2color))
    if n2lo:
        groups_document = reader.readSBML(groups_sbml)
        groups_model = groups_document.getModel()
        if gen_sbml:
            gen_document = reader.readSBML(gen_sbml)
            gen_model = gen_document.getModel()
        else:
            gen_model = False
        save_as_layout_sbml(groups_model, gen_model, groups_sbml, gen_sbml, n2lo, ub_sps)
        groups_sbgn = os.path.join(directory, '%s.sbgn' % model_id)
        gen_sbgn = os.path.join(directory, '%s_generalized.sbgn' % model_id)
        save_as_sbgn(n2lo, e2lo, groups_model, groups_sbgn)
        logging.info('   exported as SBGN %s' % groups_sbgn)
        if gen_model:
            save_as_sbgn(n2lo, e2lo, gen_model, gen_sbgn)

    serialize(directory=directory, m_dir_id=m_id, input_model=input_model, c_id2level2features=fc,
              c_id2out_c_id=c_id2out_c_id, hidden_c_ids=hidden_c_ids, c_id_hidden_ubs=c_id_hidden_ubs,
              groups_sbml=groups_sbml, layer2mask=layer2mask, tab2html=tab2html, title=title, tabs=tabs, info=info,
              invisible_layers=invisible_layers)

