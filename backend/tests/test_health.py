import asyncio

import httpx

from app.main import create_app


def test_health_endpoint_reports_stage_one_shell() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "service": "astra-api",
        "status": "ready",
        "stage": 13,
        "data_dir": response.json()["data_dir"],
        "clinical_analysis_available": False,
    }
