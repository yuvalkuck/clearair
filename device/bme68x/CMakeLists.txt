INCLUDE(${CMAKE_CURRENT_SOURCE_DIR}/../scope-share.cmake)
STM_SET_LIBNAME()

# Replace 'my_target' with your actual target name
ADD_LIBRARY(${LIBRARY_NAME} STATIC
        src/bridge_bme680.cpp
        src/task_bme680.cpp
)

# Expose header files to consumers of this library

TARGET_LINK_LIBRARIES(${LIBRARY_NAME} PUBLIC stm32cubemx stm32bsec2bme_Drivers)
TARGET_INCLUDE_DIRECTORIES(${LIBRARY_NAME} PRIVATE
        ${stm32bsec2bme_INC}
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
        ${APP_ROOT_DIR}/include
)

TARGET_INCLUDE_DIRECTORIES(${CMAKE_PROJECT_NAME} PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
        ${APP_ROOT_DIR}/include
        ${PROJECT_ROOT_DIR}/Drivers/BME68x/4.4.8
        ${PROJECT_ROOT_DIR}/Drivers/BSEC/2.6.1.0/inc
)
TARGET_LINK_DIRECTORIES(${CMAKE_PROJECT_NAME} PUBLIC
        ${CMAKE_CURRENT_BINARY_DIR}
)

# Link hardware dependencies (e.g., HAL)
TARGET_LINK_LIBRARIES(${CMAKE_PROJECT_NAME}
        ${LIBRARY_NAME}
)