def recursive_get_edge_support_graphs(
    edge: str,
    edges: set,
    auxgraphs: set,
    message_edges: dict,
    message_auxgraphs: dict,
    nodes: set,
):
    """Recursive method to find auxiliary graphs to keep when filtering. Each auxiliary
    graph then has its edges filterd."""
    edges.add(edge)
    nodes.add(message_edges[edge]["subject"])
    nodes.add(message_edges[edge]["object"])
    for attribute in message_edges.get(edge, {}).get("attributes", {}):
        if attribute.get("attribute_type_id", None) == "biolink:support_graphs":
            for auxgraph in attribute.get("value", []):
                if auxgraph not in message_auxgraphs:
                    raise KeyError(f"auxgraph {auxgraph} not in auxiliary_graphs")
                try:
                    edges, auxgraphs, nodes = recursive_get_auxgraph_edges(
                        auxgraph,
                        edges,
                        auxgraphs,
                        message_edges,
                        message_auxgraphs,
                        nodes,
                    )
                except KeyError as e:
                    raise e
    return edges, auxgraphs, nodes


def recursive_get_auxgraph_edges(
    auxgraph: str,
    edges: set,
    auxgraphs: set,
    message_edges: dict,
    message_auxgraphs: dict,
    nodes: set,
):
    """Recursive method to find edges to keep when filtering. Each edge then
    has support graphs filtered."""
    auxgraphs.add(auxgraph)
    aux_edges = message_auxgraphs.get(auxgraph, {}).get("edges", [])
    for aux_edge in aux_edges:
        if aux_edge not in message_edges:
            raise KeyError(f"aux_edge {aux_edge} not in knowledge_graph.edges")
        try:
            edges, auxgraphs, nodes = recursive_get_edge_support_graphs(
                aux_edge, edges, auxgraphs, message_edges, message_auxgraphs, nodes
            )
        except KeyError as e:
            raise e
    return edges, auxgraphs, nodes
