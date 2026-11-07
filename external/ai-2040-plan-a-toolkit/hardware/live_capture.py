
from __future__ import annotations
import platform,socket,time,struct
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class CaptureStats:
    frames:int
    bytes:int
    duration_seconds:float

def capture_linux_interface(interface:str,duration_seconds:float,max_frames:int=100000,pcap_path:str="capture.pcap")->CaptureStats:
    if platform.system()!="Linux": raise RuntimeError("live AF_PACKET capture requires Linux")
    if duration_seconds<=0 or max_frames<=0: raise ValueError("duration and max_frames must be positive")
    sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.ntohs(3))
    sock.bind((interface,0)); sock.settimeout(.25)
    start=time.time(); frames=[]; total=0
    while len(frames)<max_frames and time.time()-start<duration_seconds:
        try: data,addr=sock.recvfrom(65535)
        except socket.timeout: continue
        frames.append((time.time_ns(),data)); total+=len(data)
    sock.close()
    _write_pcap(Path(pcap_path),frames)
    return CaptureStats(len(frames),total,time.time()-start)

def _write_pcap(path:Path,frames:list[tuple[int,bytes]]):
    with path.open("wb") as f:
        f.write(struct.pack("<IHHIIII",0xa1b2c3d4,2,4,0,0,65535,1))
        for ts,frame in frames:
            sec,nsec=divmod(ts,1_000_000_000); usec=nsec//1000
            f.write(struct.pack("<IIII",sec,usec,len(frame),len(frame))); f.write(frame)
