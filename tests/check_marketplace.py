"""Offline static project gates, not a substitute for Marketplace validation."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys


def validate(root: Path) -> list[str]:
    errors = []
    try:
        hacs = json.loads((root / "hacs.json").read_text())
        if not isinstance(hacs, dict) or hacs.get("name") != "Haier SmartAir2" or hacs.get("homeassistant") != "2026.11.0":
            errors.append("hacs: project name and minimum 2026.11.0 required")
    except (OSError, ValueError):
        errors.append("hacs: invalid root JSON")
    components = root / "custom_components"
    integrations = sorted(p for p in components.iterdir() if p.is_dir() and not p.name.startswith((".", "__"))) if components.is_dir() else []
    if len(integrations) != 1:
        errors.append("integration: exactly one domain directory required")
        return errors
    integration = integrations[0]
    if not re.fullmatch(r"[a-z0-9_-]+", integration.name):
        errors.append("integration: domain must be a lowercase Marketplace slug")
    if integration.name != "haier_smartair2":
        errors.append("integration: project domain identity must remain haier_smartair2")
    try:
        manifest = json.loads((integration / "manifest.json").read_text())
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be an object")
    except (OSError, ValueError):
        errors.append("manifest: invalid or missing JSON object")
        return errors
    from urllib.parse import urlsplit
    for field in ("documentation", "issue_tracker"):
        value = manifest.get(field)
        try:
            valid = isinstance(value, str) and urlsplit(value).scheme == "https" and bool(urlsplit(value).netloc)
        except ValueError:
            valid = False
        if not valid:
            errors.append(f"manifest: {field} must be an HTTPS URL")
    expected = {"domain": integration.name, "name": "Haier SmartAir2", "version": "0.3.0", "config_flow": True,
                "iot_class": "local_push", "integration_type": "hub", "requirements": []}
    for field, value in expected.items():
        if manifest.get(field) != value or (field == "config_flow" and manifest.get(field) is not True):
            errors.append(f"manifest: project {field} must equal {value!r}")
    if manifest.get("categories") != ["climate.heat_pumps_air_conditioning"]:
        errors.append("manifest: project climate category required (platform-wide this is optional)")
    if not isinstance(manifest.get("codeowners"), list) or not manifest["codeowners"] or any(not isinstance(v, str) or not v.startswith("@") for v in manifest["codeowners"]):
        errors.append("manifest: codeowners required")

    import struct
    translations = {}
    def leaves(value, prefix=()):
        if not isinstance(value, dict) or not value:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("translation leaves must be nonempty strings")
            return {prefix}
        return set().union(*(leaves(child, prefix + (key,)) for key, child in value.items()))
    for language in ("en", "pt", "pl"):
        try:
            data = json.loads((integration / "translations" / f"{language}.json").read_text())
            translations[language] = leaves(data)
            for flow, step in (("config", "user"), ("options", "init")):
                required = {(flow, "step", step, "title"), (flow, "step", step, "description"),
                            (flow, "step", step, "data", "local_ips"), (flow, "error", "invalid_local_map")}
                if not required <= translations[language]:
                    errors.append(f"translations: {language} missing required flow text")
        except (OSError, ValueError, TypeError):
            errors.append(f"translations: {language} invalid JSON/string tree")
    for language in ("pt", "pl"):
        # HA uses English for entity labels not yet translated. Missing localized
        # keys are not a Marketplace rejection; unknown keys must have an English base.
        if translations.get(language, set()) - translations.get("en", set()):
            errors.append(f"translations: {language} keys need an English fallback")
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        try:
            png = (integration / "brand" / filename).read_bytes()
            if png[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" or len(png) < 33 or struct.unpack(">II", png[16:24]) != (size, size):
                raise ValueError("bad PNG dimensions/header")
        except (OSError, ValueError, struct.error):
            errors.append(f"brand: {filename} must be a {size}x{size} PNG")
    import ast
    for filename in ("config_flow.py", "climate.py", "const.py", "__init__.py"):
        try:
            tree = ast.parse((integration / filename).read_text())
        except (OSError, SyntaxError, UnicodeError):
            errors.append(f"source: {filename} must be parseable Python")
            continue
        if filename == "const.py":
            domains = [n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == "DOMAIN" for t in n.targets)]
            if domains != [integration.name]:
                errors.append("integration: const DOMAIN must match directory")
        if filename == "config_flow.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("async_show_form", "async_show_menu", "async_show_progress", "async_external_step"):
                    if not any(k.arg == "step_id" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str) and k.value.value for k in node.keywords):
                        errors.append("flow: explicit nonempty step_id required")
        if filename == "climate.py":
            functions = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            if not {"native_current_temperature", "native_target_temperature"} <= functions or "_attr_native_temperature_unit" not in names:
                errors.append("climate: native temperature properties/unit required")
            if {"current_temperature", "target_temperature", "temperature_unit", "_attr_temperature_unit", "_attr_current_temperature", "_attr_target_temperature"} & (functions | names):
                errors.append("climate: legacy temperature overrides prohibited by project policy")
    try:
        readme = (root / "README.md").read_text()
    except OSError:
        readme = ""
    if "0.3.0" not in readme:
        errors.append("manifest: version must match README candidate")
    for token in ("<!-- ha-marketplace:exclude-start -->", "<!-- ha-marketplace:exclude-end -->", "normally does not require a restart", "restart Home Assistant", "unpublished", "0.2.3", "2026.11.0", "handover", "backup"):
        if token not in readme:
            errors.append(f"README: project installation/release contract missing {token!r}")
    if readme.count("<!-- ha-marketplace:exclude-start -->") != 1 or readme.count("<!-- ha-marketplace:exclude-end -->") != 1 or readme.find("<!-- ha-marketplace:exclude-start -->") > readme.find("<!-- ha-marketplace:exclude-end -->"):
        errors.append("README: exclusion markers must be one ordered pair")
    return errors


if __name__ == "__main__":
    issues = validate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
    for issue in issues:
        print(issue)
    print(f"Marketplace static project gates: {len(issues)} error(s)")
    sys.exit(bool(issues))
