from tulip import tlp
from mod_sbml.annotation.chebi.chebi_annotator import CONJUGATE_ACID_BASE_RELATIONSHIPS
from sbml_vis.graph.color.color_keys import key2coord
from sbml_vis.graph.graph_properties import *


# def getKey2Layout(graph):
#   root = graph.getRoot()
# 	view_layout = root.getLayoutProperty("viewLayout")
# 	ubiquitous = root.getBooleanProperty("ubiquitous")
#
# 	key2l = {}
# 	for n in graph.getNodes():
# 		if ubiquitous[n]:
# 			r = graph.getInOutNodes(n).next()
# 			k = get_keys(n, graph, True)[0]
# 			keys = ["{0}+{1}".format(k,l) for l in getKeys(r, graph, True)]
# 		else:
# 			keys = get_keys(n, graph, True)
# 		for k in keys:
# 			key2l[k] = view_layout[n]
#
# 	print key2l


def apply_layout(graph, onto):
    root = graph.getRoot()
    view_layout = root.getLayoutProperty(VIEW_LAYOUT)
    ubiquitous = root.getBooleanProperty(UBIQUITOUS)

    # before = len(key2coord)
    for n in graph.getNodes():
        if ubiquitous[n]:
            continue
        # if not graph.deg(n):
        # 	continue
        # r = graph.getInOutNodes(n).next()
        # k = get_keys(n, graph, onto, True)[0]
        # keys = ["{0}+{1}".format(k, l) for l in get_keys(r, graph, onto, True)]
        else:
            keys = get_keys(n, graph, onto, True)
        if not keys:
            continue
        coord = next((key2coord[key] for key in keys if key in key2coord), None)
        if coord:
            view_layout[n] = tlp.Coord(coord[0], coord[1])
        else:
            for key in keys:
                key2coord[key] = view_layout[n]
            #if before < len(key2coord) : print key2coord


def get_keys(n, graph, onto, primary=False):
    root = graph.getRoot()
    ancestor_chebi_id = root.getStringProperty(ANCESTOR_TERM)
    chebi_id = root.getStringProperty(TERM)
    name = root.getStringProperty(NAME)
    ubiquitous = root.getBooleanProperty(UBIQUITOUS)

    if TYPE_REACTION == graph[TYPE][n]:
        transform = lambda nds: "r_" + "_".join(sorted([get_keys(it, graph, onto, primary)[0] for it in nds]))
        return [transform(graph.getInOutNodes(n)),
                transform(filter(lambda nd: not ubiquitous[nd], graph.getInOutNodes(n)))]
    else:
        key = None
        if not primary:
            key = ancestor_chebi_id[n]
        if not key:
            key = chebi_id[n]
        if not key:
            return [name[n]]
        t = onto.get_term(key)
        if t:
            key = get_primary_id(t, onto)
        return [key]


def get_primary_id(term, onto):
    terms = {term} | onto.get_equivalents(term, None, 0, CONJUGATE_ACID_BASE_RELATIONSHIPS)
    return sorted([t.get_id() for t in terms])[0]


def apply_node_coordinates(graph, n2xy):
    root = graph.getRoot()
    for n in graph.getNodes():
        n_id = root[ID][n]
        if n_id in n2xy:
            xywh = n2xy[n_id]
            if isinstance(xywh, dict):
                for r_id, ((x, y), (w, h)) in xywh.iteritems():
                    if root[CLONE_ID][n].find(r_id) != -1:
                        root[VIEW_LAYOUT][n] = tlp.Coord(x, y)
                        root[VIEW_SIZE][n] = tlp.Size(w, h)
                        break
            else:
                (x, y), (w, h) = xywh
                root[VIEW_LAYOUT][n] = tlp.Coord(x, y)
                root[VIEW_SIZE][n] = tlp.Size(w, h)
        elif graph.isMetaNode(n):
            x, y = 0, 0
            w, h = 0, 0
            count = 0
            for m in root[VIEW_META_GRAPH][n].getNodes():
                if root[ID][m] in n2xy:
                    xywh_ = n2xy[root[ID][m]]
                    if isinstance(xywh_, dict):
                        for r_id, ((x_, y_), (w_, h_)) in xywh_.iteritems():
                            if root[CLONE_ID][m].find(r_id) != -1:
                                x += x_
                                y += y_
                                w += w_
                                h += h_
                                count += 1
                                break
                    else:
                        (x_, y_), (w_, h_) = xywh_
                        count += 1
                        x += x_
                        y += y_
                        w += w_
                        h += h_
            if count:
                root[VIEW_LAYOUT][n] = tlp.Coord(x / count, y / count)
                root[VIEW_SIZE][n] = tlp.Size(w, h)
    root[VIEW_LAYOUT].setAllEdgeValue([])
