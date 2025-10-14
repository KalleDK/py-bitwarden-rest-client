import contextlib
import enum
import json
import logging
from datetime import datetime
from typing import Annotated, Any, Literal, NewType, Union

import httpx
import pydantic

_log = logging.getLogger(__name__)

# region API Models


class Response[T](pydantic.BaseModel):
    success: bool
    data: T


class ListResponse[T](pydantic.BaseModel):
    object: Literal["list"]
    data: list[T]


class DeleteResponse(pydantic.BaseModel, extra="forbid"):
    success: bool


# endregion

# region Lock / Unlock Models


class LockResponse(pydantic.BaseModel, extra="forbid"):
    noColor: bool
    object: str
    title: str
    message: str | None


class UnlockResponse(pydantic.BaseModel, extra="forbid"):
    noColor: bool
    object: str
    title: str
    message: str
    raw: str


class UnlockPayload(pydantic.BaseModel):
    password: pydantic.SecretStr

    @pydantic.field_serializer("password", when_used="json")
    def serialize_password(self, password: pydantic.SecretStr) -> str:
        return password.get_secret_value()


# endregion

# region Folder Models

FolderID = NewType("FolderID", str)


class Folder(pydantic.BaseModel):
    object: Literal["folder"] = pydantic.Field(exclude=True)
    name: str
    id: FolderID | None = pydantic.Field(exclude=True)


class FolderNew(pydantic.BaseModel):
    name: str


# endregion

# region Collection Models

CollectionID = NewType("CollectionID", str)

# endregion

# region Item Models

ItemID = NewType("ItemID", str)
OrgID = NewType("OrgID", str)


class ItemType(enum.IntEnum):
    login = 1
    secure_note = 2
    card = 3
    identity = 4


class URIMatch(enum.IntEnum):
    base_domain = 0
    host = 1
    starts_with = 2
    exact = 3
    regex = 4
    never = 5


class FieldType(enum.IntEnum):
    text = 0
    hidden = 1
    checkbox = 2
    linked = 3


class LinkedType(enum.IntEnum):
    username = 100
    password = 101


class UriMatch(pydantic.BaseModel, extra="forbid"):
    match: URIMatch
    uri: str


class PasswordHistory(pydantic.BaseModel, extra="forbid"):
    last_used: datetime = pydantic.Field(alias="lastUsedDate")
    password: pydantic.SecretStr


class FieldText(pydantic.BaseModel, extra="forbid"):
    type: Literal[FieldType.text] = pydantic.Field(exclude=True)
    name: str
    value: str
    linkedId: None


class FieldHidden(pydantic.BaseModel, extra="forbid"):
    type: Literal[FieldType.hidden] = pydantic.Field(exclude=True)
    name: str
    value: pydantic.SecretStr
    linkedId: None


class FieldCheckbox(pydantic.BaseModel, extra="forbid"):
    type: Literal[FieldType.checkbox] = pydantic.Field(exclude=True)
    name: str
    value: bool
    linkedId: None


class FieldLinked(pydantic.BaseModel, extra="forbid"):
    type: Literal[FieldType.linked] = pydantic.Field(exclude=True)
    name: str
    value: None
    linkedId: LinkedType


Fields = Annotated[Union[FieldText, FieldHidden, FieldCheckbox, FieldLinked], pydantic.Field(discriminator="type")]


class ItemLoginData(pydantic.BaseModel, extra="forbid"):
    uris: list[UriMatch] | None = None
    username: str | None = None
    password: pydantic.SecretStr | None = None
    totp: str | None = None
    passwordRevisionDate: datetime | None = pydantic.Field(default=None, alias="passwordRevisionDate", exclude=True)


class ItemLogin(pydantic.BaseModel, extra="forbid"):
    object: Literal["item"] = pydantic.Field(exclude=True)
    type: Literal[ItemType.login] = pydantic.Field(exclude=True)
    id: ItemID = pydantic.Field(exclude=True)
    folder_id: FolderID | None = pydantic.Field(alias="folderId")
    organization_id: OrgID | None = pydantic.Field(alias="organizationId")
    collection_ids: list[CollectionID] | None = pydantic.Field(default=None, alias="collectionIds")
    creation_date: datetime = pydantic.Field(alias="creationDate")
    revision_date: datetime = pydantic.Field(alias="revisionDate")
    deleted_date: datetime | None = pydantic.Field(alias="deletedDate")
    name: str
    login: ItemLoginData
    notes: str | None
    fields: list[Fields] | None = None
    reprompt: bool
    favorite: bool
    password_history: list[PasswordHistory] | None = pydantic.Field(alias="passwordHistory")

    @pydantic.field_serializer("reprompt", when_used="json")
    def serialize_reprompt(self, value: bool) -> int:
        return 1 if value else 0

    @pydantic.field_validator("reprompt", mode="before")
    def validate_reprompt(cls, value: int | bool) -> bool:
        if isinstance(value, bool):
            return value
        return value == 1


