/* Minimal stand-in for Blender's guarded allocator, sufficient to compile the
 * PLY importer translation units outside a full Blender build. Implements the
 * allocation API used by BLI_allocator.hh with plain libc allocation. */
#pragma once
#include <cstdlib>
#include <cstring>
#include <utility>

#define MEM_MIN_CPP_ALIGNMENT \
  (__STDCPP_DEFAULT_NEW_ALIGNMENT__ < alignof(void *) ? __STDCPP_DEFAULT_NEW_ALIGNMENT__ : \
                                                        alignof(void *))

static inline void *MEM_new_zeroed(size_t len, const char * /*str*/)
{
  return calloc(len ? len : 1, 1);
}
static inline void *MEM_new_uninitialized(size_t len, const char * /*str*/)
{
  return malloc(len ? len : 1);
}
static inline void *MEM_new_uninitialized_aligned(size_t len, size_t alignment, const char * /*str*/)
{
  size_t a = alignment < sizeof(void *) ? sizeof(void *) : alignment;
  void *p = nullptr;
  if (posix_memalign(&p, a, len ? len : 1) != 0) {
    return nullptr;
  }
  return p;
}
static inline void MEM_delete_void(void *vmemh)
{
  free(vmemh);
}
