package com.goreecloud.ai

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * Native Android SSE transport. The owner token and chat content stay in RAM;
 * only the configured API receives either. The server separately gates cloud
 * consent and paid provider budgets. Does not log events or retain credentials.
 */
internal class StreamControl {
    @Volatile private var connection: HttpURLConnection? = null
    @Volatile var cancelled: Boolean = false
        private set

    fun attach(value: HttpURLConnection) {
        connection = value
        if (cancelled) {
            value.disconnect()
            throw CancellationException("Stream cancelled")
        }
    }

    fun cancel() {
        cancelled = true
        connection?.disconnect()
    }

    fun detach() {
        connection = null
    }
}

/** A byte-bounded line reader; BufferedReader.readLine has no line-size cap. */
internal fun readBoundedLine(stream: InputStream, maximum: Int = 100_000): String? {
    val line = ByteArrayOutputStream()
    while (true) {
        val next = stream.read()
        if (next == -1) {
            if (line.size() == 0) return null
            break
        }
        if (next == 10) break
        if (line.size() >= maximum) throw IOException("SSE event exceeded size limit")
        line.write(next)
    }
    val data = line.toByteArray()
    val end = if (data.isNotEmpty() && data.last() == 13.toByte()) data.size - 1 else data.size
    return String(data, 0, end, Charsets.UTF_8)
}

/** Accepts server data frames, skips comments, and bounds cumulative traffic. */
internal class ChatSseFrames {
    private var total = 0
    private var count = 0

    fun next(line: String): String? {
        if (line.isEmpty() || line.startsWith(":")) return null
        if (!line.startsWith("data: ")) return null
        if (line.length > 100_000) throw IOException("SSE frame exceeded size limit")
        count++
        total += line.length
        if (count > 10_000 || total > 400_000) throw IOException("SSE response exceeded limit")
        return line.substring(6)
    }
}

internal object ChatStream {
    suspend fun run(
        endpoint: String,
        ownerToken: String,
        request: JSONObject,
        control: StreamControl,
        onEvent: suspend (JSONObject) -> Unit,
    ) = withContext(Dispatchers.IO) {
        require(ownerToken.isNotBlank()) { "Enter an owner token" }
        val base = AiApi.validatedBase(endpoint)
        val body = request.toString().toByteArray(Charsets.UTF_8)
        require(body.size in 1..256_000) { "Chat request too large" }

        val connection = URL(base + "/api/v1/chat/stream").openConnection() as HttpURLConnection
        connection.instanceFollowRedirects = false
        connection.connectTimeout = 10_000
        connection.readTimeout = 30_000
        connection.requestMethod = "POST"
        connection.doOutput = true
        connection.setRequestProperty("Authorization", "Bearer " + ownerToken)
        connection.setRequestProperty("Accept", "text/event-stream")
        connection.setRequestProperty("Content-Type", "application/json")
        connection.setFixedLengthStreamingMode(body.size)
        control.attach(connection)
        try {
            currentCoroutineContext().ensureActive()
            connection.outputStream.use { it.write(body) }
            val status = connection.responseCode
            if (status !in 200..299) throw IOException("Chat stream rejected (HTTP $status)")
            if (connection.contentType?.startsWith("text/event-stream") != true) {
                throw IOException("Chat endpoint returned an unexpected response")
            }
            val frames = ChatSseFrames()
            var responseCharacters = 0
            var finished = false
            BufferedInputStream(connection.inputStream).use { input ->
                while (true) {
                    currentCoroutineContext().ensureActive()
                    if (control.cancelled) throw CancellationException("Stream cancelled")
                    val line = readBoundedLine(input) ?: break
                    val data = frames.next(line) ?: continue
                    if (data == "[DONE]") break
                    val event = try { JSONObject(data) } catch (_: Exception) {
                        throw IOException("Invalid chat stream event")
                    }
                    when (event.optString("type")) {
                        "delta" -> {
                            val value = event.optString("content", "")
                            responseCharacters += value.length
                            if (responseCharacters > 120_000) {
                                throw IOException("Chat stream response exceeded limit")
                            }
                            withContext(Dispatchers.Main) { onEvent(event) }
                        }
                        "done" -> {
                            withContext(Dispatchers.Main) { onEvent(event) }
                            finished = true
                            break
                        }
                        "error" -> throw IOException("Inference provider reported an error")
                        else -> throw IOException("Unsupported chat stream event")
                    }
                }
            }
            if (!finished && !control.cancelled) throw IOException("Chat stream ended prematurely")
        } catch (exc: IOException) {
            if (control.cancelled) throw CancellationException("Stream cancelled")
            throw IOException("Chat streaming unavailable or response invalid", exc)
        } finally {
            control.detach()
            connection.disconnect()
        }
    }
}
