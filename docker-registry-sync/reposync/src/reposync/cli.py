import asyncio
import logging
from pathlib import Path
from pprint import pformat
import yaml_include

import typer
import yaml
from pydantic import NonNegativeInt, TypeAdapter
from typing_extensions import Annotated

from ._models import Configuration
from ._sync import run_sync_tasks

_logger = logging.getLogger(__name__)

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)


def _configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def _get_configuration(config_file: Path) -> Configuration:
    _logger.debug("Confoguration path: '%s'", config_file)

    # allows the usage of `!include another_file.yaml` inside the configuration
    yaml.add_constructor(
        "!include", yaml_include.Constructor(base_dir=config_file.parent)
    )
    parased_yaml = yaml.full_load(config_file.read_text())

    configuration = TypeAdapter(Configuration).validate_python(parased_yaml)
    _logger.info(
        "Parsed configuration:\n%s", pformat(configuration.model_dump(mode="python"))
    )
    return configuration


async def _repo_sync(
    config_file: Path,
    verify_only: bool,
    parallel_sync_tasks: NonNegativeInt,
    use_explicit_tags: bool,
    debug: bool,
) -> None:
    _configure_logging(debug)

    configuration = _get_configuration(config_file)

    if verify_only:
        _logger.info("Configuration is OK, closing gracefully.")
        return

    await run_sync_tasks(
        configuration,
        use_explicit_tags=use_explicit_tags,
        parallel_sync_tasks=parallel_sync_tasks,
    )


@app.command()
def run_repo_sync(
    config_file: Annotated[
        Path,
        typer.Argument(help="configuration file to be used", exists=True),
    ],
    verify_only: Annotated[
        bool, typer.Option(help="check configuration file only", allow_dash=True)
    ] = False,
    parallel_sync_tasks: Annotated[
        NonNegativeInt,
        typer.Option(
            help="amount of parallel sync tasks to be run at once", allow_dash=True
        ),
    ] = 10,
    use_explicit_tags: Annotated[
        bool,
        typer.Option(
            help="if enabled tags have to be set explictly before they are synced otherwise `tags: []` is interpreted as all tags",
            allow_dash=True,
        ),
    ] = False,
    debug: Annotated[
        bool, typer.Option(help="show additional information during sync")
    ] = False,
):
    asyncio.run(
        _repo_sync(
            config_file, verify_only, parallel_sync_tasks, use_explicit_tags, debug
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
