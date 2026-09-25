#include "BLI_fileops.hh"
FILE *BLI_fopen(const char *filepath, const char *mode)
{
  return std::fopen(filepath, mode);
}
