#!/usr/bin/env python3

#
# Copyright (c) 2014 Krzysztof Jusiak (krzysztof at jusiak dot net)
#
# Distributed under the Boost Software License, Version 1.0.
#

"""
@file       generateGmock.py
@brief      Generate mock class files from a given interface file based 
            on the Google Mock framework using libclang.
@authors    Krzysztof Jusiak (c) 2014 [krzysztof at jusiak dot net]
            Mustafa Siddiqui (c) 2023
@copyright  (c) Distributed under the Boost Software License, Version 1.0.
"""

import argparse
import os
import sys
from subprocess import call
import chevron
from clang.cindex import Index
from clang.cindex import TranslationUnit
from clang.cindex import CursorKind
from clang.cindex import Config
from enum import Enum
from typing import List

#
# Constants
#

CaseTypes = Enum("CaseTypes", ["SNAKE_CASE", "KEBAB_CASE", "SPACE"])

#
# Class Definitions
#


class StringTransform:
    """
    A wrapper class to store identifier names and transform
    them into different formats.
    """

    delimiters = {
        CaseTypes.KEBAB_CASE: "-",
        CaseTypes.SNAKE_CASE: "_",
        CaseTypes.SPACE: " ",
    }

    def __init__(self, identifier: str):
        self.obtained_string = identifier

    @property
    def _string_parts(self) -> List[str]:
        """
        Helper method to obtain a list of words in a given string that
        contains the supported delimeters.
        """
        string_parts = []

        # Assuming that there will be one kind of delimiter in a string...
        for delim in self.delimiters.values():
            if delim in self.obtained_string:
                string_parts = self.obtained_string.lower().split(delim)
                break

        # Future feature (maybe): might remove and support to separate out
        # strings in capital snake case etc.
        if len(string_parts) == 0:
            raise ValueError("Error: Unsupported delimeter")

        # Leading or trailing CaseTypes will result in empty strings
        # as elements of the broken string array, remove them
        # Also remove 'intf' from name
        for elem in string_parts:
            if elem == "" or elem == "intf":
                string_parts.remove(elem)

        return string_parts

    @property
    def _snake_case(self) -> str:
        return self.delimiters[CaseTypes.SNAKE_CASE].join(self._string_parts)

    @property
    def _kebab_case(self) -> str:
        return self.delimiters[CaseTypes.KEBAB_CASE].join(self._string_parts)

    @property
    def _space_separated(self) -> str:
        return self.delimiters[CaseTypes.SPACE].join(self._string_parts)

    @property
    def _pascal_case(self) -> str:
        return self._space_separated.title().replace(
            self.delimiters[CaseTypes.SPACE], ""
        )

    @property
    def _camel_case(self) -> str:
        return self._pascal_case[0].lower() + self._pascal_case[1:]

    @property
    def gmock_h_file_name(self) -> str:
        return self._kebab_case + self.delimiters[CaseTypes.KEBAB_CASE] + "gmock.h"

    @property
    def gmock_cpp_file_name(self) -> str:
        return self._kebab_case + self.delimiters[CaseTypes.KEBAB_CASE] + "gmock.cpp"

    @property
    def gmock_class_name(self) -> str:
        return (
            self._snake_case.upper() + self.delimiters[CaseTypes.SNAKE_CASE] + "GMOCK"
        )

    @property
    def header_guard_name(self) -> str:
        return (
            self.gmock_class_name
            + self.delimiters[CaseTypes.SNAKE_CASE]
            + "H"
            + self.delimiters[CaseTypes.SNAKE_CASE]
        )


