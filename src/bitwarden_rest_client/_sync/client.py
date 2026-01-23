import contextlib
import dataclasses
import logging
from typing import Any, overload

import httpx
import pydantic

from bitwarden_rest_client.consts import DEFAULT_BASEURL
from bitwarden_rest_client.models import (
    Card,
    CardData,
    CollectionID,
    DeleteResponse,
    Fields,
    Folder,
    FolderID,
    FolderNew,
    GeneratePasswordResponse,
    Identity,
    Item,
    ItemID,
    ItemType,
    ListResponse,
    LockResponse,
    Login,
    NewCard,
    NewIdentity,
    NewItem,
    NewLogin,
    NewLoginData,
    NewSecureNote,
    NewSSHKey,
    OrgID,
    Response,
    SecureNote,
    SSHKey,
    SyncResponse,
    UnlockPayload,
    UnlockResponse,
    UriMatch,
)

_log = logging.getLogger(__name__)


@dataclasses.dataclass
class BitwardenClient:
    client: httpx.Client

    # region Init / Dispose

    @staticmethod
    def _payload_to_json(payload: pydantic.BaseModel | None) -> Any:
        if payload is None:
            return None
        obj = payload.model_dump(mode="json", by_alias=True, exclude_none=True)

        return obj

    @classmethod
    @contextlib.contextmanager
    def session(cls, base_url: str | None = None):
        base_url = base_url if base_url is not None else DEFAULT_BASEURL
        client = cls(client=httpx.Client(base_url=base_url))
        try:
            yield client
        finally:
            client.close()

    def close(self):
        self.client.close()

    # endregion

    # region API Helpers

    def _get[T: pydantic.BaseModel](self, cls: type[T], path: str, params: httpx.QueryParams | None = None) -> T:
        _log.debug("Params: %s", params)
        response = self.client.get(path, params=params)
        response.raise_for_status()
        response_data = Response[cls].model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.data

    def _put[T: pydantic.BaseModel](self, cls: type[T], path: str, payload: pydantic.BaseModel | None = None) -> T:
        response = self.client.put(path, json=self._payload_to_json(payload))
        response.raise_for_status()
        response_data = Response[cls].model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.data

    def _post[T: pydantic.BaseModel](self, cls: type[T], path: str, payload: pydantic.BaseModel | None = None) -> T:
        response = self.client.post(path, json=self._payload_to_json(payload))
        response.raise_for_status()
        response_data = Response[cls].model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.data

    def _delete(self, path: str) -> bool:
        response = self.client.delete(path)
        response.raise_for_status()
        response_data = DeleteResponse.model_validate_json(response.text)
        if not response_data.success:
            raise RuntimeError("Request was not successful")
        return response_data.success

    # endregion

    # region Lock / Unlock

    def lock(self):
        return self._post(LockResponse, "/lock")

    def unlock(self, password: pydantic.SecretStr):
        payload = UnlockPayload(password=password)
        return self._post(UnlockResponse, "/unlock", payload=payload)

    def sync(self):
        return self._post(SyncResponse, "/sync")

    def generate_password(
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
        response = self._get(GeneratePasswordResponse, "/generate", params=params)
        return response.data

    # endregion

    # region Folders

    def folder_create(self, name: str) -> Folder:
        payload = FolderNew(name=name)
        return self._post(Folder, "/object/folder", payload=payload)

    def folder_update(self, folder: Folder) -> Folder:
        return self._put(Folder, f"/object/folder/{folder.id}", payload=folder)

    def folder_delete(self, folder: Folder) -> bool:
        return self._delete(f"/object/folder/{folder.id}")

    def folder_list(self, search: str | None = None) -> list[Folder]:
        params = httpx.QueryParams()
        if search is not None:
            params = params.set("search", search)
        response = self._get(ListResponse[Folder], "/list/object/folders", params=params)
        return response.data

    def folder_find(self, name: str) -> Folder | None:
        folders = self.folder_list(search=name)
        for folder in folders:
            if folder.name == name:
                return folder
        return None

    def folder_get(self, folder_id: FolderID | None) -> Folder:
        return self._get(Folder, f"/object/folder/{folder_id}")

    # endregion

    # region Items

    @overload
    def item_create(self, item: NewLogin) -> Login: ...

    @overload
    def item_create(self, item: NewIdentity) -> Identity: ...

    @overload
    def item_create(self, item: NewCard) -> Card: ...

    @overload
    def item_create(self, item: NewSSHKey) -> SSHKey: ...

    @overload
    def item_create(self, item: NewSecureNote) -> SecureNote: ...

    def item_create(self, item: NewItem) -> Item:
        return self._post(Item, "/object/item", payload=item)  # type: ignore[arg-type]

    def item_delete(self, item_id: ItemID | Item) -> bool:
        if not isinstance(item_id, str):
            item_id = item_id.id
        return self._delete(f"/object/item/{item_id}")  # type: ignore[arg-type]

    def item_get(self, item_id: ItemID | Item) -> Item:
        if not isinstance(item_id, str):
            item_id = item_id.id
        return self._get(Item, f"/object/item/{item_id}")  # type: ignore[arg-type]

    def item_update(self, item: Item) -> Item:
        return self._put(Item, f"/object/item/{item.id}", payload=item)  # type: ignore[arg-type]

    def item_list(
        self,
        org_id: OrgID | None = None,
        collection_id: CollectionID | None = None,
        folder_id: FolderID | None = None,
        url: str | None = None,
        item_type: ItemType | None = None,
        trash: bool = False,
        search: str | None = None,
    ) -> list[Item]:
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
        response = self._get(ListResponse[Item], "/list/object/items", params=params)
        items = response.data
        if item_type is not None:
            items = [item for item in items if item.type == item_type]
        return items

    # endregion

    # region Combo Methods for Creating / Finding Resources

    def create_or_get_folder_id(
        self, folder_id: FolderID | None, folder_name: str | None, create_if_missing: bool
    ) -> FolderID | None:
        if folder_id is not None and folder_name is not None:
            raise ValueError("Cannot specify both folder_id and folder_name")
        if folder_id is not None:
            return folder_id
        if folder_name is not None:
            folder = self.folder_find(name=folder_name)
            if folder is not None:
                return folder.id
            if create_if_missing:
                folder = self.folder_create(name=folder_name)
                return folder.id
            raise ValueError(f"Folder with name '{folder_name}' not found")

    def create_or_get_collection_id(
        self,
        collection_ids: list[CollectionID] | CollectionID | None,
        collection_names: list[str] | str | None,
        organization_id: OrgID | None,
        collection_create_if_missing: bool,
    ) -> list[CollectionID] | None:
        if collection_ids is not None and collection_names is not None:
            raise ValueError("Cannot specify both collection_ids and collection_names")
        if collection_ids is not None:
            if not isinstance(collection_ids, list):
                return [collection_ids]
            return collection_ids
        if collection_names is not None:
            if organization_id is None:
                raise ValueError("organization_id must be specified when using collection_names")
        raise NotImplementedError()

    def create_login(
        self,
        name: str,
        username: str | None = None,
        password: pydantic.SecretStr | None = None,
        totp: str | None = None,
        uris: list[UriMatch] | None = None,
        notes: str | None = None,
        favorite: bool = False,
        reprompt: bool = False,
        fields: list[Fields] | None = None,
        folder_id: FolderID | None = None,
        collection_ids: list[CollectionID] | CollectionID | None = None,
        organization_id: OrgID | None = None,
    ) -> Login:
        if collection_ids is not None and not isinstance(collection_ids, list):
            collection_ids = [collection_ids]

        return self.item_create(
            NewLogin(
                name=name,
                folder_id=folder_id,
                collection_ids=collection_ids,
                favorite=favorite,
                reprompt=reprompt,
                fields=fields,
                organization_id=organization_id,
                notes=notes,
                login=NewLoginData(
                    username=username,
                    password=password,
                    totp=totp,
                    uris=uris,
                ),
            )
        )

    def create_securenote(
        self,
        name: str,
        notes: str | None = None,
        favorite: bool = False,
        reprompt: bool = False,
        fields: list[Fields] | None = None,
        folder_id: FolderID | None = None,
        collection_ids: list[CollectionID] | CollectionID | None = None,
        organization_id: OrgID | None = None,
    ) -> SecureNote:
        if collection_ids is not None and not isinstance(collection_ids, list):
            collection_ids = [collection_ids]

        return self.item_create(
            NewSecureNote(
                name=name,
                folder_id=folder_id,
                collection_ids=collection_ids,
                favorite=favorite,
                organization_id=organization_id,
                notes=notes,
                reprompt=reprompt,
                fields=fields,
            )
        )

    def create_card(
        self,
        name: str,
        cardholder_name: str | None = None,
        brand: str | None = None,
        number: pydantic.SecretStr | None = None,
        exp_month: int | None = None,
        exp_year: int | None = None,
        code: pydantic.SecretStr | None = None,
        notes: str | None = None,
        favorite: bool = False,
        reprompt: bool = False,
        fields: list[Fields] | None = None,
        folder_id: FolderID | None = None,
        collection_ids: list[CollectionID] | CollectionID | None = None,
        organization_id: OrgID | None = None,
    ) -> Card:
        if collection_ids is not None and not isinstance(collection_ids, list):
            collection_ids = [collection_ids]

        return self.item_create(
            NewCard(
                name=name,
                folder_id=folder_id,
                collection_ids=collection_ids,
                favorite=favorite,
                organization_id=organization_id,
                reprompt=reprompt,
                fields=fields,
                notes=notes,
                card=CardData(
                    cardholder_name=cardholder_name,
                    brand=brand,
                    number=number,
                    exp_month=exp_month,
                    exp_year=exp_year,
                    code=code,
                ),
            )
        )

    # endregion
