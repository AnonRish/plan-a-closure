from __future__ import annotations
from dataclasses import dataclass
import math
from collections import defaultdict

@dataclass(frozen=True)
class LeakageReport:
    samples:int
    bins:int
    mutual_information_bits:float
    notes:str

def estimate_binary_mutual_information(signal:list[float],secret:list[int],bins:int=16)->LeakageReport:
    if len(signal)!=len(secret) or not signal:raise ValueError("signal and secret must be same non-empty length")
    if bins<2:raise ValueError("bins must be >=2")
    lo,hi=min(signal),max(signal)
    if hi==lo:return LeakageReport(len(signal),bins,0.0,"constant signal")
    width=(hi-lo)/bins
    table=defaultdict(lambda:[0,0])
    for x,s in zip(signal,secret):
        idx=min(bins-1,int((x-lo)/width))
        table[idx][1 if int(s) else 0]+=1
    n=len(signal)
    py=[sum(row[j] for row in table.values())/n for j in (0,1)]
    mi=0.0
    for row in table.values():
        row_total=sum(row)
        for j,count in enumerate(row):
            if not count:continue
            pxy=count/n; px=row_total/n
            mi+=pxy*math.log2(pxy/(px*py[j]))
    return LeakageReport(n,bins,max(0.0,mi),"Empirical binned mutual information; not a capacity upper bound")
