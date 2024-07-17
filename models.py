from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UserPartial(BaseModel):
    id: str
    username: str
    display_name: str
    avatar_url: str | None = None
    roles: list[str] = Field(default_factory=list)

    def is_subscribed(self):
        return "6076a86b09a4c63a38ebe801" in self.roles

    @field_validator("avatar_url", mode="before")
    @classmethod
    def add_protocol(cls, avatar_url: str | None):
        if avatar_url is not None:
            return "https:" + avatar_url


class EmoteFlags(BaseModel):
    value: int
    private: bool
    authentic: bool
    zero_width: bool
    sexual_content: bool
    epilepsy: bool
    edgy: bool
    twitch_disallowed: bool

    @classmethod
    def from_flags(cls, value: int):
        return cls(
            value=value,
            private=(value >> 0) & 1 == 1,
            authentic=(value >> 1) & 1 == 1,
            zero_width=(value >> 8) & 1 == 1,
            sexual_content=(value >> 16) & 1 == 1,
            epilepsy=(value >> 17) & 1 == 1,
            edgy=(value >> 18) & 1 == 1,
            twitch_disallowed=(value >> 24) & 1 == 1,
        )


class Image(BaseModel):
    name: str
    static_name: str | None = None
    width: int
    height: int
    frame_count: int
    size: int
    format: Literal["AVIF", "WEBP"]


class ImageHost(BaseModel):
    url: str
    files: list[Image]

    @field_validator("url")
    @classmethod
    def add_protocol(cls, url: str):
        return "https:" + url


class EmoteData(BaseModel):
    id: str
    name: str
    flags: EmoteFlags  # see: https://github.com/SevenTV/Website/blob/01d690c62a9978ecc64c972632fa500f837513c9/src/structures/Emote.ts#L59
    tags: list[str] = Field(default_factory=list)
    lifecycle: int
    state: list[Literal["LISTED", "PERSONAL", "NO_PERSONAL"]]
    listed: bool
    animated: bool
    owner: UserPartial | None
    host: ImageHost

    @field_validator("owner")
    @classmethod
    def validate_owner(cls, owner: UserPartial):
        # Deleted user
        if owner.id == "000000000000000000000000":
            return None
        return owner

    @field_validator("flags", mode="before")
    @classmethod
    def validate_flags(cls, value: int) -> EmoteFlags:
        return EmoteFlags.from_flags(value)


class EmoteSetEmote(BaseModel):
    id: str
    name: str
    flags: int
    timestamp: datetime
    actor_id: str | None
    data: EmoteData


class EmoteSet(BaseModel):
    id: str
    name: str
    flags: int
    tags: list[str]
    immutable: bool
    privileged: bool
    emotes: list[EmoteSetEmote] = Field(default_factory=list)
    emote_count: int = 0
    capacity: int
    owner: UserPartial


class EmoteSetPartial(BaseModel):
    id: str
    name: str
    flags: int
    tags: list[str]
    capacity: int


class EditorPermissions(BaseModel):
    value: int
    modify_emotes: bool
    use_private_emotes: bool
    manage_profile: bool
    manage_owned_emotes: bool
    manage_emote_sets: bool
    manage_billing: bool
    manage_editors: bool
    view_messages: bool

    @classmethod
    def to_permissions(cls, permissions: int):
        return cls(
            value=permissions,
            modify_emotes=(permissions >> 0) & 1 == 1,
            use_private_emotes=(permissions >> 1) & 1 == 1,
            manage_profile=(permissions >> 2) & 1 == 1,
            manage_owned_emotes=(permissions >> 3) & 1 == 1,
            manage_emote_sets=(permissions >> 4) & 1 == 1,
            manage_billing=(permissions >> 5) & 1 == 1,
            manage_editors=(permissions >> 6) & 1 == 1,
            view_messages=(permissions >> 7) & 1 == 1,
        )


class UserEditor(BaseModel):
    id: str  # 7tv id
    permissions: EditorPermissions  # see: https://github.com/SevenTV/Common/blob/048a247f3aa41a7bbf9a1fe105025314bcbdef95/structures/v3/type.user.go#L220
    visible: bool
    added_at: datetime

    @field_validator("permissions", mode="before")
    @classmethod
    def validate_permissions(cls, value: int) -> EditorPermissions:
        return EditorPermissions.to_permissions(value)


class UserConnection(BaseModel):
    id: str  # connection id
    platform: Literal["TWITCH", "YOUTUBE", "DISCORD", "KICK"]
    username: str
    display_name: str
    linked_at: datetime


class User(UserPartial):
    emote_sets: list[EmoteSetPartial] = Field(default_factory=list)
    editors: list[UserEditor] = Field(default_factory=list)
    connections: list[UserConnection] = Field(default_factory=list)
