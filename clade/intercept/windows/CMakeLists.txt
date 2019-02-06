cmake_minimum_required(VERSION 3.3)

add_executable(debugger debugger.cpp)
add_library(client_win STATIC client.cpp)
target_link_libraries(debugger client_win)
