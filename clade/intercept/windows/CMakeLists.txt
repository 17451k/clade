cmake_minimum_required(VERSION 3.3)

add_executable(debugger debugger.cpp)
add_library(client_win STATIC client.cpp)
target_link_libraries(debugger client_win)

if(MSVC)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
    add_compile_options(/O2)
endif()

set_target_properties(debugger client_win PROPERTIES CXX_STANDARD 11)
