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
from . import benchmark
from . import schema
import logging
import os

_logger = logging.getLogger(__name__)

cmakeIndent = "  "
def generateCMakeDecls(benchmarkObjs, sourceRootDir, supportedArchitecture):
  """
    Returns a string containing CMake declarations
    that declare the benchmarks in the list ``benchmarkObjs``.
  """
  assert isinstance(benchmarkObjs, list)
  assert os.path.exists(sourceRootDir)
  assert os.path.isdir(sourceRootDir)
  declStr = "# Autogenerated. DO NOT MODIFY!\n"
  for b in benchmarkObjs:
    assert isinstance(b.name, str)
    assert isinstance(b, benchmark.Benchmark)

    benchmarkArchitectures = None
    if isinstance(b.architectures, str):
      assert b.architectures == 'any'
      benchmarkArchitectures = {'any'}
    else:
      benchmarkArchitectures = b.architectures

    for arch in benchmarkArchitectures:
      declStr += "####\n"
      targetName = '{}.{}'.format(b.name, arch)
      if arch != 'any' and arch != supportedArchitecture:
        # Architecture not supported
        declStr += 'message(STATUS "Compiler cannot build target {}. Architecture not supported by compiler")\n'.format(targetName)
        continue

      # Emit code that can be used by dependencies to prevent generaton of the target.
      # This is useful if a library required is not available.
      enableTargetCMakeVariable = "ENABLE_TARGET_{}".format(b.name.upper())
      declStr += "set({} TRUE)\n".format(enableTargetCMakeVariable)
      disabledTargetReasonsCMakeVariable = "DISABLED_TARGET_REASONS"
      declStr += "set({} \"\")\n".format(disabledTargetReasonsCMakeVariable)

      dependencyHandlingCMakeDecls = generate_dependency_decls(b, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable)

      # Emit dependency code that may change guard on executable
      for (guardDecl, _) in dependencyHandlingCMakeDecls:
        declStr += guardDecl

      # Emit code that can disable building the benchmark if the language
      # version is not supported
      lang_ver = b.language.replace('+','X').upper()
      declStr += """
if (NOT HAS_STD_{lang_ver})
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "Compiler does not support language standard {lang_ver}")
endif()
  \n""".format(
      lang_ver=lang_ver,
      enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)

      # Emit guard
      declStr += "if ({})\n".format(enableTargetCMakeVariable)
      # Emit ``add_executable()``
      declStr += "{indent}add_executable({target_name}\n".format(indent=cmakeIndent, target_name=targetName)
      # FIXME: Need to put in absolute path
      for source in b.sources:
        declStr += "{indent}{indent}{source_file}\n".format(indent=cmakeIndent, source_file=os.path.join(sourceRootDir, source))
      declStr += "  )\n"
      # Emit linking info
      declStr += "{indent}target_link_libraries({target_name} PRIVATE {libs})\n".format(
        indent=cmakeIndent,
        target_name=targetName,
        libs="svcomp_runtime")
      # Emit custom macro defintions
      if len(b.defines) > 0:
        declStr += "{indent}target_compile_definitions({target_name} PRIVATE\n".format(
          indent=cmakeIndent,
          target_name=targetName)
        for macroDefine in b.defines:
          assert isinstance(macroDefine, str)
          declStr += "  {}\n".format(macroDefine)
        declStr += ")\n"
      # Emit compiler flags
      declStr += "{indent}target_compile_options({target_name} PRIVATE ${{SVCOMP_STD_{lang_ver}}})\n".format(
        indent=cmakeIndent,
        target_name=targetName,
        lang_ver= lang_ver,
        arch = arch.upper()
      )

      # Emit dependency code that adds necessary dependencies to that target
      for (_, depAddDecl) in dependencyHandlingCMakeDecls:
        declStr += depAddDecl

      # Close guard
      declStr += """
else()
{indent}set(msgConcat "")
{indent}foreach (msg ${{DISABLED_TARGET_REASONS}})
{indent}{indent}set(msgConcat "${{msgConcat}}\\n  ${{msg}}")
{indent}endforeach()
{indent}message(WARNING "Not building target {target} due to ${{msgConcat}}")
{indent}unset(msgConcat)
endif()
      \n""".format(indent=cmakeIndent, target=targetName)
  return declStr

def generate_dependency_decls(benchmarkObj, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable):
  """
    Returns a list of tuples [(preGuardCode, inGuardCode)]
  """
  decls = []
  for depName, info in benchmarkObj.dependencies.items():
    decl = None
    if depName == 'pthreads':
      decl = generate_pthreads_dependency_code(
        info,
        targetName,
        enableTargetCMakeVariable,
        disabledTargetReasonsCMakeVariable
      )
    elif depName == 'openmp':
      decl = generate_openmp_dependency_code(
        info,
        targetName,
        enableTargetCMakeVariable,
        disabledTargetReasonsCMakeVariable,
        benchmarkObj
      )
    else:
      msg = 'Unhandled benchmark dependency "{}"'.format(depName)
      _logger.error(msg)
      # FIXME: Should use our own exception type here
      raise Exception(msg)
    decls.append(decl)
  return decls

def generate_pthreads_dependency_code(info, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable):
  # This guardDecl works in cooperation with find_package(Threads)
  guardDecl = """
if (NOT CMAKE_USE_PTHREADS_INIT)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "Pthreads library not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)
  addDepDecl = "{indent}target_link_libraries({targetName} PRIVATE ${{CMAKE_THREAD_LIBS_INIT}})\n".format(indent=cmakeIndent, targetName=targetName)
  return (guardDecl, addDepDecl)

def generate_openmp_dependency_code(info, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable, benchmarkObj):
  guardDecl = """
if (NOT OPENMP_FOUND)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "OpenMP not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)

  addDepDecl=""
  if benchmarkObj.isLanguageC():
    addDepDecl += "{indent}target_compile_options({targetName} PRIVATE ${{OpenMP_C_FLAGS}})\n".format(indent=cmakeIndent, targetName=targetName)
    addDepDecl += "{indent}set_property(TARGET {targetName} APPEND_STRING PROPERTY LINK_FLAGS \" ${{OpenMP_C_FLAGS}}\")\n".format(targetName=targetName, indent=cmakeIndent)
  elif benchmarkObj.isLanguageCXX():
    addDepDecl += "{indent}target_compile_options({targetName} PRIVATE ${{OpenMP_CXX_FLAGS}})\n".format(indent=cmakeIndent, targetName=targetName)
    addDepDecl += "{indent}set_property(TARGET {targetName} APPEND_STRING PROPERTY LINK_FLAGS \" ${{OpenMP_CXX_FLAGS}}\")\n".format(targetName=targetName, indent=cmakeIndent)
  else:
    _logger.error("Unknown benchmark language")
    raise Exception("Unknown benchmark language")
  return (guardDecl, addDepDecl)