import test from 'node:test';
import assert from 'node:assert/strict';
import { createGmailApi, createGoreeCloudDriveApi, GoogleApiAccessError } from './google-api.mjs';

const rootId = 'GoreeCloudRoot001';
const folderId = 'ChildFolder002';
const fileId = 'NoteFile003';
const outsiderId = 'OutsideFile004';
const shortcutId = 'Shortcut005';
const collection = {
  [rootId]: { id: rootId, name: 'GoreeCloud', mimeType: 'application/vnd.google-apps.folder', parents: ['MyDriveRoot'], trashed: false },
  [folderId]: { id: folderId, name: 'Docs', mimeType: 'application/vnd.google-apps.folder', parents: [rootId], trashed: false },
  [fileId]: { id: fileId, name: 'Plan.txt', mimeType: 'text/plain', parents: [folderId], trashed: false },
  [outsiderId]: { id: outsiderId, name: 'Private.txt', mimeType: 'text/plain', parents: ['NotAuthorized'], trashed: false },
  NotAuthorized: { id: 'NotAuthorized', name: 'Other', mimeType: 'application/vnd.google-apps.folder', parents: ['MyDriveRoot'], trashed: false },
  MyDriveRoot: { id: 'MyDriveRoot', name: 'My Drive', mimeType: 'application/vnd.google-apps.folder', parents: [], trashed: false },
  [shortcutId]: { id: shortcutId, name: 'Outside shortcut', mimeType: 'application/vnd.google-apps.shortcut', parents: [rootId], trashed: false },
};
const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { 'content-type': 'application/json' } });
function fixture({ email = 'goreecloud@gmail.com', rootName = 'GoreeCloud', maliciousListing = false } = {}) {
  const calls = [];
  const fetchImpl = async (raw, init) => {
    const url = new URL(raw);
    calls.push({ url, init });
    assert.equal(init.redirect, 'error');
    assert.equal(init.headers.Authorization, 'Bearer test-access-token');
    if (url.pathname === '/gmail/v1/users/me/profile') return json({ emailAddress: email });
    if (url.pathname === '/gmail/v1/users/me/messages') return json({ messages: [{ id: 'msg123' }] });
    if (url.pathname === '/gmail/v1/users/me/messages/msg123') return json({ id: 'msg123', snippet: 'Hello' });
    if (url.pathname === '/gmail/v1/users/me/drafts') return json({ id: 'draft123' });
    if (url.pathname === '/drive/v3/about') return json({ user: { emailAddress: email } });
    if (url.pathname === '/drive/v3/files') {
      const query = url.searchParams.get('q');
      if (query?.includes("'" + folderId + "'")) return json({ files: [{ ...collection[fileId] }] });
      return json({ files: [{ ...collection[folderId] }, { ...collection[shortcutId] }].slice(0, maliciousListing ? 2 : 1) });
    }
    if (url.pathname === '/drive/v3/files/' + fileId && url.searchParams.get('alt') === 'media') {
      return new Response('Project plan', { status: 200, headers: { 'content-type': 'text/plain', 'content-length': '12' } });
    }
    if (url.pathname.startsWith('/drive/v3/files/')) {
      const id = url.pathname.slice('/drive/v3/files/'.length);
      if (!collection[id]) return json({ error: 'unknown' }, 404);
      return json({ ...collection[id], ...(id === rootId ? { name: rootName } : {}) });
    }
    throw new Error('Unexpected provider path: ' + url.pathname);
  };
  return { fetchImpl, calls };
}

test('Gmail reads only after expected account identity is proven', async () => {
  const { fetchImpl, calls } = fixture();
  const gmail = createGmailApi({ accessToken: 'test-access-token', fetchImpl });
  assert.deepEqual(await gmail.listMessages('subject:invoice'), { messages: [{ id: 'msg123' }] });
  assert.deepEqual(await gmail.getMessage('msg123'), { id: 'msg123', snippet: 'Hello' });
  assert.equal(calls.filter(c => c.url.pathname.endsWith('/profile')).length, 1);
});

test('Gmail never creates drafts for a mismatched account', async () => {
  const { fetchImpl, calls } = fixture({ email: 'other@gmail.com' });
  const gmail = createGmailApi({ accessToken: 'test-access-token', fetchImpl });
  await assert.rejects(gmail.createDraft({ to: 'example@example.com', subject: 'Hello', body: 'Hi' }), /Unexpected Google account/);
  assert.equal(calls.some(c => c.url.pathname.endsWith('/drafts')), false);
});

