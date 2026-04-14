from enum import Enum


class StepFunctionStatus(Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepType(Enum):
    INBUILT = "INBUILT"
    EXTERNAL = "EXTERNAL"
