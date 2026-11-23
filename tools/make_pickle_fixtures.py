"""Dev-only: build the tiny synthetic pickles the converter tests use.

Run once (numpy is only needed here, never by the app or the converter):
  uv run --no-project --with numpy python tools/make_pickle_fixtures.py
"""

import os
import pickle
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "pickles"


class Evil:
    def __reduce__(self):
        return (os.system, ("echo pwned",))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "slice": slice(577, 678, 50),
        "scalar_u8": np.uint64(6112),
        "frombuffer": {"v": np.frombuffer(bytes(range(6)), dtype=np.uint8).reshape(2, 3)},
        "ndarray": np.array([[1, 2], [300, 65535]], dtype=np.uint16),
        "mixed": {"area": {"left": 1, "s": slice(1, 5, None)}, "value": np.uint32(7),
                  "mask": np.array([[0, 1], [1, 0]], dtype=np.uint8), "f": np.float64(1.5)},
        "evil_os": Evil(),
    }
    for name, obj in fixtures.items():
        (OUT / f"{name}.pkl").write_bytes(pickle.dumps(obj, protocol=5))
        print("wrote", name)
    # Older protocols store arrays via _reconstruct + ndarray + BUILD, as some real tables do.
    (OUT / "reconstruct.pkl").write_bytes(pickle.dumps(np.array([[1, 2], [3, 40000]], dtype=np.uint16), protocol=4))
    print("wrote reconstruct")


if __name__ == "__main__":
    main()
