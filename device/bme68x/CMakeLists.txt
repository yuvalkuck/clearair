INCLUDE(${CMAKE_CURRENT_SOURCE_DIR}/../scope-share.cmake)
stm_set_libname()

ADD_LIBRARY(${LIBRARY_NAME} STATIC
        src/bridge_bme680.cpp
        src/task_bme680.cpp
)
# Expose header files to consumers of this library
target_include_directories(${LIBRARY_NAME} PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
        ${APP_ROOT_DIR}/include
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8
        ${PROJECT_ROOT_DIR}/Drivers/BSEC/2.6.1.0/inc
        ${PROJECT_ROOT_DIR}/Drivers/BSEC/2.6.1.0/config/bme680_iaq_33v_3s_4d
        stm32bsec2bme_Drivers
        STM32_Drivers
)

target_link_libraries(${LIBRARY_NAME} PUBLIC stm32cubemx)

target_include_directories(${CMAKE_PROJECT_NAME} PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
        ${APP_ROOT_DIR}/include
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8
        ${PROJECT_ROOT_DIR}/Drivers/BSEC/2.6.1.0/inc
)
target_link_directories(${CMAKE_PROJECT_NAME} PUBLIC
    ${CMAKE_CURRENT_BINARY_DIR}
)

# Link hardware dependencies (e.g., HAL)
target_link_libraries(${CMAKE_PROJECT_NAME}
        ${LIBRARY_NAME}
)