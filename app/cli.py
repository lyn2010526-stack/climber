"""Climber CLI — local skill management and diagnostics.

Usage:
    python -m app cli skills list
    python -m app cli skills install <path-or-url>
    python -m app cli skills uninstall <skill-id>
    python -m app cli skills update <skill-id> --path <path>
    python -m app cli doctor
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_skills_list(args: argparse.Namespace) -> int:
    from app.skills.package_manager import get_skill_manager
    manager = get_skill_manager()
    skills = manager.list_installed()
    if not skills:
        print("No skills installed.")
        return 0
    print(f"{'ID':<25} {'Name':<30} {'Version':<10} {'Risk':<12} {'Admin'}")
    print("-" * 85)
    for s in skills:
        admin = "YES" if s.get("requires_admin") else "no"
        print(f"{s['id']:<25} {s['name']:<30} {s['version']:<10} {s['risk_level']:<12} {admin}")
    return 0


def _cmd_skills_install(args: argparse.Namespace) -> int:
    from app.skills.package_manager import get_skill_manager
    manager = get_skill_manager()
    target = args.target
    is_admin = getattr(args, "admin", False)
    if target.startswith("http://") or target.startswith("https://"):
        ok, msg = manager.install_from_url(target, overwrite=args.force, is_admin=is_admin)
    else:
        ok, msg = manager.install_from_file(target, overwrite=args.force, is_admin=is_admin)
    print(msg)
    return 0 if ok else 1


def _cmd_skills_uninstall(args: argparse.Namespace) -> int:
    from app.skills.package_manager import get_skill_manager
    manager = get_skill_manager()
    ok, msg = manager.uninstall(args.skill_id)
    print(msg)
    return 0 if ok else 1


def _cmd_skills_update(args: argparse.Namespace) -> int:
    from app.skills.package_manager import get_skill_manager
    manager = get_skill_manager()
    path = getattr(args, "path", None)
    url = getattr(args, "url", None)
    ok, msg = manager.update(args.skill_id, path=path, url=url)
    print(msg)
    return 0 if ok else 1


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Run environment diagnostics."""
    import importlib
    import importlib.util
    checks = []

    for module in ("fastapi", "sqlalchemy", "structlog", "httpx", "playwright", "chromadb", "psutil"):
        spec = importlib.util.find_spec(module)
        checks.append(("module:" + module, "PASS" if spec else "FAIL"))

    db_path = Path("data/climber.db")
    checks.append(("database:file", "PASS" if db_path.exists() else "WARN (not created yet)"))

    log_dir = Path("logs")
    checks.append(("logs:dir", "PASS" if log_dir.exists() else "FAIL"))

    print("Climber Environment Diagnostics")
    print("=" * 40)
    all_pass = True
    for name, status in checks:
        symbol = "PASS" if "PASS" in status else ("WARN" if "WARN" in status else "FAIL")
        if symbol == "FAIL":
            all_pass = False
        print(f"  [{symbol}] {name}: {status}")
    print()
    print("All checks passed!" if all_pass else "Some checks failed. Review output above.")
    return 0 if all_pass else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="climber", description="Climber Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    skills = sub.add_parser("skills", help="Skill package management")
    skills_sub = skills.add_subparsers(dest="action", required=True)

    skills_sub.add_parser("list").set_defaults(func=_cmd_skills_list)

    install = skills_sub.add_parser("install")
    install.add_argument("target")
    install.add_argument("--force", action="store_true")
    install.add_argument("--admin", action="store_true", help="Allow installing high-risk skills")
    install.set_defaults(func=_cmd_skills_install)

    uninstall = skills_sub.add_parser("uninstall")
    uninstall.add_argument("skill_id")
    uninstall.set_defaults(func=_cmd_skills_uninstall)

    update = skills_sub.add_parser("update")
    update.add_argument("skill_id")
    update.add_argument("--path", default=None)
    update.add_argument("--url", default=None)
    update.set_defaults(func=_cmd_skills_update)

    doctor = sub.add_parser("doctor", help="Environment diagnostics")
    doctor.set_defaults(func=_cmd_doctor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
