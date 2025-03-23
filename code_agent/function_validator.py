import ast
import builtins

SAFE_BUILTIN_MODULES = [
    "math",
    "cmath",
    "decimal",
    "fractions",
    "random",
    "statistics",
    "itertools",
    "functools",
    "operator",
    "collections",
    "heapq",
    "bisect",
    "datetime",
    "time",
    "calendar",
    "re",
    "string",
    "json",
    "copy",
    "pprint",
    "logging",
    "enum",
    "abc",
    "dataclasses",
    "types",
    "traceback",
    "uuid"
]


# -------------------------------
# Helper classes (AST Visitors)
# -------------------------------

class AllowedImportsChecker(ast.NodeVisitor):
    """
    Checks that all import statements in the AST use only allowed libraries
    and disallows relative (local) imports.
    """
    def __init__(self, allowed_lib_names):
        self.allowed_lib_names = allowed_lib_names
        self.illegal_imports = set()

    def is_allowed(self, imported: str) -> bool:
        for allowed in self.allowed_lib_names:
            if imported == allowed or imported.startswith(allowed + "."):
                return True
        return False

    def visit_Import(self, node):
        for alias in node.names:
            if not self.is_allowed(alias.name):
                self.illegal_imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.level and node.level > 0:
            relative_import = "." * node.level + (node.module or "")
            self.illegal_imports.add(f"Relative import: '{relative_import}'")
        elif node.module and not self.is_allowed(node.module):
            self.illegal_imports.add(node.module)
        self.generic_visit(node)


class FunctionRenamer(ast.NodeTransformer):
    """
    Renames all function definitions in the AST to the specified new name.
    """
    def __init__(self, new_name: str):
        self.new_name = new_name

    def visit_FunctionDef(self, node):
        node.name = self.new_name
        return self.generic_visit(node)


class AssignedNamesVisitor(ast.NodeVisitor):
    """
    Collects names that are assigned within a function, including:
      - Names defined via assignments (and tuple unpacking),
      - Names defined as targets of augmented assignments,
      - Names defined in for loops,
      - Names defined in exception handlers,
      - Names defined in with statements,
      - Names of nested function definitions.
    """
    def __init__(self):
        self.assigned = set()

    def visit_FunctionDef(self, node):
        self.assigned.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assigned.add(target.id)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        self.assigned.add(elt.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.assigned.add(node.target.id)
        self.generic_visit(node)

    def visit_For(self, node):
        if isinstance(node.target, ast.Name):
            self.assigned.add(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    self.assigned.add(elt.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.assigned.add(node.name)
        self.generic_visit(node)
    
    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                self.assigned.add(item.optional_vars.id)
        self.generic_visit(node)
 
    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.assigned.add(node.target.id)
        self.generic_visit(node)
  

class UndefinedNameVisitor(ast.NodeVisitor):
    """
    Checks for any undefined names (variables, functions, etc.) used in a function.
    Updated to bypass names defined in comprehensions.
    """
    def __init__(self, allowed_names: set):
        self.allowed_names = allowed_names
        self.undefined_names = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if node.id not in self.allowed_names:
                self.undefined_names.add(node.id)
        self.generic_visit(node)

    def visit_ListComp(self, node):
        for generator in node.generators:
            self._add_comprehension_targets(generator.target)
            self.generic_visit(generator)
        self.generic_visit(node.elt)

    def visit_GeneratorExp(self, node):
        for generator in node.generators:
            self._add_comprehension_targets(generator.target)
            self.generic_visit(generator)
        self.generic_visit(node.elt)

    def visit_SetComp(self, node):
        for generator in node.generators:
            self._add_comprehension_targets(generator.target)
            self.generic_visit(generator)
        self.generic_visit(node.elt)

    def visit_DictComp(self, node):
        for generator in node.generators:
            self._add_comprehension_targets(generator.target)
            self.generic_visit(generator)
        self.generic_visit(node.key)
        self.generic_visit(node.value)

    def _add_comprehension_targets(self, target):
        if isinstance(target, ast.Name):
            self.allowed_names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                if isinstance(elt, ast.Name):
                    self.allowed_names.add(elt.id) 


class UpdatedDictCopyVisitor(ast.NodeVisitor):
    """
    Checks that the function contains an assignment of the form:
        updated_dict = previous_output.copy()
    """
    def __init__(self):
        self.found = False

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "updated_dict":
                if isinstance(node.value, ast.Call):
                    call_node = node.value
                    if isinstance(call_node.func, ast.Attribute):
                        attr = call_node.func
                        if attr.attr == "copy" and isinstance(attr.value, ast.Name) and attr.value.id == "previous_output":
                            if not call_node.args and not call_node.keywords:
                                self.found = True
        self.generic_visit(node)


class UpdatedDictGetVisitor(ast.NodeVisitor):
    """
    Checks that any call of the form:
        updated_dict.get(<key>, ...)
    uses a key that is present in previous_output.
    Modified to bypass non–literal key arguments.
    """
    def __init__(self, previous_keys: set):
        self.previous_keys = previous_keys
        self.errors = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if (node.func.attr == "get" and 
                isinstance(node.func.value, ast.Name) and 
                node.func.value.id == "updated_dict"):
                if node.args:
                    key_arg = node.args[0]
                    # Only check if the key is a string literal.
                    if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str):
                        key_used = key_arg.value
                        if key_used not in self.previous_keys:
                            self.errors.append(
                                f"Key '{key_used}' used in updated_dict.get is not present in previous_output."
                            )
                    else:
                        # Bypass the error if the key is not a literal.
                        pass
        self.generic_visit(node)


class FunctionNestingVisitor(ast.NodeVisitor):
    """
    Validates that function nesting is no deeper than one level.
    The primary function is at level 0 and its immediate nested functions are at level 1.
    Nested functions inside a helper function (level 2 or deeper) are not allowed.
    """
    def __init__(self):
        self.errors = []

    def check_nesting(self, node, depth=0):
        if isinstance(node, ast.FunctionDef):
            if depth > 1:
                self.errors.append( 
                    f"Function '{node.name}' is nested too deeply at level {depth}. Only one level of nested functions is allowed."
                )
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.FunctionDef):
                    self.check_nesting(child, depth + 1)
                else:
                    self.check_nesting(child, depth)
        else:
            for child in ast.iter_child_nodes(node):
                self.check_nesting(child, depth)


class DangerousCallVisitor(ast.NodeVisitor):
    """
    Checks for dangerous function calls such as eval, exec, compile, __import__,
    and common shell-executing functions like os.system, os.popen, subprocess.call, and subprocess.Popen.
    """
    def __init__(self):
        self.dangerous_calls = set()
        self.dangerous_function_names = {"eval", "exec", "compile", "__import__"}
        self.dangerous_full_names = {"os.system", "os.popen", "subprocess.call", "subprocess.Popen", "pickle.loads"}

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.dangerous_function_names:
                self.dangerous_calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            full_name = self._get_full_attr_name(node.func)
            if full_name in self.dangerous_full_names:
                self.dangerous_calls.add(full_name)
        self.generic_visit(node)
     
    def _get_full_attr_name(self, node):
        if isinstance(node, ast.Attribute):  
            value = self._get_full_attr_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Name):
            return node.id
        return ""  
      
  
