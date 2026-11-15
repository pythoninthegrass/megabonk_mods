/*
 * Standalone Il2Cpp binding probe: dlopens a shipped game runtime and calls it through its
 * exported C API with no mod loader, no UnityPlayer and no managed host in the process.
 * Prints one "#JSON# {...}" line the Python driver scores, plus human-readable lines on stderr.
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1 /* sigaction, dladdr, strcasecmp and MAP_ANONYMOUS out of glibc */
#endif

#include <dlfcn.h>
#include <errno.h>
#include <math.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/mman.h>
#include <unistd.h>

#if defined(__APPLE__)
#include <mach/mach.h>
#include <mach-o/dyld.h>
#include <sys/sysctl.h>
#endif

#include <signal.h>

#define SPAN_BYTES 65536u
#define THUNK_PROLOGUE_LEN 5
#define ABS_JUMP_LEN 14

typedef void *Il2CppClass;
typedef void *MethodInfo;
typedef void *Il2CppObject;
typedef void *Il2CppString;

typedef struct {
  const char *dylib;
  const char *data_dir;
  const char *leg;
  const char *invoke_image;
  const char *invoke_class;
  const char *invoke_method;
  const char *invoke_ret;
  const char *invoke_expected;
  const char *hook;
  const char *dlopen_mode;
  const char *preloads[4];
  size_t preload_count;
  const char *type_pending[8];
  size_t type_count;
  const char *arg_kinds[8];
  const char *arg_values[8];
  const char *arg_types[8];
  size_t arg_count;
  int skip_init;
} Config;

static Config cfg;

static const char *loader_markers[] = {
    "doorstop", "bepinex",   "dobby",          "coreclr",    "clrjit",
    "il2cppinterop", "0harmony", "melonloader", "funchook",  "unityplayer",
};

/* ------------------------------------------------------------------ output */

static void note(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  fprintf(stderr, "[host] ");
  vfprintf(stderr, fmt, ap);
  va_end(ap);
  fputc('\n', stderr);
  fflush(stderr);
}

#define MAX_EVIDENCE 64
static struct {
  char key[40];
  char value[512];
  int numeric;
} evidence[MAX_EVIDENCE];
static size_t evidence_count;

static void ev_add(const char *key, const char *value, int numeric) {
  for (size_t i = 0; i < evidence_count; i++) {
    if (strcmp(evidence[i].key, key) == 0) {
      snprintf(evidence[i].value, sizeof(evidence[i].value), "%s", value);
      evidence[i].numeric = numeric;
      return;
    }
  }
  if (evidence_count >= MAX_EVIDENCE) return;
  snprintf(evidence[evidence_count].key, sizeof(evidence[evidence_count].key), "%s", key);
  snprintf(evidence[evidence_count].value, sizeof(evidence[evidence_count].value), "%s", value);
  evidence[evidence_count].numeric = numeric;
  evidence_count++;
}

static void ev_num(const char *key, long long value) {
  char buf[32];
  snprintf(buf, sizeof(buf), "%lld", value);
  ev_add(key, buf, 1);
}

static void ev_str(const char *key, const char *value) {
  ev_add(key, value ? value : "", 0);
}

static void ev_ptr(const char *key, const void *value) {
  char buf[32];
  snprintf(buf, sizeof(buf), "0x%llx", (unsigned long long)(uintptr_t)value);
  ev_add(key, buf, 0);
}

__attribute__((unused)) static void ev_hex(const char *key, const unsigned char *bytes, size_t len) {
  char buf[512];
  size_t used = 0;
  buf[0] = '\0';
  for (size_t i = 0; i < len && used + 3 < sizeof(buf); i++)
    used += (size_t)snprintf(buf + used, sizeof(buf) - used, "%02x", bytes[i]);
  ev_add(key, buf, 0);
}

static void json_escape(const char *in, char *out, size_t out_len) {
  size_t used = 0;
  for (const char *p = in; *p && used + 2 < out_len; p++) {
    unsigned char c = (unsigned char)*p;
    if (c == '"' || c == '\\') {
      out[used++] = '\\';
      out[used++] = (char)c;
    } else if (c == '\n') {
      out[used++] = '\\';
      out[used++] = 'n';
    } else if (c == '\t') {
      out[used++] = '\\';
      out[used++] = 't';
    } else if (c < 0x20 || c > 0x7E) {
      used += (size_t)snprintf(out + used, out_len - used, "\\u%04x", c);
    } else {
      out[used++] = (char)c;
    }
  }
  out[used] = '\0';
}

static void emit(int status_ok, const char *reason) {
  char escaped[1024];
  json_escape(reason ? reason : "", escaped, sizeof(escaped));
  printf("#JSON# {\"status\": \"%s\", \"reason\": \"%s\", \"evidence\": {",
         status_ok ? "pass" : "fail", escaped);
  for (size_t i = 0; i < evidence_count; i++) {
    char escaped_value[1024];
    json_escape(evidence[i].value, escaped_value, sizeof(escaped_value));
    printf("%s\"%s\": ", i ? ", " : "", evidence[i].key);
    if (evidence[i].numeric)
      printf("%s", escaped_value);
    else
      printf("\"%s\"", escaped_value);
  }
  printf("}}\n");
  fflush(stdout);
}

/* ------------------------------------------------------------ image scan */

/* the two phase markers the fault handler reports */
static const char *g_phase = "startup";
static char g_hook_name[96] = "";

/* A fault while binding is a result, not a lost run: the handler writes the scored
   JSON line with the signal name before exiting, so the driver never sees silence. */
static const char *signal_name(int signo) {
  switch (signo) {
    case SIGBUS: return "SIGBUS";
    case SIGSEGV: return "SIGSEGV";
    case SIGILL: return "SIGILL";
    case SIGFPE: return "SIGFPE";
    case SIGTRAP: return "SIGTRAP";
    case SIGABRT: return "SIGABRT";
    default: return "signal";
  }
}

static void fault_handler(int signo) {
  char signature[192];
  if (g_hook_name[0]) {
    snprintf(signature, sizeof(signature), "%s during %s hooking %s", signal_name(signo), g_phase,
             g_hook_name);
  } else {
    snprintf(signature, sizeof(signature), "%s during %s", signal_name(signo), g_phase);
  }
  ev_str("crash_signal", signal_name(signo));
  emit(0, signature);
  _exit(139);
}

static void install_fault_guard(void) {
  struct sigaction sa;
  memset(&sa, 0, sizeof(sa));
  sa.sa_handler = fault_handler;
  sigemptyset(&sa.sa_mask);
  sa.sa_flags = SA_NODEFER;
  const int caught[] = {SIGBUS, SIGSEGV, SIGILL, SIGFPE, SIGTRAP, SIGABRT};
  for (size_t i = 0; i < sizeof(caught) / sizeof(caught[0]); i++) {
    sigaction(caught[i], &sa, NULL);
  }
}

static int contains_ci(const char *haystack, const char *needle) {
  for (const char *h = haystack; *h; h++) {
    const char *a = h, *b = needle;
    while (*a && *b) {
      char ca = *a, cb = *b;
      if (ca >= 'A' && ca <= 'Z') ca = (char)(ca + 32);
      if (cb >= 'A' && cb <= 'Z') cb = (char)(cb + 32);
      if (ca != cb) break;
      a++;
      b++;
    }
    if (!*b) return 1;
  }
  return 0;
}

