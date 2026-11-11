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
  element.append(heading,body);byId("conversation").append(element);byId("conversation").scrollTop=byId("conversation").scrollHeight;
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
async function submit(event){
  event.preventDefault();if(state.busy)return;
  const text=byId("prompt").value.trim();if(!text)return;
  state.busy=true;byId("send").disabled=true;error("");
  try{
    if(!state.chatId)await newChat();
    const result=await api("/api/chats/"+encodeURIComponent(state.chatId)+"/messages",{method:"POST",body:JSON.stringify({content:text,model:byId("model").value})});
    byId("prompt").value="";message("user",text);message("assistant",result.message.content,result.message.model);byId("hint").textContent=result.routing.reason;
  }catch(e){error(e.message);}
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
