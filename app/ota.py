import os
import json
import urequests


class RepoURL:
    """Abstraction of a url pointing to raw text on github.com"""

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
    """Base config that provides a repo, files, and manifest for an ota update."""

    repo_url: RepoURL
    files: list[str]
    manifest: str
    tag: str = "__hash__"

    def __init__(self):
        pass


class TestConfig(Config):
    repo_url: RepoURL = RepoURL(
        user="pierreyvesbaloche", repo="kevinmca_ota", version="main"
    )
    files = ["README.md", "test_ota.py"]
    manifest: str = "version.json"


def run_ota(config: Config) -> None:
    """Perform an OTA based upon a configuration."""
    for file in config.files:
        # NOTE: each file uses the same tag for consistency.
        download_update(
            repo_url=config.repo_url.url,
            filename=file,
            manifest=config.manifest,
            tag=config.tag,
        )


class RemoteConfig(Config):
    """A subclass that finds it's version and files dynamically."""

    REMOTE_VERSION: str = "version.json"
    TAG_KEY: str = "tag"
    FILES_KEY: str = "files"

    def __init__(self, remote_url: RepoURL) -> None:
        """Sets the REPO_URL and FILES attributes dynamically based off a remote config.

        Args:
            remote_url: url pointing to a remote configuration on github.
                Inside this directory, there must exist a file named
                REMOTE_VERSION = "version.json" with the following schema:
                {
                    "tag": "<commit, branch name, or tag>"
                    "files": [
                        "<file1>",
                        "<file2>",
                        ...
                    ]
                }
        """
        response = urequests.get(remote_url.url + self.REMOTE_VERSION)
        if response.status_code == 200:
            remote_config = json.loads(response.content)
            if self.TAG_KEY in remote_config and self.FILES_KEY in remote_config:
                self.tag = remote_config[self.TAG_KEY]
                self.repo_url = RepoURL(
                    user=remote_url.user,
                    repo=remote_url.repo,
                    # Now substitute in the tag dynamically.
                    version=self.tag,
                )
                self.files = remote_config[self.FILES_KEY]
            else:
                raise KeyError(f"{self.TAG_KEY} and {self.FILES_KEY} must present.")
        else:
            raise NotImplementedError("Remote configuration was not found.")


def download_update(repo_url: str, filename: str, manifest: str, tag: str) -> None:
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
        tag: Either a tag string or __hash__ if no tag is used.
            Use a "<tag>" with `RemoteConfig` or "__hash__" with `Config`.
            If using __hash__, the `str(hash(content))` is used as a basis
            of comparison.
    """
    info = get_current_version(filename=filename, manifest=manifest)
    set_current_version(info=info, firmware_url=repo_url + filename, tag=tag)


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


def set_current_version(info: VersionInfo, firmware_url: str, tag: str) -> None:
    """Set the latest code from the repo.

    Args:
        info: the current version's information.
        firmware_url: "https://raw.githubusercontent.com/<username>/<repo_name>/<branch_name>/<path_to_file>".
        tag: see `download_update`.
    """
    # If using hashing, we determine the "tag" based off the hash of the response.
    if tag == Config.tag:
        # Get the latest code from the repo.
        response = urequests.get(firmware_url)
        _set_current_version(
            info=info, response=response, new_version=str(hash(response.content))
        )
    # Otherwise, use the tag provided.
    elif tag != info.version:
        _set_current_version(
            info=info, response=urequests.get(firmware_url), new_version=tag
        )
    else:
        print(info.filename + " deferred.")


def _set_current_version(info: VersionInfo, response, new_version: str) -> None:
    if response.status_code == 200 and new_version != info.version:
        # Update the version with the new hash.
        # TODO: Make sure the directory exists.
        with open(info.filename, "w") as f:
            f.write(response.content)
        # Write the new version to flash memory.
        _ = info.write_version_to_file(version=new_version)
        print(info.filename + " updated.")
    else:
        print(info.filename + " deferred.")