static void scan_loaded_images(void) {
  size_t total = 0, flagged = 0;
  char first_flagged[512] = "";
#if defined(__APPLE__)
  uint32_t count = _dyld_image_count();
  for (uint32_t i = 0; i < count; i++) {
    const char *name = _dyld_get_image_name(i);
    if (!name) continue;
    total++;
    for (size_t k = 0; k < sizeof(loader_markers) / sizeof(loader_markers[0]); k++) {
      if (contains_ci(name, loader_markers[k])) {
        flagged++;
        if (!first_flagged[0]) snprintf(first_flagged, sizeof(first_flagged), "%s", name);
        break;
      }
    }
  }
#else
  FILE *f = fopen("/proc/self/maps", "r");
  if (f) {
    char line[4096];
    while (fgets(line, sizeof(line), f)) {
      char *path = strchr(line, '/');
      if (!path) continue;
      total++;
      for (size_t k = 0; k < sizeof(loader_markers) / sizeof(loader_markers[0]); k++) {
        if (contains_ci(path, loader_markers[k])) {
          flagged++;
          if (!first_flagged[0]) {
            size_t len = strlen(path);
            while (len && (path[len - 1] == '\n' || path[len - 1] == '\r')) path[--len] = '\0';
            snprintf(first_flagged, sizeof(first_flagged), "%.*s", (int)len, path);
          }
          break;
        }
      }
    }
    fclose(f);
  }
#endif
  ev_num("images", (long long)total);
  ev_num("loader_images", (long long)flagged);
  if (first_flagged[0]) ev_str("loader_image_example", first_flagged);
  note("images=%zu loader_images=%zu%s%s", total, flagged, first_flagged[0] ? " flagged=" : "",
       first_flagged);
}

/* --------------------------------------------------------------- il2cpp api */

typedef void (*api_init_t)(const char *);
typedef void (*api_set_data_dir_t)(const char *);
typedef void *(*api_domain_get_t)(void);
typedef void *(*api_thread_attach_t)(void *);
typedef const char *(*api_domain_get_name_t)(void *);
typedef Il2CppClass (*api_class_from_name_t)(void *, const char *, const char *);
typedef MethodInfo (*api_class_get_method_from_name_t)(Il2CppClass, const char *, int);
typedef const char *(*api_method_get_name_t)(MethodInfo);
typedef const char *(*api_class_get_name_t)(Il2CppClass);
typedef const char *(*api_class_get_namespace_t)(Il2CppClass);
typedef uint32_t (*api_method_get_param_count_t)(MethodInfo);
typedef uint32_t (*api_method_get_token_t)(MethodInfo);
typedef uint32_t (*api_object_get_size_t)(Il2CppObject *);
typedef Il2CppObject *(*api_object_new_t)(Il2CppClass);
typedef Il2CppObject *(*api_runtime_invoke_t)(MethodInfo, void *, void **, Il2CppObject **);
typedef Il2CppString *(*api_string_new_t)(const char *);
typedef const char *(*api_string_chars_t)(Il2CppString);
typedef uint32_t (*api_string_length_t)(Il2CppString);
typedef Il2CppClass (*api_class_from_il2cpp_object_t)(Il2CppObject);
typedef void (*api_set_commandline_arguments_t)(int, const char *const *, const char **);
typedef void (*api_add_internal_call_t)(const char *, void *);
typedef void (*api_print_exception_t)(Il2CppObject *);
typedef void *(*api_get_corlib_t)(void);
typedef void *(*api_domain_get_assemblies_t)(void *, size_t *);
typedef void *(*api_assembly_get_image_t)(void *);
typedef void *(*api_object_unbox_t)(Il2CppObject *);
typedef Il2CppClass (*api_object_get_class_t)(Il2CppObject *);
typedef void *(*api_class_get_methods_t)(Il2CppClass, void **);
typedef const char *(*api_method_get_param_name_t)(MethodInfo, uint32_t);
typedef void *(*api_method_get_param_t)(MethodInfo, uint32_t);
typedef void *(*api_method_get_return_type_t)(MethodInfo);
typedef int (*api_type_get_type_t)(void *);
typedef const char *(*api_image_get_name_t)(void *);

static struct {
  void *handle;
  api_init_t init;
  api_set_data_dir_t set_data_dir;
  api_domain_get_t domain_get;
  api_thread_attach_t thread_attach;
  api_domain_get_name_t domain_get_name;
  api_class_from_name_t class_from_name;
  api_class_get_method_from_name_t class_get_method_from_name;
  api_method_get_name_t method_get_name;
  api_class_get_name_t class_get_name;
  api_class_get_namespace_t class_get_namespace;
  api_method_get_param_count_t method_get_param_count;
  api_method_get_token_t method_get_token;
  api_object_get_size_t object_get_size;
  api_object_new_t object_new;
  api_runtime_invoke_t runtime_invoke;
  api_string_new_t string_new;
  api_string_chars_t string_chars;
  api_string_length_t string_length;
  api_class_from_il2cpp_object_t class_from_object;
  api_set_commandline_arguments_t set_commandline_arguments;
  api_add_internal_call_t add_internal_call;
  api_print_exception_t print_exception;
  api_get_corlib_t get_corlib;
  api_image_get_name_t image_get_name;
  api_domain_get_assemblies_t domain_get_assemblies;
  api_assembly_get_image_t assembly_get_image;
  api_object_unbox_t object_unbox;
  api_object_get_class_t object_get_class;
  api_class_get_methods_t class_get_methods;
  api_method_get_param_name_t method_get_param_name;
  api_method_get_param_t method_get_param;
  api_method_get_return_type_t method_get_return_type;
  api_type_get_type_t type_get_type;
  void *domain;
  int init_done;
  const char *runtime_path;
} api;

static void *sym(const char *name) {
  return dlsym(api.handle, name);
}

static void resolve_api(void) {
  api.init = (api_init_t)sym("il2cpp_init");
  api.set_data_dir = (api_set_data_dir_t)sym("il2cpp_set_data_dir");
  api.domain_get = (api_domain_get_t)sym("il2cpp_domain_get");
  api.thread_attach = (api_thread_attach_t)sym("il2cpp_thread_attach");
  api.domain_get_name = (api_domain_get_name_t)sym("il2cpp_domain_get_name");
  api.class_from_name = (api_class_from_name_t)sym("il2cpp_class_from_name");
  api.class_get_method_from_name =
      (api_class_get_method_from_name_t)sym("il2cpp_class_get_method_from_name");
  api.method_get_name = (api_method_get_name_t)sym("il2cpp_method_get_name");
  api.class_get_name = (api_class_get_name_t)sym("il2cpp_class_get_name");
  api.class_get_namespace = (api_class_get_namespace_t)sym("il2cpp_class_get_namespace");
  api.method_get_param_count = (api_method_get_param_count_t)sym("il2cpp_method_get_param_count");
  api.method_get_token = (api_method_get_token_t)sym("il2cpp_method_get_token");
  api.object_get_size = (api_object_get_size_t)sym("il2cpp_object_get_size");
  api.object_new = (api_object_new_t)sym("il2cpp_object_new");
  api.runtime_invoke = (api_runtime_invoke_t)sym("il2cpp_runtime_invoke");
  api.string_new = (api_string_new_t)sym("il2cpp_string_new");
  api.string_chars = (api_string_chars_t)sym("il2cpp_string_chars");
  api.string_length = (api_string_length_t)sym("il2cpp_string_length");
  api.class_from_object = (api_class_from_il2cpp_object_t)sym("il2cpp_class_from_il2cpp_object");
  api.set_commandline_arguments =
      (api_set_commandline_arguments_t)sym("il2cpp_set_commandline_arguments");
  api.add_internal_call = (api_add_internal_call_t)sym("il2cpp_add_internal_call");
  api.print_exception = (api_print_exception_t)sym("il2cpp_print_unhandled_exception");
  api.get_corlib = (api_get_corlib_t)sym("il2cpp_get_corlib");
  api.image_get_name = (api_image_get_name_t)sym("il2cpp_image_get_name");
  api.domain_get_assemblies = (api_domain_get_assemblies_t)sym("il2cpp_domain_get_assemblies");
  api.assembly_get_image = (api_assembly_get_image_t)sym("il2cpp_assembly_get_image");
  api.object_unbox = (api_object_unbox_t)sym("il2cpp_object_unbox");
  api.object_get_class = (api_object_get_class_t)sym("il2cpp_object_get_class");
  api.class_get_methods = (api_class_get_methods_t)sym("il2cpp_class_get_methods");
  api.method_get_param_name = (api_method_get_param_name_t)sym("il2cpp_method_get_param_name");
  api.method_get_param = (api_method_get_param_t)sym("il2cpp_method_get_param");
  api.method_get_return_type = (api_method_get_return_type_t)sym("il2cpp_method_get_return_type");
  api.type_get_type = (api_type_get_type_t)sym("il2cpp_type_get_type");
}

