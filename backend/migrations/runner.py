"""
Simple migration runner that executes timestamped migration scripts in order.
"""
from importlib import util as importlib_util
from pathlib import Path
import pkgutil
import re
from typing import List, Optional, Callable, Any


MIGRATION_FILENAME_PATTERN = re.compile(r"^\d{8}_\d{6}_.+$")
LEGACY_MODULES = ["add_profile_pic", "migrate_add_profile_pic"]


def _discover_migration_modules() -> List[str]:
    """Return migration module names sorted chronologically."""
    package_path = Path(__file__).parent
    modules: List[str] = []

    for module_info in pkgutil.iter_modules([str(package_path)]):
        if module_info.ispkg:
            continue
        if MIGRATION_FILENAME_PATTERN.match(module_info.name):
            modules.append(module_info.name)

    modules.sort()

    for legacy in LEGACY_MODULES:
        if (package_path / f"{legacy}.py").exists():
            modules.append(legacy)

    return modules


def _load_runner(module_name: str) -> Optional[Callable[[Any], None]]:
    package_path = Path(__file__).parent / f"{module_name}.py"
    if not package_path.exists():
        return None
    module_spec = importlib_util.spec_from_file_location(f"migrations.{module_name}", package_path)
    if module_spec is None or module_spec.loader is None:
        return None
    module = importlib_util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)  # type: ignore[union-attr]
    # Only run explicit legacy-style run_migration callables; Alembic migrations
    # that rely on the `op` context should be executed via Alembic, not here.
    return getattr(module, "run_migration", None)


def run_all_migrations(target_engine=None) -> None:
    """Execute all known migrations sequentially."""
    for module_name in _discover_migration_modules():
        runner = _load_runner(module_name)
        if runner:
            try:
                runner(target_engine)
            except TypeError:
                runner()


if __name__ == "__main__":
    run_all_migrations()
