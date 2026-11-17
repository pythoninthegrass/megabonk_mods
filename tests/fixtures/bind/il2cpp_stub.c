#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { void *body; } Method;
typedef struct { const char *ns; const char *name; } Class;
typedef struct { Class *klass; const char *message; } Exception;

static int body_marker;
static Method method = {&body_marker};
static Class system_class = {"System", "ThrowHelper"};
static Class thrown_class = {"System", "InvalidOperationException"};
static Exception thrown = {&thrown_class, "Nullable object must have a value."};
static int image_marker, domain_marker;

void il2cpp_init(const char *name) { (void)name; }
void *il2cpp_domain_get(void) { return &domain_marker; }
void *il2cpp_get_corlib(void) { return &image_marker; }
const char *il2cpp_image_get_name(void *image) { (void)image; return "mscorlib.dll"; }
void *il2cpp_class_from_name(void *image, const char *ns, const char *name) {
  (void)image; (void)ns; (void)name;
  return &system_class;
}
void *il2cpp_class_get_methods(void *klass, void **iter) {
  (void)klass;
  if (*iter) return NULL;
  *iter = &method;
  return &method;
}
const char *il2cpp_method_get_name(void *m) { (void)m; return "Throw"; }
uint32_t il2cpp_method_get_param_count(void *m) { (void)m; return 0; }
void *il2cpp_class_from_il2cpp_object(void *o) { return ((Exception *)o)->klass; }
void *il2cpp_object_get_class(void *o) { return ((Exception *)o)->klass; }
const char *il2cpp_class_get_name(void *k) { return ((Class *)k)->name; }
const char *il2cpp_class_get_namespace(void *k) { return ((Class *)k)->ns; }

void il2cpp_format_exception(void *ex, char *out, int size) {
  Exception *e = ex;
  snprintf(out, (size_t)size, "%s.%s: %s", e->klass->ns, e->klass->name, e->message);
}

void *il2cpp_runtime_invoke(void *m, void *obj, void **params, void **exc) {
  (void)m; (void)obj; (void)params;
  static Class int_class = {"System", "Int32"};
  static struct { Class *klass; const char *pad; int32_t value; } boxed = {&int_class, NULL, 7};
  if (getenv("STUB_THROW")) {
    *exc = &thrown;
    return NULL;
  }
  *exc = NULL;
  return &boxed;
}
