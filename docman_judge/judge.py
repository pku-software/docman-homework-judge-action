import os
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Union

from termcolor import colored

from docman_judge.cases import Case, MalformedCase


@dataclass
class JudgeResult:
    title: str
    success: bool
    log: str


def build(path: str) -> JudgeResult:
    os.chdir(path)
    if not os.path.exists("CMakeLists.txt"):
        return JudgeResult("pre-configure", False, "No build system found.")

    config_command = "cmake -B ./build" + (' -G "MinGW Makefiles"' if os.name == "nt" else "")
    cfg_r = subprocess.run(config_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = cfg_r.stdout.decode(errors="ignore") + cfg_r.stderr.decode(errors="ignore")
    if cfg_r.returncode != 0:
        return JudgeResult("configure", False, output)

    build_command = "cmake --build ./build"
    build_r = subprocess.run(build_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output += build_r.stdout.decode(errors="ignore") + build_r.stderr.decode(errors="ignore")
    if build_r.returncode != 0:
        return JudgeResult("build", False, output)

    return JudgeResult("build", True, output)


def run_exe(path: str, args: List[str], rediect_input: Union[None, str]) -> Tuple[str, int, str, bool]:
    args = [path] + args
    if rediect_input is None:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        file = open(rediect_input, "r")
        proc = subprocess.Popen(args, stdin=file, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    timeout = False
    try:  # timeout if 60 seconds passed without ending the process.
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        timeout = True
        proc.kill()
        stdout, stderr = proc.communicate()

    if rediect_input is not None:
        file.close()

    exit_code = proc.returncode
    stdout = stdout.decode(errors="ignore")
    stderr = stderr.decode(errors="ignore")
    return stdout, exit_code, " ".join([str(i) for i in args]) + "\n" + stdout + "\n" + stderr, timeout


def format_log_message(reason: str, log: str) -> str:
    return f"{colored(reason, 'blue')}\n{colored('Output', 'yellow')}:\n{log}"


def test(path: str, case: Union[Case, MalformedCase]) -> JudgeResult:
    os.chdir(path)
    exe_path = os.path.join(path, "build", "docman.exe" if os.name == "nt" else "docman")
    if not os.path.exists(exe_path):
        return JudgeResult("pretest", False, "Output executable file docman does not exist.")
    if isinstance(case, MalformedCase):
        _, code, log, timeout = run_exe(exe_path, case.args, None)  # Malformed ones shouldn't accept any input...
        if timeout:
            return JudgeResult(
                "test",
                False,
                format_log_message("Case timeout.", log),
            )
        if code == 0:
            return JudgeResult(
                "test",
                False,
                format_log_message("Malformed case should not pass.", log),
            )
        elif code == 1:
            return JudgeResult(
                "test",
                True,
                format_log_message("Failed as expected.", log),
            )
        else:
            return JudgeResult(
                "test",
                False,
                format_log_message("Error code should be 1 when failed.", log),
            )
    args = case.generate_args()
    output, code, log, timeout = run_exe(exe_path, args, case.input_doc_path if case.need_redirect else None)
    if timeout:
        return JudgeResult(
            "test",
            False,
            format_log_message("Case timeout.", log),
        )
    if case.should_error():
        if code == 0:
            return JudgeResult(
                "test",
                False,
                format_log_message("Case should error but passed.", log),
            )
        elif case.output is not None and os.path.exists(case.output):
            return JudgeResult(
                "test",
                False,
                format_log_message("Case should error, but output file created.", log),
            )
        elif code == 1:
            return JudgeResult(
                "test",
                True,
                format_log_message("Failed as expected.", log),
            )
        else:
            return JudgeResult(
                "test",
                False,
                format_log_message("Error code should be 1 when failed.", log),
            )
    else:  # Should pass...
        if code != 0:
            return JudgeResult(
                "test",
                False,
                format_log_message("Case should pass but failed.", log),
            )
    # Normally passed, check output.
    output_in_memory = ""
    if case.output is not None:
        if not os.path.exists(case.output):
            return JudgeResult(
                "test",
                False,
                format_log_message("Output file does not exist.", log),
            )
        with open(case.output, "r", encoding="utf-8") as f:
            output_in_memory = f.read()
    else:  # output in terminal
        output_in_memory = output.replace("\r\n", "\n")
    case.expect_output = case.expect_output.removesuffix("\n")
    output_in_memory = output_in_memory.removesuffix("\n")  # Don't consider trailing '\n'.

    if output_in_memory != case.expect_output:
        to_end = True
        i = 0
        for i in range(min(len(output_in_memory), len(case.expect_output))):
            if output_in_memory[i] != case.expect_output[i]:
                to_end = False
                break

        def get_char_or_eof(s, idx):
            if to_end and idx + 1 >= len(s):
                return "<EOF>"
            return s[idx]

        correct, wrong = (
            get_char_or_eof(case.expect_output, i),
            get_char_or_eof(output_in_memory, i),
        )

        with open(case.input_doc_path, "r", encoding="utf-8") as input:
            input_str = input.read()

        output_len = len(output_in_memory)

        msg = (
            f"{colored('Output mismatch.', 'blue')}\n"
            f"{colored('Output', 'yellow')} [mismatch in {i}]:\n"
            f"{output_in_memory[: i - 5]}{colored(output_in_memory[i - 5 : min(i + 5, output_len)], 'red')}"
            f"{output_in_memory[min(i + 5, output_len) :]}\n"
            f"{colored('Expect output', 'yellow')}:\n{case.expect_output}\n"
            f"expect {repr(correct)}, get {repr(wrong)}\n"
            f"{colored('Input', 'yellow')}:\n{input_str}"
        )

        return JudgeResult("test", False, msg)
    return JudgeResult("test", True, log)
