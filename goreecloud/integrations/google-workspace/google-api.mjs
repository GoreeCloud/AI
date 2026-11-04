/**
 * Credential-injected Google REST clients. No server routes, OAuth secrets,
 * credentials, or global Drive search tools are published by this module.
 * Integration into an authenticated per-user gateway requires a separate review.
 */
const GMAIL = 'https://gmail.googleapis.com/gmail/v1/users/me';
const DRIVE = 'https://www.googleapis.com/drive/v3';
const ROOT_NAME = 'GoreeCloud';
const FOLDER_MIME = 'application/vnd.google-apps.folder';
const DOC_MIME = 'application/vnd.google-apps.document';
const SHORTCUT_MIME = 'application/vnd.google-apps.shortcut';
const MAX_TEXT_BYTES = 1024 * 1024;
const MAX_ANCESTRY = 96;

export class GoogleApiAccessError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'GoogleApiAccessError';
    this.status = status;
  }
}
const deny = (reason) => { throw new GoogleApiAccessError(reason, 403); };
const validId = (id) => typeof id === 'string' && /^[A-Za-z0-9_-]{3,160}$/.test(id);
function requireId(id) {
  if (!validId(id)) throw new GoogleApiAccessError('Invalid Google resource ID', 400);
  return id;
}
function bearer(value) {
  if (typeof value !== 'string' || !value || /\s/.test(value)) {
    throw new GoogleApiAccessError('A private OAuth access token is required', 401);
  }
  return value;
}
function client({ accessToken, fetchImpl = globalThis.fetch }) {
  const secret = bearer(accessToken);
  if (typeof fetchImpl !== 'function') throw new TypeError('fetch implementation required');
  return async function request(url, { method = 'GET', body, response = 'json' } = {}) {
    const endpoint = new URL(url);
    if (endpoint.protocol !== 'https:' ||
        !['gmail.googleapis.com','www.googleapis.com'].includes(endpoint.hostname)) {
      deny('Unapproved Google API destination');
    }
    let result;
    try {
      result = await fetchImpl(endpoint.toString(), {
        method,
        headers: {
          Authorization: 'Bearer ' + secret,
          Accept: response === 'text' ? 'text/plain' : 'application/json',
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
        redirect: 'error',
        signal: AbortSignal.timeout(15_000),
      });
    } catch {
      // Never include token, upstream URL or response bodies in errors.
      throw new GoogleApiAccessError('Google API unavailable', 502);
    }
    if (!result.ok) {
      throw new GoogleApiAccessError('Google API returned HTTP ' + result.status, result.status);
    }
    if (response === 'text') {
      if (Number(result.headers.get('content-length')) > MAX_TEXT_BYTES) deny('File too large');
      // Fail closed without loading an unbounded response into memory.
      if (!result.body?.getReader) deny('Streaming response required');
      const reader = result.body.getReader();
      const chunks = [];
      let bytes = 0;
      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          bytes += value.byteLength;
          if (bytes > MAX_TEXT_BYTES) deny('File too large');
          chunks.push(value);
        }
      } finally {
        reader.releaseLock();
      }
      return new TextDecoder('utf-8', { fatal: true }).decode(
        Buffer.concat(chunks.map((chunk) => Buffer.from(chunk)), bytes),
      );
    }
    try {
      return await result.json();
    } catch {
      throw new GoogleApiAccessError('Invalid Google API response', 502);
    }
  };
}

function assertEmail(result, expectedEmail) {
  if (result?.emailAddress?.toLowerCase() !== expectedEmail.toLowerCase()) {
    deny('Unexpected Google account');
  }
}

/**
 * Gmail intentionally supports reads and drafts, not sending or deleting mail.
 * The surrounding service must obtain per-user OAuth grants and provide
 * authenticated session ownership. Never expose accessToken in a model prompt.
 */
