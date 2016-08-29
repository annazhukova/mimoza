from collections import defaultdict
import logging

import geojson

from sbml_vis.graph.layout.predefined_layout import apply_node_coordinates
from sbml_vis.graph.color.color import color, color_edges
from sbml_vis.graph.cluster.factoring import factor_nodes, comp_to_meta_node, merge_ubs_for_similar_reactions
from sbml_vis.converter.tlp2geojson import e2feature, n2feature, UBIQUITOUS_MASK, LAYER, DEFAULT_MASK
from sbml_vis.graph.graph_properties import ID, COMPARTMENT_ID, \
    TYPE_COMPARTMENT, TYPE, TYPE_REACTION, STOICHIOMETRY, RELATED_COMPARTMENT_IDS, TYPE_SPECIES, ANCESTOR_ID, TRANSPORT, \
    CLONE_ID, WIDTH, HEIGHT, VIEW_LAYOUT, VIEW_SIZE, UBIQUITOUS, ALL_COMPARTMENTS, VIEW_META_GRAPH, NAME
from sbml_vis.graph.layout.generalized_layout import rotate_generalized_ns, align_generalized_ns
from sbml_vis.graph.layout.ubiquitous_layout import bend_ubiquitous_edges, bend_edges, layout_inner_elements, \
    get_comp_borders, layout, open_meta_ns, straighten_edges_inside_compartments

DIMENSION = 512
MAX_FEATURE_NUMBER = 30000
MAX_TOTAL_FEATURE_NUMBER = 50000

__author__ = 'anna'


def update_level2features(feature, c_id2level2features, z, c_id):
    if c_id not in c_id2level2features:
        c_id2level2features[c_id] = defaultdict(list)
    if not isinstance(feature, list):
        feature = [feature]
    for f in feature:
        c_id2level2features[c_id][z].append(f)


