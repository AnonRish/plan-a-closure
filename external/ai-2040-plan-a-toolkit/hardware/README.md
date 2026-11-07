
# Hardware harness

The harness records measurements with the same evidence-oriented structure used
by the software lab. It does not invent hardware values.

Linux deployments may add a live packet adapter around AF_PACKET, DPDK or
AF_XDP and record line-rate capture/drop/failover observations. Hardware-specific
drivers remain intentionally outside the standard-library core so the reference
protocol is not coupled to one vendor.

A valid hardware result includes the raw measurement artifact, environment,
device identifier, test parameters, sample count, timestamp and SHA-256 digest.
