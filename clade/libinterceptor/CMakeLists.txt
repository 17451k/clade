cmake_minimum_required(VERSION 3.5)
project(interceptor)

add_library(interceptor SHARED interceptor.c)

target_link_libraries(interceptor ${CMAKE_DL_LIBS})
