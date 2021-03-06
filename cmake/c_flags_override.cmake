# Copyright 2016 Daniel Liew
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file overrides the default compiler flags for CMake's built-in
# configurations (CMAKE_BUILD_TYPE). Most compiler flags should not be set here.
# The main # purpose is to make sure ``-DNDEBUG`` is never set by default.
if (CMAKE_C_COMPILER_ID)
  set(_lang C)
elseif (CMAKE_CXX_COMPILER_ID)
  set(_lang CXX)
else()
  message(FATAL_ERROR "Unknown language")
endif()

if (("${CMAKE_${_lang}_COMPILER_ID}" MATCHES "Clang") OR ("${CMAKE_${_lang}_COMPILER_ID}" MATCHES "GNU"))
  # Taken from Modules/Compiler/GNU.cmake but -DNDEBUG is removed
  set(CMAKE_${_lang}_FLAGS_INIT "")
  set(CMAKE_${_lang}_FLAGS_DEBUG_INIT "-g")
  set(CMAKE_${_lang}_FLAGS_MINSIZEREL_INIT "-Os")
  set(CMAKE_${_lang}_FLAGS_RELEASE_INIT "-O3")
  set(CMAKE_${_lang}_FLAGS_RELWITHDEBINFO_INIT "-O2 -g")
else()
  message(FATAL_ERROR "Overrides not set for compiler ${CMAKE_${_lang}_COMPILER_ID}")
endif()
unset(_lang)
