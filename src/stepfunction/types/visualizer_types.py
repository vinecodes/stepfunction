from typing import TypedDict, Optional

class RenderStepFunctionParams(TypedDict, total=False):
    file_path: Optional[str]
    file_name: Optional[str]
    format: str
    renderer: str