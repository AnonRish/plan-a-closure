import ast
import inspect
import json
import socket
import threading

import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weight_diode import Encoder, LossyLink, Receiver, cli, link, receiver as receiver_module, udp_receive, udp_send

KEY = Ed25519PrivateKey.generate()
DATA = np.random.default_rng(1).integers(0, 256, 120_000, dtype=np.uint8).tobytes()
SEND_NAMES = {"send", "sendto", "sendall", "sendmsg", "sendfile", "connect", "connect_ex"}


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_real_udp_transfer_over_loopback_with_loss_and_the_receiver_never_transmits(monkeypatch):
    sent_from = []
    for name in ("sendto", "send", "sendall", "sendmsg"):
        orig = getattr(socket.socket, name)

        def spy(self, *a, _orig=orig, **k):
            r = _orig(self, *a, **k)
            try:
                sent_from.append(self.getsockname()[1])
            except OSError:
                pass
            return r
        monkeypatch.setattr(socket.socket, name, spy)
    port = free_port()
    enc = Encoder(DATA, KEY, symbol_size=512, k=20, r=8, serial=2, label="udp")
    rx = Receiver([KEY.public_key()])
    ready = threading.Event()
    t = threading.Thread(target=udp_receive, args=(rx, "127.0.0.1", port), kwargs=dict(timeout=30, ready=ready))
    t.start()
    assert ready.wait(5)
    n = udp_send(LossyLink(0.1, seed=1).transmit(enc.stream(passes=3)), ("127.0.0.1", port))
    t.join(35)
    assert not t.is_alive()
    assert rx.result(enc.manifest_id) == DATA and n > 0
    assert sent_from and port not in sent_from                    # the sender sent; the receiver's socket never did


def _calls(tree):
    return {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}


def test_receiver_module_has_no_sockets_and_the_udp_receive_loop_only_binds_and_receives():
    tree = ast.parse(inspect.getsource(receiver_module))
    imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
              {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not ({"socket", "socketserver", "asyncio", "requests", "urllib", "http"} & imports)
    assert not (_calls(tree) & SEND_NAMES)
    fn = next(n for n in ast.walk(ast.parse(inspect.getsource(link))) if isinstance(n, ast.FunctionDef) and n.name == "udp_receive")
    assert not (_calls(fn) & SEND_NAMES)
    assert {"bind", "recvfrom"} <= _calls(fn)


def test_cli_keygen_hash_overhead(tmp_path, capsys):
    out = tmp_path / "k"
    assert cli.main(["keygen", "--out", str(out)]) == 0
    assert len(open(str(out) + ".priv").read().strip()) == 64 and len(open(str(out) + ".pub").read().strip()) == 64
    f = tmp_path / "w.bin"
    f.write_bytes(b"weights")
    capsys.readouterr()
    cli.main(["hash", "--file", str(f)])
    import hashlib
    assert json.loads(capsys.readouterr().out)["sha256"] == hashlib.sha256(b"weights").hexdigest()
    cli.main(["overhead", "--size", "1000000000", "--symbol-size", "8192", "--k", "200", "--r", "55", "--loss", "0.05",
              "--link-gbps", "10"])
    o = json.loads(capsys.readouterr().out)
    assert 1.27 < o["overhead_vs_file"] < 1.45 and o["file_success_probability"] > 0.999 and o["transfer_seconds"] > 0.8


def test_cli_send_and_recv_round_trip_and_a_wrong_key_receives_nothing(tmp_path, capsys):
    k1, k2 = tmp_path / "a", tmp_path / "b"
    cli.main(["keygen", "--out", str(k1)])
    cli.main(["keygen", "--out", str(k2)])
    src, dst = tmp_path / "in.bin", tmp_path / "out.bin"
    src.write_bytes(DATA[:40_000])
    wl = tmp_path / "wl.txt"
    import hashlib
    wl.write_text(hashlib.sha256(DATA[:40_000]).hexdigest() + "\n")
    capsys.readouterr()
    for pub, expect_ok, timeout in ((str(k1) + ".pub", True, "20"), (str(k2) + ".pub", False, "1.5")):
        port = free_port()
        ready, rc = threading.Event(), []
        argv = ["recv", "--port", str(port), "--pubkey", pub, "--whitelist", str(wl), "--out", str(dst), "--timeout", timeout]
        t = threading.Thread(target=lambda: rc.append(cli.main(argv, ready=ready)))
        t.start()
        assert ready.wait(5)
        cli.main(["send", "--file", str(src), "--key", str(k1) + ".priv", "--to", f"127.0.0.1:{port}", "--k", "10", "--r", "6",
                  "--symbol-size", "256", "--passes", "3", "--simulate-loss", "0.1"])
        t.join(30)
        assert rc == [0 if expect_ok else 2]
    assert dst.read_bytes() == DATA[:40_000]
