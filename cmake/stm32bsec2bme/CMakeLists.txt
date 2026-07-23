cmake_minimum_required(VERSION 3.22)
# Enable CMake support for ASM and C languages
enable_language(C CXX ASM)
INCLUDE(../scope-share.cmake)
STM_SET_LIBNAME()

# Interface library for includes and symbols
add_library(${INTERFACE_NAME} INTERFACE)
target_include_directories(${INTERFACE_NAME} INTERFACE
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8
        ${PROJECT_ROOT_DIR}/Drivers/BSEC2
)

# Create STM32_Drivers static library
add_library(${LIBRARY_NAME}_Drivers OBJECT)
target_sources(${LIBRARY_NAME}_Drivers PRIVATE
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8/bme68xLibrary.cpp
        ${PROJECT_ROOT_DIR}/Drivers/BSEC2/bsec2.cpp
)
#target_link_libraries(${LIBRARY_NAME}_Driver PUBLIC stm32cubemx)


# Add STM32CubeMX generated application sources to the project
target_sources(${CMAKE_PROJECT_NAME} PRIVATE ${MX_Application_Src})

# Link directories setup
target_link_directories(${CMAKE_PROJECT_NAME} PRIVATE ${MX_LINK_DIRS})

# Add libraries to the project
target_link_libraries(${CMAKE_PROJECT_NAME} ${MX_LINK_LIBS})

# Add the map file to the list of files to be removed with 'clean' target
set_target_properties(${CMAKE_PROJECT_NAME} PROPERTIES ADDITIONAL_CLEAN_FILES ${CMAKE_PROJECT_NAME}.map)

# Validate that STM32CubeMX code is compatible with C standard
if((CMAKE_C_STANDARD EQUAL 90) OR (CMAKE_C_STANDARD EQUAL 99))
    message(ERROR "Generated code requires C11 or higher")
endif()
