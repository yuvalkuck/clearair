INCLUDE(${CMAKE_CURRENT_SOURCE_DIR}/../component.cmake)
stm_set_libname()
ADD_LIBRARY(${LIBRARY_NAME} STATIC
        src/telemetry_bme680.cpp
)

# Expose header files to consumers of this library
target_include_directories(${LIBRARY_NAME} PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
        ${APP_ROOT_DIR}/Drivers/BME68x/4.4.8
)
target_link_directories(${CMAKE_PROJECT_NAME} PUBLIC
    ${CMAKE_CURRENT_BINARY_DIR}
)

# Link hardware dependencies (e.g., HAL)
#target_link_libraries(${LIBRARY_NAME} PRIVATE STM32_HAL_Driver)