class ItemSecureNote(pydantic.BaseModel, extra="forbid"):
    object: Literal["item"] = pydantic.Field(exclude=True)
    type: Literal[ItemType.secure_note] = pydantic.Field(exclude=True)
    secureNote: dict[str, Any] = pydantic.Field(alias="secureNote")
    id: ItemID = pydantic.Field(exclude=True)
    folder_id: FolderID | None = pydantic.Field(alias="folderId")
    organization_id: OrgID | None = pydantic.Field(alias="organizationId")
    collection_ids: list[CollectionID] | None = pydantic.Field(alias="collectionIds")
    creation_date: datetime = pydantic.Field(alias="creationDate")
    revision_date: datetime = pydantic.Field(alias="revisionDate")
    deleted_date: datetime | None = pydantic.Field(alias="deletedDate")
    name: str
    notes: str | None
    fields: list[Fields] | None = None
    reprompt: bool
    favorite: bool
    password_history: list[PasswordHistory] | None = pydantic.Field(alias="passwordHistory")


class Card(pydantic.BaseModel, extra="forbid"):
    cardholder_name: str | None = pydantic.Field(alias="cardholderName")
    brand: str | None
    number: pydantic.SecretStr | None
    exp_month: int | None = pydantic.Field(alias="expMonth")
    exp_year: int | None = pydantic.Field(alias="expYear")
    code: pydantic.SecretStr | None


class ItemCard(pydantic.BaseModel, extra="forbid"):
    object: Literal["item"] = pydantic.Field(exclude=True)
    type: Literal[ItemType.card] = pydantic.Field(exclude=True)
    id: ItemID = pydantic.Field(exclude=True)
    folder_id: FolderID | None = pydantic.Field(alias="folderId")
    organization_id: OrgID | None = pydantic.Field(alias="organizationId")
    collection_ids: list[CollectionID] | None = pydantic.Field(alias="collectionIds")
    creation_date: datetime = pydantic.Field(alias="creationDate")
    revision_date: datetime = pydantic.Field(alias="revisionDate")
    deleted_date: datetime | None = pydantic.Field(alias="deletedDate")
    name: str
    card: Card = pydantic.Field(alias="card")
    notes: str | None
    fields: list[Fields] | None = None
    reprompt: bool
    favorite: bool
    password_history: list[PasswordHistory] | None = pydantic.Field(alias="passwordHistory")


class Identity(pydantic.BaseModel, extra="forbid"):
    first_name: str | None = pydantic.Field(alias="firstName")
    middle_name: str | None = pydantic.Field(alias="middleName")
    last_name: str | None = pydantic.Field(alias="lastName")
    title: str | None
    company: str | None
    email: str | None
    phone: str | None
    address1: str | None
    address2: str | None
    address3: str | None
    city: str | None
    state: str | None
    postal_code: str | None = pydantic.Field(alias="postalCode")
    country: str | None
    ssn: str | None
    username: str | None
    passport_number: str | None = pydantic.Field(alias="passportNumber")
    license_number: str | None = pydantic.Field(alias="licenseNumber")


class ItemIdentity(pydantic.BaseModel, extra="forbid"):
    object: Literal["item"] = pydantic.Field(exclude=True)
    type: Literal[ItemType.identity] = pydantic.Field(exclude=True)
    identity: Identity = pydantic.Field(alias="identity")
    id: ItemID = pydantic.Field(exclude=True)
    folder_id: FolderID | None = pydantic.Field(alias="folderId")
    organization_id: OrgID | None = pydantic.Field(alias="organizationId")
    collection_ids: list[CollectionID] | None = pydantic.Field(alias="collectionIds")
    creation_date: datetime = pydantic.Field(alias="creationDate")
    revision_date: datetime = pydantic.Field(alias="revisionDate")
    deleted_date: datetime | None = pydantic.Field(alias="deletedDate")
    name: str
    notes: str | None
    fields: list[Fields] | None = None
    reprompt: bool
    favorite: bool
    password_history: list[PasswordHistory] | None = pydantic.Field(alias="passwordHistory")


Items = Annotated[Union[ItemLogin, ItemSecureNote, ItemCard, ItemIdentity], pydantic.Field(discriminator="type")]


class ItemLoginNew(pydantic.BaseModel):
    type: Literal[ItemType.login] = ItemType.login
    name: str
    folder_id: FolderID | None = pydantic.Field(alias="folderId", default=None)
    organization_id: OrgID | None = pydantic.Field(alias="organizationId", default=None)
    collection_ids: list[CollectionID] | None = pydantic.Field(alias="collectionIds", default=None)
    login: ItemLoginData
    notes: str | None = None
    fields: list[Fields] | None = None
    reprompt: bool = False
    favorite: bool = False

    @pydantic.field_serializer("reprompt", when_used="json")
    def serialize_reprompt(self, value: bool) -> int:
        return 1 if value else 0

    @pydantic.field_validator("reprompt", mode="before")
    def validate_reprompt(cls, value: int | bool) -> bool:
        if isinstance(value, bool):
            return value
        return value == 1


# endregion


class BitwardenClient:
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
        print(json.dumps(obj, indent=2))  # DEBUG
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
