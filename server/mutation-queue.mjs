export function createMutationQueue() {
  let tail = Promise.resolve()

  return async function withMutation(work) {
    if (typeof work !== 'function') throw new TypeError('Mutation work must be a function')
    const previous = tail
    let release
    tail = new Promise((resolve) => { release = resolve })
    await previous
    try { return await work() }
    finally { release() }
  }
}