def export_edges(c_id2level2features, c_id2outs, c_id2gr_ids, meta_graph, processed, e2layout, id2mask=None):
    root = meta_graph.getRoot()
    # Let's call "our" compartment the one to which feature list
    # we are about to add the feature
    for e in meta_graph.getEdges():
        s, t = meta_graph.source(e), meta_graph.target(e)
        e_id = "-".join(sorted([root[ID][s], root[ID][t]]))
        if e_id in processed:
            continue
        processed.add(e_id)

        if not id2mask:
            mask = DEFAULT_MASK
        else:
            real_e = e
            while root.isMetaEdge(real_e):
                real_e = next((ee for ee in root[VIEW_META_GRAPH][real_e] if not root[UBIQUITOUS][ee]),
                              next(iter(root[VIEW_META_GRAPH][real_e])))
            e_reaction_id = root[ID][root.target(real_e)] if TYPE_REACTION == root[TYPE][root.target(real_e)] \
                else root[ID][root.source(real_e)]
            mask = id2mask[e_reaction_id] if e_reaction_id in id2mask else DEFAULT_MASK

        s_c_id, t_c_id = root[COMPARTMENT_ID][s], root[COMPARTMENT_ID][t]
        gr_id = c_id2gr_ids[root[COMPARTMENT_ID][e]] if root[COMPARTMENT_ID][e] else None
        if not gr_id:
            logging.error('Group id for the edge %s-%s should not be None' % (root[NAME][s], root[NAME][t]))
        s_gr_id, t_gr_id = (c_id2gr_ids[s_c_id] if s_c_id in c_id2gr_ids else None), \
                           (c_id2gr_ids[t_c_id] if t_c_id in c_id2gr_ids else None)

        t_type, s_type = root[TYPE][t], root[TYPE][s]

        # 1. if the edge is inside our compartment
        if s_gr_id == t_gr_id == gr_id:
            # 1.1. if it's a generalized edge
            if meta_graph.isMetaEdge(e):
                # 1.1.1. between an inner compartment and something
                if t_type == TYPE_COMPARTMENT or s_type == TYPE_COMPARTMENT:
                    # 1.1.1.a. between two inner compartments
                    if t_type == s_type:
                        f = e2feature(meta_graph, e, e_id, True, e2layout, mask=mask)
                        update_level2features(f, c_id2level2features, 0, gr_id)
                    else:
                        if t_type == TYPE_COMPARTMENT and t_gr_id == gr_id \
                                or s_type == TYPE_COMPARTMENT and s_gr_id == gr_id:
                            continue
                        f = e2feature(meta_graph, e, e_id, True, e2layout, mask=mask)
                        # 1.1.1.b. between an inner compartment and a generalized reaction/species
                        if meta_graph.isMetaNode(s) and meta_graph.isMetaNode(t):
                            z = 1
                        # 1.1.1.c. between an inner compartment and a reaction/species
                        # that was generalized on the previous zoom level
                        elif root[ANCESTOR_ID][s] or root[ANCESTOR_ID][t]:
                            z = 2
                        # 1.1.1.d. between an inner compartment and a non-generalizable reaction/species
                        else:
                            z = 0
                        update_level2features(f, c_id2level2features, z, gr_id)
                # 1.1.2. between a reaction and a species
                else:
                    # let's check that if one of the species/reaction pair is simple but generalizable,
                    # then the other one is also simple
                    # (if one is generalized and the other is not it's an intermediate state not to be exported)
                    if (root[ANCESTOR_ID][s] or root[ANCESTOR_ID][t]) and (
                                meta_graph.isMetaNode(s) or meta_graph.isMetaNode(t)):
                        continue
                    r = s if TYPE_REACTION == s_type else t
                    f = e2feature(meta_graph, e, e_id, root[TRANSPORT][r], e2layout, mask=mask)
                    all_f = e2feature(meta_graph, e, e_id, root[TRANSPORT][r], {}, mask=mask)
                    # 1.1.2.a. between a generalized reaction/species and some reaction/species
                    if meta_graph.isMetaNode(s) or meta_graph.isMetaNode(t):
                        z = 1
                    # 1.1.2.b. between a reaction/species that was generalized on the previous zoom level and something
                    elif root[ANCESTOR_ID][s] or root[ANCESTOR_ID][t]:
                        z = 2
                    # 1.1.2.c. between a non-generalizable reaction and a non-generalizable species
                    else:
                        z = 0
                    update_level2features(f, c_id2level2features, z, gr_id)
                    update_level2features(all_f, c_id2level2features, z, ALL_COMPARTMENTS)
            # 1.2. it's a simple edge
            else:
                r = s if TYPE_REACTION == s_type else t
                f = e2feature(meta_graph, e, e_id, root[TRANSPORT][r], e2layout, mask=mask)
                all_f = e2feature(meta_graph, e, e_id, root[TRANSPORT][r], {}, mask=mask)
                # 1.2.1. between a reaction/species that was generalized on the previous zoom level and something
                if root[ANCESTOR_ID][s] or root[ANCESTOR_ID][t]:
                    z = 2
                # 1.2.2. between a non-generalizable reaction and a non-generalizable species
                else:
                    z = 0
                update_level2features(f, c_id2level2features, z, gr_id)
                update_level2features(all_f, c_id2level2features, z, ALL_COMPARTMENTS)
        # 2. the edge is between two compartments that are not inside the same compartment
        # (if they are then we've already processed them during the step 1.1.1.a.)
        # => no our compartment would need it
        if TYPE_COMPARTMENT == s_type == t_type:
            continue
        comp_id = root[ID][s] if TYPE_COMPARTMENT == s_type else (root[ID][t] if TYPE_COMPARTMENT == t_type else None)
        # 3. between our closed compartment and something outside
        if comp_id:
            continue
        # 4. between some reaction and some species,
        # at least one of which is outside of our compartment
        else:
            # let's check that if one of the species/reaction pair is simple but generalizable,
            # then the other one is also simple
            # (if one is generalized and the other is not it's an intermediate state not to be exported)
            if (root[ANCESTOR_ID][s] or root[ANCESTOR_ID][t]) \
                    and (meta_graph.isMetaNode(s) or meta_graph.isMetaNode(t)):
                continue
            # the reaction
            r = s if TYPE_REACTION == s_type else t
            related_c_ids = set(root[RELATED_COMPARTMENT_IDS][r])
            if s_c_id != t_c_id:
                related_c_ids.add(root[COMPARTMENT_ID][r])
            # # only those (our) compartments for which this edge is not completely inside them will need it
            # related_c_ids = [c_id for c_id in related_c_ids
            #                  if not ((c_id == s_c_id or c_id in c_id2outs[s_c_id])
            #                          and (c_id == t_c_id or c_id in c_id2outs[t_c_id]))]

            related_c_ids = {c_id2gr_ids[c_id] for c_id in related_c_ids}
            # 4.1. it's a generalized edge
            if meta_graph.isMetaEdge(e):
                z = 1
            # 4.2. it's a simple edge but at least one of our reaction-species pair
            # was generalized on the previous zoom level
            elif root[ANCESTOR_ID][s] or root[ANCESTOR_ID][t]:
                z = 2
            # 4.3. it's a simple edge between a non-generalizable reaction and a non-generalizable species
            else:
                z = 0
            for gr_id in related_c_ids:
                f = e2feature(meta_graph, e, e_id, True, e2layout, mask=mask)
                update_level2features(f, c_id2level2features, z, gr_id)
            all_f = e2feature(meta_graph, e, e_id, True, {}, mask=mask)
            update_level2features(all_f, c_id2level2features, z, ALL_COMPARTMENTS)


