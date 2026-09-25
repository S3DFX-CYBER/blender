# PLY Importer PoC Harness — Blender `main` (5.03 alpha)

Proof-of-concept and impact demonstration for three vulnerabilities in
Blender's C++ PLY importer. The harness compiles the **actual importer code
from this repository**:

- `source/blender/io/ply/importer/ply_import_buffer.cc` — compiled unmodified
- `source/blender/io/ply/importer/ply_import_data.cc` — compiled unmodified
- `source/blender/blenlib/intern/endian_switch.cc` — compiled unmodified
- `read_header()` and its helpers — extracted **verbatim** from
  `source/blender/io/ply/importer/ply_import.cc` by `build_harness.py`
  (see the `==== VERBATIM ====` banners in the generated file)
- `find_custom_attribute()` and the gsplat consumer read expressions —
  extracted **verbatim** from `source/blender/io/ply/importer/ply_import_gsplat.cc`

Only the BKE/point-cloud plumbing that receives already-read values is
replaced (three small stub headers under `harness/stubs/`: a libc-backed
guarded-allocator, a no-op clog, and `BLI_fopen`). The vulnerable parsing
and out-of-bounds reads themselves are this repo's code, unchanged.
`-DNDEBUG` is used to match release-build semantics (asserts compiled out).

## Build

```sh
cd poc
make            # produces poc_harness_asan and poc_harness_vanilla
python3 make_inputs.py inputs   # generates the .ply PoC and control files
```

Note: `poc1_crash_large.ply` (~120 MB) is generated, not committed.

## Run

```sh
# Finding 1 — gsplat OOB read via duplicate `element vertex` sections
./poc_harness_asan   case1         inputs/poc1_duplicate_vertex_elements.ply   # ASAN heap-buffer-overflow
./poc_harness_vanilla case1-values inputs/poc1_duplicate_vertex_elements.ply   # shows OOB values
./poc_harness_vanilla case1         inputs/poc1_crash_large.ply                # SIGSEGV (exit 139)
./poc_harness_asan   case1         inputs/poc1_control_single_element.ply      # control: clean exit 0

# Finding 2 — `property` before any `element` -> elements.last() on empty Vector
./poc_harness_vanilla case2 inputs/poc2_property_before_element.ply   # SIGSEGV (exit 139), deterministic
./poc_harness_asan    case2 inputs/poc2_control_valid_header.ply     # control: clean

# Finding 3 — non-numeric element count -> uncaught std::stoi exception
./poc_harness_asan    case3 inputs/poc3_non_numeric_count.ply    # terminate/abort (exit 134)
./poc_harness_vanilla case3 inputs/poc3_out_of_range_count.ply    # terminate/abort (exit 134)
./poc_harness_asan    case3 inputs/poc3_control_valid_count.ply   # control: clean
```

Actual captured outputs are in `results/`.

## Findings

### Finding 1 (Medium) — OOB heap read in gsplat conversion via duplicate `element vertex`

`load_vertex_element()` sizes each custom attribute to its own element's
count, but appends rows to a shared vertex list. `convert_gsplat_ply_to_
point_cloud()` then iterates `i < data.vertices.size()` (the combined count
of all `element vertex` sections) while indexing attribute spans sized to the
first element's count only.

Observed (see `results/finding1_runs.log`):
- ASAN: `heap-buffer-overflow READ of size 4 ... 0 bytes after 32-byte
  region`, allocation traced through the repo's own `load_vertex_element`
  (`ply_import_data.cc:273`).
- Vanilla build: attribute `f_dc_0` at index 12 returns **2000.0 — the value
  of `f_dc_1`**, i.e. data read from a neighboring heap buffer flows into the
  imported splat; garbage floats (e.g. `-1.4e25`) also leak through.
- Crash-scale file (8 + 20,000,000 vertices): **SIGSEGV, exit 139**
  (`results/finding1_crash_run.log`).
- Control (single element, attribute size == vertex count): clean exit 0.

### Finding 2 (Low) — `property` before any `element` in the header

`read_header()` calls `r_header.elements.last().properties.append(property)`
unconditionally. With no prior `element` line, `last()` on an empty
`Vector<PlyElement>` (assert-only bounds check, compiled out with NDEBUG)
is undefined behavior, followed by an append through the resulting garbage
reference.

Observed: deterministic **SIGSEGV (exit 139)** in the vanilla build, 6/6
runs (`results/finding2_vanilla_crash.log`). Under ASAN the UB manifests as
a write through a garbage object (LeakSanitizer reports an allocation leaked
from inside `read_header`). The pre-2023 Python importer explicitly rejected
this input ("Property without element"); the check was not carried over.

### Finding 3 (Low) — uncaught `std::stoi` exception

`read_header()` parses element counts with `std::stoi` on unvalidated input;
a non-numeric or out-of-range count throws, and no handler exists on the call
chain (`PLY_import` -> `wm_ply_import_exec`), so the process terminates.

Observed: `terminate called after throwing an instance of
'std::invalid_argument' what(): stoi`, **exit 134 (SIGABRT)**; the
out-of-range variant throws `std::out_of_range`.

## Remediation

1. `ply_import_gsplat.cc`: require `attr.size() == data.vertices.size()` for
   every required gsplat attribute before the copy loop (Finding 1).
2. `ply_import.cc`: reject a `property` line when `r_header.elements` is
   empty (Finding 2).
3. `ply_import.cc`: replace `std::stoi` with `std::from_chars` + error
   string (Finding 3).

## Disclosure

Blender has no bug bounty program; security reports go to
`security@blender.org`
(https://developer.blender.org/docs/handbook/bug_reports/vulnerability_reports/).
