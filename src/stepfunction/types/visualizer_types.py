from typing import Optional, TypedDict


class RenderStepFunctionParams(TypedDict, total=False):
    file_path: Optional[str]
    file_name: Optional[str]
    format: str
    renderer: str
