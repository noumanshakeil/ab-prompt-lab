import pytest

@pytest.mark.asyncio
async def test_ab_flow(client):
    exp = await client.post(
        "/api/experiments",
        json={"name": "tone", "prompt_a": "Be formal", "prompt_b": "Be casual", "traffic_a": 50},
    )
    eid = exp.json()["id"]
    run = await client.post(
        f"/api/experiments/{eid}/run",
        json={"subject": "user-1", "input": "Explain SQL joins"},
    )
    assert run.status_code == 200
    assert run.json()["variant"] in {"A", "B"}
    metrics = await client.get(f"/api/experiments/{eid}/metrics")
    assert metrics.json()["variants"]
