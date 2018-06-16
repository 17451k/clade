cmake_minimum_required(VERSION 3.5)
project(interceptor)

add_library(interceptor SHARED interceptor.c)

target_link_libraries(interceptor ${CMAKE_DL_LIBS})

add_custom_command(
        TARGET interceptor POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
                ${CMAKE_CURRENT_BINARY_DIR}/libinterceptor.*
                ${CMAKE_SOURCE_DIR})
