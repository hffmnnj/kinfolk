#!/usr/bin/env python3
"""
Kinfolk — First-Run Configuration Wizard.

Interactive prompts to collect required settings and write them to .env.
Safe to run multiple times — preserves existing values as defaults.

Usage:
    python3 scripts/first_run.py
    python3 scripts/first_run.py --env-file /path/to/.env
    python3 scripts/first_run.py --non-interactive  # use defaults/existing
"""

import argparse
import os
import re
import secrets
import sys
from pathlib import Path

# ── Defaults ─────────────────────────────────────────────────

ENV_TEMPLATE = ".env.example"
ENV_OUTPUT = ".env"

# Settings grouped by category for the wizard flow
WIZARD_SECTIONS = [
    {
        "title": "Speech-to-Text (STT)",
        "description": "Choose how Kinfolk transcribes your voice.",
        "settings": [
            {
                "key": "STT_MODE",
                "prompt": "STT mode — 'cloud' (Whisper API, better accuracy) or 'local' (Vosk, fully offline)",
                "default": "local",
                "validate": lambda v: v in ("cloud", "local"),
                "error": "Must be 'cloud' or 'local'.",
            },
            {
                "key": "OPENAI_API_KEY",
                "prompt": "OpenAI API key (for Whisper cloud STT)",
                "default": "",
                "condition": lambda env: env.get("STT_MODE") == "cloud",
                "validate": lambda v: v.startswith("sk-") or v == "",
                "error": "OpenAI keys start with 'sk-'. Leave blank to skip.",
                "secret": True,
            },
        ],
    },
    {
        "title": "Text-to-Speech (TTS)",
        "description": "Choose the voice synthesis engine.",
        "settings": [
            {
                "key": "TTS_ENGINE",
                "prompt": "TTS engine — 'nanotts' (offline) or 'gtts' (needs network)",
                "default": "nanotts",
                "validate": lambda v: v in ("nanotts", "gtts"),
                "error": "Must be 'nanotts' or 'gtts'.",
            },
        ],
    },
    {
        "title": "Weather",
        "description": "Live weather from OpenWeatherMap (free tier).",
        "settings": [
            {
                "key": "OPENWEATHER_API_KEY",
                "prompt": "OpenWeatherMap API key (get one at https://openweathermap.org/api)",
                "default": "",
                "validate": lambda v: True,
                "secret": True,
            },
            {
                "key": "WEATHER_CITY",
                "prompt": "City name for weather forecasts",
                "default": "San Francisco",
                "validate": lambda v: len(v.strip()) > 0,
                "error": "City name cannot be empty.",
            },
            {
                "key": "WEATHER_UNITS",
                "prompt": "Temperature units — 'imperial' (°F) or 'metric' (°C)",
                "default": "imperial",
                "validate": lambda v: v in ("imperial", "metric"),
                "error": "Must be 'imperial' or 'metric'.",
            },
        ],
    },
    {
        "title": "Home Assistant",
        "description": "Connect to your Home Assistant instance (optional).",
        "settings": [
            {
                "key": "HA_URL",
                "prompt": "Home Assistant URL (e.g. http://homeassistant.local:8123)",
                "default": "",
                "validate": lambda v: v == "" or re.match(r"^https?://[^\s]+$", v),
                "error": "Must be a valid URL (http:// or https://) or blank to skip.",
            },
            {
                "key": "HA_TOKEN",
                "prompt": "Home Assistant long-lived access token",
                "default": "",
                "condition": lambda env: bool(env.get("HA_URL")),
                "validate": lambda v: True,
                "secret": True,
            },
        ],
    },
    {
        "title": "Database Encryption",
        "description": "SQLCipher encrypts your database at rest.",
        "settings": [
            {
                "key": "DATABASE_ENCRYPTION_KEY",
                "prompt": "Database encryption key (leave blank to auto-generate)",
                "default": "__auto__",
                "validate": lambda v: True,
                "secret": True,
                "auto_generate": True,
            },
        ],
    },
]


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, preserving order."""
    env = {}
    if not path.exists():
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_env_file(
    template_path: Path, output_path: Path, values: dict[str, str]
) -> None:
    """Write .env file using template structure, substituting collected values."""
    if not template_path.exists():
        # No template — write key=value pairs directly
        with open(output_path, "w") as f:
            for key, value in values.items():
                f.write(f"{key}={value}\n")
        return

    lines = []
    with open(template_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, _, _ = stripped.partition("=")
                key = key.strip()
                if key in values:
                    lines.append(f"{key}={values[key]}\n")
                else:
                    lines.append(line)
            else:
                lines.append(line)

    with open(output_path, "w") as f:
        f.writelines(lines)


def prompt_value(
    setting: dict, current_value: str | None, collected: dict[str, str]
) -> str | None:
    """Prompt user for a single setting value."""
    # Check condition (e.g. only ask for OPENAI_API_KEY if STT_MODE=cloud)
    condition = setting.get("condition")
    if condition and not condition(collected):
        return current_value or setting.get("default", "")

    key = setting["key"]
    prompt_text = setting["prompt"]
    default = current_value if current_value else setting.get("default", "")

    # Auto-generate encryption keys
    if setting.get("auto_generate") and (not default or default == "__auto__"):
        default = secrets.token_hex(32)

    # Mask display of existing secrets
    display_default = default
    if setting.get("secret") and default and default != "__auto__":
        display_default = (
            default[:4] + "..." + default[-4:] if len(default) > 8 else "****"
        )

    if display_default:
        user_input = input(f"  {prompt_text} [{display_default}]: ").strip()
    else:
        user_input = input(f"  {prompt_text}: ").strip()

    value = user_input if user_input else default

    # Validate
    validator = setting.get("validate")
    if validator and not validator(value):
        print(f"    ⚠  {setting.get('error', 'Invalid value.')}")
        return prompt_value(setting, current_value, collected)

    return value


def run_wizard(
    project_root: Path,
    env_file: str = ENV_OUTPUT,
    non_interactive: bool = False,
) -> dict[str, str]:
    """Run the first-run configuration wizard."""
    template_path = project_root / ENV_TEMPLATE
    output_path = project_root / env_file

    # Load existing values (from .env if it exists, else from template)
    existing = load_env_file(output_path)
    if not existing:
        existing = load_env_file(template_path)

    collected = dict(existing)

    if non_interactive:
        # Auto-generate encryption key if missing
        if (
            not collected.get("DATABASE_ENCRYPTION_KEY")
            or collected["DATABASE_ENCRYPTION_KEY"]
            == "replace_with_device_derived_secret"
        ):
            collected["DATABASE_ENCRYPTION_KEY"] = secrets.token_hex(32)
        write_env_file(template_path, output_path, collected)
        print(f"[OK] Wrote {output_path} with defaults (non-interactive mode).")
        return collected

    print()
    print("=" * 60)
    print("  Kinfolk — First-Run Configuration Wizard")
    print("=" * 60)
    print()
    print("  This wizard collects the settings Kinfolk needs to run.")
    print("  Press Enter to accept the default value shown in [brackets].")
    print("  Leave optional fields blank to skip them.")
    print()

    for section in WIZARD_SECTIONS:
        print(f"── {section['title']} {'─' * (50 - len(section['title']))}")
        print(f"  {section['description']}")
        print()

        for setting in section["settings"]:
            key = setting["key"]
            current = collected.get(key)
            value = prompt_value(setting, current, collected)
            if value is not None:
                collected[key] = value
        print()

    # Write the .env file
    write_env_file(template_path, output_path, collected)

    print("─" * 60)
    print(f"  ✓ Configuration saved to {output_path}")
    print()
    print("  You can edit .env directly at any time.")
    print("  Re-run this wizard with: python3 scripts/first_run.py")
    print("─" * 60)
    print()

    return collected


def main():
    parser = argparse.ArgumentParser(
        description="Kinfolk first-run configuration wizard."
    )
    parser.add_argument(
        "--env-file",
        default=ENV_OUTPUT,
        help="Output .env file path (default: .env)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use defaults without prompting (CI/automation mode).",
    )
    args = parser.parse_args()

    # Find project root (directory containing .env.example)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    if not (project_root / ENV_TEMPLATE).exists():
        print(f"Error: Cannot find {ENV_TEMPLATE} in {project_root}", file=sys.stderr)
        sys.exit(1)

    run_wizard(
        project_root=project_root,
        env_file=args.env_file,
        non_interactive=args.non_interactive,
    )


if __name__ == "__main__":
    main()
