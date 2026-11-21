package com.goreecloud.ai

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import com.goreecloud.ai.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.net.HttpURLConnection
import java.net.URL

/**
 * Small auditable native transport. API keys remain only on the server.
 * Never sends credentials to redirected/untrusted origins.
 */
internal object AiApi {
    internal fun validatedBase(endpoint: String): String {
        val base = endpoint.trim().trimEnd('/')
        val target = URL(base)
        val isEmulatorDevelopment = BuildConfig.DEBUG &&
            target.protocol == "http" && target.host == "10.0.2.2"
        require(target.protocol == "https" || isEmulatorDevelopment) {
            "Use HTTPS. Debug emulator can use http://10.0.2.2:8000"
        }
        require(target.userInfo == null && target.ref == null &&
            target.query == null) { "Invalid server address" }
        return base
    }

    internal fun selectedMethod(path: String, hasBody: Boolean, explicitMethod: String?): String {
        val verb = explicitMethod ?: if (!hasBody) "GET" else if (
            path.startsWith("/api/v1/documents/")) "PUT" else "POST"
        require(verb in setOf("GET", "POST", "PUT", "DELETE")) { "Unsupported HTTP method" }
        require((verb == "GET" || verb == "DELETE") == !hasBody) {
            "Invalid request body for method"
        }
        if (verb == "DELETE") require(
            Regex("^/api/v1/conversations/[0-9a-fA-F-]{36}$").matches(path)
        ) { "Deletion is restricted to a saved conversation UUID" }
        return verb
    }

    suspend fun call(endpoint: String, ownerToken: String, path: String,
                     body: JSONObject? = null, method: String? = null): JSONObject =
        withContext(Dispatchers.IO) {
            require(ownerToken.isNotBlank()) { "Enter an owner token" }
            val base = validatedBase(endpoint)
            require(path.startsWith("/api/")) { "Unsupported API route" }
            val connection = URL(base + path).openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 10_000
            connection.readTimeout = 90_000
            connection.setRequestProperty("Authorization", "Bearer " + ownerToken)
            connection.setRequestProperty("Accept", "application/json")
            connection.requestMethod = selectedMethod(path, body != null, method)
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
                if (status == 204) return@withContext JSONObject()
                val source = if (status in 200..299) connection.inputStream else connection.errorStream
                val data = (source ?: throw IllegalStateException("Missing API response")).use {
                    // Bound response payload to 16 MB to avoid unbounded memory for images.
                    it.readNBytes(16_000_001)
                }
                require(data.size <= 16_000_000) { "Response too large" }
                val parsed = when (val value = JSONTokener(data.toString(Charsets.UTF_8)).nextValue()) {
                    is JSONObject -> value
                    is JSONArray -> JSONObject().put("items", value)
                    else -> throw IllegalStateException("Unsupported API response")
                }
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

    fun chatBody(history: List<Pair<String, String>>, provider: String, model: String,
                 fallback: Boolean, cloudConsent: Boolean,
                 recentContextMessages: Int = 0, maxOutputTokens: Int = 2048,
                 reuseLocalResponse: Boolean = false,
                 providerResponseCache: Boolean = false) =
        JSONObject().put("messages", JSONArray().apply {
            history.forEach { (role, content) -> put(JSONObject().put("role", role).put("content", content)) }
        }).put("provider", provider).put("model", model).put("allow_local_fallback", fallback)
          .put("allow_cloud_processing", cloudConsent)
          .put("context_mode", if (recentContextMessages > 0) "last_n" else "full")
          .put("context_messages", NativeTokenPolicy.recentCount(recentContextMessages))
          .put("max_output_tokens", NativeTokenPolicy.outputCap(maxOutputTokens))
          .put("local_response_cache", reuseLocalResponse)
          .put("provider_response_cache",
               NativeTokenPolicy.providerResponseCache(provider, cloudConsent,
                   providerResponseCache))
}
