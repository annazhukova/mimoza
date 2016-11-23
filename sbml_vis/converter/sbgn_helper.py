from libsbgnpy import libsbgn
from libsbgnpy.libsbgnTypes import Language, GlyphClass, ArcClass

from sbml_vis.graph.transformation_manager import scale, get_layout_characteristics, shift, MARGIN, transform

SBO_2_GLYPH_TYPE = {'SBO:0000247': GlyphClass.SIMPLE_CHEMICAL, 'SBO:0000245': GlyphClass.MACROMOLECULE,
                    'SBO:0000421': GlyphClass.SIMPLE_CHEMICAL_MULTIMER,
                    'SBO:0000420': GlyphClass.MACROMOLECULE_MULTIMER,
                    'SBO:0000253': GlyphClass.COMPLEX, 'SBO:0000418': GlyphClass.COMPLEX_MULTIMER}


def save_as_sbgn(n2lo, e2lo, model, out_sbgn):
    """
    Converts a model with the given node and edge layout to SBGN PD (see http://www.sbgn.org/).
    :param n2lo: node layout as a dictionary    {node_id: ((x, y), (w, h)) if node is not ubiquitous
                                                else node_id : {r_ids: ((x, y), (w, h)) for r_ids of
                                                reactions using each duplicated metabolite}}
    :param e2lo: edge layout as a dictionary    {edge_id: [(x_start, y_start), (x_bend_0, y_bend_0),..,(x_end, y_end)]},
                                                where edge_id = "-".join(sorted((metabolite_id, reaction_id))).
    :param model: SBML model
    :param out_sbgn: path where to save the resulting SBGN file.
    """
    # let's scale the map so that a minimal node has a width == 16 (so that the labels fit)
    h_min, (x_shift, y_shift), (w, h) = get_layout_characteristics(n2lo)
    scale_factor = MARGIN * 1.0 / h_min if h_min else 1
    (w, h) = scale((w, h), scale_factor)
    (x_shift, y_shift) = shift(scale((x_shift, y_shift), scale_factor), MARGIN, MARGIN)

    # create empty sbgn
    sbgn = libsbgn.sbgn()

    # create map, set language and set in sbgn
    sbgn_map = libsbgn.map()
    sbgn_map.set_language(Language.PD)
    sbgn.set_map(sbgn_map)

    # create a bounding box for the map
    box = libsbgn.bbox(0, 0, w + 2 * MARGIN, h + 2 * MARGIN)
    sbgn_map.set_bbox(box)

    # glyphs with labels
    for comp in model.getListOfCompartments():
        c_id = comp.getId()
        c_name = comp.getName()
        if not c_name:
            c_name = c_id
        if c_id in n2lo:
            (x, y), (w, h) = transform(n2lo[c_id], x_shift, y_shift, scale_factor)
            g = libsbgn.glyph(class_=GlyphClass.COMPARTMENT, id=c_id)
            g.set_label(libsbgn.label(text=c_name, bbox=libsbgn.bbox(x, y, w, h)))
            g.set_bbox(libsbgn.bbox(x, y, w, h))
            sbgn_map.add_glyph(g)

    for species in model.getListOfSpecies():
        s_id = species.getId()
        s_name = species.getName()
        glyph_type = GlyphClass.UNSPECIFIED_ENTITY
        sbo_term = species.getSBOTermID()
        if sbo_term:
            sbo_term = sbo_term.upper().strip()
            if sbo_term in SBO_2_GLYPH_TYPE:
                glyph_type = SBO_2_GLYPH_TYPE[sbo_term]
        if not s_name:
            s_name = s_id
        if s_id in n2lo:
            if isinstance(n2lo[s_id], dict):
                elements = n2lo[s_id].items()
            else:
                elements = [('', n2lo[s_id])]
            for r_ids, coords in elements:
                if not r_ids or next((it for it in (model.getReaction(r_id) for r_id in r_ids) if it), False):
                    (x, y), (w, h) = transform(coords, x_shift, y_shift, scale_factor)
                    g = libsbgn.glyph(class_=glyph_type, id="%s_%s" % (s_id, '_'.join(r_ids)) if r_ids else s_id,
                                      compartmentRef=species.getCompartment())
                    g.set_label(libsbgn.label(text=s_name,
                                              bbox=libsbgn.bbox(x + w * 0.1, y + h * 0.1, w * 0.8, h * 0.8)))
                    g.set_bbox(libsbgn.bbox(x, y, w, h))
                    sbgn_map.add_glyph(g)

    # glyph with ports (process)
    for reaction in model.getListOfReactions():
        r_id = reaction.getId()
        if r_id in n2lo:
            (x, y), (w, h) = transform(n2lo[r_id], x_shift, y_shift, scale_factor)
            g = libsbgn.glyph(class_=GlyphClass.PROCESS, id=r_id)
            g.set_bbox(libsbgn.bbox(x, y, w, h))
            rev = reaction.getReversible()

            in_port = None
            for s_id in (species_ref.getSpecies() for species_ref in reaction.getListOfReactants()):
                edge_id = "-".join(sorted((s_id, r_id)))
                if edge_id in e2lo:
                    xy_list = e2lo[edge_id]
                    if not in_port:
                        port_x, port_y = shift(scale(xy_list[-2] if len(xy_list) > 2 else xy_list[-1], scale_factor),
                                               x_shift, y_shift)
                        in_port = libsbgn.port(x=port_x, y=port_y, id="%s__in" % r_id)
                        g.add_port(in_port)
                    sref_id = s_id
                    if isinstance(n2lo[s_id], dict):
                        for r_ids in n2lo[s_id].keys():
                            if r_id in r_ids:
                                sref_id = "%s_%s" % (s_id, '_'.join(r_ids))
                    a = libsbgn.arc(class_=ArcClass.PRODUCTION if rev else ArcClass.CONSUMPTION,
                                    target=sref_id if rev else in_port.get_id(),
                                    source=in_port.get_id() if rev else sref_id, id="a_%s_%s" % (s_id, r_id))
                    s_x, s_y = shift(scale(xy_list[0], scale_factor), x_shift, y_shift)
                    a.set_start(libsbgn.startType(x=in_port.get_x() if rev else s_x, y=in_port.get_y() if rev else s_y))
                    a.set_end(libsbgn.endType(x=s_x if rev else in_port.get_x(), y=s_y if rev else in_port.get_y()))
                    sbgn_map.add_arc(a)
            out_port = None
            for s_id in (species_ref.getSpecies() for species_ref in reaction.getListOfProducts()):
                edge_id = "-".join(sorted((s_id, r_id)))
                if edge_id in e2lo:
                    xy_list = e2lo[edge_id]
                    if not out_port:
                        port_x, port_y = shift(scale(xy_list[1] if len(xy_list) > 2 else xy_list[0], scale_factor),
                                               x_shift, y_shift)
                        out_port = libsbgn.port(x=port_x, y=port_y, id="%s__out" % r_id)
                        g.add_port(out_port)
                    sref_id = s_id
                    if isinstance(n2lo[s_id], dict):
                        for r_ids in n2lo[s_id].keys():
                            if r_id in r_ids:
                                sref_id = "%s_%s" % (s_id, '_'.join(r_ids))
                    a = libsbgn.arc(class_=ArcClass.PRODUCTION, target=sref_id, source=out_port.get_id(),
                                    id="a_%s_%s" % (r_id, s_id))
                    s_x, s_y = shift(scale(xy_list[-1], scale_factor), x_shift, y_shift)
                    a.set_end(libsbgn.startType(x=s_x, y=s_y))
                    a.set_start(libsbgn.endType(x=out_port.get_x(), y=out_port.get_y()))
                    sbgn_map.add_arc(a)
            sbgn_map.add_glyph(g)

    # write everything to a file
    sbgn.write_file(out_sbgn)
