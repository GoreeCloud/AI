package com.goreecloud.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

private val gcScheme = darkColorScheme(
    primary = Color(0xFFBFB8FF), onPrimary = Color(0xFF272057),
    primaryContainer = Color(0xFF413974), onPrimaryContainer = Color(0xFFE8E5FF),
    background = Color(0xFF0D121D), onBackground = Color(0xFFF2F4FB),
    surface = Color(0xFF171D2A), onSurface = Color(0xFFF2F4FB),
    surfaceVariant = Color(0xFF252D3D), onSurfaceVariant = Color(0xFFCED5E5),
    outline = Color(0xFF9CA8BC)
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = gcScheme) { AiWorkspace() } }
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
    val chat = remember { mutableStateListOf<Pair<String, String>>() }
    var prompt by remember { mutableStateOf("") }
    var imagePrompt by remember { mutableStateOf("") }
    var imageModel by remember { mutableStateOf("bytedance-seed/seedream-4.5") }
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

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { i, name ->
                    NavigationBarItem(
                        selected = current == i,
                        onClick = { current = i },
                        icon = { Text(listOf("✦", "◈", "▤", "✳", "⌘")[i]) },
                        label = { Text(name) }
                    )
                }
            }
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
                0 -> Column(modifier = Modifier.fillMaxSize().padding(18.dp)) {
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
                        Button(onClick = { provider = if (provider == "auto") "ollama" else "auto" }) {
                            Text(if (provider == "auto") "Auto · OpenRouter" else "Local · Ollama")
                        }
                        Button(onClick = { chat.clear() }) { Text("New chat") }
                    }
                    OutlinedTextField(value = model, onValueChange = { model = it },
                        label = { Text("Model ID") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Checkbox(checked = fallback, onCheckedChange = { fallback = it })
                        Text("Allow local fallback", style = MaterialTheme.typography.bodySmall)
                    }
                    OutlinedTextField(value = prompt, onValueChange = { prompt = it },
                        label = { Text("Message") }, minLines = 2, maxLines = 5,
                        modifier = Modifier.fillMaxWidth())
                    Button(enabled = !busy && prompt.isNotBlank(), onClick = {
                        val text = prompt.trim(); prompt = ""
                        chat.add("user" to text)
                        invoke("/api/v1/chat", AiApi.chatBody(chat.toList(), provider, model, fallback)) {
                            chat.add("assistant" to it.optString("content"))
                            status = "Answered via " + it.optString("provider")
                        }
                    }, modifier = Modifier.fillMaxWidth()) { Text("Send") }
                }
                1 -> Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Image studio", style = MaterialTheme.typography.titleLarge)
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
                        invoke("/api/v1/agents/plan", JSONObject().put("goal", goal).put("provider", provider)) {
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
