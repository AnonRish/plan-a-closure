
# Assurance layer

The assurance package contains conservative multi-control composition and the
sampling-economics equations used to translate a stated fake-compute fraction,
packet size, target confidence, and verifier budget into an explicit coverage
requirement.

The equations are assumptions/models, not empirical measurements. The user of
the package must separately validate the statistical sampling frame,
independence assumptions, packet reproducibility and adversarial behavior.
