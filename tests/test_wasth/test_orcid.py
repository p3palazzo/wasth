import httpx
import pytest

from wasth.core.orcid import OrcidError, orcid_exists


def make_transport(status_code: int) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (200, True),
        (404, False),
    ],
)
def test_orcid_record_exists(status_code: int, expected: bool) -> None:
    transport = make_transport(status_code)

    assert (
        orcid_exists(
            "0000-0002-1825-0097",
            transport=transport,
        )
        is expected
    )


def test_orcid_request_uses_content_negotiation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)

    orcid_exists("0000-0002-1825-0097", transport=transport)

    request = requests[0]
    assert request.method == "GET"
    assert request.url == "https://orcid.org/0000-0002-1825-0097"
    assert request.headers["Accept"] == "application/xml"
    assert "WASTH" in request.headers["User-Agent"]


@pytest.mark.parametrize("status_code", [301, 400, 403, 500, 503])
def test_unexpected_status_raises_orcid_error(status_code: int) -> None:
    transport = make_transport(status_code)

    with pytest.raises(OrcidError, match=f"HTTP {status_code}"):
        orcid_exists("0000-0002-1825-0097", transport=transport)