/* "mscorlib.dll" and "mscorlib" name the same image. */
static int same_image_name(const char *left, const char *right) {
  size_t ln = strlen(left), rn = strlen(right);
  if (ln > 4 && strcasecmp(left + ln - 4, ".dll") == 0) ln -= 4;
  if (rn > 4 && strcasecmp(right + rn - 4, ".dll") == 0) rn -= 4;
  if (ln != rn) return 0;
  return strncasecmp(left, right, ln) == 0;
}

static void *image_for(const char *wanted) {
  if (api.get_corlib && api.image_get_name) {
    void *base_image = api.get_corlib();
    const char *base_name = base_image ? api.image_get_name(base_image) : NULL;
    if (base_image && (!wanted || !wanted[0] || (base_name && same_image_name(base_name, wanted))))
      return base_image;
  }
  if (!api.domain || !api.domain_get_assemblies || !api.assembly_get_image || !api.image_get_name)
    return NULL;
  size_t count = 0;
  void **assemblies = (void **)api.domain_get_assemblies(api.domain, &count);
  ev_num("assembly_count", (long long)count);
  if (!assemblies) return NULL;
  for (size_t i = 0; i < count; i++) {
    void *candidate = api.assembly_get_image(assemblies[i]);
    const char *name = candidate ? api.image_get_name(candidate) : NULL;
    if (name && wanted && same_image_name(name, wanted)) return candidate;
  }
  return NULL;
}

static int init_runtime(const char *why) {
  g_phase = "il2cpp_init";
  if (api.init_done) return api.domain != NULL;
  if (!api.init || !api.domain_get) {
    ev_str("init_error", "il2cpp_init or il2cpp_domain_get not exported");
    return 0;
  }
  if (cfg.skip_init) {
    note("init skipped (%s): calling uninitialised", why);
    ev_num("init_skipped", 1);
    api.domain = api.domain_get();
    ev_ptr("domain", api.domain);
    return 1;
  }
  if (api.set_data_dir && cfg.data_dir) {
    api.set_data_dir(cfg.data_dir);
    ev_str("data_dir", cfg.data_dir);
  }
  if (api.set_commandline_arguments) {
    static const char *given[] = {"Megabonk", "-batchmode", "-nographics"};
    static const char *appdata[] = {""};
    api.set_commandline_arguments(3, given, appdata);
    ev_num("commandline_set", 1);
  }
  api.init("Megabonk");
  api.init_done = 1;
  api.domain = api.domain_get();
  ev_ptr("domain", api.domain);
  note("il2cpp_init done (%s) domain=%p", why, api.domain);
  if (api.domain && api.thread_attach) api.thread_attach(api.domain);
  if (api.domain && api.domain_get_name) {
    const char *name = api.domain_get_name(api.domain);
    ev_str("domain_name", name);
    note("domain name=%s", name ? name : "(null)");
  }
  if (api.get_corlib) {
    void *image = api.get_corlib();
    ev_ptr("image_corlib", image);
    if (image && api.image_get_name) {
      const char *name = api.image_get_name(image);
      ev_str("image_corlib_name", name);
      note("corlib image=%p name=%s", image, name ? name : "(null)");
    }
  }
  return api.domain != NULL;
}

/* ----------------------------------------------------------- invocation */

typedef union ArgSlot {
  int32_t i;
  float f;
} ArgSlot;

static void *make_arg(size_t index, ArgSlot *scratch) {
  const char *kind = index < cfg.arg_count ? cfg.arg_kinds[index] : "s";
  const char *text = index < cfg.arg_count ? cfg.arg_values[index] : "";
  if (strcmp(kind, "i") == 0) {
    scratch->i = (int32_t)strtol(text, NULL, 10);
    return scratch;
  }
  if (strcmp(kind, "b") == 0) {
    scratch->i = (strcmp(text, "true") == 0 || strcmp(text, "1") == 0) ? 1 : 0;
    return scratch;
  }
  if (strcmp(kind, "f") == 0) {
    scratch->f = strtof(text, NULL);
    return scratch;
  }
  if (api.string_new) {
    Il2CppString *value = api.string_new(text);
    return (void *)value;
  }
  return NULL;
}

typedef union ValueSnap {
  uint8_t bytes[16];
  int32_t i;
  float f;
  void *p;
} ValueSnap;

/* il2cpp_runtime_invoke returns a pointer into its own frame, so the value has to be
   copied before anything else can run on that stack. */
static void *invoke_snapshot(MethodInfo method, void **params, Il2CppObject **exception,
                             ValueSnap *snap) {
  if (cfg.arg_count > 0)
    ev_num("param0_value", params[0] ? (long long)*(int32_t *)params[0] : -3735928559LL);
  Il2CppObject *returned = api.runtime_invoke(method, NULL, params, exception);
  Il2CppObject *boxed = returned;
  ev_ptr("ret_ptr", returned);
  if (returned)
    ev_hex("ret_bytes", (const unsigned char *)returned, 48);
  if (boxed && api.object_get_class && api.class_get_name) {
    Il2CppClass boxed_class = api.object_get_class(boxed);
    const char *boxed_name = boxed_class ? api.class_get_name(boxed_class) : NULL;
    ev_str("ret_class", boxed_name);
  }
  if (boxed && api.object_unbox && strcmp(cfg.invoke_ret, "string") != 0) {
    void *payload = api.object_unbox(boxed);
    ev_ptr("ret_payload", payload);
    if (payload) boxed = (Il2CppObject *)payload;
  }
  if (boxed) {
    volatile uint64_t *words = (volatile uint64_t *)boxed;
    uint64_t low = words[0];
    uint64_t high = words[1];
    memcpy(snap->bytes, &low, sizeof(low));
    memcpy(snap->bytes + sizeof(low), &high, sizeof(high));
    ev_num("ret_at_0", (long long)(int32_t)low);
    ev_num("ret_at_8", (long long)(int32_t)high);
    volatile uint64_t *further = (volatile uint64_t *)((char *)boxed + 16);
    ev_num("ret_at_16", (long long)(int32_t)further[0]);
  }
  return boxed;
}

