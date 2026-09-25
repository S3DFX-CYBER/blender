/* Minimal stand-in for BLI_fileops.hh: the PLY read buffer only uses BLI_fopen. */
#pragma once
#include <cstdio>
FILE *BLI_fopen(const char *filepath, const char *mode);
