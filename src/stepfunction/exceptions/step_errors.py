class StepExecutionError(Exception):
    """Error raised when a step fails."""

    def __init__(self, exc: Exception):
        self.message = f"Step generated an exception: {exc}"
        super().__init__(self.message)


class ParallelStepExecutionError(Exception):
    """Error raised when a parallel step fails."""

    def __init__(self, exc: Exception):
        self.message = f"Parallel step generated an exception: {exc}"
        super().__init__(self.message)
