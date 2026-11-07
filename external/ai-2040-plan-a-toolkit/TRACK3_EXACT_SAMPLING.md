
# Exact finite-population sampling

The Plan A appendix uses an exponential/Poisson-style approximation for random
sampling. RVP-1 now also implements the exact detection probability for simple
random sampling without replacement:

P(detect at least one rogue unit)
= 1 - C(N-R,n) / C(N,n)

where:
- N = total sampling-frame units;
- R = rogue units;
- n = sampled units.

The implementation uses log-gamma arithmetic to avoid constructing enormous
binomial coefficients.

This does not solve more complicated designs such as stratification, clustered
sampling, unequal inclusion probabilities, or adversaries who can manipulate the
sampling frame itself. Those require separate preregistered assumptions.
