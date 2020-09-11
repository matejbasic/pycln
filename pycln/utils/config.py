"""Pycln configuration management utility."""
import configparser
import json
import os
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Pattern, Union

import toml
import typer
import yaml

from . import regexu

# Constants.
CONFIG_SECTIONS = {
    ".cfg": "pycln",
    ".toml": "tool.pycln",
    ".json": "pycln",
    ".yaml": "pycln",
    ".yml": "pycln",
}


@dataclass
class Config:

    """Pycln configs dataclass."""

    def __post_init__(self):
        if self.config is not None:
            file_path = self.config
            self.config = None
            ParseConfigFile(file_path, self)
        else:
            self._check_path()
            self._check_regex()

    path: Path
    config: Optional[Path] = None
    include: Pattern[str] = regexu.INCLUDE_REGEX
    exclude: Pattern[str] = regexu.EXCLUDE_REGEX
    all_: bool = False
    check: bool = False
    diff: bool = False
    verbose: bool = False
    quiet: bool = False
    silence: bool = False
    expand_stars: bool = False
    no_gitignore: bool = False

    def _check_path(self) -> None:
        # Validate `self.path`.
        if not self.path:
            typer.secho(
                "No Path provided. Nothing to do 😴",
                bold=True,
                err=True,
            )
            raise typer.Exit(1)

        if not (self.path.is_dir() or self.path.is_file()):
            typer.secho(
                f"'{self.path}' is not a directory or a file."
                + " Maybe it does not exist 😅",
                bold=True,
                err=True,
            )
            raise typer.Exit(1)

    def _check_regex(self) -> None:
        # Validate `self.include/exclude`.
        self.include: Pattern[str] = regexu.safe_compile(
            str(self.include), regexu.INCLUDE
        )
        self.exclude: Pattern[str] = regexu.safe_compile(
            str(self.exclude), regexu.EXCLUDE
        )

    def get_relpath(self, src: Union[Path, str]) -> Path:
        """Get relative path from the given `src`.

        :param src: an absolute path.
        :returns: a relative path (relative to `self.configs.path`).
        """
        relpath = Path(src)
        if not relpath.is_file():
            os_relpath = os.path.relpath(relpath, self.path)
            relpath = Path(os.path.join(self.path, os_relpath))
        return relpath


class ParseConfigFile:

    """Conifg file parser.

    :param file_path: config file path.
    :param config: Config instance as base.
    """

    def __init__(self, file_path: Path, config: Config):
        self._path = file_path
        self._config = config
        self._section = CONFIG_SECTIONS.get(self._path.suffix, None)
        self.parse()
        self._config.__post_init__()

    def parse(self) -> None:
        """Get conifg from a `cfg`/`toml`/`json`/`yaml`/`yml` file."""
        if not self._path.is_file():
            typer.secho(
                f"Config file {str(self._path)!r} does not exist 😅", bold=True, err=True
            )
            raise typer.Exit(1)
        if self._section is None:
            typer.secho(
                f"Config file {str(self._path)!r} is not supported 😅",
                bold=True,
                err=True,
            )
            typer.secho(f"Supported types: {CONFIG_SECTIONS.keys()}.", err=True)
            raise typer.Exit(1)
        getattr(self, f"_parse_{self._path.suffix.strip('.')}")()

    def _parse_cfg(self) -> None:
        # Parse `.cfg` file.
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.read(self._path)
        configs = parser._sections.get(self._section, {})  # type: ignore
        self._config_loader(configs)

    def _parse_toml(self) -> None:
        # Parse `.toml` file.
        parsed_toml = toml.load(self._path)
        tool, pycln = self._section.split(".")
        configs = parsed_toml.get(tool, {}).get(pycln, {})
        self._config_loader(configs)

    def _parse_json(self) -> None:
        # Parse `.json` file.
        with tokenize.open(self._path) as stream:
            parsed_json = json.load(stream)
        configs = parsed_json.get(self._section, {})
        self._config_loader(configs)

    def _parse_yaml(self) -> None:
        # Parse `.yaml` file.
        with tokenize.open(self._path) as stream:
            parsed_yaml = yaml.load(stream, Loader=yaml.SafeLoader)
        configs = parsed_yaml.get(self._section, {})
        self._config_loader(configs)

    def _parse_yml(self) -> None:
        # Support `.yml` file.
        return self._parse_yaml()

    def _config_loader(self, config_dict: dict) -> None:
        # k, v: config loader.
        if config_dict:
            for k, v in config_dict.items():
                # Python preserved name.
                # `all` ~> `all_`.
                k = "all_" if k == "all" else k
                if hasattr(Config, k):
                    setattr(self._config, k, v)
