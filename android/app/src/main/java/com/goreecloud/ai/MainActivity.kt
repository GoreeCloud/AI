package com.goreecloud.ai

import android.os.Bundle
import android.animation.ValueAnimator
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder
import java.io.ByteArrayOutputStream
import com.goreecloud.ui.material3.GoreeCloudExpressiveTheme
import com.goreecloud.ui.material3.GoreeAccent
import com.goreecloud.ui.material3.GoreeDestination
import com.goreecloud.ui.material3.GoreeFloatingNavigationBar
import com.goreecloud.ui.multiplatform.GoreeCloudAction

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            GoreeCloudExpressiveTheme(
                accent = GoreeAccent.Iris,
                dynamicWallpaperColors = false,
                reduceMotion = !ValueAnimator.areAnimatorsEnabled()
            ) { AiWorkspace() }
        }
    }
}

@Composable
private fun AiWorkspace() {
    val tabs = listOf("Chat", "Images", "Docs", "Agents", "MCP")
    var current by remember { mutableStateOf(0) }
    var endpoint by remember { mutableStateOf(if (BuildConfig.DEBUG) "http://10.0.2.2:8000" else "https://") }
    var token by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Developer preview · Keep private data out of cloud prompts") }
    var busy by remember { mutableStateOf(false) }
    var model by remember { mutableStateOf("openrouter/auto") }
    var provider by remember { mutableStateOf("auto") }
    var fallback by remember { mutableStateOf(false) }
    var cloudConsent by remember { mutableStateOf(false) }
    var streamResponses by remember { mutableStateOf(true) }
    var recentContextMessages by remember { mutableStateOf(0) }
    var maxOutputTokens by remember { mutableStateOf(2048) }
    var reuseLocalResponse by remember { mutableStateOf(false) }
    var providerResponseCache by remember { mutableStateOf(false) }
    var streamingControl by remember { mutableStateOf<StreamControl?>(null) }
    var streamingJob by remember { mutableStateOf<Job?>(null) }
    val chat = remember { mutableStateListOf<Pair<String, String>>() }
    var showChatLibrary by remember { mutableStateOf(false) }
    var savedChats by remember { mutableStateOf(JSONArray()) }
    var chatSearch by remember { mutableStateOf("") }
    var pendingDeleteId by remember { mutableStateOf("") }
    var pendingExportJson by remember { mutableStateOf<String?>(null) }
    var prompt by remember { mutableStateOf("") }
    var imagePrompt by remember { mutableStateOf("") }
    var imageModel by remember { mutableStateOf("bytedance-seed/seedream-4.5") }
    var imageCatalog by remember { mutableStateOf(JSONArray()) }
    var approvePaid by remember { mutableStateOf(false) }
    var imageData by remember { mutableStateOf("") }
    var docTitle by remember { mutableStateOf("") }
    var docBody by remember { mutableStateOf("") }
    var docId by remember { mutableStateOf("") }
    var docIndex by remember { mutableStateOf(JSONArray()) }
    var goal by remember { mutableStateOf("") }
    var plan by remember { mutableStateOf("") }
    var mcpNames by remember { mutableStateOf(JSONArray()) }
    var toolName by remember { mutableStateOf("") }
    var toolArgs by remember { mutableStateOf("{}") }
    var approveTool by remember { mutableStateOf(false) }
    var toolResult by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    val exportPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        val content = pendingExportJson
        pendingExportJson = null
        if (uri != null && content != null) scope.launch {
            try {
                withContext(Dispatchers.IO) {
                    val output = context.contentResolver.openOutputStream(uri, "w")
                        ?: throw IllegalStateException("Selected destination cannot be written")
                    output.use { it.write(content.toByteArray(Charsets.UTF_8)) }
                }
                status = "Export saved to your chosen destination. Protect the plaintext file."
            } catch (e: Exception) {
                status = "Export failed: " + (e.message ?: "Cannot write selected file")
            }
        }
    }
    val importPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null && !busy) {
            busy = true
            scope.launch {
                try {
                    val content = withContext(Dispatchers.IO) {
                        val source = context.contentResolver.openInputStream(uri)
                            ?: throw IllegalStateException("Cannot open selected JSON")
                        source.use { input ->
                            val output = ByteArrayOutputStream()
                            val buffer = ByteArray(8192)
                            while (true) {
                                val count = input.read(buffer)
                                if (count < 0) break
                                if (output.size() + count > 1_250_000)
                                    throw IllegalArgumentException("Import exceeds 1.25 MB")
                                output.write(buffer, 0, count)
                            }
                            output.toByteArray().toString(Charsets.UTF_8)
                        }
                    }
                    val imported = JSONObject(content)
                    require(imported.optString("schema") == "goreecloud.ai.conversation.v1") {
                        "Not a supported GoreeCloud AI conversation export"
                    }
                    AiApi.call(endpoint, token, "/api/v1/conversations/import", imported)
                    val index = AiApi.call(endpoint, token, "/api/v1/conversations")
                    savedChats = index.optJSONArray("items") ?: JSONArray()
                    chatSearch = ""
                    status = "New local conversation snapshot imported; no provider request."
                } catch (e: Exception) {
                    status = "Import failed: " + (e.message ?: "Invalid file or API response")
                } finally { busy = false }
            }
        }
    }

    fun invoke(path: String, body: JSONObject? = null, completed: (JSONObject) -> Unit) {
        if (busy) return
        busy = true
        status = "Processing request…"
        scope.launch {
            try {
                val result = AiApi.call(endpoint, token, path, body)
                completed(result)
            } catch (e: Exception) {
                status = e.message ?: "Request failed"
            } finally { busy = false }
        }
    }

    if (pendingDeleteId.isNotEmpty()) {
        AlertDialog(
            onDismissRequest = { pendingDeleteId = "" },
            title = { Text("Delete saved conversation?") },
            text = { Text("This removes the saved snapshot from the local database. " +
                "Exports, backups and SQLite pages may still retain copies.") },
            confirmButton = {
                Button(onClick = {
                    val id = pendingDeleteId
                    pendingDeleteId = ""
                    if (busy) return@Button
                    busy = true
                    scope.launch {
                        try {
                            AiApi.call(endpoint, token, "/api/v1/conversations/" + id,
                                method = "DELETE")
                            val index = AiApi.call(endpoint, token, "/api/v1/conversations")
                            savedChats = index.optJSONArray("items") ?: JSONArray()
                            chatSearch = ""
                            status = "Local saved conversation deleted (backups unchanged)."
                        } catch (e: Exception) {
                            status = e.message ?: "Could not delete saved conversation"
                        } finally { busy = false }
                    }
                }) { Text("Delete") }
            },
            dismissButton = {
                GoreeCloudAction(label = "Cancel", onClick = { pendingDeleteId = "" })
            }
        )
    }

    Scaffold(
        bottomBar = {
            GoreeFloatingNavigationBar(
                destinations = tabs.mapIndexed { i, name ->
                    GoreeDestination(
                        id = name,
                        label = name,
                        icon = { Text(listOf("✦", "◈", "▤", "✳", "⌘")[i]) }
                    )
                },
                selectedId = tabs[current],
                onDestinationSelected = { selected ->
                    val index = tabs.indexOf(selected)
                    if (index >= 0) current = index
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Text("GoreeCloud AI", style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 18.dp, top = 18.dp))
            Text("OpenRouter first · Ollama optional", color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 18.dp))
            OutlinedTextField(value = endpoint, onValueChange = { endpoint = it },
                label = { Text("AI API URL (HTTPS)") }, singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp))
            OutlinedTextField(value = token, onValueChange = { token = it },
                label = { Text("Owner token · memory only") }, singleLine = true,
                visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp))
            Text(status, color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 10.dp))
            HorizontalDivider()

            when (current) {
                0 -> if (showChatLibrary) Column(
                    modifier = Modifier.fillMaxSize().padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("Saved conversations", style = MaterialTheme.typography.titleLarge)
                    Text("Private local snapshots · cloud consent is never restored from history",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(enabled = !busy, onClick = { showChatLibrary = false }) {
                            Text("Back to chat")
                        }
                        Button(enabled = !busy, onClick = {
                            invoke("/api/v1/conversations") {
                                savedChats = it.optJSONArray("items") ?: JSONArray()
                                status = "Local saved conversations loaded"
                            }
                        }) { Text("Refresh") }
                    }
                    OutlinedTextField(value = chatSearch, onValueChange = {
                        chatSearch = it.take(200)
                    }, label = { Text("Search saved titles and messages") },
                        singleLine = true, modifier = Modifier.fillMaxWidth())
                    Button(enabled = !busy && chatSearch.trim().length in 2..200, onClick = {
                        val encoded = URLEncoder.encode(chatSearch.trim(), "UTF-8")
                        invoke("/api/v1/search/conversations?q=" + encoded) {
                            savedChats = it.optJSONArray("results") ?: JSONArray()
                            status = savedChats.length().toString() + " matching local conversations"
                        }
                    }) { Text("Search locally") }
                    Text("Import/export uses the Android document picker. The chosen " +
                        "destination may be an external or cloud-synced location.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Button(enabled = !busy, onClick = {
                        importPicker.launch(arrayOf("application/json"))
                    }, modifier = Modifier.fillMaxWidth()) {
                        Text("Import conversation JSON…")
                    }
                    val historyEntries = (0 until savedChats.length()).mapNotNull { savedChats.optJSONObject(it) }
                    LazyColumn(modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(historyEntries) { entry ->
                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Button(enabled = !busy, onClick = {
                                val id = entry.optString("id")
                                if (!id.matches(Regex("[0-9a-fA-F-]{36}"))) {
                                    status = "Invalid saved conversation ID"
                                } else {
                                    invoke("/api/v1/conversations/" + id) { reply ->
                                        val loaded = reply.optJSONArray("messages") ?: JSONArray()
                                        chat.clear()
                                        for (i in 0 until loaded.length()) {
                                            val message = loaded.optJSONObject(i) ?: continue
                                            val role = message.optString("role")
                                            val text = message.optString("content")
                                            if ((role == "user" || role == "assistant") && text.isNotBlank()) {
                                                chat.add(role to text)
                                            }
                                        }
                                        cloudConsent = false
                                        reuseLocalResponse = false
                                        providerResponseCache = false
                                        showChatLibrary = false
                                        status = "Loaded local snapshot · cloud approval reset"
                                    }
                                }
                            }, modifier = Modifier.fillMaxWidth()) {
                                Text(entry.optString("title", "Saved conversation").take(150))
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(enabled = !busy, onClick = {
                                    val id = entry.optString("id")
                                    if (!Regex("[0-9a-fA-F-]{36}").matches(id)) {
                                        status = "Invalid saved conversation ID"
                                    } else {
                                        invoke("/api/v1/conversations/" + id + "/export?format=json") {
                                            val payload = it.toString(2)
                                            if (payload.toByteArray(Charsets.UTF_8).size > 1_250_000) {
                                                status = "JSON export exceeds 1.25 MB"
                                            } else {
                                                pendingExportJson = payload
                                                exportPicker.launch("goreecloud-conversation-" + id + ".json")
                                            }
                                        }
                                    }
                                }) { Text("Export JSON…") }
                                Button(enabled = !busy, onClick = {
                                    val id = entry.optString("id")
                                    if (Regex("[0-9a-fA-F-]{36}").matches(id)) pendingDeleteId = id
                                }) { Text("Delete…") }
                            }
                            }
                        }
                    }
                } else Column(modifier = Modifier.fillMaxSize().padding(18.dp)) {
                    LazyColumn(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        items(chat.toList()) { (role, text) ->
                            Surface(color = if (role == "user") MaterialTheme.colorScheme.surfaceVariant
                                else MaterialTheme.colorScheme.surface,
                                shape = MaterialTheme.shapes.large) {
                                Column(modifier = Modifier.fillMaxWidth().padding(13.dp)) {
                                    Text(if (role == "user") "You" else "GoreeCloud AI",
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.primary)
                                    Text(text, style = MaterialTheme.typography.bodyLarge)
                                }
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = {
                            provider = if (provider == "auto") "ollama" else "auto"
                            cloudConsent = false
                            reuseLocalResponse = false
                            providerResponseCache = false
                        }) {
                            Text(if (provider == "auto") "Auto · OpenRouter" else "Local · Ollama")
                        }
                        Button(enabled = !busy, onClick = {
                            chat.clear()
                            cloudConsent = false
                            reuseLocalResponse = false
                            providerResponseCache = false
                        }) { Text("New chat") }
                    }
                    Button(enabled = !busy, onClick = {
                        showChatLibrary = true
                        invoke("/api/v1/conversations") {
                            savedChats = it.optJSONArray("items") ?: JSONArray()
                            status = "Local saved conversations loaded"
                        }
                    }, modifier = Modifier.fillMaxWidth()) { Text("Saved conversations") }
                    Button(enabled = !busy && chat.isNotEmpty() && chat.size <= 64 &&
                        chat.sumOf { it.second.length } <= 250000, onClick = {
                        val first = chat.firstOrNull { it.first == "user" }?.second
                            ?: "Saved conversation"
                        val messages = JSONArray()
                        chat.forEach { (role, content) ->
                            if (content.isNotBlank())
                                messages.put(JSONObject().put("role", role).put("content", content))
                        }
                        invoke("/api/v1/conversations", JSONObject()
                            .put("title", first.take(100).ifBlank { "Saved conversation" })
                            .put("messages", messages)) {
                            status = "Saved local snapshot · no cloud request"
                        }
                    }) { Text("Save conversation locally") }
                    OutlinedTextField(value = model, onValueChange = { model = it },
                        label = { Text("Model ID") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = cloudConsent, onCheckedChange = { cloudConsent = it })
                        Text("Allow cloud processing via OpenRouter", style = MaterialTheme.typography.bodySmall)
                    }
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = fallback, onCheckedChange = { fallback = it })
                        Text("Allow local fallback", style = MaterialTheme.typography.bodySmall)
                    }
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = streamResponses, onCheckedChange = { streamResponses = it })
                        Text("Stream answer · cancel anytime", style = MaterialTheme.typography.bodySmall)
                    }
                    Text("Token efficiency", style = MaterialTheme.typography.titleSmall)
                    Button(enabled = !busy, onClick = {
                        recentContextMessages = when (recentContextMessages) {
                            0 -> 4; 4 -> 8; 8 -> 16; else -> 0
                        }
                    }) {
                        Text(if (recentContextMessages == 0) "History: full"
                             else "History: last $recentContextMessages messages")
                    }
                    Button(enabled = !busy, onClick = {
                        maxOutputTokens = when (maxOutputTokens) {
                            2048 -> 1024; 1024 -> 512; 512 -> 256; else -> 2048
                        }
                    }) { Text("Maximum answer: $maxOutputTokens tokens") }
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = reuseLocalResponse,
                            enabled = !busy,
                            onCheckedChange = { reuseLocalResponse = it })
                        Text("Reuse completed streamed/ordinary answers in server RAM (5 min)",
                            style = MaterialTheme.typography.bodySmall)
                    }
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = providerResponseCache,
                            enabled = !busy && provider != "ollama",
                            onCheckedChange = { providerResponseCache = it })
                        Text("Allow OpenRouter to cache identical requests (5 min)",
                            style = MaterialTheme.typography.bodySmall)
                    }
                    Text("Caches default off. Plaintext answers may stay in API RAM; " +
                        "OpenRouter caching may retain prompts. Cloud consent is separate.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (streamResponses && fallback) {
                        Text("Local fallback uses a complete non-streaming response.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    OutlinedTextField(value = prompt, onValueChange = { prompt = it },
                        label = { Text("Message") }, minLines = 2, maxLines = 5,
                        modifier = Modifier.fillMaxWidth())
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(enabled = !busy && prompt.isNotBlank(), onClick = {
                            val text = prompt.trim()
                            prompt = ""
                            chat.add("user" to text)
                            val history = chat.toList()
                            if (streamResponses && !fallback) {
                                val index = chat.size
                                chat.add("assistant" to "")
                                val control = StreamControl()
                                streamingControl = control
                                busy = true
                                status = "Receiving streamed answer…"
                                streamingJob = scope.launch {
                                    try {
                                        ChatStream.run(endpoint, token,
                                            AiApi.chatBody(history, provider, model, false, cloudConsent,
                                                recentContextMessages, maxOutputTokens,
                                                reuseLocalResponse, providerResponseCache),
                                            control) { event ->
                                            when (event.optString("type")) {
                                                "delta" -> if (index < chat.size &&
                                                    chat[index].first == "assistant") {
                                                    chat[index] = "assistant" to (
                                                        chat[index].second + event.optString("content"))
                                                }
                                                "done" -> status = "Answered via " +
                                                    event.optString("provider", "selected provider")
                                            }
                                        }
                                    } catch (_: CancellationException) {
                                        status = "Stream cancelled"
                                    } catch (e: Exception) {
                                        status = e.message ?: "Stream unavailable"
                                        if (index < chat.size && chat[index].second.isEmpty()) {
                                            chat.removeAt(index)
                                        }
                                    } finally {
                                        busy = false
                                        streamingControl = null
                                        streamingJob = null
                                    }
                                }
                            } else {
                                invoke("/api/v1/chat",
                                    AiApi.chatBody(history, provider, model, fallback, cloudConsent,
                                        recentContextMessages, maxOutputTokens,
                                        reuseLocalResponse, providerResponseCache)) {
                                    chat.add("assistant" to it.optString("content"))
                                    status = "Answered via " + it.optString("provider")
                                }
                            }
                        }, modifier = Modifier.weight(1f)) {
                            Text(if (streamResponses && !fallback) "Stream answer" else "Send")
                        }
                        if (busy && streamingControl != null) {
                            Button(onClick = {
                                streamingControl?.cancel()
                                streamingJob?.cancel()
                                status = "Stream cancelled"
                            }) { Text("Cancel stream") }
                        }
                    }
                }
                1 -> Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Image studio", style = MaterialTheme.typography.titleLarge)
                    Button(enabled = !busy, onClick = {
                        invoke("/api/v1/images/models") {
                            imageCatalog = it.optJSONArray("models") ?: JSONArray()
                            status = "Image models listed. No paid generation requested."
                        }
                    }) { Text("Browse available image models") }
                    if (imageCatalog.length() > 0) {
                        Text("Select a discovered image model:", style = MaterialTheme.typography.labelLarge)
                        for (i in 0 until minOf(12, imageCatalog.length())) {
                            val candidate = imageCatalog.optJSONObject(i) ?: continue
                            val id = candidate.optString("id")
                            if (id.isNotBlank()) {
                                Button(enabled = !busy, onClick = {
                                    imageModel = id
                                    approvePaid = false
                                    status = "Image model selected; paid generation still needs approval."
                                }, modifier = Modifier.fillMaxWidth()) {
                                    Text(candidate.optString("name", id).take(90))
                                }
                            }
                        }
                    }
                    val bitmap = remember(imageData) { AiApi.decodeDataImage(imageData) }
                    if (bitmap != null) {
                        Image(bitmap = bitmap.asImageBitmap(), contentDescription = "Generated image",
                            modifier = Modifier.fillMaxWidth().height(230.dp))
                    } else { Text("Output will appear here after generation.") }
                    OutlinedTextField(value = imagePrompt, onValueChange = { imagePrompt = it },
                        label = { Text("Image prompt") }, minLines = 3, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = imageModel, onValueChange = { imageModel = it },
                        label = { Text("OpenRouter image model") }, modifier = Modifier.fillMaxWidth())
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = approvePaid, onCheckedChange = { approvePaid = it })
                        Text("Approve this paid image request")
                    }
                    Button(enabled = approvePaid && imagePrompt.isNotBlank() && !busy, onClick = {
                        invoke("/api/v1/images", JSONObject()
                            .put("prompt", imagePrompt).put("model", imageModel)
                            .put("approve_paid_generation", true)) {
                                imageData = it.optString("image")
                                approvePaid = false
                                status = "Image received · not stored on server"
                            }
                    }) { Text("Generate") }
                    Text("Reference-image editing is available in the web studio/API; native edit upload is pending.")
                }
                2 -> Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Documents", style = MaterialTheme.typography.titleLarge)
                    OutlinedTextField(value = docTitle, onValueChange = { docTitle = it },
                        label = { Text("Title") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = docBody, onValueChange = { docBody = it },
                        label = { Text("Markdown content") }, minLines = 5, modifier = Modifier.fillMaxWidth())
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Button(onClick = { docId = ""; docTitle = ""; docBody = "" }) { Text("New") }
                        Button(enabled = docTitle.isNotBlank() && !busy, onClick = {
                            val existing = docId
                            val path = "/api/v1/documents" + if (existing.isNotBlank()) "/" + existing else ""
                            invoke(path, JSONObject().put("title", docTitle).put("body", docBody)) {
                                docId = it.getString("id")
                                status = "Document saved"
                            }
                        }) { Text("Save") }
                        Button(onClick = {
                            invoke("/api/v1/documents") { docIndex = it.optJSONArray("items") ?: JSONArray() }
                        }) { Text("Refresh") }
                    }
                    for (i in 0 until docIndex.length()) {
                        val doc = docIndex.optJSONObject(i) ?: continue
                        Button(onClick = {
                            invoke("/api/v1/documents/" + doc.optString("id")) {
                                docId = it.optString("id")
                                docTitle = it.optString("title")
                                docBody = it.optString("body")
                                status = "Opened saved document"
                            }
                        }, modifier = Modifier.fillMaxWidth()) { Text(doc.optString("title")) }
                    }
                    Text("Document ID: " + if (docId.isBlank()) "Unsaved" else docId)
                }
                3 -> Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Agent planning", style = MaterialTheme.typography.titleLarge)
                    OutlinedTextField(value = goal, onValueChange = { goal = it },
                        label = { Text("Describe a goal") }, minLines = 4, modifier = Modifier.fillMaxWidth())
                    Button(enabled = goal.isNotBlank() && !busy, onClick = {
                        invoke("/api/v1/agents/plan", JSONObject().put("goal", goal).put("provider", provider)
                            .put("allow_cloud_processing", cloudConsent)) {
                            plan = it.optString("plan"); status = "Planning only · no action executed"
                        }
                    }) { Text("Generate plan") }
                    Text(plan)
                    Button(enabled = docId.isNotBlank() && !busy, onClick = {
                        invoke("/api/v1/agents/run", JSONObject().put("action", "document.read")
                            .put("document_id", docId).put("approved", true)) {
                            toolResult = it.optJSONObject("result")?.optString("body") ?: ""
                            status = "Approved local document read"
                        }
                    }) { Text("Approve local document read") }
                    Text(toolResult)
                }
                else -> Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("MCP · explicit tool access", style = MaterialTheme.typography.titleLarge)
                    Button(enabled = !busy, onClick = {
                        invoke("/api/v1/mcp/tools") {
                            mcpNames = it.optJSONArray("tools") ?: JSONArray()
                            status = "Tool discovery completed; nothing executed"
                        }
                    }) { Text("Discover tools") }
                    Text("Discovered tool count: " + mcpNames.length())
                    OutlinedTextField(value = toolName, onValueChange = { toolName = it },
                        label = { Text("Allowed tool name") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = toolArgs, onValueChange = { toolArgs = it },
                        label = { Text("Arguments JSON object") }, minLines = 3, modifier = Modifier.fillMaxWidth())
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = approveTool, onCheckedChange = { approveTool = it })
                        Text("Approve this exact MCP action")
                    }
                    Button(enabled = !busy && approveTool && toolName.isNotBlank(), onClick = {
                        try {
                            val args = JSONObject(toolArgs)
                            invoke("/api/v1/mcp/call", JSONObject().put("name", toolName)
                                .put("arguments", args).put("approved", true)) {
                                toolResult = it.toString(2)
                                approveTool = false
                            }
                        } catch (e: Exception) { status = "Enter a valid JSON object" }
                    }) { Text("Call approved tool") }
                    Text(toolResult)
                }
            }
        }
    }
}
