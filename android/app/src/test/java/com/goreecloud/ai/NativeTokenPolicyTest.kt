package com.goreecloud.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pure host-side safety tests for token-efficient request option validation. */
class NativeTokenPolicyTest {
    @Test fun boundedContextCounts() {
        assertEquals(4, NativeTokenPolicy.recentCount(4))
        assertEquals(16, NativeTokenPolicy.recentCount(16))
        assertEquals(8, NativeTokenPolicy.recentCount(0))
        assertEquals(8, NativeTokenPolicy.recentCount(-2))
    }

    @Test fun boundedOutputCaps() {
        assertEquals(256, NativeTokenPolicy.outputCap(256))
        assertEquals(2048, NativeTokenPolicy.outputCap(2048))
        assertEquals(2048, NativeTokenPolicy.outputCap(500000))
    }

    @Test fun providerCachingIsExplicitAndNeverLocal() {
        assertFalse(NativeTokenPolicy.providerResponseCache("ollama", true, true))
        assertFalse(NativeTokenPolicy.providerResponseCache("openrouter", false, true))
        assertFalse(NativeTokenPolicy.providerResponseCache("auto", true, false))
        assertTrue(NativeTokenPolicy.providerResponseCache("openrouter", true, true))
    }
}