def export_nodes(c_id2info, c_id2outs, c_id2gr_ids, c_id2level2features, meta_graph, processed, r2rs_ps, n2layout,
                 id2mask=None, onto=None):
    root = meta_graph.getRoot()

    get_id = lambda n: "%s_%s" % (root[ID][n], root[CLONE_ID][n])

    for n in meta_graph.getNodes():
        n_id = get_id(n)
        if n_id in processed:
            continue
        processed.add(n_id)

        mask = DEFAULT_MASK
        if id2mask:
            if root[ID][n] in id2mask:
                mask = id2mask[root[ID][n]]
            if root[UBIQUITOUS][n] and root[CLONE_ID][n]:
                clone_ids = root[CLONE_ID][n].split(",")
                if clone_ids:
                    mask = 0
                    for cl_id in clone_ids:
                        if cl_id in id2mask:
                            mask |= id2mask[cl_id]

        x, y = root[VIEW_LAYOUT][n].getX(), root[VIEW_LAYOUT][n].getY()
        w, h = root[VIEW_SIZE][n].getW(), root[VIEW_SIZE][n].getH()
        if root[UBIQUITOUS][n] and root[CLONE_ID][n]:
            clone_ids = root[CLONE_ID][n].split(",")
            if clone_ids:
                if not root[ID][n] in n2layout:
                    n2layout[root[ID][n]] = {}
                n2layout[root[ID][n]][tuple(clone_ids)] = [(x, y), (w, h)]
            else:
                n2layout[root[ID][n]] = [(x, y), (w, h)]
        else:
            n2layout[root[ID][n]] = [(x, y), (w, h)]

        n_type = root[TYPE][n]
        c_id = root[COMPARTMENT_ID][n]
        # 1. if it's a compartment
        if n_type == TYPE_COMPARTMENT:
            # 1.a. if it's not the most outside compartment,
            # then its parent needs its feature
            if c_id and c_id2gr_ids[c_id] != c_id2gr_ids[root[ID][n]]:
                f, _ = n2feature(meta_graph, n, n_id, c_id2info, r2rs_ps, False, mask=mask, onto=onto)
                update_level2features(f, c_id2level2features, 0, c_id2gr_ids[c_id])
            # add its background to its own collection
            c_id = root[ID][n]
            _, bg = n2feature(meta_graph, n, n_id, c_id2info, r2rs_ps, False, mask=mask, onto=onto)
            update_level2features(bg, c_id2level2features, 0, c_id2gr_ids[root[ID][n]])
            # If it's not the root compartment, add it to all compartments view
            # Get outside compartment from c_id2info: c_id -> (name, go, (level, out_c_id))
            if c_id2info[c_id][2][1]:
                _, all_bg = n2feature(meta_graph, n, n_id, c_id2info, r2rs_ps, False, mask=mask, onto=onto)
                update_level2features(all_bg, c_id2level2features, 0, ALL_COMPARTMENTS)
        # 2. it's a reaction or a species
        elif n_type in [TYPE_REACTION, TYPE_SPECIES]:
            gr_id = c_id2gr_ids[c_id]
            # only those (our) compartments for which this element is outside of them will need it
            related_c_ids = [comp_id for comp_id in root[RELATED_COMPARTMENT_IDS][n] if comp_id not in c_id2outs[c_id]]
            non_transport = False if TYPE_REACTION == n_type else \
                next((True for r in root.getInOutNodes(n) if TYPE_REACTION == root[TYPE][r]
                      and not root[TRANSPORT][r] and root[COMPARTMENT_ID][r] == c_id), False)
            transport = root[TRANSPORT][n] if TYPE_REACTION == n_type else \
                next((True for r in root.getInOutNodes(n) if TYPE_REACTION == root[TYPE][r] and root[TRANSPORT][r]),
                     False)

            z = 1 if meta_graph.isMetaNode(n) else (2 if root[ANCESTOR_ID][n] else 0)

            # add features to it's own compartment
            f, bg = n2feature(meta_graph, n, n_id, c_id2info, r2rs_ps, transport, mask=mask, onto=onto,
                              non_transport=non_transport)
            all_f, all_bg = n2feature(meta_graph, n, n_id, c_id2info, r2rs_ps, transport, mask=mask, onto=onto,
                                      non_transport=non_transport)

            update_level2features(f, c_id2level2features, z, gr_id)
            update_level2features(all_f, c_id2level2features, z, ALL_COMPARTMENTS)
            if meta_graph.isMetaNode(n):
                update_level2features(bg, c_id2level2features, 2, gr_id)
                update_level2features(all_bg, c_id2level2features, 2, ALL_COMPARTMENTS)
                # add features to the compartments for that it's outside
            for o_c_id in related_c_ids:
                if gr_id != c_id2gr_ids[o_c_id]:
                    f, bg = n2feature(meta_graph, n, n_id, c_id2info, r2rs_ps, True, mask=mask, onto=onto,
                                      non_transport=False)
                    update_level2features(f, c_id2level2features, z, c_id2gr_ids[o_c_id])
                    if meta_graph.isMetaNode(n):
                        update_level2features(bg, c_id2level2features, 2, c_id2gr_ids[o_c_id])


