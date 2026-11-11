import json
from pathlib import Path

import httpx
import pytest

from wasth.core.orcid import OrcidError, OrcidRecord, orcid_profile, parse_orcid

FIXTURES = Path(__file__).parent.parent / "data"
VALID_ORCID = "0000-0002-0187-774X"
INVALID_ORCID = "0000-1234-5678"


def make_transport(
    status_code: int = 200,
    json_data: dict[str, object] | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json=json_data,
        )

    return httpx.MockTransport(handler)


@pytest.fixture
def valid_fixture() -> dict[str, object]:
    valid_fixture = FIXTURES / "valid" / "OrcidProfile-001.json"
    return json.loads((valid_fixture).read_text(encoding="utf-8"))


def test_parse_valid_orcid() -> None:
    full_valid_orcid_url = "https://orcid.org/" + VALID_ORCID
    orcid_curie = "orcid:" + VALID_ORCID
    assert parse_orcid(full_valid_orcid_url) == VALID_ORCID
    assert parse_orcid(orcid_curie) == VALID_ORCID
    assert parse_orcid(VALID_ORCID) == VALID_ORCID


def test_parse_invalid_orcid() -> None:
    with pytest.raises(ValueError) as e_info:
        parse_orcid(INVALID_ORCID)


def test_orcid_profile_with_real_fixture(valid_fixture: dict[str, object]) -> None:
    transport = make_transport(json_data=valid_fixture)

    record = orcid_profile(VALID_ORCID, transport=transport)

    assert record.orcid == VALID_ORCID
    assert record.given_names == "Pedro Paulo"
    assert record.family_name == "Palazzo"
    assert record.credit_name is None
    assert record.display_name == "Pedro Paulo Palazzo"
    assert record.biography is not None


def test_missing_orcid_raises_orcid_error() -> None:
    transport = make_transport(status_code=404)

    with pytest.raises(
        OrcidError, match="Nenhum registro encontrado para ORCiD 0000-1234-5678."
    ):
        orcid_profile(INVALID_ORCID, transport=transport)


def test_orcid_request_uses_content_negotiation(
    valid_fixture: dict[str, object],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=valid_fixture)

    transport = httpx.MockTransport(handler)

    orcid_profile("0000-0002-0187-774X", transport=transport)

    request = requests[0]
    assert request.method == "GET"
    assert request.url == "https://orcid.org/0000-0002-0187-774X"
    assert request.headers["Accept"] == "application/json"
    assert "WASTH" in request.headers["User-Agent"]


@pytest.mark.parametrize("status_code", [301, 400, 403, 500, 503])
def test_unexpected_status_raises_orcid_error(status_code: int) -> None:
    transport = make_transport(status_code)

    with pytest.raises(OrcidError, match=f"HTTP {status_code}"):
        orcid_profile("0000-0002-1825-0097", transport=transport)
