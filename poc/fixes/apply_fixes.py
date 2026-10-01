#!/usr/bin/env python3
"""Applies the three PLY importer fixes and emits per-finding patch files.

Edits are applied to a pristine copy of the upstream files; the resulting
patches are standard unified diffs (git apply / patch -p1 compatible).
"""
import difflib
import os
import shutil
import sys

REPO = "/scratch/repos/blender"
IMP = os.path.join(REPO, "source/blender/io/ply/importer")
WORK = "/scratch/work/fixes"
PRISTINE = os.path.join(WORK, "pristine")
OUT = os.path.join(WORK, "patches")

os.makedirs(PRISTINE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

FILES = [
    "ply_import.cc",
    "ply_import_data.cc",
    "ply_import_mesh.cc",
    "ply_import_gsplat.cc",
]

# ---------------------------------------------------------------- edits
# (file, old, new) -- each old must match exactly once
EDITS_F2 = [(
    "ply_import.cc",
    """    else if (parse_keyword(line, "property")) {
      PlyProperty property;""",
    """    else if (parse_keyword(line, "property")) {
      if (r_header.elements.is_empty()) {
        /* A property must belong to an element. The old Python based importer rejected
         * this input as well ("Property without element"). */
        return "Property line without an element.";
      }
      PlyProperty property;""",
)]

EDITS_F3 = [
    (
        "ply_import.cc",
        """#include <array>
#include <string>""",
        """#include <array>
#include <charconv>
#include <string>""",
    ),
    (
        "ply_import.cc",
        """      skip_space(line);
      word = parse_word(line);
      element.count = std::stoi(std::string(word.data(), word.size()));
      r_header.elements.append(element);""",
        """      skip_space(line);
      word = parse_word(line);
      if (word.is_empty() ||
          std::from_chars(word.data(), word.data() + word.size(), element.count).ec !=
              std::errc() ||
          element.count < 0)
      {
        return "Invalid element count.";
      }
      r_header.elements.append(element);""",
    ),
]

EDITS_F1 = [
    (
        "ply_import_data.cc",
        """    if (element.name == "vertex") {
      error = load_vertex_element(file, header, element, data.get());
      got_vertex = true;
    }""",
        """    if (element.name == "vertex") {
      if (got_vertex) {
        /* Attribute arrays are sized to their own element's vertex count, while the
         * consumers index them by the combined vertex count of all vertex elements.
         * Multiple vertex elements would therefore lead to out-of-bounds reads. */
        data->error = "Multiple 'vertex' elements are not supported";
        return data;
      }
      error = load_vertex_element(file, header, element, data.get());
      got_vertex = true;
    }""",
    ),
    (
        "ply_import_mesh.cc",
        """    for (const PlyCustomAttribute &attr : data.vertex_custom_attr) {
      attributes.add<float>(attr.name,
                            bke::AttrDomain::Point,
                            bke::AttributeInitVArray(VArray<float>::from_span(attr.data)));
    }""",
        """    for (const PlyCustomAttribute &attr : data.vertex_custom_attr) {
      if (attr.data.size() != data.vertices.size()) {
        CLOG_WARN(
            &LOG, "PLY Importer: skipping attribute '%s' with unexpected size", attr.name.c_str());
        continue;
      }
      attributes.add<float>(attr.name,
                            bke::AttrDomain::Point,
                            bke::AttributeInitVArray(VArray<float>::from_span(attr.data)));
    }""",
    ),
    (
        "ply_import_gsplat.cc",
        """  Span<float> ply_rot[4] = {*ply_rot_0_attr, *ply_rot_1_attr, *ply_rot_2_attr, *ply_rot_3_attr};

  PointCloud *point_cloud = BKE_pointcloud_new_nomain(PointCloudType::GSplat,
                                                      data.vertices.size());""",
        """  Span<float> ply_rot[4] = {*ply_rot_0_attr, *ply_rot_1_attr, *ply_rot_2_attr, *ply_rot_3_attr};

  /* Attribute arrays are indexed by the vertex count in the copy loop below, so they
   * must be as long as the point cloud. */
  if (ply_f_dc[0].size() != data.vertices.size() ||
      ply_opacity.size() != data.vertices.size() ||
      ply_scale[0].size() != data.vertices.size() || ply_rot[0].size() != data.vertices.size())
  {
    return nullptr;
  }

  PointCloud *point_cloud = BKE_pointcloud_new_nomain(PointCloudType::GSplat,
                                                      data.vertices.size());""",
    ),
]


def apply_edits(base: dict, edits) -> dict:
    out = dict(base)
    for fname, old, new in edits:
        text = out[fname]
        if text.count(old) != 1:
            raise SystemExit(f"anchor not unique/found in {fname}: {old[:60]!r} (count={text.count(old)})")
        out[fname] = text.replace(old, new)
    return out


def make_patch(orig: dict, new: dict, path_prefix: str, out_path: str, header: str):
    chunks = []
    for fname in FILES:
        if orig[fname] == new[fname]:
            continue
        rel = f"source/blender/io/ply/importer/{fname}"
        diff = difflib.unified_diff(
            orig[fname].splitlines(keepends=True),
            new[fname].splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            n=3,
        )
        chunks.append("".join(diff))
    with open(out_path, "w") as f:
        f.write(header)
        f.write("".join(chunks))
    print("wrote", out_path)


def main():
    base = {}
    for fname in FILES:
        with open(os.path.join(IMP, fname)) as f:
            base[fname] = f.read()
        shutil.copy(os.path.join(IMP, fname), os.path.join(PRISTINE, fname))

    f2 = apply_edits(base, EDITS_F2)
    f3 = apply_edits(base, EDITS_F3)
    f1 = apply_edits(base, EDITS_F1)
    allp = apply_edits(apply_edits(apply_edits(base, EDITS_F2), EDITS_F3), EDITS_F1)

    make_patch(base, f2, "source/blender/io/ply/importer",
               os.path.join(OUT, "0001-ply-reject-property-line-without-element.patch"),
               "Fix PLY importer crash on a `property` line without a preceding `element`.\n\n"
               "read_header() appended to `elements.last()` while the list could still be\n"
               "empty; Vector::last() is assert-only, so a crafted header made the append\n"
               "write through a garbage container reference (crash).\n\n")
    make_patch(base, f3, "source/blender/io/ply/importer",
               os.path.join(OUT, "0002-ply-parse-element-count-with-from-chars.patch"),
               "Fix PLY importer terminating on an invalid element count.\n\n"
               "std::stoi() throws on non-numeric or out-of-range counts, and nothing on the\n"
               "call chain handles the exception. Parse with std::from_chars() and return a\n"
               "proper error instead.\n\n")
    make_patch(base, f1, "source/blender/io/ply/importer",
               os.path.join(OUT, "0003-ply-reject-duplicate-vertex-elements.patch"),
               "Fix out-of-bounds reads from PLY files with multiple `vertex` elements.\n\n"
               "Custom attribute arrays are sized to their own element's vertex count, while\n"
               "the mesh/gsplat consumers index them by the combined vertex count. Reject\n"
               "duplicate vertex elements, and guard the consumers against size mismatch.\n\n")

    make_patch(base, allp, "source/blender/io/ply/importer",
               os.path.join(OUT, "all-three-fixes-combined.patch"),
               "Combined PLY importer fixes (findings 1-3).\n\n")

    # Write the fully patched tree into the repo so the harness can be rebuilt from it.
    for fname in FILES:
        with open(os.path.join(IMP, fname), "w") as f:
            f.write(allp[fname])
    print("patched tree written")


if __name__ == "__main__":
    main()
