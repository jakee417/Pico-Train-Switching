from .ota import BaseConfig, RepoURL, OTAUpdate, RemoteConfig
from .connect import Connect


class RailYardConfig(BaseConfig):
    repo_url: RepoURL = RepoURL(
        user="jakee417", repo="Pico-Train-Switching", version="main"
    )
    files = [
        "bin/lib/__init__.mpy",
        "bin/lib/microdot.mpy",
        "bin/lib/picozero.mpy",
        "bin/__init__.mpy",
        "bin/config.mpy",
        "bin/connect.mpy",
        "bin/logging.mpy",
        "bin/main.mpy",
        "bin/microdot_server.mpy",
        "bin/ota.mpy",
        "bin/server_methods.mpy",
        "bin/train_switch.mpy",
    ]
    manifest: str = Connect._VERSION


class RailYardRemoteConfig(RemoteConfig):
    manifest = Connect._VERSION

    def __init__(self) -> None:
        super().__init__(
            remote_url=RepoURL(
                user="jakee417", repo="Pico-Train-Switching", version="main"
            )
        )


def ota():
    # Depending on where this code lives, it can break subsequent workflows.
    # If we have a bad config, silently fail so that our devices
    # out in the wild do not start failing mysteriously.
    try:
        OTAUpdate(config=RailYardRemoteConfig())
    except (KeyError, NotImplementedError, Exception):
        pass


def ota2():
    OTAUpdate(config=RailYardConfig())
