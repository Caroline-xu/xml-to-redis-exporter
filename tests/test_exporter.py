import json
import os

import fakeredis
import pytest

from app.exporter import export_to_redis, parse_config

HERE = os.path.dirname(__file__)
REAL_CONFIG = os.path.join(HERE, "..", "config.xml")

SAMPLE_XML = """<config>
    <subdomains>
        <subdomain>http://a.example.com</subdomain>
        <subdomain> https://b.example.com </subdomain>
    </subdomains>
    <cookies>
        <cookie name="dlp-avast" host="amazon">mmm_amz_dlp_777_ppc_m</cookie>
        <cookie name="dlp-avg" host="cnet">mmm_cnt_dlp_779_ppc_m</cookie>
    </cookies>
</config>
"""


@pytest.fixture()
def sample_file(tmp_path):
    path = tmp_path / "sample.xml"
    path.write_text(SAMPLE_XML, encoding="utf-8")
    return str(path)


def test_parse_subdomains(sample_file):
    subdomains, _ = parse_config(sample_file)
    # Order is kept and surrounding whitespace is trimmed.
    assert subdomains == ["http://a.example.com", "https://b.example.com"]


def test_parse_cookies(sample_file):
    _, cookies = parse_config(sample_file)
    assert cookies == {
        "cookie:dlp-avast:amazon": "mmm_amz_dlp_777_ppc_m",
        "cookie:dlp-avg:cnet": "mmm_cnt_dlp_779_ppc_m",
    }


def test_export_writes_expected_keys(sample_file):
    subdomains, cookies = parse_config(sample_file)
    client = fakeredis.FakeRedis(decode_responses=True)

    saved = export_to_redis(client, subdomains, cookies)

    assert json.loads(client.get("subdomains")) == subdomains
    assert client.get("cookie:dlp-avast:amazon") == "mmm_amz_dlp_777_ppc_m"
    assert sorted(saved) == sorted(client.keys("*"))
    assert len(saved) == 3  # 1 subdomains key + 2 cookie keys


def test_parse_real_config_file():
    subdomains, cookies = parse_config(REAL_CONFIG)
    assert len(subdomains) == 38
    assert subdomains[0] == "http://secureline.tools.avast.com"
    assert len(cookies) == 46
    assert cookies["cookie:dlp-avast:amazon"] == "mmm_amz_dlp_777_ppc_m"
    assert cookies["cookie:dlp-avg:vector"] == "mmm_vct_dlp_779_ppc_m"


def test_export_real_config_file():
    subdomains, cookies = parse_config(REAL_CONFIG)
    client = fakeredis.FakeRedis(decode_responses=True)

    saved = export_to_redis(client, subdomains, cookies)

    assert len(saved) == 47
    assert len(json.loads(client.get("subdomains"))) == 38
