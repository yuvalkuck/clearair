CMAKE_MINIMUM_REQUIRED(VERSION 3.22)
# Enable CMake support for ASM and C languages
ENABLE_LANGUAGE(C ASM)
INCLUDE(../scope-share.cmake)
STM_SET_LIBNAME()

# Interface library for includes and symbols
ADD_LIBRARY(${INTERFACE_NAME} INTERFACE)
TARGET_INCLUDE_DIRECTORIES(${INTERFACE_NAME} INTERFACE
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8
        ${PROJECT_ROOT_DIR}/Drivers/BSEC2
)

# Create STM32_Drivers static library
ADD_LIBRARY(${LIBRARY_NAME} OBJECT)
TARGET_SOURCES(${LIBRARY_NAME} PRIVATE
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8/bme68x/bme68x.c
        ${PROJECT_ROOT_DIR}/Drivers/BSEC2/bsec2.cpp
)
#target_link_libraries(${LIBRARY_NAME}_Driver PUBLIC stm32cubemx)


# Link directories setup
TARGET_LINK_DIRECTORIES(${CMAKE_PROJECT_NAME} PRIVATE
        ${PROJECT_ROOT_DIR}/Drivers/BSEC2/cortex-m4/1.10.2610
)

# Add libraries to the project
TARGET_LINK_LIBRARIES(${CMAKE_PROJECT_NAME}
        fpv4-sp-d16-hard-algobsec
)
