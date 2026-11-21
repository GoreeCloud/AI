package com.goreecloud.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.IOException

/** Pure host-side parser tests. Real Android/HTTPS device acceptance is separate. */
class ChatSseFramesTest {
    @Test fun parsesMultipleSseLinesAndPreservesUtf8() {
        val input = ByteArrayInputStream("data: hello\r\ndata: bye\n".toByteArray(Charsets.UTF_8))
        assertEquals("data: hello", readBoundedLine(input))
        assertEquals("data: bye", readBoundedLine(input))
        assertNull(readBoundedLine(input))
        assertEquals("data: кафе", readBoundedLine(
            ByteArrayInputStream("data: кафе".toByteArray(Charsets.UTF_8))))
    }

    @Test fun boundsLineWithoutAllocatingUnrestrictedInput() {
        val large = ByteArrayInputStream(("a".repeat(100_001) + "\n").toByteArray())
        assertThrows(IOException::class.java) { readBoundedLine(large) }
    }

    @Test fun recognizesOnlyDataFramesAndBoundsAggregate() {
        val parser = ChatSseFrames()
        assertNull(parser.next(""))
        assertNull(parser.next(": keepalive"))
        assertNull(parser.next("event: change"))
        assertEquals("{\"type\":\"delta\",\"content\":\"hi\"}",
            parser.next("data: {\"type\":\"delta\",\"content\":\"hi\"}"))
        assertEquals("[DONE]", parser.next("data: [DONE]"))
        assertThrows(IOException::class.java) { parser.next("data: " + "x".repeat(100_000)) }
    }

    @Test fun dropsAbusiveCumulativeSseTraffic() {
        val parser = ChatSseFrames()
        assertThrows(IOException::class.java) {
            repeat(10_100) { parser.next("data: x") }
        }
    }

    @Test fun cancellationIsReversibleOnlyByCreatingNewControl() {
        val first = StreamControl()
        assertFalse(first.cancelled)
        first.cancel()
        assertTrue(first.cancelled)
        val next = StreamControl()
        assertFalse(next.cancelled)
    }
}
