import os
import gc
import json
import urequests
from micropython import const


######################################################################
# Data Classes
######################################################################


class RepoURL:
    """Url pointing to raw text on github.com.

    Attributes:
        user: username owning the remote repository.
        repo: repo that the code will update from.
        version: commit, branch name, or tag of the repo.
    """

    _BASE: str = const("https://raw.githubusercontent.com")
    user: str
    repo: str
    version: str

    def __init__(self, user: str, repo: str, version: str) -> None:
        self.user = user
        self.repo = repo
        self.version = version

    @property
    def url(self) -> str:
        """Formatted url string pointing to a github repository."""
        return f"{self._BASE}/{self.user}/{self.repo}/{self.version}/"


class VersionInfo:
    """A container for a version and manifest file.

    Attributes:
        manifest: see `Config.manifest`.
        content: json representation of the contents in `manifest`.
    """

    _NO_VERSION: str = const("__NO_VERSION__")
    manifest: str
    content: dict[str, str] = dict()

    def __init__(self, manifest: str) -> None:
        self.manifest = manifest
        # Load content from file.
        if self.manifest in os.listdir():
            with open(self.manifest) as f:
                self.content = json.load(f)
        # Or set to an empty dict().
        else:
            self.write_versions_to_file(versions=dict())

    def write_versions_to_file(self, versions: dict[str, str]) -> None:
        self.content.update(versions)
        with open(self.manifest, "w") as f:
            json.dump(self.content, f)

    def version(self, file: str) -> str:
        """Retrieve the active version for a file in the manifest."""
        return self.content.get(file, self._NO_VERSION)


######################################################################
# Typed Configs
######################################################################


class BaseConfig:
    """Base config that provides a repo, files, manifest, and tag for an OTAUpdate.

    Notes:
        Subclass `BaseConfig` to define configs specific to your project.

    Attributes:
        repo_url: "https://raw.githubusercontent.com/<username>/<repo_name>/<branch_name>/"
        files: names of the files to update. if nested, ensure path is "/" delimited:
            ["test/test_ota.py", "config.py", ...]
        manifest: name of the file on disk that tracks versioning. schema is:
        {
            "<file_name>": "<str(hash(file contents))>" or "<tag>",
            ...
        }
        tag: Either a tag string or `"__hash__"` if no tag is used.
            Use a `"<tag>"` with `RemoteConfig` or `"__hash__"` otherwise.
            If using `"__hash__"`, the `str(hash(content))` is used as a basis
            of comparison.
    """

    repo_url: RepoURL
    files: list[str]
    manifest: str
    tag: str = "__hash__"

    def __init__(self):
        pass


class TestConfig(BaseConfig):
    """Test config based upon https://github.com/kevinmcaleer/ota."""

    repo_url: RepoURL = RepoURL(
        user="pierreyvesbaloche", repo="kevinmca_ota", version="main"
    )
    files = ["README.md", "test_ota.py"]
    manifest: str = "version.json"


class RemoteConfig(BaseConfig):
    """A subclass that finds it's tag and files dynamically."""

    _REMOTE_VERSION: str = const("version.json")
    _TAG_KEY: str = const("tag")
    _FILES_KEY: str = const("files")

    def __init__(self, remote_url: RepoURL) -> None:
        """Sets the `tag`, `repo_url` and `files` dynamically based off a remote config.

        Args:
            remote_url: url pointing to a remote configuration on github.
                Inside this directory, there must exist a file named
                _REMOTE_VERSION = "version.json" with the following schema:
                {
                    "tag": "<commit, branch name, or tag>",
                    "files": [
                        "<file1>",
                        "<file2>",
                        ...
                    ]
                }
        """
        response = urequests.get(remote_url.url + self._REMOTE_VERSION)
        if response.status_code == 200:
            remote_config = json.loads(response.content)
            if self._TAG_KEY in remote_config and self._FILES_KEY in remote_config:
                # Resolve tags & files dynamically.
                self.tag = remote_config[self._TAG_KEY]
                self.files = remote_config[self._FILES_KEY]
                # Set the `repo_url` based off this info.
                self.repo_url = RepoURL(
                    user=remote_url.user,
                    repo=remote_url.repo,
                    # Now substitute in the tag dynamically.
                    version=self.tag,
                )
            else:
                raise KeyError(
                    f"{self._TAG_KEY} and {self._FILES_KEY} must be present."
                )
        else:
            raise NotImplementedError("Remote configuration was not found.")


######################################################################
# OTA Methods
######################################################################


class OTAUpdate:
    """Main class responsible for conducting OTAUpdates."""

    info: VersionInfo

    def __init__(self, config: BaseConfig) -> None:
        """Perform an OTA based upon a configuration.

        Notes:
            An `OTAUpdate` instance is compatible only with the initial `config`.
            For subsequent updates (for other configs), instantiate a new `OTAUpdate`.

        Args:
            config: a configuration containing information needed to update.
        """
        self.info = VersionInfo(manifest=config.manifest)
        for file in config.files:
            self.update(
                repo_url=config.repo_url.url,
                file=file,
                tag=config.tag,
            )
            # Attempt to free up memory between iterations.
            gc.collect()

    def update(self, repo_url: str, file: str, tag: str) -> None:
        """Set the latest code for a specific file from a remote repo."""
        # If using hashing, we determine the "tag" based off the hash of the response.
        if tag == BaseConfig.tag:
            # Get the latest code from the repo.
            response = urequests.get(repo_url + file)
            self._update(
                response=response,
                file=file,
                new_version=str(hash(response.content)),
            )
        # Otherwise, use the tag provided. Note, now the version check happens
        # before pulling down any code.
        elif tag != self.info.version(file=file):
            response = self._update(
                response=urequests.get(repo_url + file),
                file=file,
                new_version=tag,
            )
        else:
            print(file + " deferred...")

    def _update(self, response, file: str, new_version: str) -> None:
        """Helper function to unpack a response and update a version."""
        if response.status_code == 200 and new_version != self.info.version(file=file):
            self.write_to_file(file, response.content)
            # Write the new version to "disk".
            self.info.write_versions_to_file(versions={const(file): new_version})
            print(file + " updated...")
        else:
            print(file + " deferred...")

    @staticmethod
    def write_to_file(file: str, content: str) -> None:
        """Ensure a directory exists before writing contents to a file."""
        _DELIM: str = const("/")
        if file.find(_DELIM) != -1:
            # Strip all but the last prefix (aka the directory).
            prefix = _DELIM.join(file.split(_DELIM)[:-1])
            try:
                os.mkdir(prefix)
            except OSError:
                pass
        with open(file, "w") as f:
            f.write(content)