static void snap_as_text(const ValueSnap *snap, const void *boxed, char *out, size_t out_len) {
  if (!boxed) {
    snprintf(out, out_len, "(null)");
    return;
  }
  if (strcmp(cfg.invoke_ret, "string") == 0) {
    Il2CppString *text = (Il2CppString *)boxed;
    if (api.string_chars) {
      /* il2cpp_string_chars hands back UTF-16 code units, not a C string. */
      const uint16_t *units = (const uint16_t *)api.string_chars(text);
      uint32_t length = api.string_length ? api.string_length(text) : 0;
      size_t limit = length ? length : 63;
      size_t written = 0;

      if (limit > 63)
        limit = 63;
      if (units) {
        while (written < limit && units[written]) {
          uint16_t unit = units[written];
          out[written] = (unit >= 0x20 && unit < 0x7f) ? (char)unit : '?';
          written++;
        }
        out[written] = '\0';
      } else {
        snprintf(out, out_len, "(null)");
      }
    } else {
      snprintf(out, out_len, "(no il2cpp_string_chars)");
    }
    return;
  }
  if (strcmp(cfg.invoke_ret, "float") == 0) {
    snprintf(out, out_len, "%g", (double)snap->f);
    return;
  }
  if (strcmp(cfg.invoke_ret, "bool") == 0) {
    snprintf(out, out_len, "%s", snap->i ? "true" : "false");
    return;
  }
  snprintf(out, out_len, "%d", snap->i);
}

static int values_match(const char *got) {
  if (!cfg.invoke_expected[0])
    return got[0] && strcmp(got, "(null)") != 0;
  if (strcmp(cfg.invoke_ret, "float") == 0) {
    double a = strtod(got, NULL), b = strtod(cfg.invoke_expected, NULL);
    double tol = 1e-4 * fmax(1.0, fabs(b));
    return fabs(a - b) <= tol;
  }
  if (strcmp(cfg.invoke_ret, "bool") == 0) {
    int a = strcmp(got, "true") == 0 || strcmp(got, "1") == 0;
    int b = strcmp(cfg.invoke_expected, "true") == 0 || strcmp(cfg.invoke_expected, "1") == 0;
    return a == b;
  }
  return strcmp(got, cfg.invoke_expected) == 0;
}

/* Splits "Ns.Cls" into namespace and class; a bare "Cls" gets an empty namespace. */
static void split_class(const char *input, char *ns, size_t ns_len, char *cls, size_t cls_len) {
  const char *dot = strrchr(input, '.');
  if (!dot) {
    ns[0] = '\0';
    snprintf(cls, cls_len, "%s", input);
    return;
  }
  snprintf(ns, ns_len, "%.*s", (int)(dot - input), input);
  snprintf(cls, cls_len, "%s", dot + 1);
}

static int type_enum_for(const char *name) {
  static const struct {
    const char *name;
    int value;
  } table[] = {
      {"void", 1},     {"bool", 2},    {"char", 3},   {"i1", 4},   {"u1", 5},
      {"i2", 6},      {"u2", 7},      {"int", 8},    {"uint", 9}, {"i8", 10},
      {"long", 10},   {"u8", 11},     {"f4", 12},    {"float", 12}, {"f8", 13},
      {"double", 13}, {"string", 14}, {"object", 28}, {"valuetype", 17},
  };
  for (size_t i = 0; i < sizeof(table) / sizeof(table[0]); i++)
    if (strcasecmp(name, table[i].name) == 0) return table[i].value;
  return -1;
}

static const char *type_kind_name(int value) {
  switch (value) {
  case 1: return "void";
  case 2: return "bool";
  case 3: return "char";
  case 8: return "int";
  case 10: return "long";
  case 12: return "float";
  case 13: return "double";
  case 14: return "string";
  default: return "?";
  }
}

static MethodInfo lookup_method(Il2CppClass *class_out, char *label, size_t label_len) {
  g_phase = "method lookup";
  char ns[192], cls[192];
  split_class(cfg.invoke_class, ns, sizeof(ns), cls, sizeof(cls));
  void *image = image_for(cfg.invoke_image);
  if (!image) {
    note("no image for %s", cfg.invoke_image[0] ? cfg.invoke_image : "(corlib)");
    ev_str("lookup_error", "image not found");
    return NULL;
  }
  if (api.image_get_name) ev_str("image", api.image_get_name(image));
  /* a NULL namespace faults inside metadata lookup: global-namespace types store "" */
  Il2CppClass klass = api.class_from_name(image, ns, cls);
  if (!klass) {
    note("class_from_name(%s, %s) = NULL", ns, cls);
    ev_str("lookup_error", "class not found");
    return NULL;
  }
  if (class_out) *class_out = klass;
  if (label) snprintf(label, label_len, "%s::%s", cfg.invoke_class, cfg.invoke_method);
  ev_ptr("class", klass);
  MethodInfo method = NULL;
  if (api.class_get_methods) {
    /* Name and arity alone pick the wrong overload: Math::Abs has int, long, float
       and double forms, so compare every candidate's parameter and return types. */
    void *iter = NULL;
    int scanned = 0, named = 0;
    MethodInfo fallback = NULL;
    void *candidate;
    while ((candidate = api.class_get_methods(klass, &iter)) != NULL) {
      scanned++;
      if (!api.method_get_name || strcmp(api.method_get_name(candidate), cfg.invoke_method) != 0)
        continue;
      named++;
      if (api.method_get_param_count &&
          (int)api.method_get_param_count(candidate) != (int)cfg.arg_count)
        continue;
      if (!fallback) fallback = candidate;
      int matches = 1;
      for (size_t i = 0; i < cfg.arg_count && matches; i++) {
        int want = type_enum_for(i < cfg.type_count ? cfg.arg_types[i] : "");
        if (want < 0 || !api.method_get_param || !api.type_get_type) break;
        void *param = api.method_get_param(candidate, (uint32_t)i);
        if (!param) break;
        if (api.type_get_type(param) != want) matches = 0;
      }
      if (matches && api.method_get_return_type && api.type_get_type) {
        void *ret_type = api.method_get_return_type(candidate);
        int want = type_enum_for(cfg.invoke_ret);
        if (ret_type && want >= 0 && api.type_get_type(ret_type) != want) matches = 0;
      }
      if (matches) {
        method = candidate;
        break;
      }
    }
    ev_num("methods_scanned", scanned);
    ev_num("methods_named", named);
    if (!method && fallback && cfg.type_count == 0) method = fallback;
    if (!method) {
      note("no %s overload matches the requested signature (%d named, %d scanned)",
           cfg.invoke_method, named, scanned);
      ev_str("lookup_error", "no overload matches the requested types");
      return NULL;
    }
  } else {
    method = api.class_get_method_from_name(klass, cfg.invoke_method, (int)cfg.arg_count);
    if (!method) {
      note("class_get_method_from_name(%s, %s, %zu) = NULL", cls, cfg.invoke_method, cfg.arg_count);
      ev_str("lookup_error", "method not found (IL2CPP pruning?)");
      return NULL;
    }
  }
  ev_ptr("method", method);
  if (api.method_get_name) ev_str("method_name", api.method_get_name(method));
  if (api.method_get_param_count)
    ev_num("param_count", (long long)api.method_get_param_count(method));
  if (api.method_get_token) ev_num("token", (long long)api.method_get_token(method));
  if (api.method_get_return_type && api.type_get_type) {
    void *ret_type = api.method_get_return_type(method);
    ev_str("return_type", ret_type ? type_kind_name(api.type_get_type(ret_type)) : "?");
  }
  for (size_t i = 0; i < cfg.arg_count && api.method_get_param && api.type_get_type; i++) {
    void *param = api.method_get_param(method, (uint32_t)i);
    char key[32], text[32];
    snprintf(key, sizeof(key), "param%zu_type", i);
    snprintf(text, sizeof(text), "%s", param ? type_kind_name(api.type_get_type(param)) : "?");
    ev_str(key, text);
  }
  note("method %s = %p name=%s", label ? label : "?", method,
       (api.method_get_name && api.method_get_name(method)) ? api.method_get_name(method) : "?");
  return method;
}

