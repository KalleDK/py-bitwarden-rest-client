from functools import wraps
from typing import Annotated, Callable, Coroutine

import pydantic
import typer
from rich.console import Console

from bitwarden_rest_client._async.client import AsyncBitwardenClient
from bitwarden_rest_client._sync.client import BitwardenClient

app = typer.Typer()
console = Console()


def as_sync[**P, R](func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        import asyncio

        return asyncio.run(func(*args, **kwargs))

    return wrapper


@app.command()
@as_sync
async def lock(password: Annotated[str, typer.Option(prompt=True, hide_input=True)]):
    async with AsyncBitwardenClient.session() as session:
        response = await session.lock()
        console.print(response)
        response = await session.unlock(pydantic.SecretStr(password))
        console.print(response)


@app.command()
@as_sync
async def folder(search: Annotated[str | None, typer.Argument()] = None):
    async with AsyncBitwardenClient.session() as session:
        response = await session.folder_list(search=search)
        console.print(response)
        if response:
            folder = response[0]
            response = await session.folder_get(folder.id)
            console.print(response)


@app.command()
def item(search: Annotated[str | None, typer.Argument()] = None):
    with BitwardenClient.session() as session:
        response = session.item_list(search=search)
        console.print(response)


if __name__ == "__main__":
    app()
