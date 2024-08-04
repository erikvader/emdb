import tomllib
from .emdb import start

def main():
    with open("./emdb.toml", "rb") as f:
        data = tomllib.load(f)
        start(
            data["database"],
            data["archive"],
            data["buffers"],
            data["inspecting"],
            data["thumbcache"],
            data["trash"],
            data["dups"],
        )

if __name__ == "__main__":
    main()
