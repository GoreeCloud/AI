export const firstCreateReviewNotice = 'Your draft is preserved. Check conversation history before resending: the first prompt may already be saved.'

export function shouldOfferHistoryReview(notice: string | null, conversationId: string | null): boolean {
  return conversationId === null && notice === firstCreateReviewNotice
}
