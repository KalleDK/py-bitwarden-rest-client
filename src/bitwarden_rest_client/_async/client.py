import contextlib
import logging
from typing import Any

import httpx
import pydantic

from bitwarden_rest_client.models import (
    CollectionID,
    DeleteResponse,
    Folder,
    FolderID,
    FolderNew,
    GeneratePasswordResponse,
    ItemID,
    ItemLoginNew,
    Items,
    ListResponse,
    LockResponse,
    OrgID,
    Response,
    SyncResponse,
    UnlockPayload,
    UnlockResponse,
)

_log = logging.getLogger(__name__)


class AsyncBitwardenClient:
    _client: httpx.AsyncClient

    # region Init / Dispose

    def __init__(self, base_url: str | None = None):
        if base_url is None:
            base_url = "http://localhost:8087"
        self._client = httpx.AsyncClient(base_url=base_url)

    @staticmethod
    def _payload_to_json(payload: pydantic.BaseModel | None) -> Any:
        if payload is None:
            return None
        obj = payload.model_dump(mode="json", by_alias=True, exclude_none=True)

        return obj

    @classmethod
    @contextlib.asynccontextmanager
    async def session(cls, base_url: str | None = None):
        client = cls(base_url=base_url)
        try:
            yield client
        finally:
            await client.close()

    async def close(self):
        await self._client.aclose()

    # endregion

    # region API Helpers

    async def _get[T: pydantic.BaseModel](self, cls: type[T], path: str, params: httpx.QueryParams | None = None) -> T:
        _log.debug("Params: %s", params)
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        response_data = Response[cls].model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.data

    async def _put[T: pydantic.BaseModel](
        self, cls: type[T], path: str, payload: pydantic.BaseModel | None = None
    ) -> T:
        response = await self._client.put(path, json=self._payload_to_json(payload))
        response.raise_for_status()
        response_data = Response[cls].model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.data

    async def _post[T: pydantic.BaseModel](
        self, cls: type[T], path: str, payload: pydantic.BaseModel | None = None
    ) -> T:
        response = await self._client.post(path, json=self._payload_to_json(payload))
        response.raise_for_status()
        response_data = Response[cls].model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.data

    async def _delete(self, path: str) -> bool:
        response = await self._client.delete(path)
        response.raise_for_status()
        response_data = DeleteResponse.model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.success

    # endregion

    # region Lock / Unlock

    async def lock(self):
        return await self._post(LockResponse, "/lock")

    async def unlock(self, password: pydantic.SecretStr):
        payload = UnlockPayload(password=password)
        return await self._post(UnlockResponse, "/unlock", payload=payload)

    async def sync(self):
        return await self._post(SyncResponse, "/sync")

    async def generate_password(
        self,
        length: int = 20,
        uppercase: bool = True,
        lowercase: bool = True,
        numbers: bool = True,
        special: bool = False,
    ) -> pydantic.SecretStr:
        params = httpx.QueryParams()
        params = params.set("length", str(length))
        if uppercase:
            params = params.set("uppercase", "true")
        if lowercase:
            params = params.set("lowercase", "true")
        if numbers:
            params = params.set("numbers", "true")
        if special:
            params = params.set("special", "true")
        response = await self._get(GeneratePasswordResponse, "/generate", params=params)
        return response.data

    # endregion

    # region Folders

    async def folder_create(self, name: str) -> Folder:
        payload = FolderNew(name=name)
        return await self._post(Folder, "/object/folder", payload=payload)

    async def folder_update(self, folder: Folder) -> Folder:
        return await self._put(Folder, f"/object/folder/{folder.id}", payload=folder)

    async def folder_delete(self, folder: Folder) -> bool:
        return await self._delete(f"/object/folder/{folder.id}")

    async def folder_list(self, search: str | None = None) -> list[Folder]:
        params = httpx.QueryParams()
        if search is not None:
            params = params.set("search", search)
        response = await self._get(ListResponse[Folder], "/list/object/folders", params=params)
        return response.data

    async def folder_get(self, folder_id: FolderID | None) -> Folder:
        return await self._get(Folder, f"/object/folder/{folder_id}")

    # endregion

    # region Items

    async def item_create(self, item: ItemLoginNew) -> Items:
        return await self._post(Items, "/object/item", payload=item)  # type: ignore[arg-type]

    async def item_delete(self, item_id: ItemID) -> bool:
        return await self._delete(f"/object/item/{item_id}")  # type: ignore[arg-type]

    async def item_get(self, item_id: ItemID) -> Items:
        return await self._get(Items, f"/object/item/{item_id}")  # type: ignore[arg-type]

    async def item_list(
        self,
        org_id: OrgID | None = None,
        collection_id: CollectionID | None = None,
        folder_id: FolderID | None = None,
        url: str | None = None,
        trash: bool = False,
        search: str | None = None,
    ) -> list[Items]:
        params = httpx.QueryParams()
        if org_id is not None:
            params = params.set("organizationId", org_id)
        if collection_id is not None:
            params = params.set("collectionId", collection_id)
        if folder_id is not None:
            params = params.set("folderId", folder_id)
        if url is not None:
            params = params.set("url", url)
        if trash:
            params = params.set("trash", "true")
        if search is not None:
            params = params.set("search", search)
        response = await self._get(ListResponse[Items], "/list/object/items", params=params)
        return response.data

    # endregion
