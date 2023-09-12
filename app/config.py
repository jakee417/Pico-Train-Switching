from app.ota import Config, RepoURL, OTAUpdate, RemoteConfig


class RailYardConfig(Config):
    repo_url: RepoURL = RepoURL(
        user="jakee417", repo="Pico-Train-Switching", version="main"
    )
    files = [
        "app/connect.py",
        "app/logging.py",
        "app/main.py",
        "app/microdot_server.py",
    ]
    manifest: str = "version.json"


class RailYardRemoteConfig(RemoteConfig):
    manifest = "version.json"

    def __init__(self) -> None:
        super().__init__(
            remote_url=RepoURL(
                user="jakee417", repo="Pico-Train-Switching", version="main"
            )
        )


def ota():
    try:
        OTAUpdate(config=RailYardRemoteConfig())
    # If we have a bad config, lets silently fail so that our devices
    # out in the wild do not start failing mysteriously.
    except KeyError:
        pass
    except NotImplementedError:
        pass


def ota2():
    OTAUpdate(config=RailYardConfig())
