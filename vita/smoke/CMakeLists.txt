cmake_minimum_required(VERSION 3.20)
set(CMAKE_TOOLCHAIN_FILE "$ENV{VITASDK}/share/vita.toolchain.cmake" CACHE FILEPATH "VitaSDK toolchain")
project(megabonk_vita_smoke C)
include("${VITASDK}/share/vita.cmake" REQUIRED)

add_executable(vita-smoke main.c)
set_target_properties(vita-smoke PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED YES)
target_compile_options(vita-smoke PRIVATE -Wall -Wextra -Werror)
target_link_libraries(vita-smoke PRIVATE SceCtrl_stub SceDisplay_stub ScePower_stub SceProcessmgr_stub SceSysmem_stub SceKernelModulemgr_stub)

vita_create_self(vita-smoke.self vita-smoke)
vita_create_vpk(megabonk-vita-smoke.vpk MBVK00001 vita-smoke.self
  VERSION 01.01
  NAME "Megabonk Vita Smoke"
  FILE "${CMAKE_CURRENT_BINARY_DIR}/sce_sys/icon0.png" sce_sys/icon0.png
  FILE "${CMAKE_CURRENT_BINARY_DIR}/sce_sys/livearea/contents/bg.png" sce_sys/livearea/contents/bg.png
  FILE "${CMAKE_CURRENT_BINARY_DIR}/sce_sys/livearea/contents/startup.png" sce_sys/livearea/contents/startup.png
  FILE "${CMAKE_CURRENT_SOURCE_DIR}/livearea.xml" sce_sys/livearea/contents/template.xml
)
