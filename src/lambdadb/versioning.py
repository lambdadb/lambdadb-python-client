"""Collection-scoped Data Versioning lifecycle clients."""

from __future__ import annotations

import json
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Generic,
    Iterator,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import quote

from lambdadb import errors, models, utils
from lambdadb.errors.contract_errors import (
    raise_catalog_conflict,
    raise_ref_delete_conflict,
)
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
RefDetailsT = TypeVar("RefDetailsT", bound=BaseModel)
SourceInput = Union[models.RefSource, models.BranchSource, Mapping[str, Any]]
TargetInput = Union[models.AliasTarget, Mapping[str, Any]]
IndexConfigsInput = Union[
    Dict[str, models.IndexConfigsUnion],
    Dict[str, models.IndexConfigsUnionTypedDict],
]


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
    def _raise_error(
        response: Any,
        *,
        catalog_conflict: bool = False,
        ref_delete_conflict: bool = False,
    ) -> None:
        if response.status_code == 409 and ref_delete_conflict:
            raise_ref_delete_conflict(response)
        if response.status_code == 409 and catalog_conflict:
            raise_catalog_conflict(response)
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
        params: Optional[Dict[str, Any]] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
        ref_delete_conflict: bool = False,
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
            params=params or None,
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
            self._raise_error(
                response,
                catalog_conflict=method.upper() in {"PATCH", "DELETE"},
                ref_delete_conflict=ref_delete_conflict,
            )
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
        params: Optional[Dict[str, Any]] = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
        ref_delete_conflict: bool = False,
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
            params=params or None,
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
            self._raise_error(
                response,
                catalog_conflict=method.upper() in {"PATCH", "DELETE"},
                ref_delete_conflict=ref_delete_conflict,
            )
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


def _page_params(size: Optional[int], page_token: Optional[str]) -> Dict[str, Any]:
    """Validate ref listing parameters; unset or empty values are not sent.

    Ref listings page exactly like the collection listing, so its request model
    supplies the size bounds (1-100).
    """
    return models.ListCollectionsRequest(
        size=size, page_token=page_token or None
    ).model_dump(by_alias=True)


class _RefReads(Generic[RefResponseT, RefListResponseT, RefDetailsT]):
    """Single read and paged listing shared by Branches, Tags, and Aliases."""

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

    def _ref_path(self, name: str) -> str:
        safe_name = quote(models.Ref.branch(name).name, safe="")
        return f"{self._base_path}/{safe_name}"

    def get(
        self, name: str, *, options: Optional[RequestOptions] = None
    ) -> RefResponseT:
        """Get one ref with its index schema.

        A name that is not a ref of this kind raises ``ResourceNotFoundError``.
        """
        return self._transport.request(
            "GET",
            self._ref_path(name),
            f"get{self.kind.title()}",
            self.response_type,
            200,
            **_options(options),
        )

    async def get_async(
        self, name: str, *, options: Optional[RequestOptions] = None
    ) -> RefResponseT:
        """Get one ref with its index schema asynchronously."""
        return await self._transport.request_async(
            "GET",
            self._ref_path(name),
            f"get{self.kind.title()}",
            self.response_type,
            200,
            **_options(options),
        )

    def list(self, *, options: Optional[RequestOptions] = None) -> RefListResponseT:
        """List every ref of this kind in name order.

        Follows ``next_page_token`` with the server's default page size until
        the last page and returns the complete listing. A failure on any page
        raises; no partial list is returned. Use ``list_page`` for one page.
        """
        response = self.list_page(options=options)
        entries = list(getattr(response, self.plural))
        while getattr(response, "next_page_token"):
            response = self.list_page(
                page_token=getattr(response, "next_page_token"), options=options
            )
            entries.extend(getattr(response, self.plural))
        return self.list_response_type.model_validate({self.plural: entries})

    async def list_async(
        self, *, options: Optional[RequestOptions] = None
    ) -> RefListResponseT:
        """List every ref of this kind in name order asynchronously."""
        response = await self.list_page_async(options=options)
        entries = list(getattr(response, self.plural))
        while getattr(response, "next_page_token"):
            response = await self.list_page_async(
                page_token=getattr(response, "next_page_token"), options=options
            )
            entries.extend(getattr(response, self.plural))
        return self.list_response_type.model_validate({self.plural: entries})

    def list_page(
        self,
        *,
        size: Optional[int] = None,
        page_token: Optional[str] = None,
        options: Optional[RequestOptions] = None,
    ) -> RefListResponseT:
        """List one page of refs in name order.

        A response with more refs to return carries ``next_page_token``; pass it
        as ``page_token`` to get the next page, or use ``list_pages``. It is
        ``None`` on the last page. Each entry has the same shape as a single read.

        :param size: Max number of refs to return at once (1-100, default 10).
        :param page_token: Opaque token returned by the previous page. Omit it for the first page; an empty value is not sent.
        """
        return self._transport.request(
            "GET",
            self._base_path,
            f"list{self.plural.title()}",
            self.list_response_type,
            200,
            params=_page_params(size, page_token),
            **_options(options),
        )

    async def list_page_async(
        self,
        *,
        size: Optional[int] = None,
        page_token: Optional[str] = None,
        options: Optional[RequestOptions] = None,
    ) -> RefListResponseT:
        """List one page of refs in name order asynchronously."""
        return await self._transport.request_async(
            "GET",
            self._base_path,
            f"list{self.plural.title()}",
            self.list_response_type,
            200,
            params=_page_params(size, page_token),
            **_options(options),
        )

    def list_pages(
        self, *, size: Optional[int] = None, options: Optional[RequestOptions] = None
    ) -> Iterator[List[RefDetailsT]]:
        """Iterate pages of refs, each with up to `size` refs (server default 10)."""
        page_token: Optional[str] = None
        while True:
            resp = self.list_page(size=size, page_token=page_token, options=options)
            yield getattr(resp, self.plural)
            page_token = getattr(resp, "next_page_token")
            if not page_token:
                break

    async def list_pages_async(
        self, *, size: Optional[int] = None, options: Optional[RequestOptions] = None
    ) -> AsyncIterator[List[RefDetailsT]]:
        """Iterate pages of refs asynchronously."""
        page_token: Optional[str] = None
        while True:
            resp = await self.list_page_async(
                size=size, page_token=page_token, options=options
            )
            yield getattr(resp, self.plural)
            page_token = getattr(resp, "next_page_token")
            if not page_token:
                break


