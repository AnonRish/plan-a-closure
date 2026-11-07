from pathlib import Path
from hardware.linux_energy import read_rapl_energy
def test_missing_powercap_is_unknown(tmp_path): assert read_rapl_energy(str(tmp_path))["status"]=="UNKNOWN"
