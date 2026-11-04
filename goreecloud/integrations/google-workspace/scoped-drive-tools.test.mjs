import test from 'node:test';
import assert from 'node:assert/strict';
import { createScopedDriveMcpTools } from './scoped-drive-tools.mjs';

function fixture() {
  const calls = [];
  const driveApi = {
    async listChildren(folder, page) {
      calls.push(['list', folder, page]);
      return { files: [{ id: 'n123', name: 'Notes' }] };
    },
    async getMetadata(id) {
      calls.push(['meta', id]);
      if (id === 'foreign') throw Error('Unauthorized folder');
      return { id, name: 'Notes' };
    },
    async readText(id) {
      calls.push(['read', id]);
      if (id === 'foreign') throw Error('Unauthorized folder');
      return 'Project notes';
    },
  };
  return { calls, bridge: createScopedDriveMcpTools({ driveApi }) };
}

test('only read-only scoped Drive operations are advertised', () => {
  const { bridge } = fixture();
  const tools = bridge.listTools();
  assert.deepEqual(tools.map(x => x.name).sort(), [
    'goreecloud_drive_get_metadata', 'goreecloud_drive_list_children', 'goreecloud_drive_read_text',
  ]);
  for (const tool of tools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.inputSchema.additionalProperties, false);
  }
});

test('each authorized call delegates only to its scoped API', async () => {
  const { bridge, calls } = fixture();
  assert.equal(JSON.parse((await bridge.callTool('goreecloud_drive_list_children')).content[0].text).files[0].name, 'Notes');
  assert.equal(JSON.parse((await bridge.callTool('goreecloud_drive_get_metadata', { fileId: 'n123' })).content[0].text).id, 'n123');
  assert.equal((await bridge.callTool('goreecloud_drive_read_text', { fileId: 'n123' })).content[0].text, 'Project notes');
  assert.deepEqual(calls, [['list', undefined, undefined], ['meta', 'n123'], ['read', 'n123']]);
});

test('unknown tools and unexpected arguments fail before any provider access', async () => {
  const { bridge, calls } = fixture();
  await assert.rejects(bridge.callTool('drive_search'), /Unrecognized Drive tool/);
  await assert.rejects(bridge.callTool('gmail_send'), /Unrecognized Drive tool/);
  await assert.rejects(bridge.callTool('goreecloud_drive_read_text', {}), /Invalid MCP tool arguments/);
  await assert.rejects(bridge.callTool('goreecloud_drive_read_text', { fileId: 'n123', url: 'https://example.com' }), /Invalid MCP tool arguments/);
  await assert.rejects(bridge.callTool('goreecloud_drive_get_metadata', Object.create({ fileId: 'n123' })), /Invalid MCP tool arguments/);
  assert.equal(calls.length, 0);
});

test('folder access denial propagates without falling back to global Drive', async () => {
  const { bridge, calls } = fixture();
  await assert.rejects(bridge.callTool('goreecloud_drive_read_text', { fileId: 'foreign' }), /Unauthorized folder/);
  assert.deepEqual(calls, [['read', 'foreign']]);
});

test('oversized text and absent API functions are rejected', async () => {
  assert.throws(() => createScopedDriveMcpTools({ driveApi: { request() {} } }), /folder-scoped Drive API/);
  const bridge = createScopedDriveMcpTools({ driveApi: {
    listChildren: async () => ({ files: [] }),
    getMetadata: async id => ({ id }),
    readText: async () => 'x'.repeat(32769),
  } });
  await assert.rejects(bridge.callTool('goreecloud_drive_read_text', { fileId: 'n123' }), /exceeds the allowed size/);
});
