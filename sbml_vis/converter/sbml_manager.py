import logging
import libsbml
from mod_sbml.annotation.gene_ontology.go_annotator import GO_PREFIX
from mod_sbml.annotation.rdf_annotation_helper import add_annotation

from sbml_generalization.sbml.sbml_helper import convert_to_lev3_v1
from mod_sbml.sbml.sbml_manager import create_compartment, generate_unique_id
from sbml_vis.graph.transformation_manager import scale, get_layout_characteristics, shift, MARGIN

__author__ = 'anna'


def get_layout(glyph):
    bb = glyph.getBoundingBox()
    d = bb.getDimensions()
    w = d.getWidth()
    h = d.getHeight()
    p = bb.getPosition()
    x = p.getXOffset() + w / 2
    y = p.getYOffset() + h / 2
    return (x, y), (w, h)


def parse_layout_sbml(layout_sbml):
    doc = libsbml.SBMLReader().readSBMLFromFile(layout_sbml)
    model = doc.getModel()
    layout_plugin = model.getPlugin("layout")
    n2xy = {}
    if layout_plugin:
        for layout in layout_plugin.getListOfLayouts():
            l_id = layout.getId()
            for s_glyph in layout.getListOfSpeciesGlyphs():
                s_id = s_glyph.getSpeciesId()
                s_glyph_id = s_glyph.getId()
                r_id = None
                prefix = "sg_%s_%s" % (l_id, s_id)
                suffix_start = s_glyph_id.find(prefix)
                if suffix_start != -1:
                    s_glyph_id = s_glyph_id[suffix_start + len(prefix):]
                    if s_glyph_id and s_glyph_id[0] == '_':
                        r_id = s_glyph_id[1:]
                lo = get_layout(s_glyph)
                if r_id:
                    if model.getReaction(r_id):
                        if s_id not in n2xy:
                            n2xy[s_id] = {}
                        n2xy[s_id][r_id] = lo
                else:
                    n2xy[s_id] = lo
            for r_glyph in layout.getListOfReactionGlyphs():
                r_id = r_glyph.getReactionId()
                n2xy[r_id] = get_layout(r_glyph)
            for c_glyph in layout.getListOfCompartmentGlyphs():
                c_id = c_glyph.getCompartmentId()
                n2xy[c_id] = get_layout(c_glyph)
    else:
        raise LoPlError()
    return n2xy


def save_as_sbml(input_model, out_sbml):
    logging.info("saving to {0}".format(out_sbml))
    out_doc = libsbml.SBMLDocument(input_model.getSBMLNamespaces())
    out_doc.setModel(input_model)
    libsbml.writeSBMLToFile(out_doc, out_sbml)


def check_compartments(model):
    if not model.getListOfCompartments():
        cell = create_compartment(model, "cell", outside=None)
        add_annotation(cell, libsbml.BQB_IS, "GO:0005623", GO_PREFIX)
        for sp in model.getListOfSpecies():
            sp.setCompartment(cell.getId())


def check_names(model):
    def name_setter(collection):
        for it in collection:
            if not it.isSetName():
                it.setName(it.getId())

    name_setter(model.getListOfCompartments())
    name_setter(model.getListOfSpecies())
    name_setter(model.getListOfSpeciesTypes())


def save_as_layout_sbml(groups_model, gen_model, layout_sbml, gen_layout_sbml, n2lo, ub_sps):
    logging.info("serializing layout")

    doc = convert_to_lev3_v1(groups_model)
    layout_model = doc.getModel()
    layout_plugin = layout_model.getPlugin("layout")

    if layout_plugin:
        create_layout(n2lo, layout_model, layout_plugin, ub_sps, groups_model)
        save_as_sbml(layout_model, layout_sbml)

    if gen_model:
        doc = convert_to_lev3_v1(gen_model)
        gen_layout_model = doc.getModel()
        gen_layout_plugin = gen_layout_model.getPlugin("layout")
        if gen_layout_plugin:
            create_layout(n2lo, gen_layout_model, gen_layout_plugin, ub_sps, gen_model)
            save_as_sbml(gen_layout_model, gen_layout_sbml)


def link_reaction_to_species(s_refs, r_glyph, l_id, r_id, n2lo, role):
    for s_ref in s_refs:
        s_id = s_ref.getSpecies()
        s_ref_glyph = r_glyph.createSpeciesReferenceGlyph()
        s_ref_glyph.setId("srg_%s_%s_%s" % (l_id, r_id, s_id))
        s_glyph_id_suffix = s_id
        if isinstance(n2lo[s_id], dict):
            for r_ids in n2lo[s_id].iterkeys():
                if r_id in r_ids:
                    s_glyph_id_suffix = "%s_%s" % (s_id, '_'.join(r_ids))
        s_ref_glyph.setSpeciesGlyphId("sg_%s_%s" % (l_id, s_glyph_id_suffix))
        s_ref_glyph.setSpeciesReferenceId(s_ref.getId())
        s_ref_glyph.setRole(role(s_id))


