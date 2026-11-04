"""Isolated, first-party AI <-> Search localhost contract smoke.

Usage (authorized local development only):
    python3 goreecloud/integrations/search/smoke_local.py /path/to/GoreeCloud/search

This test launches a temporary localhost-only Search server with a private
SQLite index, invokes this repository's Node research client, and stops it.
It makes no outside API calls, opens no public port, and does not qualify
GoreeCloud Search for a production release.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

CLIENT = Path(__file__).resolve().with_name("research-client.mjs")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: smoke_local.py /absolute/path/to/GoreeCloud/search")
    source = Path(sys.argv[1])
    if not source.is_absolute() or not (source / "goreecloud_search/server.py").is_file():
        raise SystemExit("reviewed GoreeCloud Search source checkout required")
    sys.path.insert(0, str(source))
    from goreecloud_search.providers import ProviderConfig
    from goreecloud_search.server import SearchServer
    from goreecloud_search.store import initialize, import_jsonl

    with tempfile.TemporaryDirectory(prefix="gc-search-contract-") as directory:
        base = Path(directory)
        db_path = base / "private.sqlite3"
        data_path = base / "data.jsonl"
        initialize(db_path)
        data_path.write_text(json.dumps({
            "title": "Verified GoreeCloud local integration",
            "description": "Private test fixture with no external search query.",
            "url": "https://example.org/verified",
            "source": "first-party-test",
        }) + "\n", encoding="utf-8")
        import_jsonl(db_path, data_path)
        server = SearchServer(("127.0.0.1", 0), db_path)
        # Hard-stop all optional Brave/SearXNG egress in this smoke test.
        server.provider_config = ProviderConfig()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            js = """
              import assert from 'node:assert/strict';
              const { createGoreeCloudResearchClient } =
                await import(process.env.GC_RESEARCH_CLIENT_URL);
              // Test-only release-gate simulation; never a deployment setting.
              const client = createGoreeCloudResearchClient({
                enabled: true, releaseQualified: true, allowExternal: false,
                endpoint: 'http://127.0.0.1:' + process.env.GC_SEARCH_SMOKE_PORT,
              });
              assert.deepEqual(await client.health(), {
                ready: true, provider: 'GoreeCloud Search',
              });
              const result = await client.research('Verified GoreeCloud', { limit: 3 });
              assert.equal(result.engine, 'GoreeCloud Search');
              assert.equal(result.scope, 'local-only');
              assert.equal(result.results.length, 1);
              assert.equal(result.results[0].source, 'first-party-test');
              assert.equal(result.results[0].url, 'https://example.org/verified');
              assert.equal(result.results[0].untrustedContent, true);
              await assert.rejects(
                client.research('unapproved query', {
                  providers: ['brave'], shareQuery: true,
                }),
                { code: 'consent_required' },
              );
              console.log('PASS: real Search localhost API + AI research client; no external query sharing');
            """
            env = {
                **os.environ,
                "GC_RESEARCH_CLIENT_URL": CLIENT.as_uri(),
                "GC_SEARCH_SMOKE_PORT": str(server.server_port),
            }
            result = subprocess.run(
                ["node", "--input-type=module", "--eval", js],
                env=env, capture_output=True, text=True, timeout=20, check=False,
            )
            if result.returncode:
                raise RuntimeError(
                    "AI/Search localhost contract failed (no tokens or private data shown): "
                    + result.stderr[-1800:]
                )
            print(result.stdout.strip())
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    main()
