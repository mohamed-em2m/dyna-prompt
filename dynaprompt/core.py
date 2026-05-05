"""
DynaPrompt core — LazyPrompts + _PromptSettings.

Inspired by Dynaconf's LazySettings / Settings separation:
- DynaPrompt is the lazy shell (no I/O at creation time).
- _PromptSettings is the real loaded object, instantiated on first access.
"""

from __future__ import annotations

import os
import pathlib
import re
import warnings
from contextlib import contextmanager
from typing import Any

from .hooking import Hook
from .loaders import get_loader_for
from .nodes import PromptNode, SourceMetadata
from .utils import object_merge
from .validator import PromptValidator, ValidatorList

_SUPPORTED_SUFFIXES = (".toml", ".md", ".txt", ".py", ".json", ".yaml", ".yml")


def _sanitize_name(stem: str) -> str:
    """Normalize a filename stem to a valid, snake_case prompt identifier.

    Examples::

        "Customer Support"  -> "customer_support"
        "call-analysis"     -> "call_analysis"
        "01_intro"          -> "p_01_intro"
        ""                  -> "prompt"
    """
    name = stem.lower()
    # Replace any run of non-alphanumeric chars with a single underscore
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    if not name:
        return "prompt"
    # Identifiers must not start with a digit
    if name[0].isdigit():
        name = f"p_{name}"
    return name


