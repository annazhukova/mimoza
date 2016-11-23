import json
from itertools import chain

from mod_sbml.annotation.chebi.chebi_annotator import get_chebi_id
from mod_sbml.sbml.sbml_manager import get_gene_association
from sbml_vis.graph.transformation_manager import get_layout_characteristics, MARGIN, scale, shift, transform
from mod_sbml.sbml.sbml_manager import get_reactants, get_products

EDGES = 'edges'
NODES = 'nodes'
ELEMENTS = 'elements'

INTERACTION = 'interaction'

TARGET = 'target'
SOURCE = 'source'

REVERSIBLE = 'reversible'
UBIQUITOUS = 'ubiquitous'
COMPARTMENT = 'compartment'
GLYPH_TYPE = 'glyph_type'

Y = 'y'
X = 'x'
Z = 'z'

POSITION = 'position'
DATA = 'data'
TYPE = 'type'
HEIGHT = 'h'
WEIGHT = 'w'
ID = 'id'
NAME = 'name'

SUBSTRATE = 'substrate'
PRODUCT = 'product'

COMPLEX_MULTIMER = 'COMPLEX MULTIMER'
COMPLEX = 'COMPLEX'
MACROMOLECULE_MULTIMER = 'MACROMOLECULE MULTIMER'
SIMPLE_CHEMICAL_MULTIMER = 'SIMPLE CHEMICAL MULTIMER'
MACROMOLECULE = 'MACROMOLECULE'
SIMPLE_CHEMICAL = 'SIMPLE CHEMICAL'
UNSPECIFIED_ENTITY = 'UNSPECIFIED ENTITY'

SBO_2_GLYPH_TYPE = {'SBO:0000247': SIMPLE_CHEMICAL, 'SBO:0000245': MACROMOLECULE,
                    'SBO:0000421': SIMPLE_CHEMICAL_MULTIMER,
                    'SBO:0000420': MACROMOLECULE_MULTIMER,
                    'SBO:0000253': COMPLEX, 'SBO:0000418': COMPLEX_MULTIMER}

TYPE_COMPARTMENT = 'COMPARTMENT'
TYPE_SPECIES = 'METABOLITE'
TYPE_REACTION = 'REACTION'


def get_name(element):
    name = element.getName()
    return name if name else element.getId()


def get_node(x, y, z=0, **data):
    return {DATA: data, POSITION: {X: x, Y: y, Z: z}}


def get_edge(**data):
    return {DATA: data}


def save_as_cytoscape_json(n2lo, model, out_json, ub_sp_ids):
    """
    Converts a model with the given node and edge layout to a json file readable by Cytoscape.
    :param ub_sp_ids: collection of ubiquitous species ids
    :param n2lo: node layout as a dictionary    {node_id: ((x, y), (w, h)) if node is not ubiquitous
                                                else node_id : {r_ids: ((x, y), (w, h)) for r_ids of
                                                reactions using each duplicated metabolite}}
    :param model: SBML model
    :param out_json: path where to save the resulting json file.
    """
    # let's scale the map so that a minimal node has a width == 16 (so that the labels fit)
    h_min, (x_shift, y_shift), _ = get_layout_characteristics(n2lo)
    scale_factor = MARGIN * 1.0 / h_min if h_min else 1
    (x_shift, y_shift) = shift(scale((x_shift, y_shift), scale_factor), MARGIN, MARGIN)

    nodes, edges = [], []

    for comp in model.getListOfCompartments():
        c_id = comp.getId()
        c_name = get_name(comp)
        if c_id in n2lo:
            (x, y), (w, h) = transform(n2lo[c_id], x_shift, y_shift, scale_factor)
            nodes.append(get_node(x=x + w / 2, y=y + h / 2, z=-1,
                                  **{NAME: c_name, ID: c_id, WEIGHT: w, HEIGHT: h, TYPE: TYPE_COMPARTMENT}))

    for species in model.getListOfSpecies():
        s_id = species.getId()
        s_name = get_name(species)
        glyph_type = UNSPECIFIED_ENTITY
        sbo_term = species.getSBOTermID()
        if sbo_term:
            sbo_term = sbo_term.upper().strip()
            if sbo_term in SBO_2_GLYPH_TYPE:
                glyph_type = SBO_2_GLYPH_TYPE[sbo_term]
        if s_id in n2lo:
            if isinstance(n2lo[s_id], dict):
                elements = n2lo[s_id].items()
            else:
                elements = [('', n2lo[s_id])]
            for r_ids, coords in elements:
                if not r_ids or next((it for it in (model.getReaction(r_id) for r_id in r_ids) if it), False):
                    (x, y), (w, h) = transform(coords, x_shift, y_shift, scale_factor)
                    nodes.append(
                        get_node(x=x + w / 2, y=y + h / 2, z=1,
                                 **{GLYPH_TYPE: glyph_type, ID: "%s_%s" % (s_id, '_'.join(r_ids)) if r_ids else s_id,
                                    COMPARTMENT: species.getCompartment(), NAME: s_name, WEIGHT: w, HEIGHT: h,
                                    TYPE: TYPE_SPECIES, UBIQUITOUS: s_id in ub_sp_ids,
                                    'ChEBI': get_chebi_id(species)}))

    def get_sref_id(s_id):
        if isinstance(n2lo[s_id], dict):
            for r_ids in n2lo[s_id].keys():
                if r_id in r_ids:
                    return "%s_%s" % (s_id, '_'.join(r_ids))
        return s_id

    for reaction in model.getListOfReactions():
        r_id = reaction.getId()
        r_name = get_name(reaction)
        ga = get_gene_association(reaction)
        if r_id in n2lo:
            (x, y), (w, h) = transform(n2lo[r_id], x_shift, y_shift, scale_factor)
            nodes.append(get_node(x=x + w / 2, y=y + h / 2, z=1,
                                  **{ID: r_id, NAME: ga, WEIGHT: w, HEIGHT: h, TYPE: TYPE_REACTION,
                                     REVERSIBLE: reaction.getReversible(),
                                     UBIQUITOUS:
                                         next((False for s_id in chain(get_reactants(reaction), get_products(reaction))
                                               if s_id not in ub_sp_ids), True),
                                     'genes': ga, 'r_name': r_name}))

            for s_id in get_reactants(reaction):
                edges.append(get_edge(**{ID: "%s_%s" % (r_id, s_id), SOURCE: r_id, TARGET: get_sref_id(s_id),
                                             NAME: '%s is a substrate of %s' % (get_name(model.getSpecies(s_id)), r_name),
                                             UBIQUITOUS: s_id in ub_sp_ids, INTERACTION: SUBSTRATE}))

            for s_id in get_products(reaction):
                edges.append(get_edge(**{ID: "%s_%s" % (r_id, s_id), SOURCE: r_id, TARGET: get_sref_id(s_id),
                                             NAME: '%s is a product of %s' % (get_name(model.getSpecies(s_id)), r_name),
                                             UBIQUITOUS: s_id in ub_sp_ids, INTERACTION: PRODUCT}))

    save_cyjson(nodes, edges, out_json)


def save_cyjson(nodes, edges, out_json):
    json_dict = {ELEMENTS: {NODES: nodes, EDGES: edges}}
    with open(out_json, 'w+') as fp:
        json.dump(json_dict, fp)