export function createGmailApi({ accessToken, expectedEmail = 'goreecloud@gmail.com', fetchImpl } = {}) {
  const request = client({ accessToken, fetchImpl });
  let verified = false;
  async function ensureIdentity() {
    if (verified) return;
    assertEmail(await request(GMAIL + '/profile'), expectedEmail);
    verified = true;
  }
  return {
    async listMessages(q, maxResults = 25) {
      await ensureIdentity();
      if (typeof q !== 'string' || q.length > 512 || !Number.isInteger(maxResults) ||
          maxResults < 1 || maxResults > 25) {
        throw new GoogleApiAccessError('Invalid email search', 400);
      }
      const params = new URLSearchParams({ q, maxResults: String(maxResults) });
      return request(GMAIL + '/messages?' + params);
    },
    async getMessage(messageId) {
      await ensureIdentity();
      return request(GMAIL + '/messages/' + requireId(messageId) + '?format=full');
    },
    async createDraft({ to, subject, body }) {
      await ensureIdentity();
      if (typeof to !== 'string' || !/^[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+$/.test(to) ||
          typeof subject !== 'string' || subject.length > 200 ||
          /[\r\n]/.test(subject) || typeof body !== 'string' || body.length > 100_000) {
        throw new GoogleApiAccessError('Invalid draft fields', 400);
      }
      const safeSubject = '=?UTF-8?B?' + Buffer.from(subject).toString('base64') + '?=';
      const raw = [
        'To: ' + to, 'Subject: ' + safeSubject,
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: base64', '',
        Buffer.from(body).toString('base64'),
      ].join('\r\n');
      return request(GMAIL + '/drafts', {
        method: 'POST',
        body: { message: { raw: Buffer.from(raw).toString('base64url') } },
      });
    },
  };
}

/**
 * Google Drive requests are verified against the designated root folder *before*
 * returning any file to a caller. Shortcuts and global Drive search are denied.
 * This is NOT a grant restriction: raw Google MCP tools must never be exposed
 * alongside this wrapper, as they could bypass its checks.
 */
export function createGoreeCloudDriveApi({
  accessToken,
  rootId,
  expectedEmail = 'goreecloud@gmail.com',
  fetchImpl,
} = {}) {
  requireId(rootId);
  const request = client({ accessToken, fetchImpl });
  let verified = false;
  async function meta(id) {
    const q = new URLSearchParams({
      fields: 'id,name,mimeType,parents,trashed,size',
      supportsAllDrives: 'false',
    });
    return request(DRIVE + '/files/' + requireId(id) + '?' + q);
  }
  async function ensureRoot() {
    if (verified) return;
    const about = await request(DRIVE + '/about?fields=user(emailAddress)');
    assertEmail(about?.user, expectedEmail);
    const root = await meta(rootId);
    if (root.id !== rootId || root.name !== ROOT_NAME ||
        root.mimeType !== FOLDER_MIME || root.trashed) {
      deny('Invalid or unavailable GoreeCloud folder');
    }
    verified = true;
  }
  // Only enumerate children of an *already verified* folder. Never query metadata
  // of an arbitrary model-provided ID: that would access files outside GoreeCloud/.
  async function verifiedChildren(parentId, pageToken) {
    if (pageToken !== undefined &&
        (typeof pageToken !== 'string' || !/^[A-Za-z0-9_.!~+\/=:-]{1,1024}$/.test(pageToken))) {
      throw new GoogleApiAccessError('Invalid pagination token', 400);
    }
    const q = new URLSearchParams({
      q: "'" + parentId + "' in parents and trashed = false",
      fields: 'nextPageToken,files(id,name,mimeType,parents,trashed,size)',
      pageSize: '100',
      orderBy: 'name',
      ...(pageToken ? { pageToken } : {}),
    });
    const result = await request(DRIVE + '/files?' + q);
    if (!Array.isArray(result.files) || result.files.length > 100 ||
        (result.nextPageToken != null &&
        (typeof result.nextPageToken !== 'string' ||
          !/^[A-Za-z0-9_.!~+\/=:-]{1,1024}$/.test(result.nextPageToken)))) {
      deny('Invalid Drive listing');
    }
    for (const file of result.files) {
      if (!validId(file?.id) || typeof file.name !== 'string' ||
          typeof file.mimeType !== 'string' || file.trashed ||
          file.mimeType === SHORTCUT_MIME || !Array.isArray(file.parents) ||
          !file.parents.includes(parentId)) {
        deny('Unverified Drive listing entry');
      }
    }
    return { files: result.files, nextPageToken: result.nextPageToken ?? null };
  }

  async function allow(id) {
    await ensureRoot();
    const root = await meta(rootId);
    if (root.id !== rootId || root.name !== ROOT_NAME ||
        root.mimeType !== FOLDER_MIME || root.trashed) {
      deny('Invalid or unavailable GoreeCloud folder');
    }
    if (id === rootId) return root;

    // An authorization proof begins at the only approved root, never at a
    // caller-supplied file. Fail closed on large or cyclic trees.
    const seen = new Set([rootId]);
    const folders = [{ id: rootId, depth: 0 }];
    let inspected = 0;
    let pages = 0;
    while (folders.length) {
      const current = folders.shift();
      let token;
      do {
        if (++pages > 48) deny('Drive listing limit exceeded');
        const listing = await verifiedChildren(current.id, token);
        for (const file of listing.files) {
          if (++inspected > 2400) deny('Drive ancestry limit exceeded');
          if (file.id === id) return file;
          if (file.mimeType === FOLDER_MIME && !seen.has(file.id)) {
            if (current.depth + 1 > MAX_ANCESTRY) deny('Drive ancestry limit exceeded');
            seen.add(file.id);
            folders.push({ id: file.id, depth: current.depth + 1 });
          }
        }
        token = listing.nextPageToken ?? undefined;
      } while (token);
    }
    deny('File is outside the allowed GoreeCloud tree');
  }
  return {
    async getMetadata(fileId) {
      return allow(requireId(fileId));
    },
    async listChildren(parentId = rootId, pageToken) {
      const parent = await allow(requireId(parentId));
      if (parent.mimeType !== FOLDER_MIME) deny('Parent must be a folder');
      return verifiedChildren(parentId, pageToken);
    },
    async readText(fileId) {
      const file = await allow(requireId(fileId));
      if (file.mimeType !== DOC_MIME && file.mimeType !== 'text/plain') {
        deny('Only plain text and Google Docs can be read');
      }
      const url = file.mimeType === DOC_MIME
        ? DRIVE + '/files/' + fileId + '/export?mimeType=text%2Fplain'
        : DRIVE + '/files/' + fileId + '?alt=media';
      return request(url, { response: 'text' });
    },
  };
}
