"""Code generated by Speakeasy (https://speakeasy.com). DO NOT EDIT."""

from __future__ import annotations
from lambdadb import utils
from lambdadb.types import BaseModel
from typing import Optional


class TooManyRequestsErrorData(BaseModel):
    message: Optional[str] = None


class TooManyRequestsError(Exception):
    data: TooManyRequestsErrorData

    def __init__(self, data: TooManyRequestsErrorData):
        self.data = data

    def __str__(self) -> str:
        return utils.marshal_json(self.data, TooManyRequestsErrorData)