class _PromptSettings:
    """
    The real settings object. Loads files once, resolves env layers,
    and tracks full loading history (like Dynaconf's loaded_by_loaders).
    """

    def __init__(
        self,
        settings_files: list[Any],
        current_env: str = "development",
        file_prefix: str | None = None,
        schemas: dict[str, Any] | None = None,
        variables: list[Any] | None = None,
        auto_render: bool = False,
    ):
        self._current_env = current_env
        self._file_prefix = file_prefix
        self._auto_render = auto_render
        self._schemas = schemas if schemas is not None else {}
        self._variables: dict[str, Any] = {}
        # {env: {name: data_dict}} — raw accumulated from all files
        self._raw_data: dict[str, dict[str, Any]] = {}
        # {name: merged_data} — resolved for current env (rebuilt on env switch)
        self._store: dict[str, Any] = {}
        # {name: [(SourceMetadata, raw_data_dict), ...]}
        self._history: dict[str, list] = {}
        self._validators = ValidatorList()
        self._hooks: dict[str, list[Hook]] = {}
        self._cache: dict[str, PromptNode] = {}
        self._cache_enabled = True

        self._load_variables(variables)
        self._load_files(settings_files)
        self._resolve()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_files(self, settings_files: list[Any]) -> None:
        """Load all configured files/directories in order.

        Two-pass strategy
        -----------------
        Pass 1 — resolve every entry to an absolute path and record which
                  paths are *explicitly* listed by the user (non-directories).
        Pass 2 — load each entry.  For directories, after loading all ``.md``
                  files, automatically load a *companion* TOML file named
                  ``<dirname>.toml`` that sits next to the directory, provided
                  it is not already in the explicit list (prevents double-load).

        Companion TOML convention
        -------------------------
        Given ``settings_files=["prompts/"]``, DynaPrompt will automatically
        load ``prompts.toml`` (if it exists) **after** the ``.md`` files.
        This lets users keep prompt templates as clean ``.md`` files while
        customising model, temperature, and other metadata in a single
        ``prompts.toml`` without touching the template sources.

        Explicit overrides the companion
        ---------------------------------
        If the user passes ``["prompts/", "prompts.toml"]``, the companion
        auto-discovery is suppressed — the explicit entry is used instead.
        """
        # ── Pass 1: resolve paths, record explicitly-listed files ─────────────
        resolved_items: list[Any] = []
        explicit_files: set = set()

        for item in settings_files:
            if isinstance(item, dict):
                resolved_items.append(item)
                continue

            path = pathlib.Path(item)
            if not path.is_absolute():
                path = pathlib.Path.cwd() / path
            # Use the canonical form so comparison is reliable
            path = path.resolve()
            resolved_items.append(path)
            if not path.is_dir():
                explicit_files.add(path)

        # ── Pass 2: load ───────────────────────────────────────────────────────
        for idx, item in enumerate(resolved_items):
            if isinstance(item, dict):
                container_key = f"settings_dict_{idx}"
                self._register_dict_as_variables(item, container_key, "settings")
                continue

            path = item
            if path.is_dir():
                self._load_dir(path)

                # Auto-discover companion <dirname>.toml
                companion = (path.parent / f"{path.name}.toml").resolve()
                if companion.exists() and companion not in explicit_files:
                    self._load_one_file(companion)

            elif path.exists():
                if path.suffix == ".py":
                    # Registers classes as schemas AND all public names as template vars
                    self._load_python_schemas(path)
                elif path.suffix == ".json":
                    # Registers as schema AND flattens keys as template vars
                    self._load_json_schema(path)
                    self._load_variables_file(path)
                elif path.suffix in (".yaml", ".yml"):
                    # Registers as schema AND flattens keys as template vars
                    self._load_yaml_schema(path)
                    self._load_variables_file(path)
                else:
                    self._load_one_file(path)
            else:
                # Silent: missing secrets/overlay file is normal
                pass

    def _merge_var(self, key: str, value: Any, source_tag: str) -> None:
        """Set a variable, namespacing on collision: key -> <key>_<source_tag>."""
        if self._auto_render and isinstance(value, str) and "{{" in value:
            try:
                import jinja2

                jinja_env = jinja2.Environment(undefined=jinja2.Undefined)
                value = jinja_env.from_string(value).render(**self._variables)
            except Exception as e:
                warnings.warn(
                    f"DynaPrompt: Failed to auto-render variable '{key}': {e}",
                    UserWarning,
                    stacklevel=5,
                )

        if key in self._variables and self._variables[key] is not value:
            namespaced = f"{key}_{source_tag}"
            if (
                namespaced in self._variables
                and self._variables[namespaced] is not value
            ):
                warnings.warn(
                    f"DynaPrompt: Variable '{key}' already exists from a different "
                    f"source. Both '{key}' and '{namespaced}' already set — skipping. "
                    "Rename one of your sources to avoid ambiguity.",
                    UserWarning,
                    stacklevel=4,
                )
                return
            warnings.warn(
                f"DynaPrompt: Variable '{key}' already exists. "
                f"Saving as '{namespaced}' to avoid overwriting the original.",
                UserWarning,
                stacklevel=4,
            )
            self._variables[namespaced] = value
        else:
            self._variables[key] = value

    def _register_dict_as_variables(
        self,
        data: dict[str, Any],
        container_key: str,
        source_tag: str,
    ) -> None:
        """Register *data* as a whole under *container_key* AND each element
        separately.
        """
        # Handle environment layering if present
        is_env_layered = "default" in data and isinstance(data["default"], dict)

        if is_env_layered:
            # Merge 'default' and the current environment key
            final_data: dict[str, Any] = {}
            object_merge(final_data, data.get("default", {}))
            env_data = data.get(self._current_env)
            if isinstance(env_data, dict):
                object_merge(final_data, env_data)
            data = final_data

        # 1. Whole object under container key
        self._merge_var(container_key, data, source_tag)

        # 2. Each element separately (recursively if dict)
        def _flatten(d: dict[str, Any]) -> None:
            for k, v in d.items():
                self._merge_var(k, v, source_tag)
                if isinstance(v, dict):
                    _flatten(v)

        _flatten(data)

    def _load_variables(self, variables: list[Any] | None) -> None:
        """Load and merge global template variables from files or dicts.

        Each item can be:
        - ``dict``    – saved under an auto-key and all keys flattened separately.
        - ``str/Path``  – path to a ``.py``, ``.json``, ``.yaml``, or ``.toml`` file.

        Collisions are resolved by namespacing: ``<key>_<source_tag>``.
        """
        if not variables:
            return

        for idx, item in enumerate(variables):
            if isinstance(item, dict):
                warnings.warn(
                    "DynaPrompt: Merging direct dictionary into variables. "
                    "Keys already present will be disambiguated by source tag.",
                    UserWarning,
                    stacklevel=3,
                )
                container_key = f"dict_{idx}"
                self._register_dict_as_variables(item, container_key, "dict")
            elif isinstance(item, (str, pathlib.Path)):
                path = pathlib.Path(item)
                if not path.is_absolute():
                    path = pathlib.Path.cwd() / path
                path = path.resolve()
                if path.exists():
                    self._load_variables_file(path)
                else:
                    warnings.warn(
                        f"DynaPrompt: Variables file not found: {path}",
                        UserWarning,
                        stacklevel=3,
                    )

    def _load_variables_file(self, path: pathlib.Path) -> None:
        """Load variables from a supported file and register them.

        Rules per file type
        -------------------
        ``.py``
            All module-level names that don't start with ``_`` are saved as
            template variables.  Classes are *also* registered in ``_schemas``.
        ``.json`` / ``.yaml`` / ``.yml`` / ``.toml``
            The whole parsed object is saved under ``<stem>`` (or
            ``<stem>_<ext>`` on collision). Each top-level key is also
            saved individually (with ``<key>_<stem>`` on collision).
        """
        suffix = path.suffix.lower()
        source_tag = path.stem

        try:
            if suffix == ".py":
                self._load_python_variables(path)
                return

            if suffix == ".json":
                import json

                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                file_source_tag = "json"
            elif suffix in (".yaml", ".yml"):
                import yaml

                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                file_source_tag = "yaml"
            elif suffix == ".toml":
                try:
                    import tomllib
                except ImportError:
                    try:
                        import tomli as tomllib  # type: ignore[no-redef]
                    except ImportError:
                        raise ImportError(
                            "TOML support requires Python 3.11+ or `pip install tomli`"
                        )
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                file_source_tag = "toml"
            else:
                warnings.warn(
                    f"DynaPrompt: Unsupported variables file format: {suffix}",
                    UserWarning,
                    stacklevel=3,
                )
                return

            if not isinstance(data, dict):
                warnings.warn(
                    f"DynaPrompt: Variables file '{path.name}' did not produce "
                    "a dict — skipped.",
                    UserWarning,
                    stacklevel=3,
                )
                return

            # Env-layered file? (has a 'default' key with dict values)
            is_env_layered = "default" in data and isinstance(data["default"], dict)
            if is_env_layered:
                merged: dict[str, Any] = {}
                object_merge(merged, data.get("default", {}))
                if self._current_env != "default":
                    object_merge(merged, data.get(self._current_env, {}))
                data = merged

            self._register_dict_as_variables(data, source_tag, file_source_tag)

        except Exception as e:
            warnings.warn(
                f"DynaPrompt: Failed to load variables from '{path}': {e}",
                UserWarning,
                stacklevel=3,
            )

    def _load_python_variables(self, path: pathlib.Path) -> None:
        """Import a ``.py`` file and register its public names as variables.

        - Module-level classes → ``_schemas`` (existing behaviour) *and* ``_variables``.
        - All other non-private names → ``_variables``.
        """
        import importlib.util
        import inspect
        import sys

        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return

        mod = importlib.util.module_from_spec(spec)
        parent_dir = str(path.parent)
        added_to_path = parent_dir not in sys.path
        if added_to_path:
            sys.path.insert(0, parent_dir)

        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            warnings.warn(
                f"DynaPrompt: Failed to import '{path}': {e}",
                UserWarning,
                stacklevel=4,
            )
            return
        finally:
            if added_to_path and parent_dir in sys.path:
                sys.path.remove(parent_dir)

        source_tag = "py"
        for name in dir(mod):
            if name.startswith("_"):
                continue
            obj = getattr(mod, name)
            # Only register names actually defined in this module
            origin = getattr(obj, "__module__", None)
            if origin is not None and origin != mod.__name__:
                continue
            if inspect.isclass(obj):
                # Register as schema
                self._schemas[name] = obj
            # Register everything (including classes) as a template variable
            self._merge_var(name, obj, source_tag)

    def _load_dir(self, directory: pathlib.Path) -> None:
        """Load all supported files in *directory* with name sanitization.

        - Only files whose stem starts with ``self._file_prefix`` are loaded
          (when a prefix is configured). The prefix is stripped from the name.
        - Filename stems are normalized to valid snake_case identifiers via
          :func:`_sanitize_name`.
        - Collisions after normalization are resolved by appending ``_2``,
          ``_3``, … and a :class:`UserWarning` is emitted.
        """
        seen: dict[str, pathlib.Path] = {}  # sanitized_name -> first source path

        for child in sorted(directory.iterdir()):
            if child.suffix not in _SUPPORTED_SUFFIXES:
                continue

            stem = child.stem

            # ── Prefix filter ────────────────────────────────────────────────
            if self._file_prefix:
                if not stem.startswith(self._file_prefix):
                    continue
                # Strip prefix so the API name is clean
                stem = stem[len(self._file_prefix) :]

            # ── Sanitize ─────────────────────────────────────────────────────
            sanitized = _sanitize_name(stem)

            # ── Collision handling ───────────────────────────────────────────
            if sanitized in seen:
                i = 2
                candidate = f"{sanitized}_{i}"
                while candidate in seen:
                    i += 1
                    candidate = f"{sanitized}_{i}"
                warnings.warn(
                    f"DynaPrompt: name collision in directory '{directory}' — "
                    f"'{child.name}' normalizes to '{sanitized}' which is already "
                    f"taken by '{seen[sanitized].name}'. "
                    f"Renaming to '{candidate}'.",
                    UserWarning,
                    stacklevel=5,
                )
                sanitized = candidate

            seen[sanitized] = child
            if child.suffix == ".py":
                self._load_python_schemas(child)
            elif child.suffix == ".json":
                self._load_json_schema(child)
                self._load_variables_file(child)
            elif child.suffix in (".yaml", ".yml"):
                self._load_yaml_schema(child)
                self._load_variables_file(child)
            else:
                self._load_one_file(child, override_name=sanitized)

    def _load_yaml_schema(self, path: pathlib.Path) -> None:
        """Load a YAML file and register its content as a schema."""
        import yaml

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            # Register the entire YAML object under the filename stem
            self._schemas[path.stem] = data
        except Exception as e:
            warnings.warn(
                f"DynaPrompt: Failed to load YAML schema from {path}: {e}",
                UserWarning,
                stacklevel=2,
            )

    def _load_json_schema(self, path: pathlib.Path) -> None:
        """Load a JSON file and register its content as a schema."""
        import json

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # Register the entire JSON object under the filename stem
            self._schemas[path.stem] = data
        except Exception as e:
            warnings.warn(
                f"DynaPrompt: Failed to load JSON schema from {path}: {e}",
                UserWarning,
                stacklevel=2,
            )

    def _load_python_schemas(self, path: pathlib.Path) -> None:
        """Dynamically load a Python file, registering classes as schemas
        and all public names as template variables.

        This delegates to :meth:`_load_python_variables` so both the schema
        registry and the template variable store are populated in one pass.
        """
        self._load_python_variables(path)

    def _load_one_file(
        self,
        path: pathlib.Path,
        override_name: str | None = None,
    ) -> None:
        """Load a single file.

        Args:
            path: Absolute path to the file to load.
            override_name: When provided, replace the prompt name derived from
                the filename (used by :meth:`_load_dir` after sanitization).
        """
        loader = get_loader_for(path)
        # {env: {name: data}}
        raw = loader.load(path)

        for env, prompts in raw.items():
            # Apply the sanitized/override name when loading from a directory
            if override_name and len(prompts) == 1:
                original = next(iter(prompts))
                if original != override_name:
                    prompts = {override_name: prompts[original]}

            self._raw_data.setdefault(env, {})
            for name, data in prompts.items():
                source = SourceMetadata(
                    loader=loader.__class__.__name__,
                    identifier=str(path),
                    env=env,
                )
                self._history.setdefault(name, []).append((source, data))
                # Accumulate per-env raw data with deep merge
                self._raw_data[env].setdefault(name, {})
                object_merge(self._raw_data[env][name], data)

    # ── Resolution ────────────────────────────────────────────────────────────

    def _resolve(self) -> None:
        """
        Deep-merge default + current_env layers for every known prompt.
        Called once at load time, and again after env switch (no file I/O).
        """
        all_names: set = set()
        for env_prompts in self._raw_data.values():
            all_names.update(env_prompts.keys())

        self._store = {}
        for name in all_names:
            merged: dict = {}
            # Layer 1: default
            default_data = self._raw_data.get("default", {}).get(name, {})
            object_merge(merged, default_data)
            # Layer 2: current env override
            if self._current_env != "default":
                env_data = self._raw_data.get(self._current_env, {}).get(name, {})
                object_merge(merged, env_data)
            self._store[name] = merged

    def switch_env(self, env: str) -> None:
        """Switch active environment and re-resolve (no file I/O)."""
        self._current_env = env
        self._cache.clear()  # invalidate cache for env switch
        self._resolve()

    # ── Access ────────────────────────────────────────────────────────────────

    def get(self, name: str) -> PromptNode:
        # Cache lookup
        if self._cache_enabled and name in self._cache:
            return self._cache[name]

        if name not in self._store:
            available = list(self._store.keys())
            raise AttributeError(
                f"Prompt '{name}' not found. Available prompts: {available}"
            )

        data = dict(self._store[name])
        # Resolve parent template for `extends` inheritance
        parent_template: str | None = None
        extends = data.get("extends")
        if extends and extends in self._store:
            parent_data = dict(self._store[extends])
            parent_template = parent_data.pop("template", "")

            # Deep merge parent config into current data (current data takes precedence)
            merged_data = dict(parent_data)
            object_merge(merged_data, data)
            data = merged_data

        template_str = data.pop("template", "")

        # Resolve response_schema string → class (if registered externally).
        # Supports both "response_schema" and "_response_schema" from metadata.
        schema_name_or_class = data.pop(
            "response_schema", data.pop("_response_schema", None)
        )
        response_schema = None

        if isinstance(schema_name_or_class, str):
            response_schema = self._schemas.get(schema_name_or_class)
        else:
            response_schema = schema_name_or_class

        node = PromptNode(
            name=name,
            text=template_str,
            metadata=data,
            response_schema=response_schema,
            parent_template=parent_template,
            history=self._history.get(name, []),
            variables=self._variables,
            validators=self._validators,
            hooks=self._hooks,
            current_env=self._current_env,
            auto_render=self._auto_render,
        )

        # Cache the node
        if self._cache_enabled:
            self._cache[name] = node

        return node

    def get_history(self, name: str | None = None) -> dict:
        if name:
            entries = self._history.get(name, [])
            return [{**src._asdict(), "value": data} for src, data in entries]
        return {
            pname: [{**src._asdict(), "value": data} for src, data in entries]
            for pname, entries in self._history.items()
        }


