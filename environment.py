import os
from dataclasses import dataclass

@dataclass
class EnvironmentInfo:
    environment: str
    branch: str
    commit_sha: str

def current_environment() -> EnvironmentInfo:
    environment = os.getenv("RV_ENV", "production")
    branch = os.getenv("GIT_BRANCH", "main")
    commit_sha = os.getenv("GIT_COMMIT", "")
    return EnvironmentInfo(environment, branch, commit_sha)
