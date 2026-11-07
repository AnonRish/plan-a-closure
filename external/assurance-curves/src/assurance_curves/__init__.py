"""assurance-curves: detection math for random-sampling AI verification."""
from .canary import (canaries_needed, guaranteed_detection, max_undetected_suppression,
                     p_catch_suppression, p_detected_with_suppression)
from .core import (LN_100, confidence_from_nines, fake_packets_for_confidence,
                   min_fake_packets_exact, nines, p_detected_exact,
                   p_detected_hypergeometric, p_detected_poisson, p_undetected_exact,
                   required_budget)
from .curves import (AssuranceCurve, assurance_curve, confidence_for_fraction,
                     coverage_for_confidence, fraction_for_confidence, nines_for_fraction)
from .falsealarm import (audited_packets_per_year, certifiable_fpr, expected_false_alarms,
                         gaussian_threshold_sigma, max_fpr_for_alarm_budget,
                         packets_to_certify_fpr)
from .rogue import TAP_LEVELS_H100E, RogueDeploymentModel, granularity_table
from .sequential import (BernoulliMixtureEProcess, e_bh, first_alarm_step, log_e_from_counts,
                         log_e_paths)

__version__ = "0.1.0"
