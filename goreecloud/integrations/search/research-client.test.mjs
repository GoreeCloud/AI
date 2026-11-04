import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createGoreeCloudResearchClient,
  createGoreeCloudResearchTool,
  GoreeCloudResearchError,
} from './research-client.mjs';

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), { status, headers: {
    'content-type': 'application/json', ...headers,
  }});
}
function fixture({
  enabled = true,
  releaseQualified = true,
  allowExternal = false,
  available = { local: true, brave: false, searxng: false },
  ready = { status: 'ready', scope: 'local-catalog' },
  searchReply = {
    results: [{ title: 'GoreeCloud documentation', description: 'First party research.',
      url: 'https://docs.goreecloud.com/overview', source: 'curated' }],
    count: 1, scope: 'local-only', providers: ['local'], warnings: [],
  },
  searchStatus = 200,
} = {}) {
  const calls = [];
  const fetchImpl = async (raw, init) => {
    const url = new URL(raw);
    calls.push({ url, init });
    assert.equal(url.host, '127.0.0.1:8787');
    assert.equal(init.redirect, 'error');
    assert.equal(init.headers['Cache-Control'], 'no-store');
    assert.equal(init.headers.Authorization, undefined);
    if (url.pathname === '/readyz') {
      assert.equal(init.method, 'GET');
      return json(ready, ready.status === 'ready' ? 200 : 503);
    }
    if (url.pathname === '/api/providers') {
      assert.equal(init.method, 'GET');
      return json({ available, default: ['local'], external_requires_consent: true });
    }
    if (url.pathname === '/api/search') {
      assert.equal(init.method, 'POST');
      assert.equal(init.headers['Content-Type'], 'application/json');
      return json(searchReply, searchStatus);
    }
    throw Error('Unexpected search transport path: ' + url.pathname);
  };
  const client = createGoreeCloudResearchClient({
    enabled, releaseQualified, allowExternal, fetchImpl,
  });
  return { client, calls };
}

test('disabled by default; not even readiness makes a network request', async () => {
  let calls = 0;
  const fetchImpl = () => { calls++; throw Error('must not be called'); };
  const client = createGoreeCloudResearchClient({ fetchImpl });
  assert.deepEqual(await client.health(), { ready: false, reason: 'not-qualified' });
  await assert.rejects(client.research('plans'), { code: 'not_qualified' });
  assert.equal(calls, 0);
  const partial = createGoreeCloudResearchClient({ enabled: true, fetchImpl });
  await assert.rejects(partial.research('plans'), { code: 'not_qualified' });
  assert.equal(calls, 0);
});

test('endpoint is hard-bound to explicit IPv4 loopback, never network names or arbitrary paths', () => {
  for (const endpoint of [
    'https://search-dev.goreecloud.com',
    'http://goreecloud-search:8787',
    'http://localhost:8787',
    'http://[::1]:8787',
    'http://127.0.0.1:8787/a',
    'http://127.0.0.1:8787/?target=http://evil',
    'http://admin:pass@127.0.0.1:8787',
    'http://127.0.0.1:0',
    'http://127.0.0.1:99999',
  ]) {
    assert.throws(() => createGoreeCloudResearchClient({ endpoint }), { code: 'invalid_config' }, endpoint);
  }
});

test('ready local-only Search delivers source-attributed citations without any provider egress', async () => {
  const { client, calls } = fixture();
  assert.deepEqual(await client.health(), { ready: true, provider: 'GoreeCloud Search' });
  const result = await client.research('  GoreeCloud plans  ', { limit: 8 });
  assert.equal(result.engine, 'GoreeCloud Search');
  assert.equal(result.scope, 'local-only');
  assert.deepEqual(result.results, [
    { title: 'GoreeCloud documentation', description: 'First party research.',
      url: 'https://docs.goreecloud.com/overview', source: 'curated',
      provider: 'local', untrustedContent: true },
  ]);
  assert.equal(calls.at(-1).url.pathname, '/api/search');
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), {
    query: 'GoreeCloud plans', limit: 8, providers: ['local'], share_query: false,
  });
});

test('not ready stops before querying providers or sending a research prompt', async () => {
  const { client, calls } = fixture({ ready: { status: 'unavailable', scope: 'local-catalog' } });
  assert.deepEqual(await client.health(), { ready: false, reason: 'unavailable' });
  await assert.rejects(client.research('not-ready'), { code: 'search_unavailable' });
  assert.equal(calls.some(c => c.url.pathname === '/api/search'), false);
});

test('external research never shares terms without both operator enablement and per-call user consent', async () => {
  const first = fixture({ available: { local: true, brave: true, searxng: false } });
  await assert.rejects(first.client.research('sensitive topic', {
    providers: ['local', 'brave'], shareQuery: true,
  }), { code: 'consent_required' });
  assert.equal(first.calls.length, 0);
  const second = fixture({ allowExternal: true, available: { local: true, brave: true } });
  await assert.rejects(second.client.research('sensitive topic', {
    providers: ['local', 'brave'], shareQuery: false,
  }), { code: 'consent_required' });
  assert.equal(second.calls.length, 0);
});