def export_elements(c_id2info, c_id2outs, c_id2gr_ids, c_id2level2features, meta_graph, processed, r2rs_ps, n2layout, e2layout,
                    id2mask=None, onto=None):
    export_edges(c_id2level2features, c_id2outs, c_id2gr_ids, meta_graph, processed, e2layout,
                 id2mask=id2mask)
    export_nodes(c_id2info, c_id2outs, c_id2gr_ids, c_id2level2features, meta_graph, processed, r2rs_ps, n2layout,
                 id2mask=id2mask, onto=onto)


def meta_graph2features(c_id2info, c_id2outs, c_id2gr_ids, meta_graph, r2rs_ps, n2xy=None, id2mask=None, onto=None):
    root = meta_graph.getRoot()

    c_id2level2features = {}
    processed = set()
    c_id2c_borders = {}
    n2layout, e2layout = {}, {}

    all_c_id2c_borders = {}
    while True:
        for c_id, sizes in c_id2c_borders.iteritems():
            layout_inner_elements(meta_graph, c_id, sizes)

        if n2xy:
            apply_node_coordinates(meta_graph, n2xy)

        bend_edges(meta_graph)
        straighten_edges_inside_compartments(meta_graph, all_c_id2c_borders)
        # bend_edges_around_compartments(meta_graph, (e for e in meta_graph.getEdges() if not get_e_id(e) in processed))
        # bend_species_edges(meta_graph)
        color_edges(meta_graph)
        export_elements(c_id2info, c_id2outs, c_id2gr_ids, c_id2level2features, meta_graph, processed, r2rs_ps, n2layout, e2layout,
                        id2mask=id2mask, onto=onto)

        metas = [n for n in meta_graph.getNodes() if meta_graph.isMetaNode(n) and TYPE_COMPARTMENT == root[TYPE][n]]
        if not metas:
            c_id2c_borders = {}
            metas = [n for n in meta_graph.getNodes() if meta_graph.isMetaNode(n)]
            if not metas:
                break
            align_generalized_ns(meta_graph)
            rotate_generalized_ns(meta_graph)
            bend_ubiquitous_edges(meta_graph, metas)
        else:
            c_id2c_borders = {root[ID][c]: get_comp_borders(c, root) for c in metas}
            all_c_id2c_borders.update(c_id2c_borders)
        open_meta_ns(meta_graph, metas)

    for c_id in c_id2info.iterkeys():
        (name, go, (l, out_c_id)) = c_id2info[c_id]
        comp_n = comp_to_meta_node(meta_graph, c_id, (go, name), out_c_id, False, n2xy)
        if not comp_n:
            continue
        bend_edges(meta_graph)
        color_edges(meta_graph)
        export_edges(c_id2level2features, c_id2outs, c_id2gr_ids, meta_graph, processed, e2layout, id2mask=id2mask)
        metas = factor_nodes(meta_graph)
        bend_ubiquitous_edges(meta_graph, metas)
        bend_edges(meta_graph)
        metas.append(comp_n)
        color_edges(meta_graph)
        export_edges(c_id2level2features, c_id2outs, c_id2gr_ids, meta_graph, processed, e2layout, id2mask=id2mask)
        open_meta_ns(meta_graph, metas)

    return c_id2level2features, (n2layout, e2layout)