/* Calls the candidate through il2cpp_runtime_invoke; writes the value and returns 1. */
static int invoke_candidate(void **method_slot, char *got_out, size_t got_len, const char **why) {
  MethodInfo method = method_slot && *method_slot ? *method_slot : lookup_method(NULL, NULL, 0);
  if (!method) {
    *why = "method lookup failed";
    return 0;
  }
  if (method_slot) *method_slot = method;
  ArgSlot scratch[8];
  void *params[8];
  for (size_t i = 0; i < cfg.arg_count; i++) params[i] = make_arg(i, &scratch[i]);
  Il2CppObject *exception = NULL;
  ValueSnap snap;
  memset(&snap, 0, sizeof(snap));
  Il2CppObject *boxed = invoke_snapshot(method, cfg.arg_count ? params : NULL, &exception, &snap);
  if (exception) {
    note("runtime_invoke(%s::%s) threw", cfg.invoke_class, cfg.invoke_method);
    if (api.print_exception) api.print_exception(exception);
    *why = "invoke threw";
    return 0;
  }
  if (!boxed) {
    *why = "invoke returned no value";
    return 0;
  }
  snap_as_text(&snap, boxed, got_out, got_len);
  ev_str("invoke_image", cfg.invoke_image);
  ev_str("returned", got_out);
  ev_str("expected", cfg.invoke_expected);
  note("runtime_invoke(%s::%s) => %s (expected %s)", cfg.invoke_class, cfg.invoke_method, got_out,
       cfg.invoke_expected);
  *why = NULL;
  return 1;
}

/* ------------------------------------------------------------------ legs */

static int leg1(void) {
  g_phase = "leg1";
  scan_loaded_images();
  void *domain_get_sym = sym("il2cpp_domain_get");
  void *method_get_name_sym = sym("il2cpp_method_get_name");
  ev_ptr("sym_il2cpp_domain_get", domain_get_sym);
  ev_ptr("sym_il2cpp_method_get_name", method_get_name_sym);
  note("dlsym il2cpp_domain_get=%p il2cpp_method_get_name=%p", domain_get_sym,
       method_get_name_sym);
  if (!domain_get_sym || !method_get_name_sym) {
    ev_str("dlerror", dlerror());
    emit(0, "required exports missing");
    return 1;
  }
  Dl_info info;
  if (dladdr(domain_get_sym, &info)) {
    ev_str("runtime_path", info.dli_fname);
    ev_ptr("runtime_base", info.dli_fbase);
    ev_ptr("runtime_saddr", info.dli_saddr);
    note("dladdr dli_fname=%s dli_fbase=%p dli_saddr=%p", info.dli_fname ? info.dli_fname : "?",
         info.dli_fbase, info.dli_saddr);
  }
  size_t exported = 0;
  /* count the il2cpp_* exports the host could resolve, as breadth evidence */
  static const char *counted[] = {
      "il2cpp_init",        "il2cpp_domain_get",         "il2cpp_domain_get_name",
      "il2cpp_thread_attach", "il2cpp_class_from_name",  "il2cpp_class_get_method_from_name",
      "il2cpp_method_get_name", "il2cpp_runtime_invoke", "il2cpp_add_internal_call",
      "il2cpp_string_new",  "il2cpp_object_get_size",    "il2cpp_get_corlib",
  };
  for (size_t i = 0; i < sizeof(counted) / sizeof(counted[0]); i++)
    if (sym(counted[i])) exported++;
  ev_num("exports_resolved", (long long)exported);

  if (!init_runtime("leg1")) {
    emit(0, api.init_done ? "no domain after il2cpp_init" : "il2cpp_init unavailable");
    return 1;
  }
  if (!api.domain) {
    emit(0, "il2cpp_domain_get returned NULL");
    return 1;
  }
  int values = 0;
  if (api.get_corlib && api.image_get_name) {
    void *image = api.get_corlib();
    const char *name = image ? api.image_get_name(image) : NULL;
    if (name && name[0]) {
      ev_str("corlib_image", name);
      note("il2cpp_image_get_name(corlib) = \"%s\"", name);
      values++;
    }
  }
  cfg.invoke_image = "mscorlib.dll";
  cfg.invoke_class = "System.Math";
  cfg.invoke_method = "Abs";
  cfg.arg_count = 1;
  cfg.arg_kinds[0] = "i";
  cfg.arg_values[0] = "-7";
  Il2CppClass klass = NULL;
  MethodInfo method = lookup_method(&klass, NULL, 0);
  if (klass && api.class_get_name && api.class_get_namespace) {
    const char *cls = api.class_get_name(klass);
    const char *ns = api.class_get_namespace(klass);
    ev_str("class_name_value", cls);
    note("il2cpp_class_get_name(%p) = \"%s.%s\"", klass, ns ? ns : "", cls ? cls : "(null)");
    values++;
  }
  if (klass && api.object_new) {
    Il2CppObject *instance = api.object_new(klass);
    if (instance) {
      ev_ptr("object", instance);
      if (api.object_get_size) {
        uint32_t size = api.object_get_size(instance);
        ev_num("object_size", (long long)size);
        note("il2cpp_object_get_size(new System.Math) = %u", size);
        values++;
      }
    }
  }
  if (method && api.method_get_name) {
    const char *name = api.method_get_name(method);
    ev_str("method_name_value", name);
    note("il2cpp_method_get_name(%p) = \"%s\"", method, name ? name : "(null)");
    values++;
  }
  if (values >= 2) {
    emit(1, NULL);
  } else {
    emit(0, "fewer than two exported functions returned real values");
  }
  return 0;
}

static int leg2(void) {
  g_phase = "leg2";
  scan_loaded_images();
  if (!api.runtime_invoke || !api.class_from_name) {
    emit(0, "il2cpp_runtime_invoke or il2cpp_class_from_name not exported");
    return 1;
  }
  if (!init_runtime("leg2")) {
    emit(0, "runtime not initialised");
    return 1;
  }
  char got[256];
  const char *why = NULL;
  if (!invoke_candidate(NULL, got, sizeof(got), &why)) {
    emit(0, why ? why : "invoke failed");
    return 1;
  }
  if (!values_match(got)) {
    note("value mismatch: got %s want %s", got, cfg.invoke_expected);
    emit(0, "returned value does not match the expected value");
    return 1;
  }
  emit(1, NULL);
  return 0;
}

/* -------------------------------------------------------------- detouring */

