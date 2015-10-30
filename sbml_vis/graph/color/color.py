import colorsys

from tulip import tlp
from sbml_vis.graph.graph_properties import *


__author__ = 'anna'

GRAY = tlp.Color(180, 180, 180)  # B4B4B4
TRANSPARENT_GRAY = tlp.Color(200, 200, 200, 80)
LIGHT_RED = tlp.Color(255, 100, 100)
LIGHT_BLUE = tlp.Color(100, 100, 255)
WHITE = tlp.Color(255, 255, 255)
TRANSPARENT = tlp.Color(0, 0, 0, 0)

ORANGE = tlp.Color(253, 180, 98)  # FDB462
YELLOW = tlp.Color(255, 255, 179)  # FFFFB3
RED = tlp.Color(251, 128, 114)  # FB8072
BLUE = tlp.Color(128, 177, 211)  # 80B1D3
GREEN = tlp.Color(179, 222, 105)  # B3DE69
VIOLET = tlp.Color(190, 186, 218)  # BEBADA
TURQUOISE = tlp.Color(141, 211, 199)  # 8DD3C7

RED_RGB = 251, 128, 114
BLUE_RGB = 128, 177, 211
GRAY_RGB = 180, 180, 180

NOT_GENERALIZED = 'ng'


def get_key(n, graph):
    root = graph.getRoot()
    type_ = root[TYPE][n]
    if TYPE_REACTION == type_:
        an_id = root[ANCESTOR_ID][n]
        if an_id:
            return an_id
        elif root.isMetaNode(n):
            return root[ID][n]
        return NOT_GENERALIZED, TYPE_REACTION
    # return root[ID][n]
    if TYPE_SPECIES == type_:
        an_ch = root[ANCESTOR_TERM][n]
        if an_ch:
            return an_ch
        an_id = root[ANCESTOR_ID][n]
        if an_id:
            return an_id
        elif root.isMetaNode(n):
            ch = root[TERM][n]
            if ch:
                return ch
            return root[ID][n]
        return NOT_GENERALIZED, TYPE_SPECIES
    # ch = root[TERM][n]
    # if ch:
    # return ch
    # return root[ID][n]
    return None


def color(graph):
    root = graph.getRoot()
    view_color = root.getColorProperty(VIEW_COLOR)

    s_keys = {get_key(n, graph) for n in graph.getNodes() if root[TYPE][n] == TYPE_REACTION}
    s_keys -= {(NOT_GENERALIZED, TYPE_SPECIES)}
    i = len(s_keys)
    colors = get_n_colors(i, 0.5, 0.8)
    key2color = dict(zip(s_keys, colors))

    r_keys = {get_key(n, graph) for n in graph.getNodes() if root[TYPE][n] == TYPE_SPECIES}
    r_keys -= {(NOT_GENERALIZED, TYPE_REACTION)}
    i = len(r_keys)
    colors = get_n_colors(i, 0.5, 0.8)
    key2color.update(dict(zip(r_keys, colors)))

    key2color[(NOT_GENERALIZED, TYPE_SPECIES)] = RED_RGB
    key2color[(NOT_GENERALIZED, TYPE_REACTION)] = BLUE_RGB

    # root = graph.getRoot()
    # organelles = root.getAttribute(ORGANELLES).split(";")
    # cyto = root.getAttribute(CYTOPLASM)
    # i = len(organelles) + 2
    # colors = get_n_colors(i, 0.5, 0.8)
    # key2comp_color = dict(zip(organelles + [cyto], colors[1:]))

    c_keys = {root[ID][n] for n in graph.getNodes() if root[TYPE][n] == TYPE_COMPARTMENT}
    i = len(c_keys)
    colors = get_n_colors(i, 0.5, 0.8)
    key2color.update(dict(zip(c_keys, colors)))

    for n in graph.getNodes():
        type_ = root[TYPE][n]

        if TYPE_COMPARTMENT == type_:
            r, g, b = key2color[root[ID][n]]
            view_color[n] = tlp.Color(r, g, b)
            continue
        a = 255
        if TYPE_REACTION == type_:
            r, g, b = key2color[get_key(n, graph)]
            if graph.isMetaNode(n):
                a = 100
            view_color[n] = tlp.Color(r, g, b, a)
        elif TYPE_SPECIES == type_:
            if root[UBIQUITOUS][n]:
                r, g, b = 180, 180, 180
            else:
                r, g, b = key2color[get_key(n, graph)]
                if graph.isMetaNode(n):
                    a = 100
            view_color[n] = tlp.Color(r, g, b, a)


