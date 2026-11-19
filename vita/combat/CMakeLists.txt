cmake_minimum_required(VERSION 3.20)
set(CMAKE_TOOLCHAIN_FILE "$ENV{VITASDK}/share/vita.toolchain.cmake" CACHE FILEPATH "VitaSDK toolchain")
project(megabonk_vita_combat C)
include("${VITASDK}/share/vita.cmake" REQUIRED)

add_executable(vita-combat main.c combat.c character.c render.c benchmark.c sweep.c)
set_target_properties(vita-combat PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED YES)
target_compile_options(vita-combat PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_options(vita-combat PRIVATE -Wl,--wrap=sceDisplaySetFrameBuf,--wrap=sceDisplayWaitVblankStart)
target_link_libraries(vita-combat PRIVATE vita2d SceDisplay_stub SceGxm_stub SceSysmodule_stub
  SceCtrl_stub ScePgf_stub ScePvf_stub SceCommonDialog_stub SceAppMgr_stub
  SceProcessmgr_stub SceSysmem_stub ScePower_stub freetype png jpeg z m)

vita_create_self(vita-combat.self vita-combat)
vita_create_vpk(megabonk-vita-combat.vpk MBVK00002 vita-combat.self
  VERSION 01.02
  NAME "Megabonk Vita Combat"
  FILE "${CMAKE_CURRENT_BINARY_DIR}/sce_sys/icon0.png" sce_sys/icon0.png
  FILE "${CMAKE_CURRENT_BINARY_DIR}/sce_sys/livearea/contents/bg.png" sce_sys/livearea/contents/bg.png
  FILE "${CMAKE_CURRENT_BINARY_DIR}/sce_sys/livearea/contents/startup.png" sce_sys/livearea/contents/startup.png
  FILE "${CMAKE_CURRENT_SOURCE_DIR}/livearea.xml" sce_sys/livearea/contents/template.xml
)
