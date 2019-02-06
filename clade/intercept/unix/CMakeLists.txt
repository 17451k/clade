cmake_minimum_required(VERSION 3.3)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_library(data STATIC data.c)
add_library(which STATIC which.c)
add_library(env STATIC env.c)
add_library(client STATIC client.c)
target_link_libraries(data which env client)

add_library(interceptor SHARED interceptor.c)
target_link_libraries(interceptor ${CMAKE_DL_LIBS} which data env client)

add_executable(wrapper wrapper.c)
target_link_libraries(wrapper which data env client)

set_target_properties(data which env interceptor wrapper PROPERTIES C_STANDARD 11)
