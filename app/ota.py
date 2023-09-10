import os
import json
import urequests


class URL:
    BASE: str = "https://raw.githubusercontent.com"
    user: str
    repo: str
    version: str

    def __init__(self, user: str, repo: str, version: str) -> None:
        self.user = user
        self.repo = repo
        self.version = version

    @property
    def url(self) -> str:
        return f"{self.BASE}/{self.user}/{self.repo}/{self.version}/"


class Config:
    """Base config that provides a repo, files, and manifest to an ota update."""

    REPO_URL: URL
    FILES: list[str]
    MANIFEST: str

    def __init__(self):
        pass


class TestConfig(Config):
    REPO_URL: URL = URL(user="pierreyvesbaloche", repo="kevinmca_ota", version="main")
    FILES = ["README.md", "test_ota.py"]
    MANIFEST: str = "version.json"


class RailYardConfig(Config):
    REPO_URL: URL = URL(user="jakee417", repo="Pico-Train-Switching", version="main")
    FILES = ["app/connect.py", "app/logging.py", "app/main.py", "app/microdot_server.py"]
    MANIFEST: str = "version.json"


class RemoteConfig(Config):
    """A subclass that finds it's version and files dynamically."""
    REMOTE_VERSION: str = "version.json"

    def __init__(self, base_url: URL):
        
        self.set_files(base_url=base_url)

    def set_files(self, base_url: URL) -> None:
        pass


class RailYardRemoteConfig(RemoteConfig):
    def __init__(self) -> None:
        base_url = URL(user="jakee417", repo="Pico-Train-Switching", version="main")
        self.MANIFEST = "version.json"
        super().__init__(base_url=base_url)


def ota():
    """Helper of a helper."""
    run_ota(TestConfig())


def run_ota(config: Config) -> None:
    """Helper function to run a configuration."""
    for file in config.FILES:
        print(file + " started...")
        download_update(
            repo_url=config.REPO_URL.url, filename=file, manifest=config.MANIFEST
        )


def download_update(repo_url: str, filename: str, manifest: str) -> None:
    """Check for updates, download and install them.

    Args:
        repo_url: "https://raw.githubusercontent.com/<username>/<repo_name>/<branch_name>/"
        filename: name of the file to update. if nested, ensure path is "/" delimited:
            test/test_ota.py
        manifest: name of the file on disk that tracks versioning. schema is:
        {
            "<file_name>": "<str(hash(file contents))>",
            ...
        }
    """
    info = get_current_version(filename=filename, manifest=manifest)
    set_current_version(firmware_url=repo_url + filename, info=info)


class VersionInfo:
    filename: str
    content: dict[str, str]
    manifest: str
    NO_VERSION: str = "__NO_VERSION__"
    NEW_VERSION: str = "__NEW_VERSION__"

    def __init__(self, filename: str, content: dict[str, str], manifest: str) -> None:
        self.filename = filename
        self.content = content
        self.manifest = manifest

    def write_version_to_file(self, version: str) -> "VersionInfo":
        """Overwrite file's version while preserving other files."""
        self.content[self.filename] = version
        with open(self.manifest, "w") as f:
            json.dump(self.content, f)
        return self

    @property
    def version(self) -> str:
        return self.content.get(self.filename, self.NO_VERSION)


def get_current_version(filename: str, manifest: str) -> VersionInfo:
    """Get the current version based off the manifest file and filename.

    Args:
        filename: name of the file to update.
        manifest: name of the file on disk that tracks versions.

    Returns:
        Information about the current version.
    """
    if manifest in os.listdir():
        with open(manifest) as f:
            content = json.load(f)
            if filename in content:
                version_info = VersionInfo(
                    filename=filename, content=content, manifest=manifest
                )
            else:
                version_info = VersionInfo(
                    filename=filename, content=content, manifest=manifest
                ).write_version_to_file(version=VersionInfo.NEW_VERSION)
    else:
        version_info = VersionInfo(
            filename=filename, content=dict(), manifest=manifest
        ).write_version_to_file(version=VersionInfo.NEW_VERSION)
    return version_info


def set_current_version(firmware_url: str, info: VersionInfo) -> None:
    """Set the latest code from the repo.

    Args:
        firmware_url: "https://raw.githubusercontent.com/<username>/<repo_name>/<branch_name>/<path_to_file>".
        info: the current version's information.
    """
    # Get the latest code from the repo.
    response = urequests.get(firmware_url)
    # Hash the new code to compare against the old.
    new_version = str(hash(response.content))
    if response.status_code == 200 and new_version != info.version:
        # Update the version with the new hash.
        with open(info.filename, "w") as f:
            f.write(response.content)
        # Write the new version to flash memory.
        _ = info.write_version_to_file(version=new_version)
        print(info.filename + " updated.")
    else:
        print(info.filename + " deferred.")