def get_n_colors(n, s, v):
    return [(int(255 * r), int(255 * g), int(255 * b)) for (r, g, b) in
            (colorsys.hsv_to_rgb(x * 1.0 / n, s, v) for x in xrange(n))]


def color_by_compartment(graph, c_id2m_ids):
    root = graph.getRoot()
    view_color = root.getColorProperty(VIEW_COLOR)

    i = len(c_id2m_ids.keys()) + 1

    colors = get_n_colors(i, 0.7, 0.8)
    ub_colors = get_n_colors(i, 0.2, 0.8)

    key2color = dict(zip(c_id2m_ids.iterkeys(), colors[1:]))
    key2ub_color = dict(zip(c_id2m_ids.iterkeys(), ub_colors[1:]))

    m_id2color = {}
    m_id2ub_color = {}
    for c_id, m_ids in c_id2m_ids.iteritems():
        for m_id in m_ids:
            m_id2color[m_id] = key2color[c_id]
            m_id2ub_color[m_id] = key2ub_color[c_id]

    for n in graph.getNodes():
        view_color[n] = WHITE

    for n in (n for n in graph.getNodes() if not graph.isMetaNode(n) and root[TYPE][n] == TYPE_SPECIES):
        r, g, b = m_id2color[root[ID][n]] if root[ID][n] in m_id2color else (255, 255, 255)
        for r_n in graph.getInOutNodes(n):
            type_ = root[TYPE][r_n]
            if TYPE_REACTION == type_ and view_color[r_n] == WHITE:
                view_color[r_n] = tlp.Color(r, g, b)
        if root[UBIQUITOUS][n]:
            r, g, b = m_id2ub_color[root[ID][n]] if root[ID][n] in m_id2ub_color else (255, 255, 255)
        view_color[n] = tlp.Color(r, g, b)

    for n in (n for n in graph.getNodes() if graph.isMetaNode(n)):
        type_ = root[TYPE][n]

        if TYPE_COMPARTMENT == type_:
            # view_color[n] = key2comp_color[root[NAME][n]] if root[NAME][n] in key2comp_color else TRANSPARENT_GRAY
            continue
        view_color[n] = view_color[next(root[VIEW_META_GRAPH][n].getNodes())]


def color_by_pathway(graph, pw2r_ids):
    root = graph.getRoot()
    view_color = root.getColorProperty(VIEW_COLOR)

    i = len(pw2r_ids.keys()) + 1

    colors = get_n_colors(i, 0.5, 0.8)

    key2color = dict(zip(pw2r_ids.iterkeys(), colors[1:]))

    r_id2color = {}
    for pw, r_ids in pw2r_ids.iteritems():
        for r_id in r_ids:
            r_id2color[r_id] = key2color[pw]

    for n in graph.getNodes():
        view_color[n] = WHITE

    for n in (n for n in graph.getNodes() if not graph.isMetaNode(n) and root[TYPE][n] == TYPE_REACTION):
        r, g, b = r_id2color[root[ID][n]] if root[ID][n] in r_id2color else (255, 255, 255)
        view_color[n] = tlp.Color(r, g, b)

        for m in graph.getInOutNodes(n):
            type_ = root[TYPE][m]
            if TYPE_SPECIES == type_ and view_color[m] == WHITE:
                if root[UBIQUITOUS][n]:
                    r_, g_, b_ = 180, 180, 180
                else:
                    r_, g_, b_ = r, g, b
                view_color[m] = tlp.Color(r_, g_, b_)

    for n in (n for n in graph.getNodes() if graph.isMetaNode(n)):
        type_ = root[TYPE][n]

        if TYPE_COMPARTMENT == type_:
            # view_color[n] = key2comp_color[root[NAME][n]] if root[NAME][n] in key2comp_color else TRANSPARENT_GRAY
            continue
        view_color[n] = view_color[next(root[VIEW_META_GRAPH][n].getNodes())]


