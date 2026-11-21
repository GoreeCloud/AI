package com.goreecloud.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/** Pure host-side method-policy tests; no Android storage, real token or server. */
class ConversationTransportPolicyTest {
    private val saved = "/api/v1/conversations/3c8d8d41-5a44-4831-8cc0-7caeb05729ae"

    @Test fun existingCallsPreserveMethods() {
        assertEquals("GET", AiApi.selectedMethod("/api/v1/conversations", false, null))
        assertEquals("POST", AiApi.selectedMethod("/api/v1/conversations/import", true, null))
        assertEquals("PUT", AiApi.selectedMethod("/api/v1/documents/" +
            "3c8d8d41-5a44-4831-8cc0-7caeb05729ae", true, null))
        assertEquals("GET", AiApi.selectedMethod(saved + "/export?format=json", false, null))
    }

    @Test fun explicitDeleteIsStrictlyScopedAndBodyless() {
        assertEquals("DELETE", AiApi.selectedMethod(saved, false, "DELETE"))
        for (path in listOf(
            "/api/v1/documents/3c8d8d41-5a44-4831-8cc0-7caeb05729ae",
            "/api/v1/conversations/import",
            saved + "?token=secret",
            "/api/v1/conversations/../../secrets",
        )) {
            assertThrows(IllegalArgumentException::class.java) {
                AiApi.selectedMethod(path, false, "DELETE")
            }
        }
        assertThrows(IllegalArgumentException::class.java) {
            AiApi.selectedMethod(saved, true, "DELETE")
        }
        assertThrows(IllegalArgumentException::class.java) {
            AiApi.selectedMethod(saved, false, "PATCH")
        }
        assertThrows(IllegalArgumentException::class.java) {
            AiApi.selectedMethod(saved, false, "POST")
        }
    }
}
