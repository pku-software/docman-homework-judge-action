from dataclasses import dataclass, KW_ONLY
from typing import Union, List
import os

class Case:
    input_doc_path: Union[None, str]
    input_str: Union[None, str]
    input_citation: str
    output: Union[None, str]
    expect_output: Union[None, str]
    error: bool

    def generate_args(self) -> List[str]:
        args = ["-c", self.input_citation]

        if self.output is None:
            args.extend(["-o", self.output])

        # Only one of them should be None.
        assert((self.input_doc_path is None) != (self.input_str is None))

        if self.input_doc_path is None:
            args.append(self.input_doc_path)
        else:
            args.append("-")

        return args

    def should_error(self) -> bool:
        return self.error


@dataclass
class MalformedCase:
    args: List[str]


def get_cases(input_dir: str, citation_dir: str, expect_output_dir: str) -> List[Union[Case, MalformedCase]]:
    input_dir, citation_dir, expect_output_dir = os.path.abspath(input_dir),\
        os.path.abspath(citation_dir), os.path.abspath(expect_output_dir)

    cases = []

    # For correct cases.
    for filename in os.listdir(input_dir):
        input_path, citation_path, expect_output_path = os.path.join(input_dir, filename),\
            os.path.join(expect_output_dir, filename), os.path.join(citation_dir, filename)
        assert(filename.endswith(".txt") and os.path.isfile(input_path) and \
               os.path.isfile(citation_path) and os.path.isfile(expect_output_path))
        
        input_str = open(input_path, "r").read()
        output_path = "answer" + filename

        # -c citation_path -o output_path input_file
        cases.append(Case(input_path, None, citation_path, output_path, expect_output_path, False))
        # -c citation_path input_file
        cases.append(Case(input_path, None, citation_path, None, expect_output_path, False))
        # -c citation_path -o output_path -
        cases.append(Case(None, input_str, citation_path, output_path, expect_output_path, False))
        # -c citation_path -
        cases.append(Case(None, input_str, citation_path, None, expect_output_path, False))

    # Then Malformed ones...
    cases.append(MalformedCase([]))

    return cases