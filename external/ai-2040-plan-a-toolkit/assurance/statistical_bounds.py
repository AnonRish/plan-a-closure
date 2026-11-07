from __future__ import annotations
import math
from scipy.stats import beta, norm

def finite_population_detection_probability(N: int, R: int, n: int) -> float:
    if not (0 < N and 0 <= R <= N and 0 <= n <= N): raise ValueError('invalid finite-population parameters')
    if n == 0 or R == 0: return 0.0
    if n > N - R: return 1.0
    log_p0=(math.lgamma(N-R+1)-math.lgamma(N-R-n+1)-math.lgamma(N+1)+math.lgamma(N-n+1))
    return 1.0-math.exp(log_p0)

def required_sample_size(N: int, R: int, target_detection: float) -> int:
    if not (0 < N and 0 <= R <= N) or not 0 < target_detection < 1: raise ValueError('invalid parameters')
    if R == 0: return 0
    lo,hi=0,N
    while lo<hi:
        mid=(lo+hi)//2
        if finite_population_detection_probability(N,R,mid)>=target_detection: hi=mid
        else: lo=mid+1
    return lo

def binomial_zero_failure_upper(n:int,delta:float=0.05)->float:
    if n<=0 or not 0<delta<1: raise ValueError('invalid n or delta')
    return 1.0-delta**(1.0/n)

def clopper_pearson_upper(k:int,n:int,confidence:float=0.95)->float:
    if not (0<=k<=n and n>0 and 0<confidence<1): raise ValueError('invalid interval parameters')
    if k==n: return 1.0
    alpha=1.0-confidence
    return float(beta.ppf(1.0-alpha/2.0,k+1,n-k))

def wilson_upper(k:int,n:int,confidence:float=0.95)->float:
    if not (0<=k<=n and n>0 and 0<confidence<1): raise ValueError('invalid interval parameters')
    z=float(norm.ppf((1.0+confidence)/2.0)); p=k/n; denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return min(1.0,center+half)

def finite_population_zero_failure_rogue_upper(N:int,n:int,confidence:float=0.95)->int:
    if not (0<N and 0<=n<=N and 0<confidence<1): raise ValueError('invalid population parameters')
    if n==0: return N
    alpha=1.0-confidence; lo,hi=0,N
    while lo<hi:
        mid=(lo+hi+1)//2
        p0=1.0-finite_population_detection_probability(N,mid,n)
        if p0>=alpha: lo=mid
        else: hi=mid-1
    return lo
