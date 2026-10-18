class StepExecutionError(Exception):
    """Error raised when a step fails."""

    def __init__(self, exc: Exception):
        self.message = f"Step generated an exception: {exc}"
        super().__init__(self.message)


class ParallelStepExecutionError(Exception):
    """Error raised when a parallel step fails."""

    def __init__(self, exc: list[tuple[str, Exception]]):
        self.message = f"Parallel step generated an exception: {exc}"
        super().__init__(self.message)


class DuplicateRegistrationError(Exception):
    """Error raised when a function is registered under a name that is already taken."""

    def __init__(self, name: str):
        self.message = f"A function is already registered under the name '{name}'."
        super().__init__(self.message)


class UnregisteredFunctionError(Exception):
    """Error raised when a step spec references a function that has no
    registered name, in either direction: decoding a name that was never
    registered, or encoding a function that was never given a name."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class UnserializableStepError(Exception):
    """Error raised when a step cannot be represented in a declarative spec:
    it (or one of a parallel step's tasks) was built from a BaseStep subclass
    that has no ``spec_type`` — a custom step that doesn't implement
    ``to_spec``/``from_spec``."""

    def __init__(self, step_name: str, step_class: str):
        self.message = (
            f"Step '{step_name}' cannot be serialized: {step_class} has no "
            "spec_type. Give it one, implement to_spec() and from_spec(), and "
            "register it with stepfunction.steps.register_step_type()."
        )
        super().__init__(self.message)


class UnknownStepTypeError(Exception):
    """Error raised when a spec names a step type no class is registered for."""

    def __init__(self, name: str):
        self.message = (
            f"No step type is registered under the name '{name}'. Register its "
            "class with stepfunction.steps.register_step_type() before loading "
            "this workflow spec."
        )
        super().__init__(self.message)
