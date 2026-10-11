import argparse, sys
from . import report as rep
from .fetch import fetch_all


def main(argv=None):
    ap = argparse.ArgumentParser(prog="neocloud")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download and cache the real datasets")
    f.add_argument("sites", nargs="*")
    r = sub.add_parser("run", help="run all checks from cached data and write out/report.*")
    r.add_argument("--sites", nargs="*"); r.add_argument("--only", nargs="*"); r.add_argument("--online", action="store_true")
    s = sub.add_parser("serve", help="start the API on :8000")
    s.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch_all(a.sites or None)
    elif a.cmd == "run":
        report = rep.run(a.sites, a.only, offline=not a.online)
        rep.write(report)
        print(rep.to_markdown(report).split("## ")[0])
    elif a.cmd == "serve":
        import uvicorn
        uvicorn.run("neocloud.api:app", host="0.0.0.0", port=a.port)


if __name__ == "__main__":
    main()