test('Gmail creates MIME-safe drafts without sending them', async () => {
  const { fetchImpl, calls } = fixture();
  const gmail = createGmailApi({ accessToken: 'test-access-token', fetchImpl });
  await assert.rejects(gmail.createDraft({ to: 'a@example.com\r\nBcc:evil@example.com', subject: 'Hello', body: 'Hi' }), /Invalid draft fields/);
  const draft = await gmail.createDraft({ to: 'user@example.com', subject: 'Olá', body: 'Hello!\nThis is a draft.' });
  assert.equal(draft.id, 'draft123');
  const write = calls.find(c => c.url.pathname.endsWith('/drafts'));
  assert.equal(write.init.method, 'POST');
  const raw = Buffer.from(JSON.parse(write.init.body).message.raw, 'base64url').toString('utf8');
  assert.match(raw, /To: user@example.com/);
  assert.match(raw, /Subject: =\?UTF-8\?B\?/);
  assert.equal(calls.some(c => c.url.pathname.endsWith('/send')), false);
});

test('Gmail rejects oversized search requests and malformed message IDs', async () => {
  const { fetchImpl } = fixture();
  const gmail = createGmailApi({ accessToken: 'test-access-token', fetchImpl });
  await assert.rejects(gmail.listMessages('x', 100), /Invalid email search/);
  await assert.rejects(gmail.getMessage('../private'), /Invalid Google resource ID/);
});

test('Drive reads descendants with a verified root and identity', async () => {
  const { fetchImpl, calls } = fixture();
  const drive = createGoreeCloudDriveApi({ accessToken: 'test-access-token', rootId, fetchImpl });
  assert.equal((await drive.getMetadata(fileId)).id, fileId);
  const { files } = await drive.listChildren(rootId);
  assert.deepEqual(files.map(file => file.name), ['Docs']);
  assert.equal(await drive.readText(fileId), 'Project plan');
  assert.equal(calls.some(c => c.url.pathname === '/drive/v3/files' && c.url.searchParams.get('q')?.includes("'" + rootId + "'")), true);
  assert.equal(calls.some(c => c.url.searchParams.has('q') && c.url.searchParams.get('q').includes('name contains')), false);
});

test('Drive denies files outside GoreeCloud even when user OAuth has broad access', async () => {
  const { fetchImpl, calls } = fixture();
  const drive = createGoreeCloudDriveApi({ accessToken: 'test-access-token', rootId, fetchImpl });
  await assert.rejects(drive.getMetadata(outsiderId), /outside the allowed GoreeCloud tree/);
  assert.equal(calls.some(c => c.url.pathname.includes(outsiderId)), false,
    'out-of-folder metadata must never be queried, even to verify ancestry');
  assert.equal(calls.some(c => c.url.searchParams.get('alt') === 'media'), false);
});

test('Drive refuses foreign user, forged root, shortcuts and injected listing items', async () => {
  for (const opts of [{ email: 'other@gmail.com' }, { rootName: 'NotGoreeCloud' }]) {
    const { fetchImpl } = fixture(opts);
    const drive = createGoreeCloudDriveApi({ accessToken: 'test-access-token', rootId, fetchImpl });
    await assert.rejects(drive.listChildren(rootId), /Unexpected Google account|Invalid or unavailable GoreeCloud folder/);
  }
  const { fetchImpl } = fixture({ maliciousListing: true });
  const drive = createGoreeCloudDriveApi({ accessToken: 'test-access-token', rootId, fetchImpl });
  await assert.rejects(drive.getMetadata(shortcutId), /Unverified Drive listing entry/);
  await assert.rejects(drive.listChildren(rootId), /Unverified Drive listing entry/);
});

test('Drive rejects unsafe query IDs and requires the configured root ID', async () => {
  assert.throws(() => createGoreeCloudDriveApi({ accessToken: 'test-access-token' }), /Invalid Google resource ID/);
  assert.throws(() => createGmailApi({ accessToken: '' }), /private OAuth access token/);
  const { fetchImpl } = fixture();
  const drive = createGoreeCloudDriveApi({ accessToken: 'test-access-token', rootId, fetchImpl });
  await assert.rejects(drive.listChildren('../sensitive'), /Invalid Google resource ID/);
});

test('Drive text responses over 1 MiB fail closed', async () => {
  const original = fixture();
  const fetchImpl = async (url, init) => {
    if (new URL(url).searchParams.get('alt') === 'media') {
      return new Response('a'.repeat(1024 * 1024 + 1), { status: 200, headers: { 'content-type': 'text/plain' } });
    }
    return original.fetchImpl(url, init);
  };
  const drive = createGoreeCloudDriveApi({ accessToken: 'test-access-token', rootId, fetchImpl });
  await assert.rejects(drive.readText(fileId), /File too large/);
});

test('Provider HTTP errors are sanitized rather than leaking response content', async () => {
  const gmail = createGmailApi({
    accessToken: 'test-access-token',
    fetchImpl: async () => json({ access_token: 'secret' }, 403),
  });
  await assert.rejects(gmail.listMessages('hello'), error => {
    assert.ok(error instanceof GoogleApiAccessError);
    assert.equal(error.message, 'Google API returned HTTP 403');
    assert.equal(error.message.includes('secret'), false);
    return true;
  });
});
