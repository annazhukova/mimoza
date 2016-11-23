from math import degrees, cos, sin
from sympy import to_cnf, atan2
from sympy.logic.boolalg import disjuncts, conjuncts
import math

import geojson
from jinja2 import Environment, PackageLoader

from sbml_vis.graph.rename import get_short_name, convert_formula_to_html
from sbml_vis.graph.color.colorer import get_edge_color, get_reaction_color, get_compartment_color, get_species_color, \
    get_bg_color
from sbml_vis.graph.graph_properties import TYPE_SPECIES, TYPE_COMPARTMENT, TYPE_REACTION, VIEW_SIZE, VIEW_LAYOUT, TYPE, \
    VIEW_META_GRAPH, UBIQUITOUS, VIEW_COLOR, TYPE_EDGE, STOICHIOMETRY, WIDTH, COLOR, COMPARTMENT_ID, REVERSIBLE, TERM, \
    FORMULA, HEIGHT, T, COMPARTMENT_NAME, TYPE_2_BG_TYPE, ID, TYPE_BG_COMPARTMENT, NAME, \
    ANCESTOR_NAME, LABEL
from sbml_vis.graph.resize import get_e_size

__author__ = 'anna'

_NUMERALS = '0123456789abcdefABCDEF'
_HEXDEC = {v: int(v, 16) for v in (x + y for x in _NUMERALS for y in _NUMERALS)}
LOWERCASE, UPPERCASE = 'x', 'X'

LAYER = 'layer'
TRANSPORT_MASK = 1
NON_TRANSPORT_MASK = 1 << 1
UBIQUITOUS_MASK = 1 << 2
DEFAULT_LAYER = 'default'
DEFAULT_MASK = 1 << 3

DEFAULT_LAYER2MASK = {DEFAULT_LAYER: DEFAULT_MASK}


BETA_UP = 15 * math.pi / 16
BETA_DOWN = 17 * math.pi / 16


def get_border_coord(xy, other_xy, wh, n_type):
    (x, y) = xy
    (other_x, other_y) = other_xy
    (w, h) = wh
    if n_type == TYPE_REACTION:
        edge_angle = degrees(atan2(other_y - y, other_x - x)) if other_y != y or other_x != x else 0
        diag_angle = degrees(atan2(h, w))
        abs_edge_angle = abs(edge_angle)
        if diag_angle < abs_edge_angle < 180 - diag_angle:
            y += h if edge_angle > 0 else -h
        else:
            x += w if abs_edge_angle <= 90 else -w
        return x, y
    elif n_type == TYPE_COMPARTMENT:
        c_bottom_x, c_bottom_y, c_top_x, c_top_y = x - w, y - h, x + w, y + h
        inside_y = c_bottom_y <= other_y <= c_top_y
        inside_x = c_bottom_x <= other_x <= c_top_x

        if inside_x:
            return other_x, (c_bottom_y if abs(other_y - c_bottom_y) < abs(other_y - c_top_y) else c_top_y)
        elif inside_y:
            return (c_bottom_x if abs(other_x - c_bottom_x) < abs(other_x - c_top_x) else c_top_x), other_y
        else:
            return max(c_bottom_x, min(other_x, c_top_x)), max(c_bottom_y, min(other_y, c_top_y))
    else:
        diag = pow(pow(x - other_x, 2) + pow(y - other_y, 2), 0.5)
        transformation = lambda z, other_z: (w * (((other_z - z) / diag) if diag else 1)) + z
        return transformation(x, other_x), transformation(y, other_y)


