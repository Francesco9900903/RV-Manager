from dataclasses import dataclass

@dataclass(frozen=True)
class EnvironmentConfig:
    name: str
    project_label: str
    allow_real_data: bool

def load_environment(secrets) -> EnvironmentConfig:
    app_cfg = secrets.get("app", {}) if secrets else {}
    name = str(app_cfg.get("environment", "production")).strip().lower()
    label = str(app_cfg.get("project_label", "RV Manager")).strip()
    allow_real_data = bool(
        app_cfg.get("allow_real_data", name == "production")
    )
    return EnvironmentConfig(name, label, allow_real_data)
