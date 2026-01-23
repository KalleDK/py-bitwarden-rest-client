import enum
from datetime import datetime
from typing import Annotated, Any, Literal, NewType, Union

import pydantic


class BaseLooseModel(pydantic.BaseModel, validate_by_name=True, validate_by_alias=True, serialize_by_alias=True):
    pass


class BaseStrictModel(BaseLooseModel, extra="forbid"):
    pass


# region API Models


class Response[T](pydantic.BaseModel):
    success: bool
    data: T


class ListResponse[T](pydantic.BaseModel):
    object: Literal["list"]
    data: list[T]


class DeleteResponse(BaseStrictModel):
    success: bool


# endregion

# region Lock / Unlock Models


class ActionResponse(BaseStrictModel):
    noColor: bool
    object: str
    title: str
    message: str | None


class LockResponse(ActionResponse):
    pass


class UnlockResponse(ActionResponse):
    raw: str


class SyncResponse(ActionResponse):
    pass


class UnlockPayload(BaseStrictModel):
    password: pydantic.SecretStr

    @pydantic.field_serializer("password", when_used="json")
    def serialize_password(self, password: pydantic.SecretStr) -> str:
        return password.get_secret_value()


class GeneratePasswordResponse(BaseStrictModel):
    object: Literal["string"]
    data: pydantic.SecretStr


# endregion

# region Folder Models

FolderID = NewType("FolderID", str)


class Folder(BaseStrictModel):
    object: Literal["folder"] = pydantic.Field(exclude=True)
    name: str
    id: FolderID | None = pydantic.Field(exclude=True)


class FolderNew(BaseStrictModel):
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
    ssh = 5


class SecureNoteType(enum.IntEnum):
    generic = 0  # This is a guess based on Bitwarden's API documentation


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


class UriMatch(BaseStrictModel):
    match: URIMatch | None = None
    uri: str


class PasswordHistory(BaseStrictModel):
    last_used: datetime = pydantic.Field(serialization_alias="lastUsedDate", validation_alias="lastUsedDate")
    password: pydantic.SecretStr

    @pydantic.field_serializer("password", when_used="json")
    def serialize_secretstr(self, value: pydantic.SecretStr | None) -> str | None:
        if value is None:
            return None
        return value.get_secret_value()


class FieldText(BaseStrictModel):
    type: Literal[FieldType.text] = pydantic.Field(default=FieldType.text)
    name: str
    value: str
    linkedId: None = None


class FieldHidden(BaseStrictModel):
    type: Literal[FieldType.hidden] = pydantic.Field(default=FieldType.hidden)
    name: str
    value: pydantic.SecretStr
    linkedId: None = None

    @pydantic.field_serializer("value", when_used="json")
    def serialize_secretstr(self, value: pydantic.SecretStr | None) -> str | None:
        if value is None:
            return None
        return value.get_secret_value()


class FieldCheckbox(BaseStrictModel):
    type: Literal[FieldType.checkbox] = pydantic.Field(default=FieldType.checkbox)
    name: str
    value: bool
    linkedId: None = None


class FieldLinked(BaseStrictModel):
    type: Literal[FieldType.linked] = pydantic.Field(default=FieldType.linked)
    name: str
    value: None = None
    linkedId: LinkedType


Fields = Annotated[Union[FieldText, FieldHidden, FieldCheckbox, FieldLinked], pydantic.Field(discriminator="type")]


class ItemBase(BaseStrictModel):
    object: Literal["item"] = pydantic.Field(exclude=True)
    id: ItemID = pydantic.Field(exclude=True)
    folder_id: FolderID | None = pydantic.Field(
        default=None, serialization_alias="folderId", validation_alias="folderId"
    )
    organization_id: OrgID | None = pydantic.Field(
        default=None, serialization_alias="organizationId", validation_alias="organizationId"
    )
    collection_ids: list[CollectionID] | None = pydantic.Field(
        default=None, serialization_alias="collectionIds", validation_alias="collectionIds"
    )
    creation_date: datetime = pydantic.Field(
        serialization_alias="creationDate", validation_alias="creationDate", exclude=True
    )
    revision_date: datetime = pydantic.Field(
        serialization_alias="revisionDate", validation_alias="revisionDate", exclude=True
    )
    deleted_date: datetime | None = pydantic.Field(
        default=None, serialization_alias="deletedDate", validation_alias="deletedDate", exclude=True
    )
    name: str
    attachments: list[Any] = pydantic.Field(
        serialization_alias="attachments", validation_alias="attachments", default_factory=list[Any]
    )
    notes: str | None
    fields: list[Fields] | None = None
    favorite: bool
    reprompt: bool

    @pydantic.field_serializer("reprompt", when_used="json")
    def serialize_reprompt(self, value: bool) -> int:
        return 1 if value else 0

    @pydantic.field_validator("reprompt", mode="before")
    def validate_reprompt(cls, value: int | bool) -> bool:
        if isinstance(value, bool):
            return value
        return value == 1

    password_history: list[PasswordHistory] | None = pydantic.Field(
        serialization_alias="passwordHistory", validation_alias="passwordHistory"
    )  # I don't think this makes sense, but all types seem to have it


