from dataclasses import dataclass
SPEED_OF_LIGHT_M_PER_S=299792458.0
@dataclass(frozen=True)
class PingObservation:
    rtt_seconds:float
    calibrated_processing_seconds:float
    verifier_site_id:str
    endpoint_id:str
def upper_distance_m(o):
    network=o.rtt_seconds-o.calibrated_processing_seconds
    if network<0: raise ValueError("processing exceeds RTT")
    return SPEED_OF_LIGHT_M_PER_S*network/2
def evaluate_location(o,max_distance_m):
    if o.rtt_seconds<=0 or o.calibrated_processing_seconds<0 or max_distance_m<0: raise ValueError("invalid timing")
    d=upper_distance_m(o)
    return {"status":"PASS" if d<=max_distance_m else "FAIL","upper_bound_distance_m":d,"max_distance_m":max_distance_m,"note":"Timing is only one evidence layer; endpoint identity, routing and calibration remain assumptions"}