class DynaPrompt:
    """
    Lazy-loading prompt configuration manager.
    Inspired by Dynaconf's LazySettings — zero I/O at instantiation.

    Usage::

        from dynaprompt import DynaPrompt

        prompts = DynaPrompt(
            settings_files=["prompts.toml", ".secrets.prompts.toml"],
            environments=True,
        )

        rendered = (
            prompts.customer_support
            .with_model("gpt-4.1")
            .render(user_name="Ahmed", issue="Payment failed")
        )

        print(rendered.text)
        print(rendered.config["model"])
    """

    def __init__(
        self,
        settings_files: list[Any],
        environments: bool = True,
        env: str | None = None,
        validators: list[PromptValidator] | None = None,
        file_prefix: str | None = None,
        variables: list[Any] | None = None,
        auto_render: bool = False,
    ):
        """
        Args:
            settings_files: List of file paths or directory paths to load.
                Directories are scanned for ``.toml``, ``.md``, ``.txt``,
                ``.py``, ``.json``, and ``.yaml`` (for schemas) files.
            environments: Enable environment layering (default ``True``).
            env: Active environment name. Falls back to
                ``ENV_FOR_DYNAPROMPT`` env-var, then ``"development"``.
            validators: Optional list of :class:`PromptValidator` instances
                to register immediately.
            file_prefix: When set, only files whose stem **starts with** this
                prefix are loaded from directories. The prefix is **stripped**
                from the resulting prompt name so the public API stays clean.
            variables: Optional list of paths (JSON, TOML, YAML) or dicts to
                load as global template variables. Items later in the list
                overwrite earlier ones.
            auto_render: If True, global variables that are strings and contain
                Jinja2 markers will be rendered using previously loaded variables.
        """
        self._settings_files = settings_files
        self._environments = environments
        self._env = env or os.environ.get("ENV_FOR_DYNAPROMPT", "development")
        self._file_prefix = file_prefix
        self._auto_render = auto_render
        self._validators = ValidatorList()
        if validators:
            self._validators.extend(validators)
        self._hooks: dict[str, list[Hook]] = {}
        self.schemas: dict[str, Any] = {}
        self._variables = variables
        self._wrapped: _PromptSettings | None = None

    # ── Lazy setup ────────────────────────────────────────────────────────────

    def _setup(self) -> None:
        """Called on first access — creates _PromptSettings and loads files."""
        self._wrapped = _PromptSettings(
            settings_files=self._settings_files,
            current_env=self._env,
            file_prefix=self._file_prefix,
            schemas=self.schemas,
            variables=self._variables,
            auto_render=self._auto_render,
        )
        self._wrapped._validators = self._validators
        self._wrapped._hooks = self._hooks

    # ── Attribute access ──────────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if self._wrapped is None:
            self._setup()

        # 1. Try to get a prompt
        try:
            return self._wrapped.get(name)
        except AttributeError:
            pass

        # 2. Try to get a schema
        if name in self.schemas:
            return self.schemas[name]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'. "
            f"Available prompts: {list(self._wrapped._store.keys())}. "
            f"Available schemas: {list(self.schemas.keys())}."
        )

    def __dir__(self) -> list[str]:
        """Enable tab-completion for prompts and schemas."""
        if self._wrapped is None:
            self._setup()

        # Standard attributes + prompts + schemas
        std_attrs = super().__dir__()
        prompts = list(self._wrapped._store.keys())
        schemas = list(self.schemas.keys())

        return sorted(set(std_attrs + prompts + schemas))

    def get(self, name: str) -> PromptNode:
        """Explicit getter — mirrors Dynaconf's settings.get()."""
        return self.__getattr__(name)

    # ── Environment switching ─────────────────────────────────────────────────

    @property
    def current_env(self) -> str:
        return self._env

    @contextmanager
    def using_env(self, env: str):
        """
        Temporarily switch to a different environment.
        No file I/O — just re-resolves the merge layer.

        Usage::

            with prompts.using_env('production'):
                rendered = prompts.customer_support.render(...)
                assert rendered.config['model'] == 'gpt-4.1'
        """
        if self._wrapped is None:
            self._setup()

        old_env = self._wrapped._current_env
        self._wrapped.switch_env(env)
        self._env = env
        try:
            yield self
        finally:
            self._wrapped.switch_env(old_env)
            self._env = old_env

    # ── Reload / Hot-reload ───────────────────────────────────────────────────

    def reload(self) -> None:
        """Discard all cached data and re-read all files from disk."""
        self._wrapped = None

    # ── Validators ────────────────────────────────────────────────────────────

    def add_validator(self, *validators: PromptValidator) -> None:
        """Register validators. Safe to call before or after first access."""
        self._validators.extend(validators)
        if self._wrapped:
            self._wrapped._validators = self._validators

    # ── Hooks ─────────────────────────────────────────────────────────────────

    def add_hook(self, event: str, name_or_hook: Any, hook: Hook | None = None) -> None:
        """
        Register a lifecycle hook.

        Events: 'after_render', 'after_load', 'before_render'

        Usage::

            # Instance-wide hook
            prompts.add_hook('after_render', Hook(my_func))

            # Specific prompt hook
            prompts.add_hook('after_render', 'greet', Hook(redact))
        """
        if hook is None:
            # Instance-wide hook
            self._hooks.setdefault(event, []).append(name_or_hook)
        else:
            # Per-prompt hook (event_name namespacing)
            target_event = f"{event}_{name_or_hook}"
            self._hooks.setdefault(target_event, []).append(hook)

        if self._wrapped:
            self._wrapped._hooks = self._hooks

    # ── Schema registry ───────────────────────────────────────────────────────

    def register(self, name: str, schema=None):
        """Decorator to register a Pydantic schema for a named prompt."""

        def decorator(func):
            if schema:
                self.schemas[name] = schema
            return func

        return decorator

    # ── Inspection ────────────────────────────────────────────────────────────

    def inspect(self, name: str | None = None) -> dict:
        """Return full loading history. Mirrors Dynaconf's inspect_settings()."""
        if self._wrapped is None:
            self._setup()
        return self._wrapped.get_history(name)

    # ── Repr ──────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        status = "initialized" if self._wrapped else "lazy"
        return f"DynaPrompt(env={self._env!r}, status={status!r})"
