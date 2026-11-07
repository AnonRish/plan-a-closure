from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json,struct,time
from pathlib import Path
from frame_processor.processor import Whitelist,process_pcap

@dataclass(frozen=True)
class BenchmarkConfig:
    frame_count:int=5000
    payload_bytes:int=256
    attack_fraction:float=0.05
    drop_every:int=0
    seed:int=20260928
@dataclass(frozen=True)
class PacketCase:
    frame:bytes
    digest:str
    compliant:bool

def _eth(src,dst,ethertype,payload): return dst+src+struct.pack('!H',ethertype)+payload
def _ipv4(src,dst,proto,payload):
    h=bytearray(20); h[0]=0x45; struct.pack_into('!H',h,2,20+len(payload)); h[8]=64; h[9]=proto; h[12:16]=src; h[16:20]=dst; return bytes(h)+payload
def _tcp(sport,dport,payload):
    h=bytearray(20); struct.pack_into('!HHII',h,0,sport,dport,1,1); h[12]=0x50; h[13]=0x18; return bytes(h)+payload
def _pcap_global(): return struct.pack('<IHHIIII',0xA1B2C3D4,2,4,0,0,65535,1)
def _pcap_record(ts_ns,frame):
    sec,ns=divmod(ts_ns,1_000_000_000); return struct.pack('<IIII',sec,ns//1000,len(frame),len(frame))+frame

def build_fixture(config):
    if config.frame_count<=0 or config.payload_bytes<0 or not 0<=config.attack_fraction<=1: raise ValueError('invalid benchmark dimensions')
    w=Whitelist('02:00:00:00:00:01','02:00:00:00:00:02','10.0.0.1','10.0.0.2')
    src=bytes.fromhex(w.prover_mac.replace(':','')); dst=bytes.fromhex(w.verifier_mac.replace(':',''))
    ips=bytes(map(int,w.prover_ip.split('.'))); ipd=bytes(map(int,w.verifier_ip.split('.'))); out=[]
    for i in range(config.frame_count):
        attack=(hashlib.sha256(f'{config.seed}:{i}'.encode()).digest()[0]/255.0)<config.attack_fraction
        body=bytes((i+j)%256 for j in range(config.payload_bytes)); port=9000 if attack else w.inference_port
        frame=_eth(src,dst,0x0800,_ipv4(ips,ipd,6,_tcp(port,port,body)))
        out.append(PacketCase(frame,hashlib.sha256(frame).hexdigest(),not attack))
    return w,out

def write_pcap(path,cases,drop_every=0):
    if drop_every<0: raise ValueError('drop_every must be >= 0')
    written=dropped=0
    with open(path,'wb') as fh:
        fh.write(_pcap_global())
        for i,case in enumerate(cases):
            if drop_every and (i+1)%drop_every==0: dropped+=1; continue
            fh.write(_pcap_record(1_000_000_000+i*1000,case.frame)); written+=1
    return {'expected_frames':len(cases),'written_frames':written,'dropped_frames':dropped}

def line_rate_projection(frame_bytes,line_rate_gbps):
    if frame_bytes<=0 or line_rate_gbps<=0: raise ValueError('positive parameters required')
    wire_bytes=frame_bytes+20
    return {'frame_bytes':frame_bytes,'line_rate_gbps':line_rate_gbps,'wire_bytes_per_frame_assumption':wire_bytes,'theoretical_frames_per_second':(line_rate_gbps*1_000_000_000)/(wire_bytes*8),'measured':False}

def run(config=BenchmarkConfig(),output_dir='.'):
    w,cases=build_fixture(config); outdir=Path(output_dir); outdir.mkdir(parents=True,exist_ok=True); pcap=outdir/'capture_fixture.pcap'; info=write_pcap(str(pcap),cases,config.drop_every)
    start=time.perf_counter(); processed=process_pcap(str(pcap),w); elapsed=time.perf_counter()-start; total_expected=len(cases); observed=processed['frames']
    return {'schema_version':1,'benchmark':'software_capture_replay','config':asdict(config),'pcap':str(pcap),'expected_frames':total_expected,'observed_frames':observed,'observed_noncompliant':len(processed['findings']),'processing_seconds':elapsed,'frames_per_second':observed/elapsed if elapsed else 0.0,'expected_dropped_frames':total_expected-info['written_frames'],'observed_drop_rate':(total_expected-observed)/total_expected,'line_rate_projections':[line_rate_projection(64,x) for x in (100,400,800,1600)],'hardware_observation':False,'write_info':info}

def write_result(path,result): Path(path).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    result=run(); write_result('capture_benchmark_result.json',result); print(json.dumps(result,indent=2))
