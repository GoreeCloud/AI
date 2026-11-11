"use strict";
const byId = (id) => document.getElementById(id);
const state = {chatId:null, busy:false, controller:null, token:sessionStorage.getItem("goreeai-token")||""};
async function api(path, options={}) {
  const headers = {"Content-Type":"application/json",...(state.token?{"X-API-Key":state.token}:{})};
  const response=await fetch(path,{...options,headers:{...headers,...options.headers}});
  if(response.status===401 && !state.token){
    const entered=window.prompt("Enter your GoreeCloud AI API token");
    if(entered){state.token=entered;sessionStorage.setItem("goreeai-token",entered);return api(path,options);}
  }
  if(!response.ok){let error={};try{error=await response.json()}catch(_e){};throw new Error(typeof error.detail==="string"?error.detail:"Request failed ("+response.status+")");}
  return response.json();
}
function error(message){byId("error").hidden=!message;byId("error").textContent=message||"";}
function message(role,content,model){
  const element=document.createElement("article");
  element.className="message "+(role==="user"?"user":"assistant");
  const heading=document.createElement("div");heading.className="role";heading.textContent=role==="user"?"You":model?"AI · "+model:"GoreeCloud AI";
  const body=document.createElement("div");body.textContent=content;
  element.append(heading,body);byId("conversation").append(element);byId("conversation").scrollTop=byId("conversation").scrollHeight;return {element,heading,body};
}
function clearMessages(){byId("conversation").replaceChildren();}
async function loadChats(){
  const term=byId("chat-search").value.trim();
  const chats=term?await api("/api/chats/search",{method:"POST",body:JSON.stringify({query:term})}):await api("/api/chats");
  byId("chats").replaceChildren();
  for(const chat of chats){
    const button=document.createElement("button");
    button.type="button";button.className="chat-link"+(chat.id===state.chatId?" active":"");
    button.textContent=chat.title;button.onclick=()=>openChat(chat.id);
    byId("chats").append(button);
  }
}
async function openChat(id){
  const chat=await api("/api/chats/"+encodeURIComponent(id));
  state.chatId=id;byId("export-chat").disabled=false;byId("delete-chat").disabled=false;clearMessages();
  for(const item of chat.messages)message(item.role,item.content,item.model);
  await loadChats();
}
async function newChat(){
  error("");const chat=await api("/api/chats",{method:"POST",body:JSON.stringify({title:"New conversation"})});
  await openChat(chat.id);byId("prompt").focus();
}
async function loadModels(){
  const data=await api("/api/models");
  const select=byId("model");select.replaceChildren();
  const smart=document.createElement("option");smart.value="smart";smart.textContent="✦ Smart Model";select.append(smart);
  for(const [value,label] of [
    ["smart:fast","✦ Smart Model · Fast"],
    ["smart:balanced","✦ Smart Model · Balanced"],
    ["smart:quality","✦ Smart Model · Quality preference"],
  ]){const option=document.createElement("option");option.value=value;option.textContent=label;select.append(option);}

  for(const name of data.models){const option=document.createElement("option");option.value=name;option.textContent=name;select.append(option);}
}

async function streamAnswer(path, text, model, useKnowledge, onChunk, signal) {
  const headers={"Content-Type":"application/json",...(state.token?{"X-API-Key":state.token}:{})};
  const response=await fetch(path,{method:"POST",headers,signal,body:JSON.stringify({content:text,model,use_knowledge:useKnowledge})});
  if(!response.ok){let item={};try{item=await response.json()}catch(_e){}throw new Error(typeof item.detail==="string"?item.detail:"Request failed ("+response.status+")");}
  if(!response.body)throw new Error("This browser does not support streaming responses");
  const reader=response.body.getReader(), decoder=new TextDecoder();
  let buffer="", finished=false, info=null;
  async function consume(block){
    const lines=block.split("\n");
    let eventName="", payload="";
    for(const line of lines){if(line.startsWith("event:"))eventName=line.slice(6).trim();if(line.startsWith("data:"))payload+=line.slice(5).trim();}
    if(!payload)return;
    const data=JSON.parse(payload);
    if(eventName==="chunk")onChunk(data.content);
    else if(eventName==="done"){finished=true;info=data;}
    else if(eventName==="error")throw new Error(data.detail||"Generation failed");
  }
  try{
    while(true){
      const next=await reader.read();
      if(next.done)break;
      buffer+=decoder.decode(next.value,{stream:true}).replace(/\r/g,"");
      let offset;
      while((offset=buffer.indexOf("\n\n"))>=0){const part=buffer.slice(0,offset);buffer=buffer.slice(offset+2);await consume(part);}
    }
    if(buffer.trim())await consume(buffer);
    if(!finished)throw new Error("Generation ended unexpectedly");
    return info;
  }finally{reader.releaseLock();}
}