#if defined(__x86_64__)

static volatile uint64_t hook_calls;
static unsigned char *tramp;
static unsigned char hook_stub[ABS_JUMP_LEN];
static unsigned char saved_bytes[ABS_JUMP_LEN];
static unsigned char *patched_slot;
static int patched;

static void emit_abs_jump(unsigned char *dst, void *to) {
  dst[0] = 0xFF;
  dst[1] = 0x25;
  dst[2] = dst[3] = dst[4] = dst[5] = 0x00;
  memcpy(dst + 6, &to, sizeof(to));
}

static void *call_trampoline(void *a0, void *a1, void *a2, void *a3) {
  if (!tramp) return NULL;
  void *(*fn)(void *, void *, void *, void *) = (void *(*)(void *, void *, void *, void *))tramp;
  return fn(a0, a1, a2, a3);
}

typedef void *(*hook0_t)(void);

static void *hook_zero(void) {
  hook_calls++;
  return call_trampoline(NULL, NULL, NULL, NULL);
}
static void *hook_one(void *a) {
  hook_calls++;
  return call_trampoline(a, NULL, NULL, NULL);
}
static void *hook_two(void *a, void *b) {
  hook_calls++;
  return call_trampoline(a, b, NULL, NULL);
}
static void *hook_three(void *a, void *b, void *c) {
  hook_calls++;
  return call_trampoline(a, b, c, NULL);
}
static void *hook_four(void *a, void *b, void **c, void **d) {
  hook_calls++;
  return call_trampoline(a, b, (void *)c, (void *)d);
}

static int alloc_exec_page(size_t size, void **out) {
  struct {
    const char *name;
    int prot;
    int flags_extra;
  } variants[] = {
      {"rw", PROT_READ | PROT_WRITE, 0},
      {"rwx", PROT_READ | PROT_WRITE | PROT_EXEC, 0},
      {"rwx_jit", PROT_READ | PROT_WRITE | PROT_EXEC, 0x20 /* MAP_JIT */},
  };
  for (size_t i = 0; i < sizeof(variants) / sizeof(variants[0]); i++) {
    int flags = MAP_PRIVATE | MAP_ANONYMOUS;
#if defined(MAP_JIT)
    flags |= variants[i].flags_extra;
#endif
    void *page = mmap(NULL, size, variants[i].prot, flags, -1, 0);
    if (page == MAP_FAILED) {
      note("mmap %s failed: %s", variants[i].name, strerror(errno));
      continue;
    }
    if (variants[i].prot != (PROT_READ | PROT_WRITE)) {
      *out = page;
      ev_str("alloc_mode", variants[i].name);
      ev_ptr("alloc_addr", page);
      note("exec page %s at %p", variants[i].name, page);
      return (int)i;
    }
    /* W^X path: fill while writable, then make executable */
    *out = page;
    ev_str("alloc_mode", "rw_then_rx");
    ev_ptr("alloc_addr", page);
    note("exec page rw at %p, upgrading", page);
    return (int)i;
  }
  return -1;
}

static int finalize_exec_page(void *page, size_t size, int mode) {
  static const int prots[] = {PROT_READ | PROT_WRITE, PROT_READ | PROT_WRITE | PROT_EXEC,
                             PROT_READ | PROT_WRITE | PROT_EXEC};
  if (mode == 0) {
    if (mprotect(page, size, prots[1]) != 0) {
      note("mprotect rx after write failed: %s", strerror(errno));
      return 0;
    }
  }
  __builtin___clear_cache((char *)page, (char *)page + size);
  return 1;
}

static size_t probe_page_size(void) {
#if defined(__APPLE__)
  return (size_t)vm_kernel_page_size;
#else
  return (size_t)sysconf(_SC_PAGESIZE);
#endif
}

static int page_span(void *addr, size_t size, uintptr_t *base, size_t *span) {
  size_t page = probe_page_size();
  if (!page || (page & (page - 1))) return 0;
  uintptr_t start = (uintptr_t)addr & ~(page - 1);
  uintptr_t end = (uintptr_t)addr + size;
  *base = start;
  *span = ((end - start + page - 1) / page) * page;
  return 1;
}

static int writable(void *addr, size_t size) {
  uintptr_t base;
  size_t span;
  if (!page_span(addr, size, &base, &span)) return 0;
#if defined(__APPLE__)
  kern_return_t kr = vm_protect(mach_task_self(), (vm_address_t)base, span, FALSE,
                                VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY);
  if (kr != KERN_SUCCESS) note("vm_protect rw kr=%d (%s)", kr, mach_error_string(kr));
#endif
  if (mprotect((void *)base, span, PROT_READ | PROT_WRITE) != 0) {
    note("mprotect rw failed: %s", strerror(errno));
    return 0;
  }
  return 1;
}

static int restore_ro(void *addr, size_t size) {
  uintptr_t base;
  size_t span;
  if (!page_span(addr, size, &base, &span)) return 0;
  if (mprotect((void *)base, span, PROT_READ | PROT_EXEC) != 0) {
    note("mprotect r-x failed: %s", strerror(errno));
    return 0;
  }
  __builtin___clear_cache((char *)addr, (char *)addr + size);
  return 1;
}

static void call_invoke(unsigned char *entry, MethodInfo method, char *into, size_t into_len) {
  ArgSlot scratch[8];
  void *params[8];
  for (size_t i = 0; i < cfg.arg_count; i++) params[i] = make_arg(i, &scratch[i]);
  Il2CppObject *exception = NULL;
  api_runtime_invoke_t fn = (api_runtime_invoke_t)entry;
  Il2CppObject *boxed = fn(method, NULL, cfg.arg_count ? params : NULL, &exception);
  if (boxed && api.object_unbox && strcmp(cfg.invoke_ret, "string") != 0) {
    void *payload = api.object_unbox(boxed);
    if (payload) boxed = (Il2CppObject *)payload;
  }
  ValueSnap snap;
  memset(&snap, 0, sizeof(snap));
  if (boxed) {
    volatile uint64_t *words = (volatile uint64_t *)boxed;
    uint64_t low = words[0];
    uint64_t high = words[1];
    memcpy(snap.bytes, &low, sizeof(low));
    memcpy(snap.bytes + sizeof(low), &high, sizeof(high));
  }
  if (!boxed || exception) {
    snprintf(into, into_len, "(no value)");
    return;
  }
  snap_as_text(&snap, boxed, into, into_len);
}

static int hook_arity(const char *symbol) {
  if (strcmp(symbol, "il2cpp_domain_get") == 0) return 0;
  if (strcmp(symbol, "il2cpp_method_get_name") == 0) return 1;
  if (strcmp(symbol, "il2cpp_class_get_name") == 0) return 1;
  if (strcmp(symbol, "il2cpp_class_get_method_from_name") == 0) return 3;
  if (strcmp(symbol, "il2cpp_runtime_invoke") == 0) return 4;
  return 1;
}

static void *hook_for_arity(int arity) {
  switch (arity) {
  case 0: return (void *)hook_zero;
  case 2: return (void *)hook_two;
  case 3: return (void *)hook_three;
  case 4: return (void *)hook_four;
  default: return (void *)hook_one;
  }
}

