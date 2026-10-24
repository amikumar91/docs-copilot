import typer

from docs_copilot import __version__

app = typer.Typer(help="docs-copilot: ask your docs, with citations.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run the HTTP API."""
    import uvicorn

    uvicorn.run("docs_copilot.api.app:app", host=host, port=port, reload=reload)