async function submit(event){
  event.preventDefault();if(state.busy)return;
  const text=byId("prompt").value.trim();if(!text)return;
  state.busy=true;state.controller=new AbortController();byId("send").disabled=true;byId("stop").disabled=false;error("");
  try{
    if(!state.chatId)await newChat();
    message("user",text);
    const output=message("assistant","",null);
    const result=await streamAnswer("/api/chats/"+encodeURIComponent(state.chatId)+"/stream",text,byId("model").value,byId("use-knowledge").checked,(part)=>{
      output.body.textContent+=part;byId("conversation").scrollTop=byId("conversation").scrollHeight;
    },state.controller.signal);
    output.heading.textContent="AI · "+result.model;byId("prompt").value="";
    byId("hint").textContent=result.routing.reason+(result.sources&&result.sources.length?" · "+result.sources.map(s=>s.title).join(", "):"");
    await loadChats();
  }catch(e){error(e.name==="AbortError"?"Generation stopped":e.message);if(state.chatId){try{await openChat(state.chatId)}catch(_ignore){}}}
  finally{state.busy=false;state.controller=null;byId("send").disabled=false;byId("stop").disabled=true;}
}


async function importChat(file){
  if(!file)return;
  if(file.size>1500000)throw new Error("Conversation import is limited to 1.5 MB");
  const imported=await api("/api/chats/import",{method:"POST",body:await file.text()});
  await openChat(imported.id);
  byId("chat-search").value="";
  await loadChats();
}

async function exportChat(){
  if(!state.chatId)return;
  const response=await fetch("/api/chats/"+encodeURIComponent(state.chatId)+"/export",{
    headers:state.token?{"X-API-Key":state.token}:{}
  });
  if(!response.ok)throw new Error("Unable to export conversation");
  const blob=await response.blob();
  const link=document.createElement("a"),url=URL.createObjectURL(blob);
  link.href=url;link.download="goreecloud-ai-chat-"+state.chatId+".json";
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}


async function deleteChat(){
  if(!state.chatId || state.busy)return;
  if(!window.confirm("Permanently delete this conversation?"))return;
  await api("/api/chats/"+encodeURIComponent(state.chatId),{method:"DELETE"});
  state.chatId=null;
  byId("export-chat").disabled=true;byId("delete-chat").disabled=true;
  clearMessages();
  const intro=document.createElement("p");
  intro.className="empty-message";intro.textContent="Conversation deleted. Create a new conversation to begin.";
  byId("conversation").append(intro);
  await loadChats();
}

function knowledgeError(message){
  const element=byId("knowledge-error");
  element.hidden=!message;
  element.textContent=message||"";
}
async function loadKnowledge(){
  const list=byId("knowledge-list");
  const documents=await api("/api/knowledge/documents");
  list.replaceChildren();
  if(!documents.length){
    const note=document.createElement("p");note.textContent="No knowledge documents yet.";list.append(note);
    return;
  }
  for(const doc of documents){
    const item=document.createElement("div");item.className="knowledge-item";
    const label=document.createElement("span");label.textContent=doc.title;
    const remove=document.createElement("button");remove.type="button";remove.textContent="Delete";
    remove.setAttribute("aria-label","Delete document "+doc.title);
    remove.onclick=async()=>{
      if(!window.confirm("Delete this knowledge document permanently?"))return;
      try{
        knowledgeError("");
        await api("/api/knowledge/documents/"+encodeURIComponent(doc.id),{method:"DELETE"});
        await loadKnowledge();
      }catch(e){knowledgeError(e.message);}
    };
    item.append(label,remove);list.append(item);
  }
}

