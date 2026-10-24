"""Export data from a config.xml file into Redis.

Keys written:
  - "subdomains"              -> JSON array with all <subdomain> values
  - "cookie:<name>:<host>"   -> the text value of each <cookie> element

The parsing is kept separate from the Redis writing so both parts can be
unit-tested on their own.
"""

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET


def parse_config(xml_path):
    """Read an XML file and return (subdomains, cookies).

    subdomains: list of strings, in file order, whitespace trimmed.
    cookies:    dict {"cookie:<name>:<host>": value}
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    subdomains = []
    for element in root.iter("subdomain"):
        value = (element.text or "").strip()
        if value:
            subdomains.append(value)

    cookies = {}
    for element in root.iter("cookie"):
        name = element.get("name")
        host = element.get("host")
        if not name or not host:
            # A cookie without a name or host cannot form its key, skip it.
            continue
        value = (element.text or "").strip()
        cookies[f"cookie:{name}:{host}"] = value

    return subdomains, cookies


def export_to_redis(client, subdomains, cookies):
    """Write everything to Redis. Returns the list of keys that were saved."""
    pipe = client.pipeline()
    pipe.set("subdomains", json.dumps(subdomains))
    for key, value in cookies.items():
        pipe.set(key, value)
    pipe.execute()
    return ["subdomains", *cookies.keys()]


def connect_redis(host, port, retries=10, delay_seconds=1.0):
    """Connect to Redis, retrying briefly (Redis may still be starting)."""
    import redis  # imported here so parsing/tests do not need a server

    last_error = None
    for _ in range(retries):
        try:
            client = redis.Redis(
                host=host, port=port, decode_responses=True,
                socket_connect_timeout=2,
            )
            client.ping()
            return client
        except redis.RedisError as error:
            last_error = error
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to Redis at {host}:{port}: {last_error}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export subdomains and cookies from an XML file to Redis."
    )
    parser.add_argument("xml", help="path to the XML file, e.g. config.xml")
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="print all keys saved to Redis",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.xml):
        print(f"Error: file not found: {args.xml}", file=sys.stderr)
        return 1

    try:
        subdomains, cookies = parse_config(args.xml)
    except ET.ParseError as error:
        print(f"Error: could not parse XML file {args.xml}: {error}", file=sys.stderr)
        return 1

    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    client = connect_redis(host, port)

    saved_keys = export_to_redis(client, subdomains, cookies)

    if args.verbose:
        for key in saved_keys:
            print(key)
    print(f"Exported {len(saved_keys)} keys to Redis "
          f"({len(subdomains)} subdomains, {len(cookies)} cookies).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
