INCLUDE(${CMAKE_CURRENT_SOURCE_DIR}/../scope-share.cmake)
stm_set_libname()

ADD_LIBRARY(${LIBRARY_NAME} STATIC
        src/bridge_particle.cpp
        src/task_particle.cpp
)

# Expose header files to consumers of this library
target_include_directories(${LIBRARY_NAME} PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
        ${PROJECT_ROOT_DIR}/Drivers/SPS30
        stm32sps30_Drivers
        STM32_Drivers

)
target_link_libraries(${LIBRARY_NAME} PUBLIC stm32cubemx)

target_include_directories(${CMAKE_PROJECT_NAME} PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/inc
)
target_link_directories(${CMAKE_PROJECT_NAME} PUBLIC
    ${CMAKE_CURRENT_BINARY_DIR}
)

# Link hardware dependencies (e.g., HAL)
target_link_libraries(${CMAKE_PROJECT_NAME}
        ${LIBRARY_NAME}
)