class MockMethod:
    """
    Class that represents a mock method. It is constructed
    with some variables representing different aspects of a
    method & can generator a string representation of the
    method in the appropriate manner for a gmock file.
    """

    operators = {
        "operator,": "comma_operator",
        "operator!": "logical_not_operator",
        "operator!=": "inequality_operator",
        "operator%": "modulus_operator",
        "operator%=": "modulus_assignment_operator",
        "operator&": "address_of_or_bitwise_and_operator",
        "operator&&": "logical_and_operator",
        "operator&=": "bitwise_and_assignment_operator",
        "operator()": "function_call_or_cast_operator",
        "operator*": "multiplication_or_dereference_operator",
        "operator*=": "multiplication_assignment_operator",
        "operator+": "addition_or_unary_plus_operator",
        "operator++": "increment1_operator",
        "operator+=": "addition_assignment_operator",
        "operator-": "subtraction_or_unary_negation_operator",
        "operator--": "decrement1_operator",
        "operator-=": "subtraction_assignment_operator",
        "operator->": "member_selection_operator",
        "operator->*": "pointer_to_member_selection_operator",
        "operator/": "division_operator",
        "operator/=": "division_assignment_operator",
        "operator<": "less_than_operator",
        "operator<<": "left_shift_operator",
        "operator<<=": "left_shift_assignment_operator",
        "operator<=": "less_than_or_equal_to_operator",
        "operator=": "assignment_operator",
        "operator==": "equality_operator",
        "operator>": "greater_than_operator",
        "operator>=": "greater_than_or_equal_to_operator",
        "operator>>": "right_shift_operator",
        "operator>>=": "right_shift_assignment_operator",
        "operator[]": "array_subscript_operator",
        "operator^": "exclusive_or_operator",
        "operator^=": "exclusive_or_assignment_operator",
        "operator|": "bitwise_inclusive_or_operator",
        "operator|=": "bitwise_inclusive_or_assignment_operator",
        "operator||": "logical_or_operator",
        "operator~": "complement_operator",
    }

    def __init__(
        self,
        result_type,
        name,
        is_const,
        is_template,
        args_size,
        args,
        args_prefix="arg",
    ):
        self.result_type = result_type
        self.name = name
        self.is_const = is_const
        self.is_template = is_template
        self.args_size = args_size
        self.args = args
        self.args_prefix = args_prefix

    def _named_args(self):
        result = []
        for i in range(0, self.args_size):
            i and result.append(", ")
            result.append(self.args_prefix + str(i))
        return "".join(result)

    def _named_args_with_types(self):
        if self.args == "":
            return ""
        result = []
        in_type = False
        i = 0
        for c in self.args:
            if c in ["<", "("]:
                in_type = True
            elif c in [">", ")"]:
                in_type = False
            if not in_type and c == ",":
                result.append(" " + self.args_prefix + str(i))
                i += 1
            result.append(c)
        result.append(" " + self.args_prefix + str(i))
        return "".join(result)

    def to_string(self, gap: str = "    ") -> str:
        mock = []
        name = self.name
        if self.name in self.operators:
            mock.append(gap)
            mock.append(
                "virtual %(result_type)s %(name)s(%(args)s) %(const)s{ %(return)s %(body)s; }\n"
                % {
                    "result_type": self.result_type,
                    "name": self.name,
                    "args": self.args,
                    "const": self.is_const and "const " or "",
                    "return": self.result_type.strip() != "void" and "return" or "",
                    "body": self.operators[self.name] + "(" + self.args + ")",
                }
            )
            name = self.operators[self.name]

        mock.append(gap)
        mock.append(
            "MOCK_%(const)sMETHOD%(nr)s%(template)s(%(name)s, %(result_type)s(%(args)s));"
            % {
                "const": self.is_const and "CONST_" or "",
                "nr": self.args_size,
                "template": self.is_template and "_T" or "",
                "name": name,
                "result_type": self.result_type,
                "args": self.args,
            }
        )

        return "".join(mock)


