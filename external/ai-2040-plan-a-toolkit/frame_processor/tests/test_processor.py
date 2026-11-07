
import struct
from frame_processor.processor import *

def eth(src,dst,et,payload):
    return bytes.fromhex(dst.replace(":",""))+bytes.fromhex(src.replace(":",""))+struct.pack("!H",et)+payload
def ipv4(src,dst,proto,payload):
    hdr=bytearray(20);hdr[0]=0x45;struct.pack_into("!H",hdr,2,20+len(payload));hdr[8]=64;hdr[9]=proto;hdr[12:16]=__import__("socket").inet_aton(src);hdr[16:20]=__import__("socket").inet_aton(dst)
    return bytes(hdr)+payload
def udp(sport,dport,payload):
    return struct.pack("!HHHH",sport,dport,8+len(payload),0)+payload
def tcp(sport,dport,payload=b""):
    h=bytearray(20);struct.pack_into("!HHII",h,0,sport,dport,1,1);h[12]=0x50;h[13]=0x18;return bytes(h)+payload

W=Whitelist("02:00:00:00:00:01","02:00:00:00:00:02","10.0.0.1","10.0.0.2")

def test_health_passes():
    f=eth(W.prover_mac,W.verifier_mac,ETH_IPV4,ipv4(W.prover_ip,W.verifier_ip,17,udp(9999,9999,W.health_prefix)))
    assert process_frame(f,W,"out").classification=="ALLOWED_HEALTH"

def test_bad_udp_is_finding():
    f=eth(W.prover_mac,W.verifier_mac,ETH_IPV4,ipv4(W.prover_ip,W.verifier_ip,17,udp(9999,9999,b"bad")))
    assert process_frame(f,W,"out").classification=="NON_COMPLIANT"

def test_inference_candidate():
    f=eth(W.prover_mac,W.verifier_mac,ETH_IPV4,ipv4(W.prover_ip,W.verifier_ip,6,tcp(8000,8000,b"GET /")))
    assert process_frame(f,W,"out").classification=="INFERENCE_CANDIDATE"

def test_unexpected_protocol_fails():
    f=eth(W.prover_mac,W.verifier_mac,ETH_IPV4,ipv4(W.prover_ip,W.verifier_ip,1,b"x"))
    assert process_frame(f,W,"out").classification=="NON_COMPLIANT"

def test_reassembly_detects_gap():
    r=TCPReassembler();flow=("a","b",8000,8000);r.add(flow,0,b"aa");r.add(flow,3,b"bb");assert r.reconstruct(flow)["status"]=="FAIL"
