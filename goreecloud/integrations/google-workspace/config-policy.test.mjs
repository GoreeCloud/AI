import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../../deployment/librechat.config.yml', import.meta.url), 'utf8');
const lines = source.split(/\r?\n/);
function block(serverName) {
  const start = lines.findIndex(line => line === '  ' + serverName + ':');
  assert.notEqual(start, -1, serverName + ' must exist in MCP config');
  let end = start + 1;
  while (end < lines.length && !/^  [a-z][a-z0-9-]*:$/.test(lines[end])) end++;
  return lines.slice(start + 1, end).join('\n');
}

test('Gmail MCP uses only official HTTPS provider and limited scopes', () => {
  const gmail = block('gmail');
  assert.match(gmail, /^    url: https:\/\/gmailmcp\.googleapis\.com\/mcp\/v1$/m);
  assert.match(gmail, /^    requiresOAuth: true$/m);
  assert.match(gmail, /^    startup: false$/m);
  assert.match(gmail, /gmail\.readonly/);
  assert.doesNotMatch(gmail, /gmail\.compose/);
  assert.doesNotMatch(gmail, /https:\/\/mail\.google\.com\/|gmail\.modify|gmail\.send/);
  assert.match(gmail, /\$\{GOOGLE_WORKSPACE_MCP_CLIENT_ID\}/);
  assert.match(gmail, /\$\{GOOGLE_WORKSPACE_MCP_CLIENT_SECRET\}/);
  assert.match(gmail, /https:\/\/ai\.goreecloud\.com\/api\/mcp\/gmail\/oauth\/callback/);
});

test('the raw Google Drive MCP endpoint is absent from the server catalog', () => {
  assert.doesNotMatch(source, /^  google-drive:$/m);
  assert.doesNotMatch(source, /drivemcp\.googleapis\.com/);
});
