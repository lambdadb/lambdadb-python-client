"""Collection-scoped Data Versioning lifecycle clients."""

from __future__ import annotations

import json
from typing import Any, Dict, Generic, Mapping, Optional, Type, TypeVar, Union
from urllib.parse import quote

from lambdadb import errors, models, utils
from lambdadb._hooks import HookContext
from lambdadb.basesdk import BaseSDK
from lambdadb.requestoptions import RequestOptions
from lambdadb.sdkconfiguration import SDKConfiguration
from lambdadb.types import BaseModel, OptionalNullable, UNSET
from lambdadb.utils import get_security_from_env
from lambdadb.utils.unmarshal_json_response import unmarshal_json_response

ResponseT = TypeVar("ResponseT", bound=BaseModel)
RefResponseT = TypeVar("RefResponseT", bound=BaseModel)
RefListResponseT = TypeVar("RefListResponseT", bound=BaseModel)
SourceInput = Union[models.RefSource, Mapping[str, Any]]
TargetInput = Union[models.AliasTarget, Mapping[str, Any]]


class _VersioningTransport(BaseSDK):
    def __init__(
        self,
        sdk_configuration: SDKConfiguration,
        collection_name: str,
        parent_ref: Optional[object] = None,
    ) -> None:
        super().__init__(sdk_configuration, parent_ref=parent_ref)
        self.collection_name = collection_name

    def _url(self, path: str, server_url: Optional[str]) -> str:
        base_url = server_url or self._get_url(None, None)
        return f"{base_url.rstrip('/')}{path}"

    def _headers(self, http_headers: Optional[Mapping[str, str]]) -> Dict[str, str]:
        security: Any = self.sdk_configuration.security
        if callable(security):
            security = security()
        security = get_security_from_env(security, models.Security)
        headers, _ = utils.get_security(security)
        headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": self.sdk_configuration.user_agent,
            }
        )
        if http_headers:
            headers.update(http_headers)
        return headers

    def _retry_config(
        self, retries: OptionalNullable[utils.RetryConfig]
    ) -> Optional[tuple]:
        if retries == UNSET:
            retries = self.sdk_configuration.retry_config
        if retries == UNSET:
            retries = utils.RetryConfig(
                "backoff", utils.BackoffStrategy(500, 60000, 1.5, 3600000), True
            )
        if isinstance(retries, utils.RetryConfig):
            return retries, ["429", "5XX"]
        return None

    @staticmethod
    def _raise_error(response: Any) -> None:
        mappings = {
            400: (errors.BadRequestErrorData, errors.BadRequestError),
            401: (errors.UnauthenticatedErrorData, errors.UnauthenticatedError),
            404: (errors.ResourceNotFoundErrorData, errors.ResourceNotFoundError),
            409: (
                errors.ResourceAlreadyExistsErrorData,
                errors.ResourceAlreadyExistsError,
            ),
            429: (errors.TooManyRequestsErrorData, errors.TooManyRequestsError),
            500: (errors.InternalServerErrorData, errors.InternalServerError),
        }
        mapping = mappings.get(response.status_code)
        if (
            mapping
            and response.headers.get("content-type", "").split(";")[0]
            == "application/json"
        ):
            data = unmarshal_json_response(mapping[0], response)
            raise mapping[1](data, response)
        raise errors.APIError("API error occurred", response, response.text)

    def request(
        self,
        method: str,
        path: str,
        operation_id: str,
        response_type: Type[ResponseT],
        expected_status: int,
        *,
        body: Optional[Dict[str, Any]] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> ResponseT:
        client = self.sdk_configuration.client
        if client is None:
            raise ValueError("HTTP client is not available")
        timeout = (
            timeout_ms if timeout_ms is not None else self.sdk_configuration.timeout_ms
        )
        request = client.build_request(
            method,
            self._url(path, server_url),
            content=None if body is None else json.dumps(body).encode("utf-8"),
            headers=self._headers(http_headers),
            timeout=None if timeout is None else timeout / 1000,
        )
        response = self.do_request(
            HookContext(
                config=self.sdk_configuration,
                base_url=self._url("", server_url),
                operation_id=operation_id,
                oauth2_scopes=None,
                security_source=get_security_from_env(
                    self.sdk_configuration.security, models.Security
                ),
            ),
            request,
            ["400", "401", "404", "409", "429", "4XX", "500", "5XX"],
            retry_config=self._retry_config(retries),
        )
        if response.status_code != expected_status:
            self._raise_error(response)
        return unmarshal_json_response(response_type, response)

    async def request_async(
        self,
        method: str,
        path: str,
        operation_id: str,
        response_type: Type[ResponseT],
        expected_status: int,
        *,
        body: Optional[Dict[str, Any]] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> ResponseT:
        client = self.sdk_configuration.async_client
        if client is None:
            raise ValueError("Async HTTP client is not available")
        timeout = (
            timeout_ms if timeout_ms is not None else self.sdk_configuration.timeout_ms
        )
        request = client.build_request(
            method,
            self._url(path, server_url),
            content=None if body is None else json.dumps(body).encode("utf-8"),
            headers=self._headers(http_headers),
            timeout=None if timeout is None else timeout / 1000,
        )
        response = await self.do_request_async(
            HookContext(
                config=self.sdk_configuration,
                base_url=self._url("", server_url),
                operation_id=operation_id,
                oauth2_scopes=None,
                security_source=get_security_from_env(
                    self.sdk_configuration.security, models.Security
                ),
            ),
            request,
            ["400", "401", "404", "409", "429", "4XX", "500", "5XX"],
            retry_config=self._retry_config(retries),
        )
        if response.status_code != expected_status:
            self._raise_error(response)
        return unmarshal_json_response(response_type, response)


def _options(options: Optional[RequestOptions]) -> Dict[str, Any]:
    if options is None:
        return {}
    return {
        "retries": options.retries,
        "server_url": options.server_url,
        "timeout_ms": options.timeout_ms,
        "http_headers": options.http_headers,
    }


class _Refs(Generic[RefResponseT, RefListResponseT]):
    kind: str
    plural: str
    response_type: Type[RefResponseT]
    list_response_type: Type[RefListResponseT]

    def __init__(self, transport: _VersioningTransport) -> None:
        self._transport = transport

    @property
    def _base_path(self) -> str:
        collection = quote(self._transport.collection_name, safe="")
        return f"/collections/{collection}/{self.plural}"

    def create(
        self,
        name: str,
        *,
        source: Optional[SourceInput] = None,
        options: Optional[RequestOptions] = None,
    ) -> RefResponseT:
        source_model = (
            None if source is None else models.RefSource.model_validate(source)
        )
        body: Dict[str, Any] = {f"{self.kind}Name": models.Ref.branch(name).name}
        if source_model is not None:
            body["source"] = source_model.model_dump(
                mode="json", by_alias=True, exclude_none=True
            )
        return self._transport.request(
            "POST",
            self._base_path,
            f"create{self.kind.title()}",
            self.response_type,
            201,
            body=body,
            **_options(options),
        )

    async def create_async(
        self,
        name: str,
        *,
        source: Optional[SourceInput] = None,
        options: Optional[RequestOptions] = None,
    ) -> RefResponseT:
        source_model = (
            None if source is None else models.RefSource.model_validate(source)
        )
        body: Dict[str, Any] = {f"{self.kind}Name": models.Ref.branch(name).name}
        if source_model is not None:
            body["source"] = source_model.model_dump(
                mode="json", by_alias=True, exclude_none=True
            )
        return await self._transport.request_async(
            "POST",
            self._base_path,
            f"create{self.kind.title()}",
            self.response_type,
            201,
            body=body,
            **_options(options),
        )

    def list(self, *, options: Optional[RequestOptions] = None) -> RefListResponseT:
        return self._transport.request(
            "GET",
            self._base_path,
            f"list{self.kind.title()}s",
            self.list_response_type,
            200,
            **_options(options),
        )

    async def list_async(
        self, *, options: Optional[RequestOptions] = None
    ) -> RefListResponseT:
        return await self._transport.request_async(
            "GET",
            self._base_path,
            f"list{self.kind.title()}s",
            self.list_response_type,
            200,
            **_options(options),
        )

    def delete(
        self, name: str, *, options: Optional[RequestOptions] = None
    ) -> models.MessageResponse:
        safe_name = quote(models.Ref.branch(name).name, safe="")
        return self._transport.request(
            "DELETE",
            f"{self._base_path}/{safe_name}",
            f"delete{self.kind.title()}",
            models.MessageResponse,
            200,
            **_options(options),
        )

    async def delete_async(
        self, name: str, *, options: Optional[RequestOptions] = None
    ) -> models.MessageResponse:
        safe_name = quote(models.Ref.branch(name).name, safe="")
        return await self._transport.request_async(
            "DELETE",
            f"{self._base_path}/{safe_name}",
            f"delete{self.kind.title()}",
            models.MessageResponse,
            200,
            **_options(options),
        )


class Branches(_Refs[models.BranchResponse, models.BranchListResponse]):
    """Branch lifecycle operations for one collection."""

    kind = "branch"
    plural = "branches"
    response_type = models.BranchResponse
    list_response_type = models.BranchListResponse


class Tags(_Refs[models.TagResponse, models.TagListResponse]):
    """Tag lifecycle operations for one collection."""

    kind = "tag"
    plural = "tags"
    response_type = models.TagResponse
    list_response_type = models.TagListResponse


class Aliases:
    """Alias lifecycle operations for one collection."""

    def __init__(self, transport: _VersioningTransport) -> None:
        self._transport = transport

    @property
    def _base_path(self) -> str:
        collection = quote(self._transport.collection_name, safe="")
        return f"/collections/{collection}/aliases"

    @staticmethod
    def _target(target: TargetInput) -> Dict[str, Any]:
        return models.AliasTarget.model_validate(target).model_dump(mode="json")

    def create(
        self,
        name: str,
        *,
        target: TargetInput,
        options: Optional[RequestOptions] = None,
    ) -> models.AliasResponse:
        alias_name = models.Ref.alias(name).name
        return self._transport.request(
            "POST",
            self._base_path,
            "createAlias",
            models.AliasResponse,
            201,
            body={"aliasName": alias_name, "target": self._target(target)},
            **_options(options),
        )

    async def create_async(
        self,
        name: str,
        *,
        target: TargetInput,
        options: Optional[RequestOptions] = None,
    ) -> models.AliasResponse:
        alias_name = models.Ref.alias(name).name
        return await self._transport.request_async(
            "POST",
            self._base_path,
            "createAlias",
            models.AliasResponse,
            201,
            body={"aliasName": alias_name, "target": self._target(target)},
            **_options(options),
        )

    def list(
        self, *, options: Optional[RequestOptions] = None
    ) -> models.AliasListResponse:
        return self._transport.request(
            "GET",
            self._base_path,
            "listAliases",
            models.AliasListResponse,
            200,
            **_options(options),
        )

    async def list_async(
        self, *, options: Optional[RequestOptions] = None
    ) -> models.AliasListResponse:
        return await self._transport.request_async(
            "GET",
            self._base_path,
            "listAliases",
            models.AliasListResponse,
            200,
            **_options(options),
        )

    def retarget(
        self,
        name: str,
        *,
        target: TargetInput,
        options: Optional[RequestOptions] = None,
    ) -> models.AliasResponse:
        safe_name = quote(models.Ref.alias(name).name, safe="")
        return self._transport.request(
            "PATCH",
            f"{self._base_path}/{safe_name}",
            "retargetAlias",
            models.AliasResponse,
            200,
            body={"target": self._target(target)},
            **_options(options),
        )

    async def retarget_async(
        self,
        name: str,
        *,
        target: TargetInput,
        options: Optional[RequestOptions] = None,
    ) -> models.AliasResponse:
        safe_name = quote(models.Ref.alias(name).name, safe="")
        return await self._transport.request_async(
            "PATCH",
            f"{self._base_path}/{safe_name}",
            "retargetAlias",
            models.AliasResponse,
            200,
            body={"target": self._target(target)},
            **_options(options),
        )

    def delete(
        self, name: str, *, options: Optional[RequestOptions] = None
    ) -> models.MessageResponse:
        safe_name = quote(models.Ref.alias(name).name, safe="")
        return self._transport.request(
            "DELETE",
            f"{self._base_path}/{safe_name}",
            "deleteAlias",
            models.MessageResponse,
            200,
            **_options(options),
        )

    async def delete_async(
        self, name: str, *, options: Optional[RequestOptions] = None
    ) -> models.MessageResponse:
        safe_name = quote(models.Ref.alias(name).name, safe="")
        return await self._transport.request_async(
            "DELETE",
            f"{self._base_path}/{safe_name}",
            "deleteAlias",
            models.MessageResponse,
            200,
            **_options(options),
        )


class CollectionVersioning:
    """Branch, tag, and alias lifecycle APIs bound to one collection."""

    def __init__(
        self,
        sdk_configuration: SDKConfiguration,
        collection_name: str,
        parent_ref: Optional[object] = None,
    ) -> None:
        transport = _VersioningTransport(sdk_configuration, collection_name, parent_ref)
        self.branches = Branches(transport)
        self.tags = Tags(transport)
        self.aliases = Aliases(transport)
