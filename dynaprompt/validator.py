"""Declarative validation for prompt variables — inspired by Dynaconf's Validator."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Callable


class ValidationError(Exception):
    def __init__(self, message: str, details: list = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class PromptValidator:
    """
    Declarative validator attached to a prompt name.

    Usage::

        PromptValidator('customer_support',
            requires=['user_name', 'issue'],
            max_tokens=4096,
            env='production',
        )

        # Composition with & / |
        PromptValidator('p1', requires=['a']) & PromptValidator('p2', requires=['b'])
    """

    def __init__(
        self,
        *names: str,
        requires: list[str] = None,
        max_tokens: int | None = None,
        response_schema=None,
        condition: Callable | None = None,
        when: PromptValidator | None = None,
        env: str | Sequence[str] | None = None,
        description: str = None,
    ):
        self.names = names
        self.requires = requires or []
        self.max_tokens = max_tokens
        self.response_schema = response_schema
        self.condition = condition
        self.when = when
        self.description = description
        if isinstance(env, str):
            self.envs = [env]
        elif env:
            self.envs = list(env)
        else:
            self.envs = []

    def __or__(self, other: PromptValidator) -> OrValidator:
        return OrValidator(self, other)

    def __and__(self, other: PromptValidator) -> AndValidator:
        return AndValidator(self, other)

    def __repr__(self):
        parts = [repr(n) for n in self.names]
        if self.requires:
            parts.append(f"requires={self.requires}")
        if self.max_tokens:
            parts.append(f"max_tokens={self.max_tokens}")
        if self.envs:
            parts.append(f"env={self.envs}")
        return f"PromptValidator({', '.join(parts)})"

    def validate(self, prompt_node, kwargs: dict, current_env: str = "default") -> None:
        """Raise ValidationError if invalid."""
        # Honor `when` condition — skip if when itself fails
        if self.when is not None:
            try:
                self.when.validate(prompt_node, kwargs, current_env)
            except ValidationError:
                return  # condition not met, skip this validator

        # Honor env scope
        if self.envs and current_env not in self.envs:
            return

        # Filter by prompt name scope (empty names = applies to all)
        if self.names and prompt_node.name not in self.names:
            return

        # 1. Required variables check
        for var in self.requires:
            if var not in kwargs:
                raise ValidationError(
                    f"Prompt '{prompt_node.name}' requires variable '{var}' "
                    f"but it was not provided to .render()."
                )

        # 2. Token estimate guard (rough: 1 word ≈ 1.3 tokens)
        if self.max_tokens is not None:
            word_count = len(prompt_node.text.split())
            estimated_tokens = int(word_count * 1.3)
            if estimated_tokens > self.max_tokens:
                raise ValidationError(
                    f"Prompt '{prompt_node.name}' estimated ~{estimated_tokens} tokens "
                    f"but max_tokens={self.max_tokens}."
                )

        # 3. Custom callable condition
        if self.condition is not None:
            if not self.condition(prompt_node, kwargs):
                raise ValidationError(
                    f"Prompt '{prompt_node.name}' failed custom validation condition."
                )


class CombinedValidator(PromptValidator):
    def __init__(self, a: PromptValidator, b: PromptValidator):
        self.validators = (a, b)
        self.names = ()
        self.requires = []
        self.max_tokens = None
        self.response_schema = None
        self.condition = None
        self.when = None
        self.envs = []
        self.description = None


class OrValidator(CombinedValidator):
    def validate(self, prompt_node, kwargs: dict, current_env: str = "default") -> None:
        errors = []
        for v in self.validators:
            try:
                v.validate(prompt_node, kwargs, current_env)
                return  # one passed — OR is satisfied
            except ValidationError as e:
                errors.append(str(e))
        raise ValidationError(" OR ".join(errors))


class AndValidator(CombinedValidator):
    def validate(self, prompt_node, kwargs: dict, current_env: str = "default") -> None:
        for v in self.validators:
            v.validate(prompt_node, kwargs, current_env)  # all must pass


class ValidatorList(list):
    """A list of validators that can be run together."""

    def validate(self, prompt_node, kwargs: dict, current_env: str = "default") -> None:
        for v in self:
            v.validate(prompt_node, kwargs, current_env)

    def validate_all(
        self,
        prompt_node,
        kwargs: dict,
        current_env: str = "default",
        raise_error: bool = True,
    ) -> list[ValidationError]:
        errors = []
        for v in self:
            try:
                v.validate(prompt_node, kwargs, current_env)
            except ValidationError as e:
                errors.append(e)
        if errors and raise_error:
            raise ValidationError("; ".join(str(e) for e in errors), details=errors)
        return errors
