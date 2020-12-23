cmake_minimum_required(VERSION 3.3)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_compile_options(
    -Wall
    -Wextra
    -Wno-unused-parameter
    -O3
)

add_library(data STATIC data.c)
add_library(which STATIC which.c)
add_library(env STATIC env.c)
add_library(client STATIC client.c)
add_library(lock STATIC lock.c)
target_link_libraries(data which env client lock)

add_library(interceptor SHARED interceptor.c)
target_link_libraries(interceptor ${CMAKE_DL_LIBS} which data env client lock)

add_executable(wrapper wrapper.c)
target_link_libraries(wrapper which data env client lock)

set_target_properties(data which env interceptor wrapper lock PROPERTIES C_STANDARD 11)