def get_reaction2reactants_products(root):
    r2rs_ps = {}
    for r in (r for r in root.getNodes() if TYPE_REACTION == root[TYPE][r]):
        rs = [(root[STOICHIOMETRY][e], root.source(e)) for e in root.getInEdges(r)]
        ps = [(root[STOICHIOMETRY][e], root.target(e)) for e in root.getOutEdges(r)]
        r2rs_ps[r] = rs, ps
    return r2rs_ps


def calculate_related_compartments(root):
    for r in (r for r in root.getNodes() if TYPE_REACTION == root[TYPE][r]):
        root[RELATED_COMPARTMENT_IDS][r] = list(
            {root[COMPARTMENT_ID][n] for n in root.getInOutNodes(r)} - {root[COMPARTMENT_ID][r]})
    for s in (s for s in root.getNodes() if TYPE_SPECIES == root[TYPE][s]):
        result = set()
        for r in root.getInOutNodes(s):
            result |= set(root[RELATED_COMPARTMENT_IDS][r]) | {root[COMPARTMENT_ID][r]}
        root[RELATED_COMPARTMENT_IDS][s] = list(result - {root[COMPARTMENT_ID][s]})


def graph2geojson(c_id2info, c_id2outs, c_id2gr_id, graph, n2xy=None, colorer=color, id2mask=None, onto=None):
    root = graph.getRoot()

    logging.info('generalized species/reactions -> metanodes')
    merge_ubs_for_similar_reactions(root)

    r2rs_ps = get_reaction2reactants_products(root)

    meta_graph = graph.inducedSubGraph([n for n in graph.getNodes()])

    logging.info('compartments -> metanodes')
    process_compartments(c_id2info, meta_graph, n2xy)

    calculate_related_compartments(root)

    colorer(root)
    color_edges(root)

    logging.info('tlp nodes -> geojson features')
    c_id2level2features, (n2lo, e2lo) = meta_graph2features(c_id2info, c_id2outs, c_id2gr_id, meta_graph,
                                                            r2rs_ps, n2xy, id2mask=id2mask, onto=onto)

    geometry = geojson.Polygon([[0, DIMENSION], [0, 0], [DIMENSION, 0], [DIMENSION, DIMENSION]])

    hidden_c_ids, c_id_hidden_ubs = filter_features(c_id2level2features)
    rescale(c_id2level2features)
    get_l2fs = lambda l2fs: {lev: geojson.FeatureCollection(features, geometry=geometry) for (lev, features) in
                             l2fs.iteritems()}
    return {c_id: get_l2fs(l2fs) for (c_id, l2fs) in c_id2level2features.iteritems()}, (n2lo, e2lo), \
           hidden_c_ids, c_id_hidden_ubs


