# Software capture benchmark

This benchmark is deliberately useful without pretending to be a 400/800/1600GbE hardware result.

It generates deterministic Ethernet/IPv4/TCP traffic, writes a real Ethernet pcap, runs the repository frame parser and whitelist, measures software processing throughput, and keeps attack traffic distinct from compliant traffic.

The output also contains theoretical line-rate packet-per-second projections for 100/400/800/1600 Gbps. They are marked measured=false. An empirical claim requires the same harness on the target NIC/DPU/TAP/capture host plus raw drop counters, hardware identifiers, driver versions and run logs.

PowerShell:

    python -m capture_benchmark.harness