def color_by_id(graph, id2color):
    root = graph.getRoot()
    view_color = root.getColorProperty(VIEW_COLOR)

    c_keys = {root[ID][n] for n in graph.getNodes() if root[TYPE][n] == TYPE_COMPARTMENT}
    i = len(c_keys)
    colors = get_n_colors(i, 0.7, 0.7)
    key2color = dict(zip(c_keys, colors))

    for n in (n for n in graph.getNodes() if not graph.isMetaNode(n) and root[TYPE][n] == TYPE_REACTION):
        r, g, b = id2color[root[ID][n]] if root[ID][n] in id2color else BLUE_RGB
        view_color[n] = tlp.Color(r, g, b)

        for m in graph.getInOutNodes(n):
            type_ = root[TYPE][m]
            if TYPE_SPECIES == type_:
                view_color[m] = GRAY if root[UBIQUITOUS][n] else view_color[n]

        for e in graph.getInOutEdges(n):
            view_color[e] = GRAY if root[UBIQUITOUS][root.target(e)] or root[UBIQUITOUS][root.source(e)] else view_color[n]

    for n in (n for n in graph.getNodes() if not graph.isMetaNode(n) and root[TYPE][n] == TYPE_SPECIES):
        if root[UBIQUITOUS][n]:
            r, g, b = GRAY_RGB
        elif root[ID][n] not in id2color:
            r, g, b = RED_RGB
        else:
            r, g, b = id2color[root[ID][n]]
        view_color[n] = tlp.Color(r, g, b)

    for n in (n for n in graph.getNodes() if graph.isMetaNode(n)):
        type_ = root[TYPE][n]

        if TYPE_COMPARTMENT == type_:
            r, g, b = key2color[root[ID][n]]
            view_color[n] = tlp.Color(r, g, b)
        else:
            view_color[n] = view_color[next(root[VIEW_META_GRAPH][n].getNodes())]


def color_edges(graph):
    root = graph.getRoot()
    view_color = root.getColorProperty(VIEW_COLOR)
    for e in graph.getEdges():
        real_e = e
        while root.isMetaEdge(real_e):
            real_e = next((ee for ee in root[VIEW_META_GRAPH][real_e] if not root[UBIQUITOUS][ee]),
                          next(iter(root[VIEW_META_GRAPH][real_e])))
        t = root.target(real_e)
        s = root.source(real_e)
        if root[UBIQUITOUS][real_e] or root[UBIQUITOUS][t] or root[UBIQUITOUS][s]:
            view_color[e] = GRAY
        else:
            view_color[e] = view_color[s if TYPE_REACTION == root[TYPE][s] else t]


def simple_color(graph):
    root = graph.getRoot()
    view_color = root.getColorProperty(VIEW_COLOR)

    for n in root.getNodes():
        type_ = root[TYPE][n]
        if TYPE_COMPARTMENT == type_:
            view_color[n] = YELLOW
        elif TYPE_REACTION == type_:
            is_transport = root[TRANSPORT][n]
            if root.isMetaNode(n):
                view_color[n] = TURQUOISE if is_transport else VIOLET
            else:
                view_color[n] = GREEN if is_transport else BLUE
            for e in root.getInOutEdges(n):
                if root[UBIQUITOUS][root.target(e)] or root[UBIQUITOUS][root.source(e)]:
                    view_color[e] = GRAY
                else:
                    view_color[e] = view_color[n]
        elif TYPE_SPECIES == type_:
            if root[UBIQUITOUS][n]:
                view_color[n] = GRAY
            else:
                if root.isMetaNode(n):
                    view_color[n] = ORANGE
                else:
                    view_color[n] = RED