def e2feature(graph, e, e_id, transport, e2layout, mask=DEFAULT_LAYER2MASK[DEFAULT_LAYER]):
    root = graph.getRoot()
    layout = root[VIEW_LAYOUT]
    s, t = graph.source(e), graph.target(e)

    xy = lambda n: (layout[n].getX(), layout[n].getY())
    wh = lambda n: (root[VIEW_SIZE][n].getW() / 2, root[VIEW_SIZE][n].getH() / 2)
    e_lo = layout[e]
    while e_lo and xy(s) == [e_lo[0][0], e_lo[0][1]]:
        e_lo = e_lo[1:]
    while e_lo and xy(t) == [e_lo[-1][0], e_lo[-1][1]]:
        e_lo = e_lo[:-1]
    s_x, s_y = get_border_coord(xy(s), (e_lo[0][0], e_lo[0][1]) if e_lo else xy(t), wh(s), root[TYPE][s])
    t_x, t_y = get_border_coord(xy(t), (e_lo[-1][0], e_lo[-1][1]) if e_lo else xy(s), wh(t),
                                root[TYPE][t])
    while e_lo and [s_x, s_y] == [e_lo[0][0], e_lo[0][1]]:
        e_lo = e_lo[1:]
    while e_lo and [t_x, t_y] == [e_lo[-1][0], e_lo[-1][1]]:
        e_lo = e_lo[:-1]

    e2layout[e_id] = [[s_x, s_y]] + [[it[0], it[1]] for it in e_lo] + [[t_x, t_y]]
    geom = geojson.MultiPoint(e2layout[e_id])
    generalized = graph.isMetaNode(s) or graph.isMetaNode(t)

    real_e = e
    while root.isMetaEdge(real_e):
        real_e = next((ee for ee in root[VIEW_META_GRAPH][real_e] if not root[UBIQUITOUS][ee]),
                      next(iter(root[VIEW_META_GRAPH][real_e])))
    ubiquitous = root[UBIQUITOUS][real_e]
    color = triplet(root[VIEW_COLOR][real_e])
    props = {WIDTH: get_e_size(root, e).getW(), TYPE: TYPE_EDGE, STOICHIOMETRY: graph[STOICHIOMETRY][e],
             COLOR: get_edge_color(ubiquitous, generalized, transport, color), LAYER: mask}
    if not transport:
        props[COMPARTMENT_ID] = root[COMPARTMENT_ID][s]
    else:
        props[LAYER] |= TRANSPORT_MASK
    if ubiquitous:
        props[LAYER] |= UBIQUITOUS_MASK
    features = [geojson.Feature(id=e_id, geometry=geom, properties=props)]

    # Draw an arrow if it's a edge between a reaction and a product or between a reversible reaction and a reactant
    t_reaction = root.target(real_e) if TYPE_REACTION == root[TYPE][root.target(real_e)] else None
    s_reaction = root.source(real_e) if TYPE_REACTION == root[TYPE][root.source(real_e)] else None
    p_x, p_y = None, None
    st_x, st_y = None, None
    if t_reaction and root[REVERSIBLE][t_reaction]:
        p_x, p_y = s_x, s_y
        st_x, st_y = (e_lo[0][0], e_lo[0][1]) if e_lo else (t_x, t_y)
    elif s_reaction:
        p_x, p_y = t_x, t_y
        st_x, st_y = (e_lo[-1][0], e_lo[-1][1]) if e_lo else (s_x, s_y)
    if p_x is not None and p_y is not None:
        alpha = atan2(p_y - st_y, p_x - st_x)
        if not math.isnan(alpha):
            l = .4
            # point (l, 0)
            # rotate alpha +- beta
            # move p_x, p_y
            up_x_y = [p_x + l * cos(alpha + BETA_UP), p_y + l * sin(alpha + BETA_UP)]
            down_x_y = [p_x + l * cos(alpha + BETA_DOWN), p_y + l * sin(alpha + BETA_DOWN)]
            arrow_up = geojson.Feature(id=e_id + "_up",
                                         geometry=geojson.MultiPoint([[p_x, p_y], up_x_y]),
                                         properties=props.copy())
            arrow_down = geojson.Feature(id=e_id + "_down",
                                         geometry=geojson.MultiPoint([[p_x, p_y], down_x_y]),
                                         properties=props.copy())
            features.append(arrow_down)
            features.append(arrow_up)
    return features


