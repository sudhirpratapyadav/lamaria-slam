cmake_minimum_required(VERSION 3.16)
project(vi_ba CXX)
# Non-causal global visual-inertial bundle adjustment over a VIO run (lamaria-slam v4).
# Header-only deps come from Basalt's vcpkg tree; Ceres from the system (2.0).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(BASALT_TP ${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/basalt/thirdparty/vcpkg/packages)
find_package(Ceres REQUIRED)
add_executable(vi_ba vi_ba.cpp)
target_include_directories(vi_ba SYSTEM PRIVATE
  ${BASALT_TP}/eigen3_x64-linux/include/eigen3
  ${BASALT_TP}/sophus_x64-linux/include
  ${BASALT_TP}/basalt-headers_x64-linux/include
  ${BASALT_TP}/nlohmann-json_x64-linux/include
  ${BASALT_TP}/fmt_x64-linux/include)
target_compile_definitions(vi_ba PRIVATE SOPHUS_USE_BASIC_LOGGING SOPHUS_DISABLE_ENSURES EIGEN_DONT_PARALLELIZE)
target_compile_options(vi_ba PRIVATE -O3 -march=native -ffp-contract=off -Wall)
target_link_libraries(vi_ba PRIVATE Ceres::ceres)
