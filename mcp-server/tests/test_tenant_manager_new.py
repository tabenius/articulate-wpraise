"""Tests for TenantManager orchestration.

Mocks DB and Docker operations to test the orchestration logic.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet


@pytest.fixture
def manager():
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    with patch("articulate_mcp.tenants.manager.default_db") as mock_db, \
         patch("articulate_mcp.tenants.manager.TenantDockerOps") as mock_docker_cls:
        mock_db.fetchone = AsyncMock(return_value=None)
        mock_db.fetchall = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=1)
        mock_db.insert = AsyncMock(return_value=1)

        from articulate_mcp.tenants.manager import TenantManager
        mgr = TenantManager(
            encryption_key=os.environ["ENCRYPTION_KEY"],
            template_dir=os.path.join(os.path.dirname(__file__), "..", "..", "templates"),
            compose_output_dir="/tmp/tenants",
        )
        mgr.docker_ops = mock_docker_cls.return_value
        mgr.db = mock_db
        yield mgr


@pytest.mark.asyncio
async def test_create_tenant_returns_tenant_id(manager):
    result = await manager.create_tenant(name="testsite", owner_user_id=1)
    assert "tenant_id" in result
    assert result["name"] == "testsite"
    assert result["domain"] == "testsite.ragbaz.cc"
    assert result["default_view"] == "wordpress"
    assert result["status"] == "running"


@pytest.mark.asyncio
async def test_create_tenant_calls_docker_up(manager):
    await manager.create_tenant(name="testsite", owner_user_id=1)
    manager.docker_ops.up.assert_called_once()


@pytest.mark.asyncio
async def test_create_tenant_inserts_db_records(manager):
    await manager.create_tenant(name="testsite", owner_user_id=1)
    # Should have 4 DB calls: insert tenant, insert secrets, insert tenant_users, update status
    assert manager.db.execute.call_count == 4


@pytest.mark.asyncio
async def test_create_tenant_validates_name(manager):
    with pytest.raises(ValueError, match="DNS-safe"):
        await manager.create_tenant(name="INVALID NAME!", owner_user_id=1)


@pytest.mark.asyncio
async def test_create_tenant_rejects_reserved_name(manager):
    with pytest.raises(ValueError, match="reserved"):
        await manager.create_tenant(name="app", owner_user_id=1)


@pytest.mark.asyncio
async def test_create_tenant_rejects_duplicate(manager):
    manager.db.fetchone = AsyncMock(return_value={"id": "existing"})
    with pytest.raises(ValueError, match="already exists"):
        await manager.create_tenant(name="testsite", owner_user_id=1)


@pytest.mark.asyncio
async def test_set_default_view(manager):
    manager.db.execute = AsyncMock(return_value=1)
    result = await manager.set_default_view("abc", "faust")
    assert result is True


@pytest.mark.asyncio
async def test_set_default_view_rejects_invalid(manager):
    with pytest.raises(ValueError, match="Invalid view"):
        await manager.set_default_view("abc", "nextjs")


@pytest.mark.asyncio
async def test_delete_tenant(manager):
    manager.db.fetchone = AsyncMock(return_value={"id": "abc", "name": "test"})
    manager.db.execute = AsyncMock(return_value=1)
    result = await manager.delete_tenant("abc")
    assert result is True
    manager.docker_ops.down.assert_called_once()


@pytest.mark.asyncio
async def test_delete_tenant_not_found(manager):
    manager.db.fetchone = AsyncMock(return_value=None)
    result = await manager.delete_tenant("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_add_custom_domain(manager):
    manager.db.insert = AsyncMock(return_value=42)
    result = await manager.add_custom_domain("abc", "myblog.com", "faust")
    assert result == 42


@pytest.mark.asyncio
async def test_add_custom_domain_rejects_invalid_view(manager):
    with pytest.raises(ValueError, match="Invalid view"):
        await manager.add_custom_domain("abc", "myblog.com", "nextjs")


@pytest.mark.asyncio
async def test_list_tenants(manager):
    manager.db.fetchall = AsyncMock(return_value=[{"id": "abc", "name": "test"}])
    result = await manager.list_tenants(owner_user_id=1)
    assert len(result) == 1
