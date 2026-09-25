# PoC harness build for three Blender PLY-importer findings.
# REPO must point at a checkout of this fork (defaults to the repo root).
REPO ?= ..
CXX ?= g++
CXXFLAGS = -std=c++20 -DNDEBUG -g -O1 -fno-omit-frame-pointer \
  -Iharness/stubs \
  -I$(REPO)/source/blender/blenlib \
  -I$(REPO)/source/blender/io/ply/intern \
  -I$(REPO)/source/blender/io/ply/importer \
  -I$(REPO)/extern/fast_float

REAL_SRC = \
  $(REPO)/source/blender/io/ply/importer/ply_import_buffer.cc \
  $(REPO)/source/blender/io/ply/importer/ply_import_data.cc \
  $(REPO)/source/blender/blenlib/intern/endian_switch.cc \
  harness/stubs/stubs.cc

all: poc_harness_asan poc_harness_vanilla

poc_harness_generated.cc: build_harness.py $(REPO)/source/blender/io/ply/importer/ply_import.cc \
                     $(REPO)/source/blender/io/ply/importer/ply_import_gsplat.cc
	python3 build_harness.py $(REPO) .

poc_harness_asan: poc_harness_generated.cc $(REAL_SRC)
	$(CXX) $(CXXFLAGS) -fsanitize=address -o $@ $^

poc_harness_vanilla: poc_harness_generated.cc $(REAL_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $^

inputs:
	python3 make_inputs.py inputs

clean:
	rm -f poc_harness_asan poc_harness_vanilla poc_harness_generated.cc

.PHONY: inputs clean