static int leg3(void) {
  g_phase = "leg3";
  scan_loaded_images();
  if (!cfg.hook || !cfg.hook[0]) {
    emit(0, "no hook target");
    return 1;
  }
  if (!init_runtime("leg3")) {
    emit(0, "runtime not initialised");
    return 1;
  }
  ev_str("hook", cfg.hook);
  snprintf(g_hook_name, sizeof(g_hook_name), "%s", cfg.hook);
  unsigned char *slot = (unsigned char *)sym(cfg.hook);
  if (!slot) {
    emit(0, "hook target not exported");
    return 1;
  }
  ev_ptr("slot", slot);
  ev_hex("slot_bytes", slot, 16);
  int shape_ok = memcmp(slot, "\x55\x48\x89\xE5", 4) == 0 && (slot[4] == 0x58 || slot[4] == 0x5D) &&
                 slot[5] == 0xE9;
  ev_num("thunk_shape", shape_ok ? 1 : 0);
  if (!shape_ok) {
    note("unexpected export shape, first bytes=%02x %02x %02x %02x %02x %02x", slot[0], slot[1],
         slot[2], slot[3], slot[4], slot[5]);
    emit(0, "export is not the expected thunk shape");
    return 1;
  }
  int32_t rel32;
  memcpy(&rel32, slot + 6, sizeof(rel32));
  unsigned char *impl = slot + 10 + rel32;
  ev_ptr("impl", impl);
  note("thunk impl=%p (rel32=%d)", impl, rel32);

  void *page = NULL;
  int mode = alloc_exec_page(SPAN_BYTES, &page);
  if (mode < 0) {
    emit(0, "no executable memory");
    return 1;
  }
  memcpy(page, slot, THUNK_PROLOGUE_LEN);
  emit_abs_jump((unsigned char *)page + THUNK_PROLOGUE_LEN, impl);
  if (!finalize_exec_page(page, SPAN_BYTES, mode)) {
    emit(0, "trampoline page not executable");
    return 1;
  }
  tramp = (unsigned char *)page;
  ev_ptr("trampoline", tramp);

  int arity = hook_arity(cfg.hook);
  void *hook = hook_for_arity(arity);
  ev_ptr("hook_addr", hook);
  ev_num("hook_arity", arity);

  MethodInfo method = NULL;
  Il2CppClass klass = NULL;
  char label[256] = "";
  int uses_invoke = strcmp(cfg.hook, "il2cpp_runtime_invoke") == 0;
  int uses_lookup = strcmp(cfg.hook, "il2cpp_class_get_method_from_name") == 0;
  int uses_name = strcmp(cfg.hook, "il2cpp_method_get_name") == 0;
  char baseline[256] = "", during[256] = "", restored[256] = "";

  if (uses_invoke || uses_lookup || uses_name) {
    method = lookup_method(&klass, label, sizeof(label));
    if (!method) {
      emit(0, "method lookup failed for the verification call");
      return 1;
    }
  }

  /* The baseline goes through the copied prologue, so the exported slot stays
     unexecuted until it is patched: Rosetta has not translated it yet. */
  for (int stage = 0; stage < 3; stage++) {
    unsigned char *entry;
    const char *name_of_stage;
    if (stage == 0) {
      entry = tramp;
      name_of_stage = "baseline";
      ev_str("baseline_via", "trampoline");
    } else if (stage == 1) {
      if (!writable(slot, ABS_JUMP_LEN)) {
        emit(0, "text page not writable");
        return 1;
      }
      emit_abs_jump(hook_stub, hook);
      memcpy(saved_bytes, slot, ABS_JUMP_LEN);
      memcpy(slot, hook_stub, ABS_JUMP_LEN);
      /* the page is read/write while patched bytes are written: it has to be
         executable again before the export is called through */
      restore_ro(slot, ABS_JUMP_LEN);
      ev_num("patch_readback_ok", memcmp(slot, hook_stub, ABS_JUMP_LEN) == 0 ? 1 : 0);
      ev_hex("patched_slot_bytes", slot, 16);
      patched = 1;
      patched_slot = slot;
      ev_num("patched", 1);
      note("patched %s with an absolute jump to %p", cfg.hook, hook);
      entry = slot;
      name_of_stage = "patched";
    } else {
      if (writable(slot, ABS_JUMP_LEN)) {
        memcpy(slot, saved_bytes, ABS_JUMP_LEN);
        restore_ro(slot, ABS_JUMP_LEN);
      }
      patched = 0;
      ev_num("patched", 0);
      note("restored %s", cfg.hook);
      entry = slot;
      name_of_stage = "restored";
    }

    char *into = stage == 0 ? baseline : (stage == 1 ? during : restored);
    g_phase = name_of_stage;
    if (uses_invoke) {
      call_invoke(entry, method, into, 256);
    } else if (uses_lookup) {
      MethodInfo found = ((api_class_get_method_from_name_t)entry)(klass, cfg.invoke_method,
                                                                   (int)cfg.arg_count);
      snprintf(into, 256, "0x%llx", (unsigned long long)(uintptr_t)found);
    } else if (uses_name) {
      const char *value = ((api_method_get_name_t)entry)(method);
      snprintf(into, 256, "%s", value ? value : "(null)");
    } else {
      void *value = ((hook0_t)entry)();
      snprintf(into, 256, "0x%llx", (unsigned long long)(uintptr_t)value);
    }
    note("%s %s -> %s", name_of_stage, cfg.hook, into);
  }

  ev_str("baseline_value", baseline);
  ev_str("patched_value", during);
  ev_str("restored_value", restored);
  ev_num("hook_calls", (long long)hook_calls);

  int consistent = strcmp(baseline, during) == 0 && strcmp(baseline, restored) == 0 &&
                   strcmp(baseline, "(no value)") != 0;
  if (hook_calls == 0) {
    emit(0, "the hook never fired");
    return 1;
  }
  if (!consistent) {
    emit(0, "the patched export returned a different value than the baseline");
    return 1;
  }
  emit(1, NULL);
  return 0;
}

#else /* not x86_64 */

static int leg3(void) {
  g_phase = "leg3";
  scan_loaded_images();
  ev_str("alloc_mode", "unavailable");
  emit(0, "leg3 needs x86_64 absolute-jump patching");
  return 1;
}

#endif

/* ------------------------------------------------------------------ main */

static int need_value(int argc, char **argv, int i, const char **slot) {
  if (i + 1 >= argc) {
    fprintf(stderr, "missing value for %s\n", argv[i]);
    exit(2);
  }
  *slot = argv[i + 1];
  return 2;
}

static void usage(void) {
  fprintf(stderr,
          "usage: host --dylib PATH [--data-dir DIR] --leg leg1|leg2|leg3\n"
          "            [--invoke-image I --invoke-class Ns.Cls --invoke-method M]\n"
          "            [--invoke-ret int|float|bool|string --invoke-expected V]\n"
          "            [--invoke-arg k:v ...] [--invoke-arg-type T ...] [--hook SYMBOL]\n"
          "            [--dlopen-mode auto|now|lazy|lazy_global] [--preload LIB ...] [--skip-init]\n");
}

