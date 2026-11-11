"use strict";
const byId = (id) => document.getElementById(id);
const state = {chatId:null, busy:false, token:sessionStorage.getItem("goreeai-token")||""};
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
  const chats=await api("/api/chats");
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
  state.chatId=id;clearMessages();
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
  for(const name of data.models){const option=document.createElement("option");option.value=name;option.textContent=name;select.append(option);}
}

async function streamAnswer(path, text, model, useKnowledge, onChunk) {
  const headers={"Content-Type":"application/json",...(state.token?{"X-API-Key":state.token}:{})};
  const response=await fetch(path,{method:"POST",headers,body:JSON.stringify({content:text,model,use_knowledge:useKnowledge})});
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
  state.busy=true;byId("send").disabled=true;error("");
  try{
    if(!state.chatId)await newChat();
    message("user",text);
    const output=message("assistant","",null);
    const result=await streamAnswer("/api/chats/"+encodeURIComponent(state.chatId)+"/stream",text,byId("model").value,byId("use-knowledge").checked,(part)=>{
      output.body.textContent+=part;byId("conversation").scrollTop=byId("conversation").scrollHeight;
    });
    output.heading.textContent="AI · "+result.model;byId("prompt").value="";
    byId("hint").textContent=result.routing.reason+(result.sources&&result.sources.length?" · "+result.sources.map(s=>s.title).join(", "):"");
    await loadChats();
  }catch(e){error(e.message);if(state.chatId){try{await openChat(state.chatId)}catch(_ignore){}}}
  finally{state.busy=false;byId("send").disabled=false;}
}
async function init(){
  byId("composer").addEventListener("submit",submit);
  byId("new-chat").addEventListener("click",()=>newChat().catch(e=>error(e.message)));
  byId("prompt").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();byId("composer").requestSubmit();}});
  try{await Promise.all([loadModels(),loadChats()]);}catch(e){error(e.message);}
  try{const data=await api("/api/health");byId("health").textContent="Ollama "+data.ollama;byId("health-dot").classList.toggle("online",data.ollama==="online");}catch(_e){byId("health").textContent="Status unavailable";}
}
init();
