from collections import defaultdict

from sbml_vis.graph.layout.predefined_layout import apply_node_coordinates
from sbml_vis.graph.node_cloner import merge_nodes
from sbml_vis.graph.resize import get_n_size
from sbml_vis.graph.graph_properties import *
from sbml_vis.graph.layout.ubiquitous_layout import layout


__author__ = 'anna'


def merge_ubs_for_similar_reactions(graph):
    root = graph.getRoot()

    ancestor2nodes = defaultdict(list)
    for node in graph.getNodes():
        ancestor = root[ANCESTOR_ID][node]
        if ancestor and TYPE_REACTION == root[TYPE][node]:
            ancestor = ancestor, root[COMPARTMENT_ID][node]
            ancestor2nodes[ancestor].append(node)

    ubiquitous = root[UBIQUITOUS]
    for nodes in (nodes for nodes in ancestor2nodes.itervalues() if len(nodes) > 1):
        id2ub_ns = defaultdict(set)
        for node in nodes:
            for n in (n for n in graph.getInOutNodes(node) if ubiquitous[n]):
                id2ub_ns[root[ID][n]].add(n)
        for ubs in id2ub_ns.itervalues():
            merge_nodes(root, ubs)


def factor_nodes(graph, ns=None):
    root = graph.getRoot()
    if not ns:
        ns = graph.getNodes()

    ancestor2nodes = defaultdict(list)
    for node in ns:
        ancestor = root[ANCESTOR_ID][node]
        if ancestor:
            ancestor = ancestor, root[TYPE][node], root[COMPARTMENT_ID][node]
            ancestor2nodes[ancestor].append(node)

    meta_ns = []
    for (ancestor, type_, c_id), nodes in ((k, ns) for (k, ns) in ancestor2nodes.iteritems() if len(ns) > 1):
        sample_n = nodes[0]
        meta_n = graph.createMetaNode(nodes, False)

        for prop in [COMPARTMENT_ID, TYPE, REVERSIBLE, UBIQUITOUS, VIEW_SHAPE, RELATED_COMPARTMENT_IDS]:
            root[prop][meta_n] = root[prop][sample_n]
        root[ID][meta_n] = root[ANCESTOR_ID][sample_n]
        root[VIEW_SIZE][meta_n] = get_n_size(root, meta_n)
        root[NAME][meta_n] = root[ANCESTOR_NAME][sample_n]

        if TYPE_REACTION == type_:
            root[REVERSIBLE][meta_n] = False
            root[TRANSPORT][meta_n] = False
            for sample_n in nodes:
                if root[REVERSIBLE][sample_n]:
                    root[REVERSIBLE][meta_n] = True
                if root[TRANSPORT][sample_n]:
                    root[TRANSPORT][meta_n] = True
            root[TERM][meta_n] = "\nor\n".join({root[TERM][it] for it in nodes})
            for ub in root.getInOutNodes(meta_n):
                if root[UBIQUITOUS][ub]:
                    clone_ids = set(root[CLONE_ID][ub].split(',')) if root[CLONE_ID][ub] else set()
                    clone_ids.add(root[ID][meta_n])
                    root[CLONE_ID][ub] = ','.join(sorted(clone_ids))
        else:
            root[TERM][meta_n] = root[ANCESTOR_TERM][sample_n]

        for meta_e in root.getInOutEdges(meta_n):
            sample_e = next(iter(root[VIEW_META_GRAPH][meta_e]))
            root[UBIQUITOUS][meta_e] = root[UBIQUITOUS][sample_e]
            root[STOICHIOMETRY][meta_e] = root[STOICHIOMETRY][sample_e]
            root[COMPARTMENT_ID][meta_e] = root[COMPARTMENT_ID][sample_e]
            # todo: this is not True but will help with cycle detection
            root[REVERSIBLE][meta_e] = not root[UBIQUITOUS][meta_e]

        meta_ns.append(meta_n)
    return meta_ns


def comp_to_meta_node(meta_graph, c_id, (go_id, c_name), out_comp, do_layout=True, n2xy=None):
    root = meta_graph.getRoot()
    ns = [n for n in meta_graph.getNodes() if root[COMPARTMENT_ID][n] == c_id]
    if not ns:
        return None
    comp_n = meta_graph.createMetaNode(ns, False)
    comp_graph = root[VIEW_META_GRAPH][comp_n]
    if do_layout:
        if n2xy:
            apply_node_coordinates(comp_graph, n2xy)
        else:
            layout(comp_graph)
    root[NAME][comp_n] = c_name
    root[COMPARTMENT_ID][comp_n] = out_comp
    root[TYPE][comp_n] = TYPE_COMPARTMENT
    root[VIEW_SHAPE][comp_n] = COMPARTMENT_SHAPE
    root[ID][comp_n] = c_id
    root[TERM][comp_n] = go_id
    root[VIEW_SIZE][comp_n] = get_n_size(meta_graph, comp_n)
    for meta_e in root.getInOutEdges(comp_n):
        sample_e = next((ee for ee in root[VIEW_META_GRAPH][meta_e] if not root[UBIQUITOUS][ee]),
                        next(iter(root[VIEW_META_GRAPH][meta_e])))
        root[UBIQUITOUS][meta_e] = root[UBIQUITOUS][sample_e]
        root[STOICHIOMETRY][meta_e] = sum(root[STOICHIOMETRY][ee] for ee in root[VIEW_META_GRAPH][meta_e])
        root[COMPARTMENT_ID][meta_e] = root[COMPARTMENT_ID][sample_e]
        # todo: this is not True but will help with cycle detection
        root[REVERSIBLE][meta_e] = root[REVERSIBLE][sample_e] and not root[UBIQUITOUS][sample_e]
    return comp_n
