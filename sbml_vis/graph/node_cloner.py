from sbml_vis.graph.graph_properties import CLONE_ID, ID

__author__ = 'anna'


def clone_node(graph, n, get_neighbour_nodes=lambda m, gr: gr.getInOutNodes(m)):
    root = graph.getRoot()

    graphs_to_update = get_graphs_by_node(n, root)

    # used_n = False
    for r in get_neighbour_nodes(n, root):
        clone_id = root[ID][r]
        # if not used_n:
        #     root[CLONE_ID][n] = clone_id
        #     used_n = True
        #     continue
        # duplicate node
        dup = root.addNode()
        for prop_name in root.getProperties():
            root[prop_name][dup] = root[prop_name][n]
        root[CLONE_ID][dup] = clone_id

        for graph in (graph for graph in graphs_to_update if graph.isElement(r)):
            if not graph.isElement(dup):
                graph.addNode(dup)
            e = graph.existEdge(r, n, False)
            if graph.isElement(e):
                graph.setTarget(e, dup) if n == graph.target(e) else graph.setSource(e, dup)
    for graph in graphs_to_update:
        if graph.deg(n) == 0:
            graph.delNode(n, True)


def get_graphs_by_node(n, root):
    if not root.isElement(n):
        return []
    graphs_to_update = [root]
    for gr in root.getSubGraphs():
        graphs_to_update = get_graphs_by_node(n, gr) + graphs_to_update
    return graphs_to_update


def merge_nodes(graph, ns):
    if len(ns) <= 1:
        return
    root = graph.getRoot()

    n = ns.pop()
    for m in ns:
        for e in root.getInEdges(m):
            root.setTarget(e, n)
        for e in root.getOutEdges(m):
            root.setSource(e, n)
        if root[CLONE_ID][m]:
            clone_ids = set(root[CLONE_ID][n].split(',')) if root[CLONE_ID][n] else set()
            clone_ids |= set(root[CLONE_ID][m].split(',')) if root[CLONE_ID][m] else set()
            root[CLONE_ID][n] = ','.join(sorted(clone_ids))
        root.delNode(m, True)
