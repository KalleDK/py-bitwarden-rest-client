import dataclasses
import pathlib

import pydantic

from bitwarden_rest_client.consts import DEFAULT_APP_DATA, DEFAULT_BIN_PATH, DEFAULT_PORT


@dataclasses.dataclass(kw_only=True, slots=True)
class ServerConfig:
    bw_path: pathlib.Path = DEFAULT_BIN_PATH
    bw_appdata_dir: pathlib.Path = DEFAULT_APP_DATA
    port: int = DEFAULT_PORT
    client_id: str
    client_secret: pydantic.SecretStr
