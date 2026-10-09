import test from 'node:test'
import assert from 'node:assert/strict'
import { firstCreateReviewNotice, shouldOfferHistoryReview } from './firstCreateRecovery.ts'
test('history action only appears for uncertain new chat creation', () => {
  assert.equal(shouldOfferHistoryReview(firstCreateReviewNotice, null), true)
  assert.equal(shouldOfferHistoryReview(null, null), false)
  assert.equal(shouldOfferHistoryReview(firstCreateReviewNotice, '123e4567-e89b-42d3-a456-426614174000'), false)
})
