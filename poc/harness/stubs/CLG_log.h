/* Minimal no-op stand-in for Blender's clog. The PLY importer only uses
 * CLG_LogRef declarations and the CLOG_WARN/CLOG_ERROR/CLOG_DEBUG macros,
 * which do not affect control flow. */
#pragma once
struct CLG_LogRef {
  const char *identifier;
};
#define CLOG_WARN(log_ref, ...) ((void)0)
#define CLOG_ERROR(log_ref, ...) ((void)0)
#define CLOG_DEBUG(log_ref, ...) ((void)0)
