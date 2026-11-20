package com.goreecloud.ai

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import com.goreecloud.ai.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Small auditable native transport. API keys remain only on the server.
 * Never sends credentials to redirected/untrusted origins.
 */
internal object AiApi {
    suspend fun call(endpoint: String, ownerToken: String, path: String, body: JSONObject? = null): JSONObject =
        withContext(Dispatchers.IO) {
            require(ownerToken.isNotBlank()) { "Enter an owner token" }
            val base = endpoint.trim().trimEnd('/')
            val target = URL(base)
            val isEmulatorDevelopment = BuildConfig.DEBUG &&
                target.protocol == "http" && target.host == "10.0.2.2"
            require(target.protocol == "https" || isEmulatorDevelopment) {
                "Use HTTPS. Debug emulator can use http://10.0.2.2:8000"
            }
            require(target.userInfo == null && target.ref == null) { "Invalid server address" }
            require(path.startsWith("/api/")) { "Unsupported API route" }
            val connection = URL(base + path).openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 10_000
            connection.readTimeout = 90_000
            connection.setRequestProperty("Authorization", "Bearer " + ownerToken)
            connection.setRequestProperty("Accept", "application/json")
            connection.requestMethod = if (body != null) "POST" else "GET"
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
            }
            try {
                if (body != null) {
                    connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                }
                val status = connection.responseCode
                require(status !in 300..399) { "Redirect blocked" }
                val source = if (status in 200..299) connection.inputStream else connection.errorStream
                val data = (source ?: throw IllegalStateException("Missing API response")).use {
                    // Bound response payload to 16 MB to avoid unbounded memory for images.
                    it.readNBytes(16_000_001)
                }
                require(data.size <= 16_000_000) { "Response too large" }
                val parsed = JSONObject(data.toString(Charsets.UTF_8))
                if (status !in 200..299) {
                    throw IllegalStateException(parsed.optString("detail", "Request failed (HTTP " + status + ")"))
                }
                parsed
            } finally {
                connection.disconnect()
            }
        }

    fun decodeDataImage(dataUri: String): Bitmap? {
        if (!dataUri.startsWith("data:image/png;base64,") &&
            !dataUri.startsWith("data:image/jpeg;base64,") &&
            !dataUri.startsWith("data:image/webp;base64,")) return null
        val payload = dataUri.substringAfter(',')
        if (payload.length > 12_000_000) return null
        return try {
            val bytes = Base64.decode(payload, Base64.DEFAULT)
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        } catch (_: IllegalArgumentException) { null }
    }

    fun chatBody(history: List<Pair<String, String>>, provider: String, model: String, fallback: Boolean) =
        JSONObject().put("messages", JSONArray().apply {
            history.forEach { (role, content) -> put(JSONObject().put("role", role).put("content", content)) }
        }).put("provider", provider).put("model", model).put("allow_local_fallback", fallback)
}
