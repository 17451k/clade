cmake_minimum_required(VERSION 3.5)
project(interceptor)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_library(data STATIC data.c)
add_library(which STATIC which.c)
target_link_libraries(data which)
add_library(interceptor SHARED interceptor.c)
target_link_libraries(interceptor ${CMAKE_DL_LIBS} which data)

add_executable(wrapper wrapper.c)
target_link_libraries(wrapper which data)

add_custom_command(
        TARGET interceptor POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
                ${CMAKE_CURRENT_BINARY_DIR}/libinterceptor.*
                ${CMAKE_SOURCE_DIR})
add_custom_command(
        TARGET interceptor POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
                ${CMAKE_CURRENT_BINARY_DIR}/wrapper*
                ${CMAKE_SOURCE_DIR})