def create_dimensions(width, height):
    """Create a dimension object with given width and height"""
    dim = libsbml.Dimensions()
    dim.setWidth(width)
    dim.setHeight(height)
    return dim


def create_bounding_box(x, y, width, height):
    """Create a bounding box object with given coordinates and dimensions"""
    bb = libsbml.BoundingBox()
    bb.setX(x - width / 2)
    bb.setY(y - height / 2)
    bb.setWidth(width)
    bb.setHeight(height)
    return bb


def add_label(label, layout, glyph, _id, w, h, x, y):
    text_glyph = layout.createTextGlyph()
    text_glyph.setId("tg_%s_%s" % (layout.getId(), _id))
    text_glyph.setBoundingBox(create_bounding_box(x, y, w * 1.8, h * 1.8))
    text_glyph.setText(label)
    text_glyph.setGraphicalObjectId(glyph.getId())


def create_layout(n2lo, layout_model, layout_plugin, ub_sps, model):
    h_min, (x_shift, y_shift), (w, h) = get_layout_characteristics(n2lo)
    scale_factor = MARGIN * 1.0 / (h_min if h_min else 1)
    (w, h) = scale((w, h), scale_factor)
    (x_shift, y_shift) = shift(scale((x_shift, y_shift), scale_factor), MARGIN, MARGIN)

    layout = layout_plugin.createLayout()
    layout.setId(generate_unique_id(layout_model, "l_"))
    l_id = layout.getId()
    layout.setDimensions(create_dimensions(w + 2 * MARGIN, h + 2 * MARGIN))

    for comp in model.getListOfCompartments():
        c_id = comp.getId()
        c_name = comp.getName()
        if c_id in n2lo:
            (x, y), (w, h) = n2lo[c_id]
            (x, y), (w, h) = shift(scale((x, y), scale_factor), x_shift, y_shift), scale((w, h), scale_factor)
            comp_glyph = layout.createCompartmentGlyph()
            comp_glyph.setId("cg_%s_%s" % (l_id, c_id))
            comp_glyph.setCompartmentId(c_id)
            comp_glyph.setBoundingBox(create_bounding_box(x, y, w, h))
            add_label(c_name, layout, comp_glyph, c_id, w, h, x, y)

    for species in model.getListOfSpecies():
        s_id = species.getId()
        s_name = species.getName()
        if s_id in n2lo:
            if isinstance(n2lo[s_id], dict):
                elements = n2lo[s_id].iteritems()
            else:
                elements = [('', n2lo[s_id])]
            for r_ids, [(x, y), (w, h)] in elements:
                if not r_ids or next((it for it in (model.getReaction(r_id) for r_id in r_ids) if it), False):
                    (x, y), (w, h) = shift(scale((x, y), scale_factor), x_shift, y_shift), scale((w, h), scale_factor)
                    s_glyph = layout.createSpeciesGlyph()
                    s_glyph.setSpeciesId(s_id)
                    s_glyph_suffix = "%s_%s" % (s_id, '_'.join(r_ids)) if r_ids else s_id
                    s_glyph.setId("sg_%s_%s" % (l_id, s_glyph_suffix))
                    s_glyph.setBoundingBox(create_bounding_box(x, y, w, h))
                    add_label(s_name, layout, s_glyph, s_id, w, h, x, y)

    for reaction in model.getListOfReactions():
        r_id = reaction.getId()
        r_name = reaction.getName()
        if r_id in n2lo:
            (x, y), (w, h) = n2lo[r_id]
            (x, y), (w, h) = shift(scale((x, y), scale_factor), x_shift, y_shift), scale((w, h), scale_factor)
            r_glyph = layout.createReactionGlyph()
            r_glyph.setReactionId(r_id)
            r_glyph.setId("rg_%s_%s" % (l_id, r_id))
            r_glyph.setBoundingBox(create_bounding_box(x, y, w, h))
            add_label(r_name, layout, r_glyph, r_id, w, h, x, y)
            link_reaction_to_species(reaction.getListOfReactants(), r_glyph, l_id, r_id, n2lo,
                                     lambda s_id: libsbml.SPECIES_ROLE_SIDESUBSTRATE
                                     if s_id in ub_sps else libsbml.SPECIES_ROLE_SUBSTRATE)
            link_reaction_to_species(reaction.getListOfProducts(), r_glyph, l_id, r_id, n2lo,
                                     lambda s_id: libsbml.SPECIES_ROLE_SIDEPRODUCT
                                     if s_id in ub_sps else libsbml.SPECIES_ROLE_PRODUCT)


class LoPlError(Exception):
    def __init__(self):
        self.msg = "layout plugin not installed"
