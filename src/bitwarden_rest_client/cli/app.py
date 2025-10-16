import enum
from typing import Annotated, cast

import pydantic
import typer
from rich.console import Console

from bitwarden_rest_client._sync.client import BitwardenClient
from bitwarden_rest_client.models import ItemLoginData, ItemLoginNew, URIMatch, UriMatch

app = typer.Typer()
console = Console()


@app.command()
def lock():
    with BitwardenClient.session() as session:
        response = session.lock()
        console.print(response)


def as_secret(value: str | pydantic.SecretStr) -> pydantic.SecretStr:
    if isinstance(value, pydantic.SecretStr):
        return value
    return pydantic.SecretStr(value)


@app.command()
def unlock(
    password: Annotated[pydantic.SecretStr, typer.Option(prompt=True, hide_input=True, parser=as_secret)],
):
    with BitwardenClient.session() as session:
        response = session.unlock(password)
        console.print(response)


@app.command()
def sync():
    with BitwardenClient.session() as session:
        response = session.sync()
        console.print(response)


@app.command()
def password(
    length: Annotated[int, typer.Argument()] = 20,
    lowercase: Annotated[bool, typer.Option("--lowercase/--no-lowercase", "-l/-L")] = True,
    uppercase: Annotated[bool, typer.Option("--uppercase/--no-uppercase", "-u/-U")] = True,
    numbers: Annotated[bool, typer.Option("--numbers/--no-numbers", "-n/-N")] = True,
    special: Annotated[bool, typer.Option("--special/--no-special", "-s/-S")] = False,
):
    with BitwardenClient.session() as session:
        response = session.generate_password(
            length=length, lowercase=lowercase, uppercase=uppercase, numbers=numbers, special=special
        )
        console.print(response.get_secret_value())


# region Folder

folder_group = typer.Typer()
app.add_typer(folder_group, name="folder")


@folder_group.command("search")
def folder_search(search: Annotated[str | None, typer.Argument()] = None):
    with BitwardenClient.session() as session:
        response = session.folder_list(search=search)
        console.print(response)
        if response:
            folder = response[0]
            response = session.folder_get(folder.id)
            console.print(response)


@folder_group.command("create")
def folder_create(name: str, sync: Annotated[bool, typer.Option("--sync", "-s")] = False):
    with BitwardenClient.session() as session:
        response = session.folder_create(name=name)
        console.print(response)
        if sync:
            response = session.sync()
            console.print(response)


@folder_group.command("list")
def folder_list():
    with BitwardenClient.session() as session:
        response = session.folder_list()
        console.print(response)


# endregion

# region LoginItem

login_group = typer.Typer()
app.add_typer(login_group, name="login")


class Password(enum.StrEnum):
    PROMPT = "-"
    GENERATE = "?"


@login_group.command("create")
def login_create(
    name: str,
    username: Annotated[str | None, typer.Option("--username", "-u")] = None,
    password: Annotated[Password | None, typer.Option("--password", "-p")] = None,
    uri: str | None = None,
    folder: Annotated[str | None, typer.Option("--folder", "-f")] = None,
    sync: Annotated[bool, typer.Option("--sync", "-s")] = False,
):
    with BitwardenClient.session() as session:
        if folder is not None:
            folders = session.folder_list(search=folder)
            folders = [f for f in folders if f.name == folder]
            if not folders:
                console.print(f"[red]Folder '{folder}' not found[/red]")
                raise typer.Exit(code=1)
            if len(folders) > 1:
                console.print(f"[red]Multiple folders found with name '{folder}'[/red]")
                raise typer.Exit(code=1)
            folder_id = folders[0].id
        else:
            folder_id = None
        if uri is not None:
            uris = [
                UriMatch(match=URIMatch.exact, uri=uri),
            ]
        else:
            uris = None
        if password == Password.GENERATE:
            _password = session.generate_password()
        elif password == Password.PROMPT:
            _password = cast(
                pydantic.SecretStr, typer.prompt("Password: ", hide_input=True, value_proc=pydantic.SecretStr)
            )
        else:
            _password = None
        response = session.item_create(
            ItemLoginNew(
                name=name,
                login=ItemLoginData(
                    username=username,
                    password=_password,
                    uris=uris,
                ),
                folderId=folder_id,
            )
        )

        console.print(response)
        if sync:
            response = session.sync()
            console.print(response)


# endregion

# region Item


@app.command()
def item(search: Annotated[str | None, typer.Argument()] = None):
    with BitwardenClient.session() as session:
        response = session.item_list(search=search)
        console.print(response)


# endregion


def main():
    app()
