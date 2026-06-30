"""Function registry for declarative (JSON) workflow loading.

Author: Vineeth Penugonda
"""

from typing import Any, Callable, Dict, Optional

from stepfunction.exceptions.step_errors import (
    DuplicateRegistrationError,
    UnregisteredFunctionError,
)


class StepRegistry:
    """A name -> callable registry used to resolve string function references
    in a declarative (JSON) workflow spec back into real Python callables.

    Step functions and branch-router functions share one namespace, since
    both are simply ``Callable[[Any], Any]`` — the calling context
    (``add_step`` vs. ``branch=``), not the function itself, determines the
    role a registered callable plays in a given workflow.

    A module-level default instance (``registry``) covers the common case of
    a single process-wide registry. Construct your own ``StepRegistry()`` for
    isolated namespaces (e.g. per-tenant, or test isolation).
    """

    def __init__(self):
        self.__functions: Dict[str, Callable[[Any], Any]] = {}

    def register(
        self, name: str, func: Optional[Callable[[Any], Any]] = None
    ) -> Callable[[Any], Any]:
        """Register ``func`` under ``name``.

        Usable as a direct call (``registry.register("my_step", my_step)``)
        or as a decorator (``@registry.register("my_step")``).

        Raises:
            DuplicateRegistrationError: If ``name`` is already registered.
        """
        if func is not None:
            self.__add(name, func)
            return func

        def decorator(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
            self.__add(name, fn)
            return fn

        return decorator

    def __add(self, name: str, func: Callable[[Any], Any]) -> None:
        if name in self.__functions:
            raise DuplicateRegistrationError(name)
        self.__functions[name] = func

    def unregister(self, name: str) -> None:
        """Remove a registration if present. No error if ``name`` isn't registered."""
        self.__functions.pop(name, None)

    def get(self, name: str) -> Callable[[Any], Any]:
        """Look up a registered callable by name.

        Raises:
            UnregisteredFunctionError: If ``name`` has not been registered.
        """
        try:
            return self.__functions[name]
        except KeyError:
            raise UnregisteredFunctionError(
                f"No function is registered under the name '{name}'. Register it "
                "with stepfunction.registry.step_registry.register_step() (or your "
                "own StepRegistry instance) before loading this workflow spec."
            ) from None

    def name_for(self, func: Callable[[Any], Any]) -> Optional[str]:
        """Reverse lookup: the registered name for ``func``, or ``None`` if it
        isn't registered under this registry."""
        for registered_name, registered_func in self.__functions.items():
            if registered_func is func:
                return registered_name
        return None

    def __contains__(self, name: str) -> bool:
        return name in self.__functions

    def clear(self) -> None:
        """Remove all registrations. Primarily useful for test isolation."""
        self.__functions.clear()


# Module-level default singleton, covering the common case of one
# process-wide registry.
registry = StepRegistry()

register_step = registry.register
get_step = registry.get