class _Refs(_RefReads[RefResponseT, RefListResponseT, RefDetailsT]):
    @staticmethod
    def _validate_source(source: SourceInput) -> models.RefSource:
        """Validate the source before either sync or async transport is used."""
        if isinstance(source, BaseModel):
            source = source.model_dump(mode="json", by_alias=True, exclude_none=True)
        return models.RefSource.model_validate(source)

    def create(
        self,
        name: str,
        *,
        source: Optional[SourceInput] = None,
        options: Optional[RequestOptions] = None,
    ) -> RefResponseT:
        """Create a ref from a Branch or Tag source; omit ``source`` to use main.

        Without ``as_of``, creation pins the source snapshot and the fixed
        inherited and pending write ranges of the source, without copying them
        or waiting for the source build. ``as_of`` is valid only for a Branch
        source and selects the latest retained committed snapshot at or before
        the cutoff, with no pending or inherited writes.
        """
        source_model = None if source is None else self._validate_source(source)
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
        """Create a ref from a Branch or Tag source asynchronously."""
        source_model = None if source is None else self._validate_source(source)
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
            ref_delete_conflict=True,
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
            ref_delete_conflict=True,
            **_options(options),
        )


class Branches(
    _Refs[models.BranchResponse, models.BranchListResponse, models.BranchDetails]
):
    """Branch lifecycle operations for one collection."""

    kind = "branch"
    plural = "branches"
    response_type = models.BranchResponse
    list_response_type = models.BranchListResponse

    @staticmethod
    def _update_body(index_configs: IndexConfigsInput) -> Dict[str, Any]:
        return models.UpdateBranchRequestBody(
            index_configs=utils.get_pydantic_model(
                index_configs, Dict[str, models.IndexConfigsUnion]
            )
        ).model_dump(mode="json", by_alias=True, exclude_none=True)

    def update(
        self,
        name: str,
        *,
        index_configs: IndexConfigsInput,
        options: Optional[RequestOptions] = None,
    ) -> models.BranchResponse:
        """Update the index schema of one Branch.

        The change applies to this Branch only; updating main also updates the
        collection's index configs, which mirror main. ``index_configs`` must
        be the Branch's complete nonempty schema: preserve existing fields and
        settings (the server-managed id field may be included as returned or
        omitted), add new fields at any object depth, and set, replace, or
        clear (``""``) a field description. Concurrent additive updates of the
        same Branch are merged. Naming a Tag or an Alias raises
        ``BadRequestError``.
        """
        return self._transport.request(
            "PATCH",
            self._ref_path(name),
            "updateBranch",
            models.BranchResponse,
            200,
            body=self._update_body(index_configs),
            **_options(options),
        )

    async def update_async(
        self,
        name: str,
        *,
        index_configs: IndexConfigsInput,
        options: Optional[RequestOptions] = None,
    ) -> models.BranchResponse:
        """Update the index schema of one Branch asynchronously."""
        return await self._transport.request_async(
            "PATCH",
            self._ref_path(name),
            "updateBranch",
            models.BranchResponse,
            200,
            body=self._update_body(index_configs),
            **_options(options),
        )


class Tags(_Refs[models.TagResponse, models.TagListResponse, models.TagDetails]):
    """Tag lifecycle operations for one collection."""

    kind = "tag"
    plural = "tags"
    response_type = models.TagResponse
    list_response_type = models.TagListResponse


class Aliases(
    _RefReads[models.AliasResponse, models.AliasListResponse, models.AliasDetails]
):
    """Alias lifecycle operations for one collection."""

    kind = "alias"
    plural = "aliases"
    response_type = models.AliasResponse
    list_response_type = models.AliasListResponse

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