class LoginData(BaseStrictModel):
    uris: list[UriMatch] | None = None
    username: str | None = None
    password: pydantic.SecretStr | None = None
    totp: str | None = None
    passwordRevisionDate: datetime | None = pydantic.Field(
        default=None, serialization_alias="passwordRevisionDate", validation_alias="passwordRevisionDate", exclude=True
    )
    fido2credentials: list[Any] = pydantic.Field(
        serialization_alias="fido2Credentials",
        validation_alias="fido2Credentials",
        default_factory=list[Any],
        exclude=True,
    )

    @pydantic.field_serializer("password", when_used="json")
    def serialize_secretstr(self, value: pydantic.SecretStr | None) -> str | None:
        if value is None:
            return None
        return value.get_secret_value()


class ItemLogin(ItemBase):
    type: Literal[ItemType.login]
    login: LoginData


class SecureNoteData(BaseStrictModel):
    type: SecureNoteType


class ItemSecureNote(ItemBase):
    type: Literal[ItemType.secure_note] = pydantic.Field(exclude=True)
    secureNote: SecureNoteData = pydantic.Field(serialization_alias="secureNote", validation_alias="secureNote")


class Card(BaseStrictModel):
    cardholder_name: str | None = pydantic.Field(
        serialization_alias="cardholderName", validation_alias="cardholderName"
    )
    brand: str | None
    number: pydantic.SecretStr | None
    exp_month: int | None = pydantic.Field(serialization_alias="expMonth", validation_alias="expMonth")
    exp_year: int | None = pydantic.Field(serialization_alias="expYear", validation_alias="expYear")
    code: pydantic.SecretStr | None

    @pydantic.field_serializer("number", "code", when_used="json")
    def serialize_secretstr(self, value: pydantic.SecretStr | None) -> str | None:
        if value is None:
            return None
        return value.get_secret_value()


class ItemCard(ItemBase):
    type: Literal[ItemType.card] = pydantic.Field(exclude=True)
    card: Card = pydantic.Field(serialization_alias="card", validation_alias="card")


class Identity(BaseStrictModel):
    first_name: str | None = pydantic.Field(serialization_alias="firstName", validation_alias="firstName")
    middle_name: str | None = pydantic.Field(serialization_alias="middleName", validation_alias="middleName")
    last_name: str | None = pydantic.Field(serialization_alias="lastName", validation_alias="lastName")
    title: str | None
    company: str | None
    email: str | None
    phone: str | None
    address1: str | None
    address2: str | None
    address3: str | None
    city: str | None
    state: str | None
    postal_code: str | None = pydantic.Field(serialization_alias="postalCode", validation_alias="postalCode")
    country: str | None
    ssn: str | None
    username: str | None
    passport_number: str | None = pydantic.Field(
        serialization_alias="passportNumber", validation_alias="passportNumber"
    )
    license_number: str | None = pydantic.Field(serialization_alias="licenseNumber", validation_alias="licenseNumber")


class ItemIdentity(ItemBase):
    type: Literal[ItemType.identity] = pydantic.Field(exclude=True)
    identity: Identity = pydantic.Field(serialization_alias="identity", validation_alias="identity")


class SSHKey(BaseStrictModel):
    private_key: pydantic.SecretStr = pydantic.Field(serialization_alias="privateKey", validation_alias="privateKey")
    public_key: str = pydantic.Field(serialization_alias="publicKey", validation_alias="publicKey")
    fingerprint: str = pydantic.Field(serialization_alias="keyFingerprint", validation_alias="keyFingerprint")


class ItemSSH(ItemBase):
    type: Literal[ItemType.ssh] = pydantic.Field(exclude=True)

    ssh_key: SSHKey = pydantic.Field(serialization_alias="sshKey", validation_alias="sshKey")


Item = Annotated[
    Union[ItemLogin, ItemSecureNote, ItemCard, ItemIdentity, ItemSSH], pydantic.Field(discriminator="type")
]


class ItemLoginNew(pydantic.BaseModel):
    type: Literal[ItemType.login] = ItemType.login
    name: str
    folder_id: FolderID | None = pydantic.Field(
        default=None, serialization_alias="folderId", validation_alias="folderId"
    )
    organization_id: OrgID | None = pydantic.Field(
        serialization_alias="organizationId", validation_alias="organizationId", default=None
    )
    collection_ids: list[CollectionID] | None = pydantic.Field(
        serialization_alias="collectionIds", validation_alias="collectionIds", default=None
    )
    login: LoginData
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
