import importlib.util
import json
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
_spec = importlib.util.spec_from_file_location("convert_tables", ROOT / "tools" / "convert_tables.py")
ct = importlib.util.module_from_spec(_spec)
sys.modules["convert_tables"] = ct
_spec.loader.exec_module(ct)
safe_load, to_json, convert, PINNED = ct.safe_load, ct.to_json, ct.convert, ct.PINNED

FX = ROOT / "tests" / "fixtures" / "pickles"


def fx(name: str) -> bytes:
    return (FX / name).read_bytes()


def test_slice_and_scalar():
    assert to_json(safe_load(fx("slice.pkl"))) == {"slice": [577, 678, 50]}
    assert to_json(safe_load(fx("scalar_u8.pkl"))) == 6112


def test_arrays_become_lists():
    nd = to_json(safe_load(fx("ndarray.pkl")))
    assert nd == {"array": [[1, 2], [300, 65535]], "dtype": "<u2", "shape": [2, 2]}
    assert to_json(safe_load(fx("frombuffer.pkl")))["v"]["array"] == [[0, 1, 2], [3, 4, 5]]


def test_reconstruct_route():
    assert to_json(safe_load(fx("reconstruct.pkl")))["array"] == [[1, 2], [3, 40000]]


def test_mixed_and_gzip():
    import gzip
    out = to_json(safe_load(gzip.compress(fx("mixed.pkl"))))
    assert out["area"] == {"left": 1, "s": {"slice": [1, 5, None]}}
    assert out["value"] == 7 and out["f"] == 1.5 and out["mask"]["array"] == [[0, 1], [1, 0]]


def test_refuses_other_globals():
    with pytest.raises(pickle.UnpicklingError, match="refused global"):
        safe_load(fx("evil_os.pkl"))


def test_never_imports_numpy():
    code = (
        "import importlib.util,sys;"
        f"s=importlib.util.spec_from_file_location('ct', r'{ROOT / 'tools' / 'convert_tables.py'}');"
        "m=importlib.util.module_from_spec(s);sys.modules['ct']=m;s.loader.exec_module(m);"
        f"m.to_json(m.safe_load(open(r'{FX / 'mixed.pkl'}','rb').read()));"
        f"m.to_json(m.safe_load(open(r'{FX / 'reconstruct.pkl'}','rb').read()));"
        "print('numpy' in sys.modules)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


def call_pickle(module: str, name: str, args: tuple) -> bytes:
    """A pickle that calls module.name(*args), built from opcodes so no real object is needed."""
    return f"c{module}\n{name}\n".encode() + pickle.dumps(args, protocol=0)[:-1] + b"R."


@pytest.mark.parametrize("module,name,args", [
    ("numpy", "dtype", ("c16", False, True)),                     # unsupported dtype kind
    ("numpy", "dtype", ("u3", False, True)),                      # unsupported size
    ("builtins", "slice", (1, 2, 3, 4)),                          # too many arguments
    ("numpy._core.numeric", "_frombuffer", ("x", "u1", (1,), "C")),  # dtype isn't a dtype
])
def test_bad_stand_in_args_raise(module, name, args):
    with pytest.raises(ValueError):
        safe_load(call_pickle(module, name, args))


def test_fortran_order_refused():
    dt = ct.DtypeStub.from_spec("u1")
    with pytest.raises(ValueError):
        ct.frombuffer(b"\x00\x01", dt, (1, 2), "F")


def test_scalar_with_wrong_byte_count_raises():
    # scalar(dtype('<u8'), 3 bytes) must be a clean ValueError, never a struct crash elsewhere
    dt = ct.DtypeStub.from_spec("u8")
    with pytest.raises(ValueError):
        ct.scalar(dt, b"\x01\x02\x03")


def test_convert_writes_json_and_manifest(tmp_path):
    m = convert(["slice"], tmp_path, fetch=lambda n, c: fx("slice.pkl"))
    assert json.loads((tmp_path / "slice.json").read_text()) == {"slice": [577, 678, 50]}
    assert m["commit"] == PINNED and "sha256_res" in m["files"]["slice"]
    assert json.loads((tmp_path / "manifest.json").read_text())["files"]["slice"]["bytes"] == len(fx("slice.pkl"))


def test_convert_passes_plain_json_tables_through(tmp_path):
    convert(["musicnamechanges"], tmp_path, fetch=lambda n, c: b'[["a", "b"]]')
    assert json.loads((tmp_path / "musicnamechanges.json").read_text()) == [["a", "b"]]
