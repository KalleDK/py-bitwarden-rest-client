import pathlib

DEFAULT_PORT = 8087
DEFAULT_BASEURL = f"http://localhost:{DEFAULT_PORT}"
DEFAULT_BIN_PATH = pathlib.Path("/usr/local/bin/bw")
DEFAULT_APP_DATA = pathlib.Path.home() / ".local" / "share" / "bw_rest" / "default"
