from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib, json

class NodeType(Enum):
    OBSERVATION="OBSERVATION"
    EVIDENCE="EVIDENCE"
    CLAIM="CLAIM"
    PROCEDURE="PROCEDURE"
    RESULT="RESULT"
    ATTESTATION="ATTESTATION"

@dataclass(frozen=True)
class Node:
    node_id:str
    node_type:NodeType
    digest:str
    independence_group:str|None=None
    evidence_level:int=1

@dataclass(frozen=True)
class Edge:
    src:str
    dst:str
    relation:str

@dataclass
class EvidenceGraph:
    nodes:dict[str,Node]=field(default_factory=dict)
    edges:list[Edge]=field(default_factory=list)
    def add_node(self,node:Node):
        if node.node_id in self.nodes: raise ValueError("duplicate node")
        self.nodes[node.node_id]=node
    def add_edge(self,edge:Edge):
        if edge.src not in self.nodes or edge.dst not in self.nodes: raise ValueError("edge references unknown node")
        self.edges.append(edge)
    def root_digest(self)->str:
        payload={
            "nodes":[{"node_id":n.node_id,"node_type":n.node_type.value,"digest":n.digest,"independence_group":n.independence_group,"evidence_level":n.evidence_level} for n in (self.nodes[k] for k in sorted(self.nodes))],
            "edges":[e.__dict__ for e in sorted(self.edges,key=lambda x:(x.src,x.dst,x.relation))]
        }
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def validate(self)->dict:
        errors=[]
        if any(e.src==e.dst for e in self.edges): errors.append("self-loop")
        causal={"DERIVED_FROM","SUPPORTS","VERIFIED_BY","PRODUCES"}
        adj={k:[] for k in self.nodes}
        for e in self.edges:
            if e.relation in causal: adj[e.src].append(e.dst)
        visiting=set(); visited=set()
        def dfs(u):
            if u in visiting:return True
            if u in visited:return False
            visiting.add(u)
            for v in adj[u]:
                if dfs(v):return True
            visiting.remove(u);visited.add(u);return False
        if any(dfs(k) for k in self.nodes if k not in visited): errors.append("causal cycle")
        return {"status":"PASS" if not errors else "FAIL","errors":errors,"root_digest":self.root_digest()}
    def claim_support(self,claim_id:str,minimum_level:int=1)->dict:
        if claim_id not in self.nodes:return {"status":"UNKNOWN","reason":"claim not found"}
        supporting=[self.nodes[e.src] for e in self.edges if e.dst==claim_id and e.relation=="SUPPORTS" and e.src in self.nodes]
        eligible=[n for n in supporting if n.evidence_level>=minimum_level]
        groups={n.independence_group or n.node_id for n in eligible}
        return {"status":"PASS" if eligible else "UNKNOWN","supporting_nodes":[n.node_id for n in eligible],"independent_groups":len(groups),"root_digest":self.root_digest()}