int main(int argc, char **argv) {
  cfg.leg = "leg1";
  cfg.dlopen_mode = "auto";
  cfg.invoke_ret = "int";
  cfg.invoke_expected = "0";
  cfg.invoke_class = "System.Math";
  cfg.invoke_method = "Abs";
  cfg.invoke_image = "";
  for (size_t i = 0; i < 8; i++) {
    cfg.arg_kinds[i] = "s";
    cfg.arg_values[i] = "";
    cfg.arg_types[i] = "";
  }
  for (int i = 1; i < argc; i++) {
    const char *value;
    int used = 0;
    if (strcmp(argv[i], "--dylib") == 0)
      used = need_value(argc, argv, i, &cfg.dylib);
    else if (strcmp(argv[i], "--data-dir") == 0)
      used = need_value(argc, argv, i, &cfg.data_dir);
    else if (strcmp(argv[i], "--leg") == 0)
      used = need_value(argc, argv, i, &cfg.leg);
    else if (strcmp(argv[i], "--invoke-image") == 0)
      used = need_value(argc, argv, i, &cfg.invoke_image);
    else if (strcmp(argv[i], "--invoke-class") == 0)
      used = need_value(argc, argv, i, &cfg.invoke_class);
    else if (strcmp(argv[i], "--invoke-method") == 0)
      used = need_value(argc, argv, i, &cfg.invoke_method);
    else if (strcmp(argv[i], "--invoke-ret") == 0)
      used = need_value(argc, argv, i, &cfg.invoke_ret);
    else if (strcmp(argv[i], "--invoke-expected") == 0)
      used = need_value(argc, argv, i, &cfg.invoke_expected);
    else if (strcmp(argv[i], "--hook") == 0)
      used = need_value(argc, argv, i, &cfg.hook);
    else if (strcmp(argv[i], "--invoke-arg") == 0) {
      const char *token;
      used = need_value(argc, argv, i, &token);
      if (cfg.arg_count < 8) {
        const char *colon = strchr(token, ':');
        if (!colon) {
          fprintf(stderr, "bad --invoke-arg %s\n", token);
          return 2;
        }
        if (colon - token != 1) {
          fprintf(stderr, "bad --invoke-arg %s (want k:v)\n", token);
          return 2;
        }
        char kind[2] = {token[0], '\0'};
        cfg.arg_kinds[cfg.arg_count] = strdup(kind);
        cfg.arg_values[cfg.arg_count] = colon + 1;
        cfg.arg_count++;
      }
    } else if (strcmp(argv[i], "--invoke-arg-type") == 0) {
      const char *token;
      used = need_value(argc, argv, i, &token);
      if (cfg.type_count < 8) cfg.arg_types[cfg.type_count++] = token;
    } else if (strcmp(argv[i], "--dlopen-mode") == 0) {
      used = need_value(argc, argv, i, &cfg.dlopen_mode);
    } else if (strcmp(argv[i], "--preload") == 0) {
      const char *token;
      used = need_value(argc, argv, i, &token);
      if (cfg.preload_count < 4) cfg.preloads[cfg.preload_count++] = token;
    } else if (strcmp(argv[i], "--skip-init") == 0) {
      cfg.skip_init = 1;
    } else {
      usage();
      return 2;
    }
    (void)value;
    i += used - 1;
  }
  if (!cfg.dylib) {
    usage();
    return 2;
  }

  for (size_t i = 0; i < cfg.arg_count; i++) {
    char key[24], text[64];
    snprintf(key, sizeof(key), "arg%zu_kind", i);
    snprintf(text, sizeof(text), "%s=%s", cfg.arg_kinds[i], cfg.arg_values[i]);
    ev_str(key, text);
  }
#if defined(__APPLE__)
  int translated = 0;
  size_t translated_len = sizeof(translated);
  if (sysctlbyname("sysctl.proc_translated", &translated, &translated_len, NULL, 0) != 0) {
    translated = -1;
  }
  ev_num("proc_translated", translated);
#endif
  ev_num("pid", (long long)getpid());
  ev_str("leg", cfg.leg);
  ev_str("arch",
#if defined(__x86_64__)
         "x86_64"
#elif defined(__aarch64__)
         "arm64"
#else
         "unknown"
#endif
  );
#if defined(__APPLE__)
  ev_str("platform", "macos");
#else
  ev_str("platform", "linux");
#endif

  install_fault_guard();
  g_phase = "preload";
  for (size_t i = 0; i < cfg.preload_count; i++) {
    void *lib = dlopen(cfg.preloads[i], RTLD_LAZY | RTLD_GLOBAL);
    char key[32], text[200];
    snprintf(key, sizeof(key), "preload%zu", i);
    if (lib) {
      snprintf(text, sizeof(text), "%s", cfg.preloads[i]);
    } else {
      snprintf(text, sizeof(text), "%s: %s", cfg.preloads[i], dlerror());
      note("preload %s failed: %s", cfg.preloads[i], dlerror());
    }
    ev_str(key, text);
  }
  g_phase = "dlopen";
  struct {
    const char *name;
    int flags;
  } modes[] = {{"now", RTLD_NOW | RTLD_LOCAL},
               {"lazy", RTLD_LAZY | RTLD_LOCAL},
               {"lazy_global", RTLD_LAZY | RTLD_GLOBAL}};
  int requested = -1;
  if (strcmp(cfg.dlopen_mode, "lazy") == 0) requested = 1;
  else if (strcmp(cfg.dlopen_mode, "lazy_global") == 0) requested = 2;
  else if (strcmp(cfg.dlopen_mode, "now") == 0) requested = 0;
  int attempts = 0;
  for (size_t i = 0; i < sizeof(modes) / sizeof(modes[0]) && !api.handle; i++) {
    if (requested >= 0 && (int)i != requested) continue;
    api.handle = dlopen(cfg.dylib, modes[i].flags);
    attempts++;
    if (api.handle) {
      ev_str("dlopen_mode", modes[i].name);
      ev_num("dlopen_attempts", attempts);
    } else {
      char key[48], text[320];
      snprintf(key, sizeof(key), "dlopen_%s_error", modes[i].name);
      snprintf(text, sizeof(text), "%.280s", dlerror());
      ev_str(key, text);
      note("dlopen %s (%s) failed: %s", cfg.dylib, modes[i].name, dlerror());
    }
  }
  if (!api.handle) {
    ev_str("dlopen_error", dlerror());
    ev_num("dlopen_attempts", attempts);
    scan_loaded_images();
    emit(0, "dlopen failed");
    return 1;
  }
  note("dlopen %s -> %p mode=%s", cfg.dylib, api.handle, cfg.dlopen_mode);
  resolve_api();
  size_t resolved = 0;
  void *slots[] = {(void *)api.init,        (void *)api.set_data_dir,
                   (void *)api.domain_get,  (void *)api.thread_attach,
                   (void *)api.domain_get_name, (void *)api.class_from_name,
                   (void *)api.class_get_method_from_name, (void *)api.method_get_name,
                   (void *)api.class_get_name, (void *)api.method_get_param_count,
                   (void *)api.object_get_size, (void *)api.object_new, (void *)api.runtime_invoke,
                   (void *)api.string_new,  (void *)api.add_internal_call};
  for (size_t i = 0; i < sizeof(slots) / sizeof(slots[0]); i++)
    if (slots[i]) resolved++;
  ev_num("exports_resolved", (long long)resolved);
  note("resolved %zu/%zu il2cpp exports", resolved, sizeof(slots) / sizeof(slots[0]));

  int rc;
  if (strcmp(cfg.leg, "leg1") == 0)
    rc = leg1();
  else if (strcmp(cfg.leg, "leg2") == 0)
    rc = leg2();
  else if (strcmp(cfg.leg, "leg3") == 0)
    rc = leg3();
  else {
    usage();
    return 2;
  }
  dlclose(api.handle);
  return rc;
}
