from pydantic import BaseModel


class ExportFormatsResponse(BaseModel):
    formats: list[str]
    excel_supported: bool