def filter_features(c_id2level2features):
    c_ids = c_id2level2features.keys()
    c_id_hidden_ubs, hidden_c_ids = set(), set()
    for c_id in c_ids:
        l2fs = c_id2level2features[c_id]
        total_f_number = 0
        levels = l2fs.keys()
        f_num = (len(l2fs[0]) if 0 in l2fs else 0) + (len(l2fs[2]) if 2 in l2fs else 0)
        if f_num > MAX_FEATURE_NUMBER:
            c_id_hidden_ubs.add(c_id)
            for l in levels:
                l2fs[l] = [f for f in l2fs[l] if 0 == (UBIQUITOUS_MASK & f.properties[LAYER])]
                total_f_number += len(l2fs[l])
        if total_f_number > MAX_TOTAL_FEATURE_NUMBER:
            c_id_hidden_ubs -= {c_id}
            hidden_c_ids.add(c_id)
            logging.info("deleting compartment %s view, as it's too big" % c_id)
            del c_id2level2features[c_id]
    return hidden_c_ids, c_id_hidden_ubs


def rescale(c_id2level2features):
    for c_id, lev2fs in c_id2level2features.iteritems():
        if ALL_COMPARTMENTS == c_id:
            continue
        fs = []
        if 1 in lev2fs:
            fs += lev2fs[1]
        if 0 in lev2fs:
            fs += lev2fs[0]
        min_x, min_y, max_x, max_y = None, None, None, None
        for f in fs:
            if type(f.geometry) == geojson.Point:
                [x, y] = f.geometry.coordinates
                w = f.properties[WIDTH]
                h = f.properties[HEIGHT]\
                    if HEIGHT in f.properties else f.properties[WIDTH]
                if min_x is None or min_x > x - w:
                    min_x = x - w
                if min_y is None or min_y > y - h:
                    min_y = y - h
                if max_x is None or max_x < x + w:
                    max_x = x + w
                if max_y is None or max_y < y + h:
                    max_y = y + h
        if min_x is None:
            continue

        scale_coefficient = float(DIMENSION / max(max_x - min_x, max_y - min_y))
        if scale_coefficient == 1.0:
            continue

        processed = set()
        for fs in lev2fs.itervalues():
            for f in fs:
                if f.id in processed:
                    continue
                else:
                    processed.add(f.id)
                if type(f.geometry) == geojson.Point:
                    f.geometry.coordinates[0] *= scale_coefficient
                    f.geometry.coordinates[1] *= scale_coefficient
                elif type(f.geometry) == geojson.MultiPoint:
                    for coord in f.geometry.coordinates:
                        coord[0] *= scale_coefficient
                        coord[1] *= scale_coefficient
                f.properties[WIDTH] *= scale_coefficient
                if HEIGHT in f.properties:
                    f.properties[HEIGHT] *= scale_coefficient


def process_compartments(c_id2info, meta_graph, n2xy=None):
    # root = meta_graph.getRoot()
    factor_nodes(meta_graph)

    current_zoom_level = max({info[2][0] for info in c_id2info.itervalues()})
    while current_zoom_level >= 0:
        for c_id in c_id2info.iterkeys():
            (name, go, (l, out_c_id)) = c_id2info[c_id]
            if current_zoom_level == l:
                # ns = [n for n in meta_graph.getNodes() if root[COMPARTMENT_ID][n] == c_id]
                # factor_nodes(meta_graph, ns)
                comp_to_meta_node(meta_graph, c_id, (go, name), out_c_id, True, n2xy)
        current_zoom_level -= 1
        if n2xy:
            apply_node_coordinates(meta_graph, n2xy)
        else:
            layout(meta_graph)