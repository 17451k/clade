cmake_minimum_required(VERSION 3.3)
project(interceptor)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# find_package( Threads REQUIRED )

add_library(data STATIC data.c)
add_library(which STATIC which.c)
add_library(env STATIC env.c)
add_library(interceptor SHARED interceptor.c)
target_link_libraries(data which env)
target_link_libraries(interceptor ${CMAKE_DL_LIBS} which data env)

add_executable(wrapper wrapper.c)
target_link_libraries(wrapper which data env)

set_target_properties(data which interceptor which env PROPERTIES C_STANDARD 11)
