"""API-level tests for auth enforcement, the setup wizard, feed CRUD and stats."""
import pytest

from conftest import TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD

PROTECTED_WRITE = "http://localhost/some-feed"  # localhost -> discover_feed skips network


# ---------------------------------------------------------------------------
# Setup wizard flow
# ---------------------------------------------------------------------------

class TestSetupWizard:
    async def test_requests_redirect_to_setup_before_first_admin(self, client):
        resp = await client.get("/")
        assert resp.status_code == 307
        assert resp.headers["location"] == "/setup"

    async def test_setup_form_renders(self, client):
        resp = await client.get("/setup")
        assert resp.status_code == 200
        assert "Welcome aboard" in resp.text

    async def test_setup_rejects_mismatched_passwords(self, client):
        resp = await client.post(
            "/setup",
            data={"username": "alice", "password": "password123", "confirm_password": "different"},
        )
        assert resp.status_code == 200
        assert "Passwords do not match" in resp.text

    async def test_setup_rejects_short_password(self, client):
        resp = await client.post(
            "/setup",
            data={"username": "alice", "password": "short", "confirm_password": "short"},
        )
        assert resp.status_code == 200
        assert "at least 8 characters" in resp.text

    async def test_setup_creates_admin_and_then_locks(self, client):
        resp = await client.post(
            "/setup",
            data={"username": "alice", "password": "password123", "confirm_password": "password123"},
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

        # Once an admin exists, the app leaves setup mode: root is served.
        root = await client.get("/")
        assert root.status_code == 200

        # /setup is permanently locked afterwards.
        locked = await client.post(
            "/setup",
            data={"username": "bob", "password": "password123", "confirm_password": "password123"},
        )
        assert locked.status_code == 403

        # The freshly created admin can authenticate against a protected endpoint.
        ok = await client.post("/api/refresh", auth=("alice", "password123"))
        assert ok.status_code == 200

    async def test_setup_redirects_to_root_when_admin_exists(self, client, admin_credentials):
        resp = await client.get("/setup")
        assert resp.status_code == 307
        assert resp.headers["location"] == "/"


# ---------------------------------------------------------------------------
# Auth enforcement on mutating endpoints
# ---------------------------------------------------------------------------

class TestAuthEnforcement:
    @pytest.mark.parametrize(
        "method,url",
        [
            ("post", "/api/refresh"),
            ("post", "/api/feeds"),
            ("delete", "/api/feeds/1"),
        ],
    )
    async def test_missing_credentials_rejected(self, client, admin_credentials, method, url):
        resp = await client.request(method, url, json={} if method == "post" else None)
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "method,url",
        [
            ("post", "/api/refresh"),
            ("post", "/api/feeds"),
            ("delete", "/api/feeds/1"),
        ],
    )
    async def test_wrong_credentials_rejected(self, client, admin_credentials, method, url):
        resp = await client.request(
            method, url, auth=("testadmin", "wrongpass"),
            json={} if method == "post" else None,
        )
        assert resp.status_code == 401

    async def test_correct_credentials_accepted_refresh(self, client, admin_credentials, monkeypatch):
        import main

        async def _noop():
            return None

        monkeypatch.setattr(main, "update_all_feeds", _noop)
        resp = await client.post("/api/refresh", auth=(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD))
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

    async def test_correct_credentials_accepted_delete(self, client, admin_credentials):
        # Deleting a non-existent feed still succeeds (idempotent), proving auth passed.
        resp = await client.delete("/api/feeds/999", auth=(TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Env-var credentials take priority over DB / wizard
# ---------------------------------------------------------------------------

class TestEnvCredentialOverride:
    async def test_env_creds_skip_setup_and_authenticate(self, client, monkeypatch):
        monkeypatch.setenv("ADMIN_USERNAME", "envadmin")
        monkeypatch.setenv("ADMIN_PASSWORD", "envpass")

        # No admin in DB, but env creds mean we are NOT in setup mode.
        root = await client.get("/")
        assert root.status_code == 200

        good = await client.delete("/api/feeds/1", auth=("envadmin", "envpass"))
        assert good.status_code == 200

        bad = await client.delete("/api/feeds/1", auth=("envadmin", "nope"))
        assert bad.status_code == 401


# ---------------------------------------------------------------------------
# Feed CRUD
# ---------------------------------------------------------------------------

class TestFeedCrud:
    async def test_add_and_delete_feed(self, client, admin_credentials):
        auth = (TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD)
        create = await client.post(
            "/api/feeds",
            auth=auth,
            json={"url": PROTECTED_WRITE, "category_name": "Testing", "title": "Local Feed"},
        )
        assert create.status_code == 200
        body = create.json()
        assert body["status"] == "success"
        feed_id = body["id"]

        # The new category/feed shows up in init_data.
        init = await client.get("/api/init_data")
        assert init.status_code == 200
        names = [cat["name"] for cat in init.json()]
        assert "Testing" in names

        delete = await client.delete(f"/api/feeds/{feed_id}", auth=auth)
        assert delete.status_code == 200

    async def test_articles_pagination_shape(self, client, admin_credentials):
        resp = await client.get("/api/articles")
        assert resp.status_code == 200
        body = resp.json()
        assert set(["articles", "has_next", "total"]).issubset(body.keys())
        assert body["articles"] == []
        assert body["total"] == 0
        assert body["has_next"] is False


# ---------------------------------------------------------------------------
# Quality stats endpoint
# ---------------------------------------------------------------------------

class TestQualityStats:
    async def test_quality_stats_schema_empty_db(self, client, admin_credentials):
        resp = await client.get("/api/stats/quality")
        assert resp.status_code == 200
        body = resp.json()
        for key in ("total_articles", "filtered_articles", "pass_rate", "avg_quality_score", "top_flags"):
            assert key in body
        assert body["total_articles"] == 0
        assert body["filtered_articles"] == 0
        assert body["pass_rate"] == 100.0
        assert isinstance(body["top_flags"], list)