# -------------------------------
# Main FunctionValidator Class  
# -------------------------------
 
class FunctionValidator: 
    def __init__(self, subtask_name: str, allowed_lib_names: list, subtask_idx: int, total_subtasks: int, previous_output: dict = None):
        """
        Initializes the validator with the expected subtask name, a list of allowed libraries,
        and the index of the subtask (to validate the parameter signature accordingly).

        :param subtask_name: The expected name of the function. 
        :param allowed_lib_names: A list of allowed library names.
        :param subtask_idx: The index of the subtask.
        """
        self.subtask_name = subtask_name
        self.allowed_lib_names = list(set(allowed_lib_names + SAFE_BUILTIN_MODULES))
        self.subtask_idx = subtask_idx
        self.previous_output = previous_output
        self.total_subtasks = total_subtasks
        self.errors_for_regeneration = []

    def validate(self, code_string: str) -> dict:
        """
        Validates the given code by:
         1. Checking for syntax errors.  
         2. Ensuring that only allowed libraries are imported.
         3. Checking that all used names are defined.
         4. Validating the function parameter signature based on the subtask index.
         5. For subtask indices > 0, verifying that the function includes the assignment
            'updated_dict = previous_output.copy()'.
         6. If previous_output is provided, ensuring that any calls to updated_dict.get(...)
            use keys that are present in previous_output.  
         7. Validating that there is only one level of function nesting.
         8. Ensuring that dangerous function calls are not used.
         9. Renaming the function to match the expected subtask name if no errors occur.
        """
        try:
            tree = ast.parse(code_string)
        except SyntaxError as e:
            self.errors_for_regeneration.append(f"Syntax error in code: {e}")
            tree = None

        if tree is not None:
            # Check allowed imports.
            import_checker = AllowedImportsChecker(self.allowed_lib_names)
            import_checker.visit(tree)
            if import_checker.illegal_imports:
                self.errors_for_regeneration.append(
                    f"Illegal import(s) detected: {sorted(import_checker.illegal_imports)}. Allowed libraries: {self.allowed_lib_names}."
                )

            # Find the first function definition.
            function_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_def = node
                    break

            if function_def:
                # === Parameter Validation Based on Subtask Index ===

                if function_def.args.vararg is not None:
                    self.errors_for_regeneration.append("Varargs (*args) are not allowed in the subtask function definition.")
                if function_def.args.kwarg is not None:
                    self.errors_for_regeneration.append("Keyword arguments (**kwargs) are not allowed in the subtask function definition.")

                # Validate keyword-only arguments: each must have a default.
                for arg, default in zip(function_def.args.kwonlyargs, function_def.args.kw_defaults):
                    if default is None:
                        self.errors_for_regeneration.append(f"Keyword-only argument '{arg.arg}' must have a default value.")

                # Validate positional arguments.
                positional_args = function_def.args.args  
                num_defaults = len(function_def.args.defaults)
                non_default_count = len(positional_args) - num_defaults

                if self.subtask_idx == 0:
                    if non_default_count != 0 and self.total_subtasks > 1:
                        self.errors_for_regeneration.append(
                            f"For subtask at index 0, all positional parameters must have default values. Found {non_default_count} parameter(s) without defaults."
                        )
                else:
                    if not positional_args:
                        self.errors_for_regeneration.append("For subtask index > 0, the function must have at least one parameter named 'previous_output'.")
                    else:
                        if positional_args[0].arg != "previous_output":
                            self.errors_for_regeneration.append("For subtask index > 0, the first parameter must be named 'previous_output'.")
                        if non_default_count != 1:
                            self.errors_for_regeneration.append(
                                f"For subtask index > 0, only 'previous_output' can be a non-default parameter. Found {non_default_count} non-default positional parameter(s)."
                            )

                    # === Check for 'updated_dict = previous_output.copy()' assignment ===
                    updated_dict_visitor = UpdatedDictCopyVisitor()
                    updated_dict_visitor.visit(function_def)
                    if not updated_dict_visitor.found:
                        self.errors_for_regeneration.append(
                            "For subtask index > 0, the function must include the assignment 'updated_dict = previous_output.copy()'."
                        )

                # === End of Parameter Validation ===

                # Build the allowed names set.
                allowed_names = set(dir(builtins))
                allowed_names.add("self")
                for arg in function_def.args.args:
                    allowed_names.add(arg.arg)
                if function_def.args.vararg:
                    allowed_names.add(function_def.args.vararg.arg)
                if function_def.args.kwarg:
                    allowed_names.add(function_def.args.kwarg.arg)

                assigned_visitor = AssignedNamesVisitor()
                assigned_visitor.visit(function_def)
                allowed_names |= assigned_visitor.assigned

                for node in ast.walk(tree):      
                    if isinstance(node, ast.Import):
                        for alias in node.names:     
                            allowed_names.add(alias.asname if alias.asname else alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            allowed_names.add(alias.asname if alias.asname else alias.name)

                allowed_names.update({"error", "logger", "session_id", "socketio"})
 
                undefined_visitor = UndefinedNameVisitor(allowed_names)  
                undefined_visitor.visit(function_def) 
                if undefined_visitor.undefined_names:
                    for name in sorted(undefined_visitor.undefined_names):
                        self.errors_for_regeneration.append(
                            f"Undefined name: '{name}' is used but not defined."
                        )

                # === Validate Function Nesting Level ===
                nesting_visitor = FunctionNestingVisitor() 
                nesting_visitor.check_nesting(function_def, depth=0)
                if nesting_visitor.errors:
                    self.errors_for_regeneration.extend(nesting_visitor.errors)

                # === Validate Dangerous Function Calls ===
                dangerous_visitor = DangerousCallVisitor()
                dangerous_visitor.visit(function_def)
                if dangerous_visitor.dangerous_calls:
                    for call in sorted(dangerous_visitor.dangerous_calls):
                        self.errors_for_regeneration.append(
                            f"Dangerous function call '{call}' is not allowed."
                        )

                # === Validate updated_dict.get keys if previous_output is provided ===
                if self.subtask_idx > 0 and self.previous_output is not None:
                    previous_keys = set(self.previous_output.keys())
                    updated_dict_get_visitor = UpdatedDictGetVisitor(previous_keys)
                    updated_dict_get_visitor.visit(function_def)
                    if updated_dict_get_visitor.errors:
                        self.errors_for_regeneration.extend(updated_dict_get_visitor.errors)
            else:
                self.errors_for_regeneration.append("No function definition found in code.")

            if not self.errors_for_regeneration:
                renamer = FunctionRenamer(self.subtask_name)
                tree = renamer.visit(tree)
                code_string = ast.unparse(tree)

        return { 
            "code_string": code_string,
            "errors_for_regeneration": self.errors_for_regeneration
        }
