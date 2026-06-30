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
    """Error raised when a step cannot be represented in a declarative spec.

    Currently applies to any step built from a BaseStep instance (e.g.
    RetryStep, TimeoutStep, WaitStep) — only the built closure survives
    add_step(), not the original instance/config needed to reconstruct it.
    """

    def __init__(self, step_name: str, step_type: object):
        self.message = (
            f"Step '{step_name}' cannot be serialized: it was built from a "
            f"BaseStep instance (step_type={step_type}). Serializing "
            "BaseStep-derived steps (RetryStep, TimeoutStep, WaitStep, or "
            "custom BaseStep subclasses) is not yet supported."
        )
        super().__init__(self.message)