def n2feature(graph, n, n_id, c_id2info, r2rs_ps, transport, mask=DEFAULT_LAYER, onto=None, non_transport=False):
    root = graph.getRoot()

    x, y = root[VIEW_LAYOUT][n].getX(), root[VIEW_LAYOUT][n].getY()
    geom = geojson.Point([x, y])
    c_id = root[COMPARTMENT_ID][n]
    w, h = root[VIEW_SIZE][n].getW() / 2, root[VIEW_SIZE][n].getH() / 2
    node_type = root[TYPE][n]
    generalized = graph.isMetaNode(n)
    props = {WIDTH: w, TYPE: node_type, COMPARTMENT_ID: c_id, ID: root[ID][n],
             NAME: root[NAME][n], LAYER: mask}
    color = triplet(root[VIEW_COLOR][n])
    if TYPE_REACTION == node_type:
        # ins, outs = get_formula(graph, n, r2rs_ps)
        formula = get_formula(graph, n, r2rs_ps, root[REVERSIBLE][n])
        genes = get_gene_association_list(root[TERM][n])
        if not next((m for m in root.getInOutNodes(n) if TYPE_SPECIES == root[TYPE][m] and not root[UBIQUITOUS][m]), False):
            props[LAYER] |= UBIQUITOUS_MASK
        if genes:
            props[TERM] = genes
        # if ins:
        # props[REACTANTS] = ins
        # if outs:
        # props[PRODUCTS] = outs
        if formula:
            props[FORMULA] = formula
        props[COLOR] = get_reaction_color(generalized, transport, color)
        if transport:
            del props[COMPARTMENT_ID]
            props[LAYER] |= TRANSPORT_MASK
    elif TYPE_COMPARTMENT == node_type:
        term = root[TERM][n]
        if term:
            term = term.upper()
            props[T] = term
            props[TERM] = "<a href=\'http://www.ebi.ac.uk/QuickGO/GTerm?id=%s\' target=\'_blank\'>%s</a>" % (term, term)

        props.update({HEIGHT: h, COLOR: get_compartment_color(color)})
    elif TYPE_SPECIES == node_type:
        if root[FORMULA][n]:
            props[FORMULA] = convert_formula_to_html(root[FORMULA][n])
        props[LABEL] = get_short_name(graph, n, onto)
        ubiquitous = root[UBIQUITOUS][n]
        if ubiquitous:
            props[LAYER] |= UBIQUITOUS_MASK
        if transport:
            props[LAYER] |= TRANSPORT_MASK
            if non_transport:
                props[LAYER] |= NON_TRANSPORT_MASK

        # Get compartment name from c_id2info: c_id -> (name, go, (level, out_c_id))
        comp_name = c_id2info[c_id][0]
        term = root[TERM][n]
        if term:
            term = term.upper()
            if term.find("UNKNOWN") == -1:
                props[T] = term
                props[
                    TERM] = "<a href=\'http://www.ebi.ac.uk/chebi/searchId.do?chebiId=%s\' target=\'_blank\'>%s</a>" % (
                    term, term)
        props.update({COMPARTMENT_NAME: comp_name, COLOR: get_species_color(ubiquitous, generalized, color)})

    bg_feature = None
    # if generalized:
    if generalized:
        node_type = TYPE_2_BG_TYPE[node_type]
        bg_props = {ID: root[ID][n], WIDTH: w, TYPE: node_type, COLOR: get_bg_color(node_type, transport, color),
                    LAYER: props[LAYER]}
        if LABEL in props:
            bg_props[LABEL] = props[LABEL]
        if COMPARTMENT_ID in props:
            bg_props[COMPARTMENT_ID] = root[COMPARTMENT_ID][n]
        if TYPE_BG_COMPARTMENT == node_type:
            bg_props[HEIGHT] = h
            bg_props[COMPARTMENT_ID] = root[ID][n]
            bg_props[NAME] = root[NAME][n]
        bg_feature = geojson.Feature(id="%s_bg" % n_id, geometry=geom, properties=bg_props)
    return geojson.Feature(id=n_id, geometry=geojson.Point([x, y]), properties=props), bg_feature


def get_gene_association_list(ga):
    gene_association = ga.replace('and', '&').replace('or', '|').replace('OR', '|')
    if not gene_association:
        return ""
    try:
        res = to_cnf(gene_association, False)
        gene_association = [[str(it) for it in disjuncts(cjs)] for cjs in conjuncts(res)]
        result = '''<table class="p_table" border="0" width="100%%">
						<tr class="centre"><th colspan="%d" class="centre">Gene association</th></tr>
						<tr>''' % (2 * len(gene_association) - 1)
        first = True
        for genes in gene_association:
            if first:
                first = False
            else:
                result += '<td class="centre"><i>and</i></td>'
            result += '<td><table border="0">'
            if len(genes) > 1:
                result += "<tr><td class='centre'><i>(or)</i></td></tr>"
            for gene in genes:
                result += "<tr><td class='main'><a href=\'http://www.ncbi.nlm.nih.gov/gene/?term=%s[sym]\' target=\'_blank\'>%s</a></td></tr>" % (
                    gene, gene)
            result += '</table></td>'
        result += '</tr></table>'
        return result
    except:
        return ""


def get_reaction_participants_inside_compartment(n, r, root):
    if TYPE_COMPARTMENT == root[TYPE][n]:
        result = set()
        for m in root[VIEW_META_GRAPH][n].getNodes():
            result |= get_reaction_participants_inside_compartment(m, r, root)
        return result
    elif not root.isMetaNode(n) or root.isMetaNode(r):
        return {n}
    else:
        return {s for s in root[VIEW_META_GRAPH][n].getNodes()}


def get_formula(graph, r, r2rs_ps, reversible):
    root = graph.getRoot()
    name_prop = NAME
    format_st = lambda st: "" if st == 1 else ("%g" % st)
    formatter = lambda st, n, prop: [root[prop if root[prop][n] else NAME][n], format_st(float(st))]
    if graph.isMetaNode(r):
        r = root[VIEW_META_GRAPH][r].getOneNode()
        name_prop = ANCESTOR_NAME
    rs, ps = r2rs_ps[r]
    rs, ps = sorted(formatter(it[0], it[1], name_prop) for it in rs), \
             sorted(formatter(it[0], it[1], name_prop) for it in ps)

    env = Environment(loader=PackageLoader('sbml_vis.html', 'templates'))
    template = env.get_template('formula.html')
    return template.render(rs=rs, ps=ps, reversible=reversible)


def rgb(rrggbb):
    return _HEXDEC[rrggbb[0:2]], _HEXDEC[rrggbb[2:4]], _HEXDEC[rrggbb[4:6]]


def triplet(c, lettercase=LOWERCASE):
    return '#' + format((c.getR() << 16 | c.getG() << 8 | c.getB()), '06' + lettercase)
