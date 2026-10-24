# XML → Redis exporter

A small app that reads a `config.xml` file and exports its data to Redis.

## What gets written to Redis

| Key | Value |
| --- | --- |
| `subdomains` | JSON array with all `<subdomain>` values, e.g. `["http://secureline.tools.avast.com", "http://gf.tools.avast.com"]` |
| `cookie:<name>:<host>` | The text of each `<cookie>` element, e.g. key `cookie:dlp-avast:amazon` → `mmm_amz_dlp_777_ppc_m` |

With the provided `config.xml` this is 47 keys in total:
1 `subdomains` key (38 entries) and 46 `cookie:...` keys.

## How to run

Requirements: Docker with the Compose plugin.

```bash
./export.sh -v /path/to/config.xml
```

- Without `-v` the app only prints a short summary.
- With `-v` it also prints every key it saved to Redis, one per line.

`export.sh` starts the Redis container, waits until it is healthy, then runs
the exporter once in its own container with your XML file mounted in read-only.

You can also start everything with the bundled example file:

```bash
docker compose up --build app
```

and afterwards inspect the data, for example:

```bash
docker compose exec redis redis-cli GET subdomains
docker compose exec redis redis-cli 'KEYS' 'cookie:*'
```

## Project structure

- `app/exporter.py` — the whole app. Parsing (`parse_config`) is separate from
  writing (`export_to_redis`) so both can be tested without a real server.
  The Redis connection retries for a few seconds, because the app container
  can start before Redis is ready to accept connections.
- `export.sh` — the one-command entry point described above.
- `Dockerfile` / `docker-compose.yml` — two services: `redis` (redis:7-alpine,
  with a healthcheck) and `app` (Python 3.12).
- `tests/test_exporter.py` — unit tests (pytest). Parsing is tested on a small
  sample file and on the real `config.xml`; writing is tested against
  fakeredis, an in-memory Redis, so no running server is needed.
- `config.xml` — the example input file from the task.

## How to run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Notes / decisions

- Cookie values are copied exactly as they appear in the file
  (they are case-sensitive, e.g. one value in the file starts with a
  capital letter and is kept that way).
- A `<cookie>` without a `name` or `host` attribute is skipped, because
  its Redis key cannot be built.
- Re-running the export simply overwrites the same keys with the same
  values, so it is safe to run more than once.
