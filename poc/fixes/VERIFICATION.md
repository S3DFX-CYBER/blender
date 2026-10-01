# Fix verification — PLY importer findings 1-3

Patches in this directory fix three PLY importer issues (reported to
security@blender.org; filing in the tracker per Sergey Sharybin's suggestion):

| Patch | Fixes | File(s) |
|---|---|---|
| `0001-ply-reject-property-line-without-element.patch` | crash: `property` line before any `element` | `ply_import.cc` |
| `0002-ply-parse-element-count-with-from-chars.patch` | unhandled `std::stoi` exception on bad element count | `ply_import.cc` |
| `0003-ply-reject-duplicate-vertex-elements.patch` | out-of-bounds reads with multiple `vertex` elements | `ply_import_data.cc`, `ply_import_mesh.cc`, `ply_import_gsplat.cc` |

All three apply cleanly in sequence to current `main` (`git apply`), and can be
applied together via `all-three-fixes-combined.patch`.

## How they were verified

The PoC harness in `../` compiles the repository's own importer translation
units (`ply_import_buffer.cc`, `ply_import_data.cc`) plus `read_header()`
extracted verbatim from `ply_import.cc`, under AddressSanitizer and in a
release-semantics (`-DNDEBUG`) build. The same seven PoC and control files
were run against the unpatched and patched trees.

## Results (patched tree)

```
Finding 1 (poc1_duplicate_vertex_elements.ply):
  before: ASAN heap-buffer-overflow READ of size 4 (0 bytes after 32-byte
          region, allocation stack through load_vertex_element); vanilla
          build read 64 values out of bounds, leaking adjacent heap into
          the imported attributes; 120 MB variant SIGSEGV
  after:  import error: "Multiple 'vertex' elements are not supported" —
          no out-of-bounds access (ASAN clean)
  control (poc1_control_single_element.ply): still imports, 72/72 valid
          attribute values, 0 out-of-bounds reads

Finding 2 (poc2_property_before_element.ply):
  before: deterministic SIGSEGV (6/6 runs); production 5.2.2 LTS crash log:
          EXCEPTION_ACCESS_VIOLATION reading 0xFFFFFFFFFFFFFFFF, stack
          read_header -> Vector<PlyProperty>::append_as
  after:  read_header() returns "Property line without an element." —
          no crash
  control (poc2_control_valid_header.ply): parses cleanly

Finding 3 (poc3_non_numeric_count.ply / poc3_out_of_range_count.ply):
  before: terminate called after throwing an instance of
          'std::invalid_argument' what(): stoi (SIGABRT, exit 134)
  after:  read_header() returns "Invalid element count." — no exception
  control (poc3_control_valid_count.ply): parses cleanly
```

Raw log: `verification.log` (this directory).
