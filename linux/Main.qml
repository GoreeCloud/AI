import QtQuick 6.12
import QtQuick.Controls 6.12
import QtQuick.Layouts 6.12
import QtQuick.Window 6.12

ApplicationWindow {
    id: window
    width: 1140
    height: 760
    minimumWidth: 720
    minimumHeight: 550
    visible: true
    title: "GoreeCloud AI · Developer Preview"
    color: "#0D121D"

    property string endpoint: "http://127.0.0.1:8000"
    property string token: ""
    property string provider: "auto"
    property string model: "openrouter/auto"
    property bool allowFallback: false
    property bool cloudConsent: false
    property bool streamResponses: true
    property int activeStreamRow: -1
    property bool busy: false
    property string feedback: ""
    property string documentId: ""
    property var documents: []
    property var mcpTools: []
    property string renderedImage: ""
    property var imageModels: []
    property int restRequestCounter: 0
    property var restPendingCallbacks: ({})

    function request(method, path, payload, callback) {
        if (busy)
            return
        if (token.length === 0) {
            feedback = "Enter an owner token before sending a request."
            return
        }
        busy = true
        feedback = ""
        restRequestCounter += 1
        if (restRequestCounter > 2000000000)
            restRequestCounter = 1
        var id = restRequestCounter
        restPendingCallbacks[id] = callback
        restBridge.start(id, endpoint, token, method, path,
                         payload === null ? "" : JSON.stringify(payload))
    }

    Connections {
        target: restBridge
        function onSucceeded(requestId, jsonText) {
            var callback = window.restPendingCallbacks[requestId]
            delete window.restPendingCallbacks[requestId]
            window.busy = false
            try {
                if (callback)
                    callback(JSON.parse(jsonText))
            } catch (_error) {
                window.feedback = "API response could not be applied"
            }
        }
        function onFailed(requestId, message) {
            delete window.restPendingCallbacks[requestId]
            window.busy = false
            window.feedback = message
        }
    }

    function sendChat() {
        if (chatPrompt.text.trim().length === 0 || busy)
            return
        var userText = chatPrompt.text.trim()
        chatPrompt.text = ""
        threadModel.append({role: "You", text: userText})
        var chain = []
        for (var i = 0; i < threadModel.count; i++) {
            var current = threadModel.get(i)
            chain.push({role: current.role === "You" ? "user" : "assistant", content: current.text})
        }
        var payload = {
            messages: chain,
            model: model,
            provider: provider,
            allow_local_fallback: allowFallback,
            allow_cloud_processing: cloudConsent
        }
        if (streamResponses && !allowFallback) {
            if (token.length === 0) {
                feedback = "Enter an owner token before sending a request."
                return
            }
            activeStreamRow = threadModel.count
            threadModel.append({role: "GoreeCloud AI", text: ""})
            busy = true
            feedback = "Receiving streamed answer…"
            streamBridge.start(endpoint, token, JSON.stringify(payload))
        } else {
            request("POST", "/api/v1/chat", payload, function(reply) {
                threadModel.append({role: "GoreeCloud AI", text: reply.content})
                feedback = "Answered via " + reply.provider + " · " + reply.model
            })
        }
    }

    Connections {
        target: streamBridge
        function onDelta(value) {
            if (window.activeStreamRow < 0 || window.activeStreamRow >= threadModel.count)
                return
            var row = threadModel.get(window.activeStreamRow)
            threadModel.setProperty(window.activeStreamRow, "text", row.text + value)
        }
        function onCompleted(resultProvider, resultModel) {
            window.activeStreamRow = -1
            window.busy = false
            window.feedback = "Answered via " + resultProvider + " · " + resultModel
        }
        function onFailed(message) {
            if (window.activeStreamRow >= 0 &&
                window.activeStreamRow < threadModel.count &&
                threadModel.get(window.activeStreamRow).text.length === 0) {
                threadModel.remove(window.activeStreamRow)
            }
            window.activeStreamRow = -1
            window.busy = false
            window.feedback = message
        }
        function onStopped() {
            window.activeStreamRow = -1
            window.busy = false
            window.feedback = "Stream cancelled; provider usage may already be billable."
        }
    }

    header: ToolBar {
        background: Rectangle { color: "#171D2A" }
        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 14
            Label { text: "✦ GoreeCloud AI"; color: "#BFB8FF"; font.pixelSize: 21; font.bold: true }
            Label { text: "DEVELOPER PREVIEW"; color: "#CED5E5"; font.pixelSize: 11 }
            Item { Layout.fillWidth: true }
            Label { text: "API"; color: "#CED5E5" }
            TextField {
                implicitWidth: 240
                text: window.endpoint
                onEditingFinished: window.endpoint = text
                Accessible.name: "API endpoint"
            }
            Label { text: "Token"; color: "#CED5E5" }
            TextField {
                implicitWidth: 180
                echoMode: TextInput.Password
                placeholderText: "Owner token (memory only)"
                onTextChanged: window.token = text
                Accessible.name: "Owner token"
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        TabBar {
            id: tabs
            Layout.fillWidth: true
            background: Rectangle { color: "#171D2A"; radius: 12 }
            TabButton { text: "Chat" }
            TabButton { text: "Images" }
            TabButton { text: "Documents" }
            TabButton { text: "Agents" }
            TabButton { text: "MCP tools" }
        }

        Label {
            Layout.fillWidth: true
            text: window.feedback.length ? window.feedback : "Cloud prompts leave your server; local Ollama stays on the configured host."
            color: window.feedback.length ? "#FFCE83" : "#CED5E5"
            wrapMode: Text.WordWrap
            font.pixelSize: 12
            Accessible.name: "Service status"
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            RowLayout {
                spacing: 15
                Rectangle {
                    color: "#171D2A"; radius: 20
                    Layout.fillWidth: true; Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            model: ListModel { id: threadModel }
                            spacing: 12
                            clip: true
                            delegate: Rectangle {
                                width: ListView.view.width
                                height: messageColumn.implicitHeight + 22
                                color: role === "You" ? "#252D3D" : "#171D2A"
                                radius: 12
                                Column {
                                    id: messageColumn
                                    x: 12; y: 10; width: parent.width - 24; spacing: 5
                                    Label { text: role; font.bold: true; color: "#BFB8FF" }
                                    Label { text: model.text; width: parent.width; color: "#F2F4FB"; wrapMode: Text.WrapAnywhere }
                                }
                            }
                        }
                        TextArea {
                            id: chatPrompt
                            Layout.fillWidth: true
                            placeholderText: "Ask a question, draft text, or explore a problem..."
                            wrapMode: TextEdit.Wrap
                            implicitHeight: 95
                            Accessible.name: "Chat message"
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Button {
                                text: window.busy ? "Working..." :
                                    (window.streamResponses && !window.allowFallback ? "Stream answer" : "Send")
                                enabled: !window.busy && chatPrompt.text.trim().length > 0
                                onClicked: window.sendChat()
                            }
                            Button {
                                text: "Cancel stream"
                                visible: window.busy && window.activeStreamRow >= 0
                                enabled: visible
                                onClicked: streamBridge.cancel()
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 260
                    Layout.fillHeight: true; radius: 20; color: "#171D2A"
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 14
                        Label { text: "Model routing"; font.bold: true; color: "#F2F4FB"; font.pixelSize: 19 }
                        ComboBox {
                            model: ["Auto · OpenRouter first", "OpenRouter", "Ollama local"]
                            Layout.fillWidth: true
                            onCurrentIndexChanged: window.provider = ["auto", "openrouter", "ollama"][currentIndex]
                            Accessible.name: "Inference provider"
                        }
                        TextField {
                            Layout.fillWidth: true; text: window.model
                            onTextChanged: window.model = text
                            Accessible.name: "Model identifier"
                        }
                        CheckBox {
                            text: "Approve sending text to OpenRouter"
                            checked: window.cloudConsent
                            onToggled: window.cloudConsent = checked
                            Accessible.name: "Allow cloud processing"
                        }
                        CheckBox {
                            text: "Allow local fallback"
                            checked: window.allowFallback
                            onToggled: window.allowFallback = checked
                        }
                        CheckBox {
                            text: "Stream answer with cancel"
                            checked: window.streamResponses
                            onToggled: window.streamResponses = checked
                            Accessible.name: "Stream chat response"
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: "#CED5E5"
                            font.pixelSize: 11
                            text: window.allowFallback && window.streamResponses ?
                                "Local fallback requires a non-streaming request." :
                                "Streaming may incur provider usage before cancellation."
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: "#CED5E5"
                            text: "Paid OpenRouter calls require a configured provider key. Local model selection never routes to cloud."
                        }
                        Item { Layout.fillHeight: true }
                        Button {
                            text: "New conversation"
                            enabled: !window.busy
                            onClicked: threadModel.clear()
                        }
                    }
                }
            }

            RowLayout {
                spacing: 15
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    color: "#171D2A"; radius: 20
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20
                        Label { text: "Image canvas"; color: "#F2F4FB"; font.pixelSize: 20 }
                        Image {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            fillMode: Image.PreserveAspectFit
                            source: window.renderedImage
                            cache: false
                        }
                        Label {
                            Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter
                            text: window.renderedImage ? "Image returned by provider" : "Generate an image to preview here."
                            color: "#CED5E5"
                        }
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true; color: "#171D2A"; radius: 20
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 14
                        Label { text: "Creative controls"; color: "#F2F4FB"; font.pixelSize: 20 }
                        TextField { id: imageModel; Layout.fillWidth: true; text: "bytedance-seed/seedream-4.5"; Accessible.name: "Image model ID" }
                        Button {
                            text: "Browse available image models"
                            enabled: !window.busy
                            Accessible.name: "Discover image models without generating"
                            onClicked: window.request("GET", "/api/v1/images/models", null, function(reply) {
                                window.imageModels = reply.models || []
                                window.feedback = "Image models listed. No paid generation requested."
                            })
                        }
                        ComboBox {
                            Layout.fillWidth: true
                            visible: window.imageModels.length > 0
                            model: window.imageModels
                            textRole: "name"
                            Accessible.name: "Choose discovered image model"
                            onActivated: function(index) {
                                if (index >= 0 && index < window.imageModels.length) {
                                    imageModel.text = window.imageModels[index].id
                                    imageApproved.checked = false
                                    window.feedback = "Model selected. Paid generation still needs approval."
                                }
                            }
                        }
                        TextArea {
                            id: imagePrompt
                            Layout.fillWidth: true; Layout.preferredHeight: 165
                            placeholderText: "Describe the image to create..."
                            wrapMode: TextEdit.Wrap
                        }
                        CheckBox { id: imageApproved; text: "Authorize paid image call" }
                        Button {
                            text: "Generate image"; enabled: !window.busy && imageApproved.checked && imagePrompt.text.trim().length > 0
                            onClicked: {
                                window.request("POST", "/api/v1/images", {
                                    prompt: imagePrompt.text, model: imageModel.text,
                                    approve_paid_generation: true
                                }, function(reply) {
                                    window.renderedImage = reply.image
                                    imageApproved.checked = false
                                    window.feedback = "Image returned. The Linux image preview uses data URLs."
                                })
                            }
                        }
                        Label {
                            Layout.fillWidth: true; wrapMode: Text.WordWrap
                            color: "#CED5E5"
                            text: "Reference-image editing and file export are available through the API and web UI, not yet this native preview."
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            RowLayout {
                spacing: 15
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "#171D2A"; radius: 20
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 18
                        TextField { id: docTitle; Layout.fillWidth: true; placeholderText: "Document title" }
                        TextArea {
                            id: docBody; Layout.fillWidth: true; Layout.fillHeight: true
                            placeholderText: "Write Markdown..."
                            wrapMode: TextEdit.Wrap
                        }
                        RowLayout {
                            Button { text: "New"; onClicked: { window.documentId = ""; docTitle.text = ""; docBody.text = "" } }
                            Button {
                                text: "Save"
                                enabled: !window.busy && docTitle.text.trim().length > 0
                                onClicked: window.request(
                                    window.documentId ? "PUT" : "POST",
                                    "/api/v1/documents" + (window.documentId ? "/" + window.documentId : ""),
                                    {title: docTitle.text, body: docBody.text}, function(reply) {
                                        window.documentId = reply.id
                                        window.feedback = "Saved to local server database."
                                    })
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 300; Layout.fillHeight: true
                    color: "#171D2A"; radius: 20
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 15
                        Button {
                            text: "Refresh library"; enabled: !window.busy
                            onClicked: window.request("GET", "/api/v1/documents", null, function(reply) {
                                documentList.clear()
                                for (var i = 0; i < reply.length; i++)
                                    documentList.append({id: reply[i].id, title: reply[i].title})
                            })
                        }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            model: ListModel { id: documentList }
                            clip: true
                            delegate: Button {
                                width: ListView.view.width
                                text: title
                                onClicked: window.request("GET", "/api/v1/documents/" + id, null, function(reply) {
                                    window.documentId = reply.id
                                    docTitle.text = reply.title
                                    docBody.text = reply.body
                                })
                            }
                        }
                    }
                }
            }

            RowLayout {
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "#171D2A"; radius: 20
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 14
                        Label { text: "Agent planner"; color: "#F2F4FB"; font.pixelSize: 20 }
                        TextArea {
                            id: agentGoal; Layout.fillWidth: true; Layout.preferredHeight: 100
                            placeholderText: "Describe your goal..."
                            wrapMode: TextEdit.Wrap
                        }
                        Button {
                            text: "Create plan"; enabled: !window.busy && agentGoal.text.trim().length > 0
                            onClicked: window.request("POST", "/api/v1/agents/plan",
                                {goal: agentGoal.text, provider: window.provider,
                                 allow_cloud_processing: window.cloudConsent}, function(reply) {
                                    agentPlan.text = reply.plan
                                    window.feedback = "Plan created; no actions were executed."
                                })
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            TextArea { id: agentPlan; readOnly: true; wrapMode: TextEdit.Wrap; placeholderText: "Plan appears here." }
                        }
                    }
                }
            }

            RowLayout {
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "#171D2A"; radius: 20
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 13
                        Label { text: "MCP · explicit control"; color: "#F2F4FB"; font.pixelSize: 20 }
                        Button {
                            text: "Discover tools"; enabled: !window.busy
                            onClicked: window.request("GET", "/api/v1/mcp/tools", null, function(reply) {
                                toolChoices.model = reply.tools
                                window.feedback = "Tools discovered; no action was executed."
                            })
                        }
                        ComboBox {
                            id: toolChoices; Layout.fillWidth: true; model: []
                            Accessible.name: "MCP tool"
                        }
                        TextArea {
                            id: toolArguments; Layout.fillWidth: true; Layout.preferredHeight: 100
                            text: "{}"; wrapMode: TextEdit.Wrap
                            Accessible.name: "Tool arguments JSON"
                        }
                        CheckBox { id: toolApproved; text: "Approve this exact tool action" }
                        Button {
                            text: "Invoke allowed tool"
                            enabled: !window.busy && toolApproved.checked && toolChoices.currentText.length > 0
                            onClicked: {
                                try {
                                    var args = JSON.parse(toolArguments.text)
                                    if (args === null || Array.isArray(args) || typeof args !== "object")
                                        throw new Error("Arguments must be a JSON object")
                                    window.request("POST", "/api/v1/mcp/call", {
                                        name: toolChoices.currentText, arguments: args, approved: true
                                    }, function(reply) {
                                        toolApproved.checked = false
                                        toolResults.text = JSON.stringify(reply, null, 2)
                                    })
                                } catch (err) { window.feedback = "Invalid tool arguments JSON" }
                            }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            TextArea { id: toolResults; readOnly: true; wrapMode: TextEdit.Wrap }
                        }
                    }
                }
            }
        }
    }
}
