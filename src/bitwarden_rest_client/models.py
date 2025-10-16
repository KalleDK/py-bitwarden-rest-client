import enum
from datetime import datetime
from typing import Annotated, Any, Literal, NewType, Union

import pydantic

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


class ActionResponse(pydantic.BaseModel, extra="forbid"):
    noColor: bool
    object: str
    title: str
    message: str | None


class LockResponse(ActionResponse, extra="forbid"):
    pass


class UnlockResponse(ActionResponse, extra="forbid"):
    raw: str


class SyncResponse(ActionResponse, extra="forbid"):
    pass


class UnlockPayload(pydantic.BaseModel):
    password: pydantic.SecretStr

    @pydantic.field_serializer("password", when_used="json")
    def serialize_password(self, password: pydantic.SecretStr) -> str:
        return password.get_secret_value()


class GeneratePasswordResponse(pydantic.BaseModel):
    object: Literal["string"]
    data: pydantic.SecretStr


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
    match: URIMatch | None
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

    @pydantic.field_serializer("password", when_used="json")
    def serialize_password(self, password: pydantic.SecretStr | None) -> str | None:
        if password is None:
            return None
        return password.get_secret_value()


class ItemLogin(pydantic.BaseModel, extra="forbid"):
    object: Literal["item"] = pydantic.Field(exclude=True)
    type: Literal[ItemType.login] = pydantic.Field(exclude=True)
    id: ItemID = pydantic.Field(exclude=True)
    folder_id: FolderID | None = pydantic.Field(alias="folderId")
    organization_id: OrgID | None = pydantic.Field(alias="organizationId")
    collection_ids: list[CollectionID] | None = pydantic.Field(default=None, alias="collectionIds")
    attachments: list[Any] = pydantic.Field(alias="attachments", default_factory=list[Any])
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
