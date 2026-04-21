import json
import os
import random
import string
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from docman_judge.correct import transform_article


@dataclass
class Case:
    input_doc_path: Union[None, Path]
    need_redirect: bool
    input_citation: Path
    output: Union[None, str]
    expect_output: Union[None, str]
    error: bool

    def generate_args(self) -> List[str]:
        args = ["-c", self.input_citation]

        if self.output is not None:
            args.extend(["-o", self.output])

        if not self.need_redirect:
            args.append(self.input_doc_path)
        else:
            args.append("-")

        return args

    def should_error(self) -> bool:
        return self.error


@dataclass
class MalformedCase:
    args: List[str]

def get_cases(input_dir: Path, citation_dir: Path, output_dir: Path) -> List[Union[Case, MalformedCase]]:
    cases = []

    for filename in os.listdir(input_dir):
        input_path, citation_path = (
            input_dir / filename,
            citation_dir / filename,
        )
        assert filename.endswith(".txt") and input_path.is_file() and citation_path.is_file()

        with open(input_path, "r") as file:
            input_str = file.read()
        output_path = output_dir / f"answer{filename}"
        expect_output = transform_article(input_str, citation_path)
        expect_output, error = expect_output.result, not expect_output.success

        # -c citation_path -o output_path input_file
        cases.append(Case(input_path, False, citation_path, output_path, expect_output, error))
        # -c citation_path input_file
        cases.append(Case(input_path, False, citation_path, None, expect_output, error))
        # -c citation_path -o output_path -
        cases.append(Case(input_path, True, citation_path, output_path, expect_output, error))
        # -c citation_path -
        cases.append(Case(input_path, True, citation_path, None, expect_output, error))

    valid_input, valid_citation = (
        input_dir / "1.txt",
        citation_dir / "1.txt",
    )
    invalid_input, invalid_citation = (
        input_dir / "10086.txt",
        citation_dir / "10086.txt",
    )

    # Input paths not exist:
    cases.extend(
        [
            Case(invalid_input, False, valid_citation, None, None, True),
            Case(invalid_input, False, valid_citation, "non-exist.txt", None, True),
        ]
    )

    # Citation paths not exist:
    cases.extend(
        [
            Case(valid_input, False, invalid_citation, None, None, True),
            Case(valid_input, False, invalid_citation, "non-exist.txt", None, True),
        ]
    )

    # Then malformed ones...
    cases.extend(
        [
            MalformedCase([]),
            MalformedCase(["stray"]),
            MalformedCase(["more", "stray"]),
            MalformedCase(["--unrecognized"]),
            MalformedCase(["-c"]),
            MalformedCase(["-o", "a.txt", "-o", "b.txt", valid_input]),
        ]
    )

    return cases
