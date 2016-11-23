from tulip import tlp

from tarjan import tarjan_iter

from sbml_vis.graph.resize import get_mn_size, SPECIES_SIZE
from sbml_vis.graph.graph_properties import *

COMPONENT_PACKING = "Connected Component Packing"

FM3 = "FM^3 (OGDF)"

CIRCULAR = "Circular (OGDF)"

HIERARCHICAL_GRAPH = "Sugiyama (OGDF)"  # "Hierarchical Graph"

OVERLAP_REMOVAL = "Fast Overlap Removal"


def get_distance(qo):
    root = qo.getRoot()
    n2size = {n: max(root[VIEW_SIZE][n].getW(), root[VIEW_SIZE][n].getH()) for n in qo.getNodes()}

    def get_neighbour_size(n):
        neighbour_sizes = {n2size[m] for m in qo.getOutNodes(n) if m in n2size}
        return max(neighbour_sizes) if neighbour_sizes else 0

    return max(n2size[n] + get_neighbour_size(n) for n in n2size.keys()) / 2


def layout_hierarchically(qo, margin=1):
    root = qo.getRoot()
    ds = tlp.getDefaultPluginParameters(HIERARCHICAL_GRAPH, qo)
    if qo.numberOfNodes() > 1:
        # looks like there is a bug in Tulip and it uses the 'layer spacing' value
        # instead of the 'node spacing' one and visa versa
        d = SPECIES_SIZE + margin #get_distance(qo)
        ds["layer spacing"] = d
        ds["node spacing"] = d
        ds["layer distance"] = d
        ds["node distance"] = d
    qo.applyLayoutAlgorithm(HIERARCHICAL_GRAPH, root[VIEW_LAYOUT], ds)


def layout_circle(qo, margin=1):
    root = qo.getRoot()
    ds = tlp.getDefaultPluginParameters(CIRCULAR, qo)
    if qo.numberOfNodes() > 1:
        dist = get_distance(qo) + margin
        ds["minDistCircle"] = dist
        ds["minDistLevel"] = dist
        ds["minDistCC"] = 1
        ds["minDistSibling"] = dist
    qo.applyLayoutAlgorithm(CIRCULAR, root[VIEW_LAYOUT], ds)


def layout_force(qo, margin=1):
    root = qo.getRoot()
    ds = tlp.getDefaultPluginParameters(FM3, qo)
    ds["Unit edge length"] = 2 * SPECIES_SIZE + margin
    qo.applyLayoutAlgorithm(FM3, root[VIEW_LAYOUT], ds)

    remove_overlaps(qo, margin)


def pack_cc(graph):
    root = graph.getRoot()
    ds = tlp.getDefaultPluginParameters(COMPONENT_PACKING, graph)
    graph.applyLayoutAlgorithm(COMPONENT_PACKING, root[VIEW_LAYOUT], ds)


def remove_overlaps(graph, margin=1):
    root = graph.getRoot()
    ds = tlp.getDefaultPluginParameters(OVERLAP_REMOVAL, graph)
    ds["x border"] = margin
    ds["y border"] = margin
    graph.applyLayoutAlgorithm(OVERLAP_REMOVAL, root[VIEW_LAYOUT], ds)


def layout_components(graph, cycle_number_threshold=40, node_number_threshold=300, margin=5):
    root = graph.getRoot()
    comp_list = tlp.ConnectedTest.computeConnectedComponents(graph)
    followers_rev_or_gen = lambda n, gr: (gr.opposite(e, n) for e in gr.getInOutEdges(n) if n == gr.source(e)
                                          or gr[REVERSIBLE][e] or gr.isMetaNode(n) and gr.isMetaNode(gr.opposite(e, n)))
    followers_rev = lambda n, gr: (gr.opposite(e, n) for e in gr.getInOutEdges(n) if n == gr.source(e)
                                   or gr[REVERSIBLE][e])
    followers_irrev = lambda n, gr: gr.getOutNodes(n)
    followers_irrev_gen_only = lambda n, gr: (m for m in gr.getOutNodes(n) if gr.isMetaNode(m))

    def process_cc(gr, ns, meta_ns, follower_method_iterator):
        try:
            follower_method = next(follower_method_iterator)
        except StopIteration:
            if len(ns) < node_number_threshold:
                mn = gr.createMetaNode(ns, False)
                cc_graph = root[VIEW_META_GRAPH][mn]
                layout_hierarchically(cc_graph)
                meta_ns.append(mn)
            return
        # iterate over strongly connected components
        for cc in tarjan_iter({n: list(follower_method(n, gr)) for n in ns}):
            if len(cc) > 3:
                if dfs(cc[0], gr, set(), None, cycle_number_threshold, follower_method) \
                        <= cycle_number_threshold:
                    mn = gr.createMetaNode(cc, False)
                    cc_graph = root[VIEW_META_GRAPH][mn]
                    layout_circle(cc_graph, margin)
                    meta_ns.append(mn)
                else:
                    process_cc(gr, cc, meta_ns, follower_method_iterator)

    for ns in comp_list:
        gr = graph.inducedSubGraph(ns)
        meta_ns = []
        process_cc(gr, (n for n in gr.getNodes() if gr[TYPE][n] != TYPE_COMPARTMENT), meta_ns,
                   iter((followers_rev_or_gen, followers_rev, followers_irrev, followers_irrev_gen_only)))
        for mn in meta_ns:
            root[VIEW_SHAPE][mn] = COMPARTMENT_SHAPE
            w, h = get_mn_size(mn, root)
            root[VIEW_SIZE][mn] = tlp.Size(w, h)
        if gr.numberOfNodes() < node_number_threshold and \
                not next((n for n in gr.getNodes() if root[TYPE][n] == TYPE_COMPARTMENT), False):
            layout_hierarchically(gr)
        else:
            layout_force(gr, margin)
        for mn in meta_ns:
            gr.openMetaNode(mn)


# deep-first search
# every cycle will be counted twice
# as every node of a cycle can be approached from two sides
def dfs(n, graph, visited, prev, limit, followers):
    if n in visited:
        return 1
    num = 0
    visited.add(n)
    for m in followers(n, graph):
        if m == prev:
            continue
        else:
            num += dfs(m, graph, visited, n, limit, followers)
            if num > limit:
                return num
    return num
