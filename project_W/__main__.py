import click

from project_W import __version__, create_app


@click.command()
@click.version_option(__version__)
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=8080, show_default=True)
@click.option("--customConfigPath", required=False)
def main(host: str, port: int, customconfigpath=None):
    app = create_app(customConfigPath=customconfigpath)
    app.run(host=host, port=port)
