
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib, ipaddress, socket, struct, time
from typing import Iterable

ETH_IPV4=0x0800
ETH_ARP=0x0806
PROTO_TCP=6
PROTO_UDP=17

def digest_frame(frame:bytes)->str:
    return hashlib.sha256(frame).hexdigest()

@dataclass(frozen=True)
class FrameEvent:
    timestamp_ns:int
    direction:str
    classification:str
    reason:str
    frame_digest:str
    payload_len:int

@dataclass(frozen=True)
class Whitelist:
    prover_mac:str
    verifier_mac:str
    prover_ip:str
    verifier_ip:str
    health_port:int=9999
    inference_port:int=8000
    health_prefix:bytes=b"LVHEM-TAPPED-LINK-HEALTH/1 REQ\n"

@dataclass
class TCPReassembler:
    flows:dict[tuple,dict[int,bytes]]=field(default_factory=dict)
    def add(self,flow:tuple,sequence:int,payload:bytes):
        self.flows.setdefault(flow,{})[sequence]=payload
    def reconstruct(self,flow:tuple):
        chunks=self.flows.get(flow,{})
        if not chunks:return {"status":"UNKNOWN","data":b"","missing":True}
        seqs=sorted(chunks)
        cursor=seqs[0]; out=[]
        for seq in seqs:
            if seq!=cursor:return {"status":"FAIL","data":b"".join(out),"missing":True}
            out.append(chunks[seq]); cursor+=len(chunks[seq])
        return {"status":"PASS","data":b"".join(out),"missing":False}

def _mac(raw:bytes)->str:
    return ":".join(f"{x:02x}" for x in raw)

def _parse_ipv4(data:bytes):
    if len(data)<20:return None
    vihl=data[0]; version=vihl>>4; ihl=(vihl&15)*4
    if version!=4 or ihl<20 or len(data)<ihl:return None
    total=struct.unpack("!H",data[2:4])[0]
    proto=data[9]
    src=socket.inet_ntoa(data[12:16]); dst=socket.inet_ntoa(data[16:20])
    return {"ihl":ihl,"total":total,"proto":proto,"src":src,"dst":dst,"payload":data[ihl:total]}

def parse_ethernet(frame:bytes):
    if len(frame)<14: raise ValueError("truncated ethernet frame")
    dst,src=frame[:6],frame[6:12]; et=struct.unpack("!H",frame[12:14])[0]; off=14
    while et in (0x8100,0x88a8,0x9100):
        if len(frame)<off+4: raise ValueError("truncated vlan header")
        et=struct.unpack("!H",frame[off+2:off+4])[0]; off+=4
    return _mac(dst),_mac(src),et,frame[off:]

def process_frame(frame:bytes,whitelist:Whitelist,direction:str,timestamp_ns:int|None=None)->FrameEvent:
    ts=time.time_ns() if timestamp_ns is None else timestamp_ns
    digest=digest_frame(frame)
    try:
        dst,src,et,payload=parse_ethernet(frame)
    except ValueError as e:
        return FrameEvent(ts,direction,"NON_COMPLIANT",str(e),digest,len(frame))
    expected_pair={(whitelist.prover_mac.lower(),whitelist.verifier_mac.lower()),(whitelist.verifier_mac.lower(),whitelist.prover_mac.lower())}
    if (src.lower(),dst.lower()) not in expected_pair:
        return FrameEvent(ts,direction,"NON_COMPLIANT","unexpected MAC pair",digest,len(frame))
    if et==ETH_ARP:
        return FrameEvent(ts,direction,"ALLOWED_ARP","whitelisted ARP",digest,len(payload))
    if et!=ETH_IPV4:
        return FrameEvent(ts,direction,"NON_COMPLIANT","disallowed ethertype",digest,len(payload))
    ip=_parse_ipv4(payload)
    if ip is None:
        return FrameEvent(ts,direction,"NON_COMPLIANT","malformed IPv4",digest,len(payload))
    if {ip["src"],ip["dst"]}!={whitelist.prover_ip,whitelist.verifier_ip}:
        return FrameEvent(ts,direction,"NON_COMPLIANT","unexpected IP endpoints",digest,len(payload))
    if ip["proto"] not in (PROTO_TCP,PROTO_UDP):
        return FrameEvent(ts,direction,"NON_COMPLIANT","disallowed IP protocol",digest,len(payload))
    transport=ip["payload"]
    if ip["proto"]==PROTO_UDP:
        if len(transport)<8:return FrameEvent(ts,direction,"NON_COMPLIANT","truncated UDP",digest,len(transport))
        sport,dport,length=struct.unpack("!HHH",transport[:6]); body=transport[8:length]
        if sport==whitelist.health_port or dport==whitelist.health_port:
            if body!=whitelist.health_prefix:
                return FrameEvent(ts,direction,"NON_COMPLIANT","invalid health-check payload",digest,len(body))
            return FrameEvent(ts,direction,"ALLOWED_HEALTH","valid health check",digest,len(body))
        return FrameEvent(ts,direction,"NON_COMPLIANT","non-whitelisted UDP port",digest,len(body))
    if len(transport)<20:return FrameEvent(ts,direction,"NON_COMPLIANT","truncated TCP",digest,len(transport))
    sport,dport=struct.unpack("!HH",transport[:4]); data_offset=(transport[12]>>4)*4
    if len(transport)<data_offset:return FrameEvent(ts,direction,"NON_COMPLIANT","invalid TCP header",digest,len(transport))
    if whitelist.inference_port not in (sport,dport):
        return FrameEvent(ts,direction,"NON_COMPLIANT","non-whitelisted TCP port",digest,len(transport)-data_offset)
    return FrameEvent(ts,direction,"INFERENCE_CANDIDATE","HTTP inference port",digest,len(transport)-data_offset)

def process_frames(frames:Iterable[tuple[int,bytes]],whitelist:Whitelist)->list[FrameEvent]:
    return [process_frame(f,whitelist,"unknown",ts) for ts,f in frames]

class PcapReader:
    def __init__(self,path:str):
        self.path=path
    def frames(self):
        with open(self.path,"rb") as fh:
            gh=fh.read(24)
            if len(gh)!=24:raise ValueError("short pcap header")
            magic=gh[:4]
            if magic==b"\xd4\xc3\xb2\xa1": endian="<"
            elif magic==b"\xa1\xb2\xc3\xd4": endian=">"
            else: raise ValueError("unsupported pcap magic")
            _,_,_,_,_,_,linktype=struct.unpack(endian+"IHHIIII",gh)
            if linktype!=1:raise ValueError("only Ethernet pcap is supported")
            while True:
                ph=fh.read(16)
                if not ph:break
                if len(ph)!=16:raise ValueError("truncated packet header")
                sec,usec,incl,_=struct.unpack(endian+"IIII",ph)
                frame=fh.read(incl)
                if len(frame)!=incl:raise ValueError("truncated packet")
                yield sec*1_000_000_000+usec*1000,frame

def process_pcap(path:str,whitelist:Whitelist)->dict:
    events=list(process_frames(PcapReader(path).frames(),whitelist))
    counts={}
    for e in events:counts[e.classification]=counts.get(e.classification,0)+1
    return {"frames":len(events),"counts":counts,"findings":[e.__dict__ for e in events if e.classification=="NON_COMPLIANT"]}