test('approved external provider requires actual availability and preserves attribution', async () => {
  const reply = {
    results: [{ title: 'New research', description: 'Reported fact',
      url: 'https://news.example.org/a', source: 'Brave Search', provider: 'brave' }],
    count: 1, scope: 'federated', providers: ['local', 'brave'], warnings: [],
  };
  const denied = fixture({ allowExternal: true, searchReply: reply });
  await assert.rejects(denied.client.research('market report', {
    providers: ['local', 'brave'], shareQuery: true,
  }), { code: 'provider_unavailable' });
  assert.equal(denied.calls.some(c => c.url.pathname === '/api/search'), false);

  const allowed = fixture({ allowExternal: true,
    available: { local: true, brave: true, searxng: false }, searchReply: reply });
  const result = await allowed.client.research('market report', {
    providers: ['local', 'brave'], shareQuery: true,
  });
  assert.equal(result.scope, 'federated');
  assert.equal(result.results[0].provider, 'brave');
  const call = allowed.calls.at(-1);
  assert.deepEqual(JSON.parse(call.init.body), {
    query: 'market report', limit: 8, providers: ['local', 'brave'], share_query: true,
  });
});

test('malformed query, duplicates, bogus limits and local consent fail before I/O', async () => {
  const { client, calls } = fixture({ allowExternal: true });
  const cases = [
    ['', {}], ['x'.repeat(161), {}], ['note', { limit: true }],
    ['note', { limit: 21 }], ['note', { providers: ['local', 'local'] }],
    ['note', { providers: ['unknown'] }], ['note', { shareQuery: true }],
    ['note', { providers: ['brave'], shareQuery: 'yes' }],
  ];
  for (const [query, options] of cases) {
    await assert.rejects(client.research(query, options), { code: 'invalid_query' });
  }
  assert.equal(calls.length, 0);
});

test('untrusted private citation links, credentials and provider spoofing are refused', async () => {
  for (const url of [
    'http://example.org/not-secure',
    'https://127.0.0.1/private',
    'https://[::1]/',
    'https://localhost/',
    'https://intranet.internal/',
    'https://admin:password@example.org/',
    'https://example.org:8080/foo',
    'https://example.org/#fragment',
  ]) {
    const { client } = fixture({ searchReply: {
      results: [{ title: 'Title', description: 'Text', url, source: 'source' }],
      count: 1, scope: 'local-only', providers: ['local'], warnings: [],
    } });
    await assert.rejects(client.research('question'), { code: 'invalid_reply' }, url);
  }
  const { client } = fixture({ searchReply: {
    results: [{ title: 'Title', description: 'Text', url: 'https://example.org/a', source: 'brave', provider: 'brave' }],
    count: 1, scope: 'local-only', providers: ['local'], warnings: [],
  } });
  await assert.rejects(client.research('question'), { code: 'invalid_reply' });
});

test('provider response mismatch and unrecognized warning fail closed', async () => {
  for (const changes of [
    { count: 2 }, { scope: 'federated' }, { providers: ['brave'] },
    { warnings: [{ provider: 'local', code: 'secret-exposure' }] },
  ]) {
    const { client } = fixture({ searchReply: {
      results: [], count: 0, scope: 'local-only', providers: ['local'], warnings: [], ...changes,
    } });
    await assert.rejects(client.research('question'), { code: 'invalid_reply' });
  }
});

test('bad HTTP status and oversized response fail closed without silent fallback', async () => {
  const unavailable = fixture({ searchStatus: 503 });
  await assert.rejects(unavailable.client.research('something'), { code: 'search_unavailable' });
  const huge = fixture({ searchReply: {
    results: [], count: 0, scope: 'local-only', providers: ['local'], warnings: [],
    extra: 'x'.repeat(132000),
  } });
  await assert.rejects(huge.client.research('something'), { code: 'invalid_reply' });
});

test('MCP tool is not published until both release and enablement gates pass', async () => {
  const client = createGoreeCloudResearchClient({ fetchImpl: () => { throw Error('offline'); } });
  const tool = createGoreeCloudResearchTool({ client, authorizeRequest: async () => true });
  assert.deepEqual(tool.listTools(), []);
  await assert.rejects(tool.callTool('goreecloud_search_research', { query: 'x' }, {}), {
    code: 'not_qualified',
  });
});

test('MCP session auth, schema and provider policy restrict model tool calls', async () => {
  const { client, calls } = fixture();
  let authorized = 0;
  const tool = createGoreeCloudResearchTool({ client, authorizeRequest: async ctx => {
    authorized++;
    return ctx?.userId === 'user-123';
  } });
  assert.equal(tool.listTools()[0].name, 'goreecloud_search_research');
  await assert.rejects(tool.callTool('web_search', { query: 'test' }, { userId: 'user-123' }), {
    code: 'invalid_query',
  });
  await assert.rejects(tool.callTool('goreecloud_search_research', {
    query: 'test', endpoint: 'http://attacker',
  }, { userId: 'user-123' }), { code: 'invalid_query' });
  await assert.rejects(tool.callTool('goreecloud_search_research', { query: 'test' }), {
    code: 'not_authorized',
  });
  await assert.rejects(tool.callTool('goreecloud_search_research', { query: 'test' }, {
    userId: 'other-user',
  }), { code: 'not_authorized' });
  assert.equal(calls.length, 0);
  assert.equal(authorized, 1);
  const output = await tool.callTool('goreecloud_search_research', {
    query: 'test', limit: 3,
  }, { userId: 'user-123' });
  assert.equal(JSON.parse(output.content[0].text).engine, 'GoreeCloud Search');
  assert.equal(authorized, 2);
});

test('MCP authorizer exceptions are sanitized and fail closed', async () => {
  const { client, calls } = fixture();
  const tool = createGoreeCloudResearchTool({ client,
    authorizeRequest: async () => { throw Error('internal identity-token-secret'); },
  });
  await assert.rejects(tool.callTool('goreecloud_search_research', { query: 'test' }, {}), error => {
    assert.ok(error instanceof GoreeCloudResearchError);
    assert.equal(error.code, 'not_authorized');
    assert.doesNotMatch(error.message, /secret/);
    return true;
  });
  assert.equal(calls.length, 0);
});
