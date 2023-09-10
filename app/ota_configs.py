from app.ota import Config, RepoURL, run_ota, RemoteConfig


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
    def __init__(self) -> None:
        self.MANIFEST = "version.json"
        super().__init__(
            remote_url=RepoURL(
                user="jakee417", repo="Pico-Train-Switching", version="main"
            )
        )


def ota():
    """Helper of a helper."""
    try:
        run_ota(RailYardRemoteConfig())
    # If we have a bad config, lets silently fail so that our devices
    # out in the wild do not start failing mysteriously.
    except KeyError:
        pass
    except NotImplementedError:
        pass