class MockGenerator:
    """
    Class that processes a given mock method object and generates
    the gmock file(s).
    """

    def __init__(
        self,
        file: str,
        expr: str,
        path: str,
        encode: str = "utf-8",
    ):
        self.expr = expr
        self.path = path
        self.encode = encode
        self.cursor = self._parse(file).cursor

    def _is_template_class(self, expr: str) -> bool:
        """
        Checks if a class is a template class or not.
        """

        return "<" in expr

    def _get_arguments_and_num_args(self, tokens: List[str]) -> str:
        """
        Processes a list of tokens containing what is read for a
        method by the parser and returns everything in between '()'
        in the order it is received / processed, along with the number
        of arguments determined.
        """

        args_with_types = ""
        number_of_commas_encountered = 0
        reached_end_of_args = False

        for i in range(1, len(tokens)):
            # Handle special case of function call operator
            # If this is not done, the function will think that
            # upon reaching the closing parenthesis, we have reached
            # the end of the arguments -- which is not the case
            if tokens[i - 1] == "operator":
                if tokens[i] == "(" and tokens[i + 1] == ")":
                    i = i + 3

            # We don't want opening bracket in our result
            if tokens[i - 1] == "(":
                in_between_template_type = False
                while tokens[i] != ")":
                    args_with_types += tokens[i]

                    # Don't insert spaces
                    #  - before ','
                    #  - before ')'
                    #  - before '>'
                    #  - before '>>', '>>>', '>>>>' etc. (they are parsed as single tokens)
                    #  - before or after '::'
                    #  - before or after '<'
                    if not (
                        tokens[i + 1] in ["::", ",", ")", "<", ">"]
                        or tokens[i] in ["::", "<"]
                        or (tokens[i + 1][0] == ">" and tokens[i + 1][-1] == ">")
                    ):
                        args_with_types += " "

                    # Track if we're processing tokens between
                    # '<' & '>' -- we do not want to take into
                    # account the commas encountered during this
                    # since we use that info to determine the
                    # number of arguments
                    if tokens[i] == "<":
                        in_between_template_type = True
                    elif tokens[i + 1][0] == ">" and tokens[i + 1][-1] == ">":
                        in_between_template_type = False
                    else:
                        if tokens[i] == "," and in_between_template_type == False:
                            number_of_commas_encountered += 1

                    i += 1

                reached_end_of_args = True

            if reached_end_of_args:
                break

        if len(args_with_types) == 0:
            num_args = 0
        else:
            num_args = number_of_commas_encountered + 1

        return (num_args, args_with_types)

    def _get_result_type(self, tokens: List[str], name: str) -> str:
        """
        Processes a list of tokens containing what is read for a
        method by the parser and returns the return variable type.
        """

        result_type = []
        for token in tokens:
            if token in [name, "operator"]:
                break
            if token not in ["virtual", "inline", "volatile"]:
                result_type.append(token)
            if token in ["const", "volatile"]:
                result_type.append(" ")
        return "".join(result_type)

    def _pretty_template(self, expr: str) -> str:
        first = False
        typename = []
        typenames = []
        for token in expr.split("::")[-1]:
            if token == "<":
                first = True
            elif token == ",":
                typenames.append("".join(typename))
                typename = []
            elif token == ">":
                typenames.append("".join(typename))
                typename = []
            elif token == " ":
                continue
            elif first:
                typename.append(token)

        result = []
        if len(typenames) > 0:
            result.append("template<")
            for i, t in enumerate(typenames):
                i != 0 and result.append(", ")
                result.append("typename ")
                result.append(t)
            result.append(">")
            result.append("\n")

        return "".join(result)

    def _pretty_mock_methods(self, mock_methods: List[MockMethod]) -> str:
        result = []
        for i, mock_method in enumerate(mock_methods):
            i and result.append("\n")
            result.append(mock_method.to_string())

        return "".join(result)

    def _pretty_namespaces_begin(self, expr: str) -> str:
        result = []
        for i, namespace in enumerate(expr.split("::")[0:-1]):
            i and result.append("\n")
            result.append("namespace " + namespace + " {")
        return "".join(result)

    def _pretty_namespaces_end(self, expr: str) -> str:
        result = []
        for i, namespace in enumerate(expr.split("::")[0:-1]):
            i and result.append("\n")
            result.append("} // namespace " + namespace)
        return "".join(result)

    def _get_interface(self, expr: str) -> str:
        result = []
        ignore = False
        for token in expr.split("::")[-1]:
            if token == "<":
                ignore = True
            if not ignore:
                result.append(token)
            if token == ">":
                ignore = False
        return "".join(result)

    def _get_mock_methods(self, node, mock_methods: dict, expr="") -> None:
        """
        Populates the dictionary given with generated MockMethod
        objects given a cursor (generic object representing a node in
        the AST).
        """

        # Note: node.displayname returns 'int' for a function
        # argument with the '::' operator in name
        # (e.g. setString(std::string name)). 'int' is the default
        # type in libclang when it comes across some error or
        # undefined / unsupported situation.
        name = node.displayname

        if node.kind == CursorKind.CXX_METHOD:
            spelling = node.spelling
            tokens = [token.spelling for token in node.get_tokens()]
            num_args, args_with_types = self._get_arguments_and_num_args(tokens)
            file = node.location.file.name
            mock_methods.setdefault(expr, [file]).append(
                MockMethod(
                    result_type=self._get_result_type(tokens, spelling),
                    name=spelling,
                    is_const=node.is_const_method(),
                    is_template=self._is_template_class(expr),
                    args_size=num_args,
                    args=args_with_types,
                    args_prefix=name[len(node.spelling) + 1 : -1],
                )
            )
        elif node.kind in [
            CursorKind.CLASS_TEMPLATE,
            CursorKind.STRUCT_DECL,
            CursorKind.CLASS_DECL,
            CursorKind.NAMESPACE,
        ]:
            expr = expr == "" and name or expr + (name == "" and "" or "::") + name
            if expr.startswith(self.expr):
                [
                    self._get_mock_methods(c, mock_methods, expr)
                    for c in node.get_children()
                ]
        else:
            [self._get_mock_methods(c, mock_methods, expr) for c in node.get_children()]

    def _parse(self, file: str) -> TranslationUnit:
        tmp_file = b"~.hpp"

        include = f'#include "{file}"\n'

        return Index.create(excludeDecls=False).parse(
            path=tmp_file,
            unsaved_files=[(tmp_file, bytes(include, self.encode))],
            options=TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
            | TranslationUnit.PARSE_INCOMPLETE,
        )

    def generate_data(self) -> dict:
        """
        Parses the input interface file, generates mock methods, and populates the
        replacement data dictionary.
        """

        mock_methods = {}
        self._get_mock_methods(self.cursor, mock_methods)

        if len(mock_methods) == 0:
            raise RuntimeError("Error: could not process interface methods.")

        # There's only going to be one entry since we read only one
        # input interface file
        expr = list(iter(mock_methods))[0]
        mock_methods_list = mock_methods[expr]

        interfaceNameObj = StringTransform(self._get_interface(expr))

        def _get_templated_class_name(
            className: str, templateInterfaceName: str
        ) -> str:
            """
            Helper method to create a templated class name if the interface
            is templated.
            template_interface_name = OBJ_INTF<T1, T2> etc.
            """

            # If interface not templated, return class name as is
            if "<" not in templateInterfaceName:
                return className

            template_typenames = templateInterfaceName.split("<")
            template_typenames = "<" + template_typenames[-1]

            return className + template_typenames

        templatedClassName = _get_templated_class_name(
            interfaceNameObj.gmock_class_name, expr.split("::")[-1]
        )

        replacements = {
            "mock_file_hpp": interfaceNameObj.gmock_h_file_name,
            "mock_file_cpp": interfaceNameObj.gmock_cpp_file_name,
            "generated_dir": self.path,
            "guard": interfaceNameObj.header_guard_name,
            "file": os.path.basename(mock_methods_list[0]),
            "namespaces_begin": self._pretty_namespaces_begin(expr),
            "interface": interfaceNameObj._snake_case.upper(),
            "class_name": interfaceNameObj.gmock_class_name,
            "template_class_name": templatedClassName,
            "template_interface": expr.split("::")[-1],
            "template": self._pretty_template(expr),
            "mock_methods": self._pretty_mock_methods(mock_methods_list[1:]),
            "namespaces_end": self._pretty_namespaces_end(expr),
        }

        return replacements