async function importKnowledgeFile(event){
  const file=event.target.files?.[0];
  if(!file)return;
  try{
    knowledgeError("");
    const ext=file.name.split(".").pop()?.toLowerCase();
    if(!["txt","md","csv","json"].includes(ext))throw new Error("Choose a .txt, .md, .csv or .json file");
    if(file.size>100000)throw new Error("Local file imports are limited to 100 KB");
    const content=await file.text();
    if(!content.trim())throw new Error("The selected file is empty");
    if(content.length>50000)throw new Error("Document text exceeds 50,000 characters");
    await api("/api/knowledge/documents",{method:"POST",body:JSON.stringify({
      title:file.name.slice(0,120),content
    })});
    await loadKnowledge();
  }catch(e){knowledgeError(e.message);}
  finally{event.target.value="";}
}

async function searchKnowledge(event){
  event.preventDefault();
  const box=byId("knowledge-search-results");
  box.replaceChildren();
  const query=byId("knowledge-search-query").value.trim();
  if(!query)return;
  try{
    knowledgeError("");
    const results=await api("/api/knowledge/search",{method:"POST",body:JSON.stringify({query})});
    if(!results.length){
      const empty=document.createElement("p");empty.textContent="No matching excerpts.";box.append(empty);
      return;
    }
    for(const result of results){
      const item=document.createElement("article");item.className="knowledge-result";
      const title=document.createElement("strong");title.textContent=result.title;
      const excerpt=document.createElement("p");excerpt.textContent=result.excerpt;
      item.append(title,excerpt);box.append(item);
    }
  }catch(e){knowledgeError(e.message);}
}

async function showKnowledge(){
  knowledgeError("");
  byId("knowledge-dialog").showModal();
  try{await loadKnowledge();}catch(e){knowledgeError(e.message);}
}
async function saveKnowledge(event){
  event.preventDefault();knowledgeError("");
  const button=byId("knowledge-save");button.disabled=true;
  try{
    await api("/api/knowledge/documents",{
      method:"POST",body:JSON.stringify({
        title:byId("knowledge-title").value.trim(),
        content:byId("knowledge-content").value
      })
    });
    byId("knowledge-form").reset();
    await loadKnowledge();
  }catch(e){knowledgeError(e.message);}
  finally{button.disabled=false;}
}

async function init(){
  byId("composer").addEventListener("submit",submit);
  byId("stop").addEventListener("click",()=>state.controller?.abort());
  byId("delete-chat").addEventListener("click",()=>deleteChat().catch(e=>error(e.message)));
  byId("manage-knowledge").addEventListener("click",showKnowledge);
  byId("close-knowledge").addEventListener("click",()=>byId("knowledge-dialog").close());
  byId("knowledge-form").addEventListener("submit",saveKnowledge);
  byId("knowledge-file").addEventListener("change",importKnowledgeFile);
  byId("knowledge-search-form").addEventListener("submit",searchKnowledge);
  byId("chat-search").addEventListener("input",()=>loadChats().catch(e=>error(e.message)));
  byId("import-chat").addEventListener("click",()=>byId("import-chat-file").click());
  byId("import-chat-file").addEventListener("change",async event=>{
    const file=event.target.files?.[0];
    try{await importChat(file);error("");}catch(e){error(e.message);}
    finally{event.target.value="";}
  });
  byId("export-chat").addEventListener("click",()=>exportChat().catch(e=>error(e.message)));
  byId("new-chat").addEventListener("click",()=>newChat().catch(e=>error(e.message)));
  byId("prompt").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();byId("composer").requestSubmit();}});
  try{await Promise.all([loadModels(),loadChats()]);}catch(e){error(e.message);}
  try{const data=await api("/api/health");byId("health").textContent="Ollama "+data.ollama;byId("health-dot").classList.toggle("online",data.ollama==="online");}catch(_e){byId("health").textContent="Status unavailable";}
}
init();
