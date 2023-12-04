import click
from project_W import create_app

@click.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=8080, show_default=True)
def main(host: str, port: int):
    app = create_app()
    app.run(host=host, port=port)