#
# Function Definitions
#


def generate_rendered_mustache_file(
    template_file: str, output_file: str, data: dict
) -> None:
    """
    Reads template mustache file, renders it, and creates the autogenerated file.
    """

    if data["generated_dir"] != ".":
        output_file = data["generated_dir"] + "/" + output_file

    with open(template_file, "r") as h_file_template:
        rendered_data = chevron.render(h_file_template, data)

    with open(output_file, "w") as h_file_rendered:
        h_file_rendered.write(rendered_data)


#
# Main
#


def main(args):
    parser = argparse.ArgumentParser(
        description="""Generate gmock files from an interface given mustache templates."""
    )

    parser.add_argument(
        "-d",
        "--dir",
        help="Directory to store generated mock files in. Default = current directory.",
        type=str,
        default=".",
    )

    parser.add_argument(
        "-f",
        "--file",
        help="Path to the interface file from which the mock file is to be generated.",
        type=str,
        required=True,
    )

    parser.add_argument(
        "-e",
        "--expr",
        help="Limit to interfaces within expression. Default = ''",
        type=str,
        default="",
    )

    parser.add_argument(
        "-l",
        "--libclang",
        help="Path to libclang.so. Default = None",
        type=str,
        default=None,
    )

    args = parser.parse_args()

    if args.libclang:
        Config.set_library_file(args.libclang)

    replacements = MockGenerator(
        file=args.file, expr=args.expr, path=args.dir
    ).generate_data()

    # Generate mock files based on mustache templates
    dir_path = os.path.dirname(os.path.realpath(__file__))

    template_h_file_path = dir_path + "/templates/gmock-template-h.mustache"
    generate_rendered_mustache_file(
        template_file=template_h_file_path,
        output_file=replacements["mock_file_hpp"],
        data=replacements,
    )

    template_cpp_file_path = dir_path + "/templates/gmock-template-cpp.mustache"
    generate_rendered_mustache_file(
        template_file=template_cpp_file_path,
        output_file=replacements["mock_file_cpp"],
        data=replacements,
    )

    # Run clang-format on generated files
    lc_h_file = ["clang-format", replacements["mock_file_hpp"], "-i"]
    lc_cpp_file = ["clang-format", replacements["mock_file_cpp"], "-i"]

    call(lc_h_file)
    call(lc_cpp_file)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
