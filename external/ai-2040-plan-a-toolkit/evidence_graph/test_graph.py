from evidence_graph.graph import *
def test_claim_support_counts_independent_groups():
    g=EvidenceGraph()
    g.add_node(Node("e1",NodeType.EVIDENCE,"a","source-a",3))
    g.add_node(Node("e2",NodeType.EVIDENCE,"b","source-b",3))
    g.add_node(Node("c",NodeType.CLAIM,"c",None,3))
    g.add_edge(Edge("e1","c","SUPPORTS")); g.add_edge(Edge("e2","c","SUPPORTS"))
    assert g.claim_support("c",3)["independent_groups"]==2
def test_cycle_is_rejected():
    g=EvidenceGraph()
    g.add_node(Node("a",NodeType.EVIDENCE,"a")); g.add_node(Node("b",NodeType.CLAIM,"b"))
    g.add_edge(Edge("a","b","SUPPORTS")); g.add_edge(Edge("b","a","DERIVED_FROM"))
    assert g.validate()["status"]=="FAIL"
def test_missing_claim_is_unknown():
    assert EvidenceGraph().claim_support("missing")["status"]=="UNKNOWN"
