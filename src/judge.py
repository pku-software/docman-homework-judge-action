from typing import Union, List, Tuple
from cases import Case, MalformedCase
from dataclasses import dataclass
import os
import shutil
import subprocess

@dataclass
class JudgeResult:
    title: str
    success: bool
    log: str

def prepare(path: str) -> JudgeResult:
    dirname = os.path.dirname(os.path.abspath(__file__))

    # TODO: copy files

    copies = [
    ]
    for file, dir in copies:
        full_path = os.path.join(path, dir)
        os.makedirs(full_path, exist_ok=True)
        shutil.copy(os.path.join(dirname, "../dummy", file), full_path)

    return JudgeResult("prepare", True, "")

def build(path: str) -> JudgeResult:
    os.chdir(path)
    if not os.path.exists("CMakeLists.txt"):
        return JudgeResult("pre-configure", False, "No build system found.")

    config_command = "cmake -B ./build" + (" -G \"MinGW Makefiles\"" if os.name == "nt" else "")
    cfg_r = subprocess.run(
        config_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = cfg_r.stdout.decode(errors="ignore") + \
        cfg_r.stderr.decode(errors="ignore")
    if cfg_r.returncode != 0:
        return JudgeResult("configure", False, output)

    build_command = "cmake --build ./build"
    build_r = subprocess.run(
        build_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output += build_r.stdout.decode(errors="ignore") + \
        build_r.stderr.decode(errors="ignore")
    if build_r.returncode != 0:
        return JudgeResult("build", False, output)

    return JudgeResult("build", True, output)

def run_exe(path: str, args: List[str], stdin_str: Union[None, str] = None) -> Tuple[str, int, str, bool]:
    args = [path] + args
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    timeout = False
    try: # timeout if 60 seconds passed without ending the process.
        stdout, stderr = proc.communicate(stdin_str.encode(errors="ignore") if stdin_str is not None else None, 60)
    except subprocess.TimeoutExpired:
        timeout = True
        proc.kill()
        stdout, stderr = proc.communicate()

    exit_code = proc.returncode
    stdout = stdout.decode(errors="ignore")
    stderr = stderr.decode(errors="ignore")
    return stdout, exit_code, ' '.join(args) + '\n' + stdout + '\n' + stderr, timeout

def test(path: str, case: Union[Case, MalformedCase]) -> JudgeResult:
    os.chdir(path)
    exe_path = os.path.join(
        path, "build", "docman.exe" if os.name == "nt" else "docman")
    if not os.path.exists(exe_path):
        return JudgeResult("pretest", False, "Output executable file docman does not exist.")
    if isinstance(case, MalformedCase):
        _, code, log, timeout = run_exe(exe_path, case.args) # Malformed ones shouldn't accept any input...
        if timeout:
            return JudgeResult("test", False, "Case timeout. Output:\n" + log)
        if code == 0:
            return JudgeResult("test", False, "Malformed case should not pass. Output:\n" + log)
        else:
            return JudgeResult("test", True, "Failed as expected. Output:\n" + log)
    args = case.generate_args()
    output, code, log, timeout = run_exe(exe_path, args, case.input_str)
    if timeout:
        return JudgeResult("test", False, "Case timeout. Output:\n"+ log)
    if case.should_error():
        if code == 0:
            return JudgeResult("test", False, "Case should error but passed. Output:\n" + log)
        elif case.output is not None and os.path.exists(case.output):
            return JudgeResult("test", False, "Case should error, but output file created. Output:\n" + log)
        else:
            return JudgeResult("test", True, "Failed as expected. Output:\n" + log)
    else: # Should pass...
        if code != 0:
            return JudgeResult("test", False, "Case should pass but failed. Output:\n" + log)
    # Normally passed, check output.
    output_in_memory = ""
    if case.output is not None:
        if not os.path.exists(case.output):
            return JudgeResult("test", False, "Output file does not exist.\nOutput:\n" + log)
        with open(case.output, "r", encoding="utf-8") as f:
            output_in_memory = f.read()
    else: # output in terminal
        output_in_memory = output

    if output_in_memory != case.expect_output:
        return JudgeResult("test", False, "Output mismatch.\nOutput:\n" + log)
    return JudgeResult("test", True, log)