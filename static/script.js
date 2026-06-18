// ── GUARD: skip if loaded inside iframe (call lives in top window) ──
if(window.top!==window){
  ['callOverlay','callIncoming','callPip'].forEach(function(id){
    var el=document.getElementById(id);if(el)el.remove();
  });
} else {
  // Restore original setInterval so call intervals are NOT tracked by page tracker
  if(window.__origSetInterval)window.setInterval=window.__origSetInterval;

// ── WEBRTC CALLING ──
const STUN_SERVERS={'iceServers':[{'urls':'stun:stun.l.google.com:19302'},{'urls':'stun:stun1.l.google.com:19302'},{'urls':'turn:openrelay.metered.ca:80',username:'openrelayproject',credential:'openrelayproject'},{'urls':'turns:openrelay.metered.ca:443',username:'openrelayproject',credential:'openrelayproject'}]};
let pc=null;
let localStream=null;
let screenStream=null;
let callPeerId=null;
let callStartTime=null;
let callTimer=null;
let callIsVideo=false;
let callPollInterval=null;
let callSetupTimeout=null;
let pendingIceCandidates=[];
let pipActive=false;
let callMinimized=false;

let incomingCallerId=null;
let incomingOffer=null;
let incomingMissedTimeout=null;

function createPeerConnection(){
  pc=new RTCPeerConnection(STUN_SERVERS);
  localStream.getTracks().forEach(function(t){pc.addTrack(t,localStream);});
  pc.ontrack=function(e){
    var vid=document.getElementById('remoteVideo');
    var pipVid=document.getElementById('pipVideo');
    if(e.streams&&e.streams[0]){
      vid.style.display='block';
      vid.srcObject=e.streams[0];
      pipVid.srcObject=e.streams[0];
    }else if(e.track){
      var s=new MediaStream();
      s.addTrack(e.track);
      vid.style.display='block';
      vid.srcObject=s;
      pipVid.srcObject=s;
    }
    vid.play().catch(function(){});
    pipVid.play().catch(function(){});
  };
  pc.onicecandidate=function(e){
    if(e.candidate){
      fetch('/chatx/call/signal/'+callPeerId+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken': getCSRFToken()},body:JSON.stringify({type:'ice',data:e.candidate})});
    }
  };
  pc.onconnectionstatechange=function(){
    if(pc&&pc.connectionState==='connected'){
      document.getElementById('callStatus').textContent='Connected';
      if(callSetupTimeout){clearTimeout(callSetupTimeout);callSetupTimeout=null;}
    }else if(pc&&(pc.connectionState==='disconnected'||pc.connectionState==='failed')){
      showCallToast('Call ended');
      endCall();
    }
  };
  pc.oniceconnectionstatechange=function(){
    if(pc&&pc.iceConnectionState==='failed'){endCall();}
  };
  pc.onnegotiationneeded=function(){
    pc.createOffer().then(function(offer){
      return pc.setLocalDescription(offer);
    }).then(function(){
      fetch('/chatx/call/signal/'+callPeerId+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken': getCSRFToken()},body:JSON.stringify({type:'offer',data:pc.localDescription.toJSON()})});
    }).catch(function(e){console.error('negotiationneeded error',e);});
  };
}

function getCSRFToken(){
  var m=document.cookie.match(/csrftoken=([\w-]+)/);
  return m?m[1]:'';
}

function showCallToast(msg){
  var t=document.createElement('div');
  t.textContent=msg;
  t.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:8px;z-index:99999;font-size:.85rem;animation:fadeIn .2s;';
  document.body.appendChild(t);
  setTimeout(function(){t.remove();},3000);
}

function flushIceCandidates(){
  if(!pc||!pc.remoteDescription)return;
  pendingIceCandidates.forEach(function(c){
    try{pc.addIceCandidate(new RTCIceCandidate(c));}catch(e){}
  });
  pendingIceCandidates=[];
}

// ── START CALL ──
function startCall(video){
  if(!window.currentChatUserId){showCallToast('Select a conversation first');return;}
  callIsVideo=video;
  callPeerId=window.currentChatUserId;
  const name=document.getElementById('chatHeaderName')?document.getElementById('chatHeaderName').textContent:'User';
  document.getElementById('callName').textContent=name;
  document.getElementById('callStatus').textContent='Calling...';
  var av=document.getElementById('callAvatar');
  var ha=document.getElementById('chatHeaderAvatar')?document.getElementById('chatHeaderAvatar').style.backgroundImage:'';
  av.style.backgroundImage=ha;
  av.textContent=ha?'':name[0].toUpperCase();
  document.getElementById('callOverlay').classList.add('active');
  document.getElementById('remoteVideo').style.display='none';
  const constraints={audio:true,video:video};
  navigator.mediaDevices.getUserMedia(constraints).then(function(stream){
    localStream=stream;
    document.getElementById('localVideo').srcObject=stream;
    createPeerConnection();
    pc.createOffer().then(function(offer){
      return pc.setLocalDescription(offer);
    }).then(function(){
      fetch('/chatx/call/signal/'+callPeerId+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken': getCSRFToken()},body:JSON.stringify({type:'offer',data:pc.localDescription.toJSON()})});
    }).catch(function(e){
      console.error('createOffer error',e);
      showCallToast('Failed to create offer');
      endCall();
    });
    callStartTime=Date.now();
    startPolling();
    startCallTimer();
    callSetupTimeout=setTimeout(function(){
      if(pc&&pc.connectionState!=='connected'){
        showCallToast('Call timed out - no answer');
        endCall();
      }
    },30000);
  }).catch(function(err){
    showCallToast('Could not access camera/microphone: '+err.message);
    document.getElementById('callOverlay').classList.remove('active');
  });
}

// ── POLL SIGNALS ──
function pollCallSignals(){
  if(!pc||!callPeerId)return;
  fetch('/chatx/call/poll/',{credentials:'same-origin'}).then(function(r){
    if(!r.ok)throw new Error('Poll status '+r.status);
    return r.json();
  }).then(function(d){
    d.signals.forEach(function(s){
      var uid=window.callUserId||0;
      if(s.caller_id!==callPeerId&&s.caller_id!==uid)return;
      if(s.type==='answer'&&s.data){
        try{
          var desc=JSON.parse(s.data);
          if(!pc.remoteDescription||pc.signalingState==='stable'){
            pc.setRemoteDescription(new RTCSessionDescription(desc)).then(function(){
              flushIceCandidates();
            }).catch(function(e){console.error('setRemoteDescription answer',e);});
          }
        }catch(e){console.error('poll answer parse',e);}
      }else if(s.type==='ice'&&s.data){
        try{
          var cand=JSON.parse(s.data);
          if(pc.remoteDescription){
            pc.addIceCandidate(new RTCIceCandidate(cand)).catch(function(e){console.error('addIceCandidate',e);});
          }else{
            pendingIceCandidates.push(cand);
          }
        }catch(e){console.error('poll ice parse',e);}
      }else if(s.type==='end'){
        endCall();
      }
    });
  }).catch(function(e){console.error('pollCallSignals',e);});
}

function startPolling(){
  if(callPollInterval)clearInterval(callPollInterval);
  callPollInterval=setInterval(pollCallSignals,pc&&pc.connectionState==='connected'?2000:500);
  if(_callInts.indexOf(callPollInterval)<0)_callInts.push(callPollInterval);
}

function startCallTimer(){
  if(callTimer)clearInterval(callTimer);
  callTimer=setInterval(function(){
    var sec=Math.floor((Date.now()-callStartTime)/1000);
    var m=String(Math.floor(sec/60)).padStart(2,'0');
    var s=String(sec%60).padStart(2,'0');
    document.getElementById('callDuration').textContent=m+':'+s;
  },1000);
  if(_callInts.indexOf(callTimer)<0)_callInts.push(callTimer);
}

// ── END CALL ──
function endCall(){
  if(callSetupTimeout){clearTimeout(callSetupTimeout);callSetupTimeout=null;}
  if(callPollInterval){clearInterval(callPollInterval);callPollInterval=null;}
  if(callTimer){clearInterval(callTimer);callTimer=null;}
  if(pc){pc.close();pc=null;}
  if(localStream){localStream.getTracks().forEach(function(t){t.stop();});localStream=null;}
  if(screenStream){screenStream.getTracks().forEach(function(t){t.stop();});screenStream=null;}
  document.getElementById('callOverlay').classList.remove('active');
  document.getElementById('callIncoming').classList.remove('active');
  document.getElementById('callPip').classList.remove('active');
  document.body.style.overflow='';
  callMinimized=false;
  pipActive=false;
  if(callPeerId){
    fetch('/chatx/call/signal/'+callPeerId+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken': getCSRFToken()},body:JSON.stringify({type:'end',data:''})}).catch(function(){});
  }
  callPeerId=null;
  incomingCallerId=null;
  incomingOffer=null;
  pendingIceCandidates=[];
  var rv=document.getElementById('remoteVideo');if(rv){rv.srcObject=null;rv.style.display='none';}
  var lv=document.getElementById('localVideo');if(lv){lv.srcObject=null;}
  var pv=document.getElementById('pipVideo');if(pv){pv.srcObject=null;}
}

// ── TOGGLE MIC ──
function callToggleMic(){
  if(!localStream)return;
  const t=localStream.getAudioTracks()[0];
  if(t){t.enabled=!t.enabled;
    document.getElementById('callToggleMic').classList.toggle('muted',!t.enabled);
    document.getElementById('callToggleMic').querySelector('i').className=t.enabled?'fas fa-microphone':'fas fa-microphone-slash';
  }
}

// ── TOGGLE CAM ──
function callToggleCam(){
  if(!localStream)return;
  const t=localStream.getVideoTracks()[0];
  if(t){t.enabled=!t.enabled;
    document.getElementById('callToggleCam').classList.toggle('muted',!t.enabled);
    document.getElementById('callToggleCam').querySelector('i').className=t.enabled?'fas fa-video':'fas fa-video-slash';
  }
}

// ── SCREEN SHARE ──
function callToggleScreen(){
  var btn=document.getElementById('callToggleScreen');
  if(screenStream){
    screenStream.getTracks().forEach(function(t){t.stop();});
    screenStream=null;
    if(localStream){
      var camTrack=localStream.getVideoTracks()[0];
      if(camTrack&&pc){
        var sender=pc.getSenders().find(function(s){return s.track&&s.track.kind==='video';});
        if(sender)sender.replaceTrack(camTrack);
      }
    }
    btn.classList.remove('muted');
    btn.querySelector('i').className='fas fa-desktop';
    return;
  }
  navigator.mediaDevices.getDisplayMedia({video:true,audio:false}).then(function(stream){
    screenStream=stream;
    var screenTrack=stream.getVideoTracks()[0];
    if(screenTrack&&pc){
      var sender=pc.getSenders().find(function(s){return s.track&&s.track.kind==='video';});
      if(sender)sender.replaceTrack(screenTrack);
    }
    btn.classList.add('muted');
    btn.querySelector('i').className='fas fa-stop-circle';
    screenTrack.onended=function(){callToggleScreen();};
  }).catch(function(){});
}

// ── PICTURE-IN-PICTURE (floating bubble) ──
function callTogglePip(){
  if(callMinimized){expandCall();}else{minimizeCall();}
}

function minimizeCall(){
  callMinimized=true;
  document.getElementById('callOverlay').classList.remove('active');
  document.getElementById('callPip').classList.add('active');
  var pipVid=document.getElementById('pipVideo');
  var rv=document.getElementById('remoteVideo');
  if(rv&&rv.srcObject)pipVid.srcObject=rv.srcObject;
  pipVid.play().catch(function(){});
  document.getElementById('callTogglePip').querySelector('i').className='fas fa-expand';
  document.getElementById('callTogglePip').title='Expand';
}

function expandCall(){
  callMinimized=false;
  document.getElementById('callPip').classList.remove('active');
  document.getElementById('callOverlay').classList.add('active');
  document.getElementById('callTogglePip').querySelector('i').className='fas fa-compress';
  document.getElementById('callTogglePip').title='Picture-in-Picture';
  document.body.style.overflow='';
}

// ── INCOMING CALL HANDLING ──
function checkIncomingCalls(){
  if(pc||incomingCallerId)return;
  fetch('/chatx/call/poll/',{credentials:'same-origin'}).then(function(r){
    if(!r.ok)throw new Error('Incoming poll status '+r.status);
    return r.json();
  }).then(function(d){
    d.signals.forEach(function(s){
      if(s.type==='offer'&&!pc&&!incomingCallerId){
        incomingCallerId=s.caller_id;
        incomingOffer=s.data;
        const name=s.caller_name;
        try{
          const offer=JSON.parse(s.data);
          callIsVideo=offer&&offer.sdp&&offer.sdp.includes('m=video');
        }catch(e){callIsVideo=false;}
        document.getElementById('incomingName').textContent=name;
        document.getElementById('incomingLabel').textContent='Incoming '+(callIsVideo?'video':'voice')+' call...';
        const av=document.getElementById('incomingAvatar');
        av.style.backgroundImage=s.caller_avatar?'url(/api/shop/avatar/?user_id='+s.caller_id+')':'';
        av.textContent=s.caller_avatar?'':name[0].toUpperCase();
        document.getElementById('callIncoming').classList.add('active');
        incomingMissedTimeout=setTimeout(function(){
          if(incomingCallerId===s.caller_id){
            declineCall();
            showCallToast('Missed call from '+name);
          }
        },30000);
      }
      if(s.type==='ice'&&incomingCallerId&&s.caller_id===incomingCallerId&&!pc){
        try{pendingIceCandidates.push(JSON.parse(s.data));}catch(e){}
      }
    });
  }).catch(function(e){console.error('checkIncomingCalls',e);});
}
var _callInts=[setInterval(checkIncomingCalls,5000)];

function acceptCall(){
  document.getElementById('callIncoming').classList.remove('active');
  if(!incomingCallerId||!incomingOffer)return;
  if(incomingMissedTimeout){clearTimeout(incomingMissedTimeout);incomingMissedTimeout=null;}
  callPeerId=incomingCallerId;
  const name=document.getElementById('incomingName').textContent;
  document.getElementById('callName').textContent=name;
  document.getElementById('callStatus').textContent='Connecting...';
  const av=document.getElementById('callAvatar');
  av.style.backgroundImage=document.getElementById('incomingAvatar').style.backgroundImage;
  av.textContent=document.getElementById('incomingAvatar').textContent;
  document.getElementById('callOverlay').classList.add('active');
  document.getElementById('remoteVideo').style.display='none';
  const constraints={audio:true,video:callIsVideo};
  navigator.mediaDevices.getUserMedia(constraints).then(function(stream){
    localStream=stream;
    document.getElementById('localVideo').srcObject=stream;
    createPeerConnection();
    var parsedOffer;
    try{parsedOffer=JSON.parse(incomingOffer);}catch(e){
      showCallToast('Invalid offer data');
      endCall();
      return;
    }
    if(!parsedOffer||!parsedOffer.type){
      showCallToast('Invalid offer');
      endCall();
      return;
    }
    pc.setRemoteDescription(new RTCSessionDescription(parsedOffer)).then(function(){
      flushIceCandidates();
      return pc.createAnswer();
    }).then(function(answer){
      return pc.setLocalDescription(answer);
    }).then(function(){
      fetch('/chatx/call/signal/'+callPeerId+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken': getCSRFToken()},body:JSON.stringify({type:'answer',data:pc.localDescription.toJSON()})});
    }).catch(function(e){
      console.error('acceptCall SDP error',e);
      showCallToast('Connection failed');
      endCall();
    });
    callStartTime=Date.now();
    startPolling();
    startCallTimer();
    incomingCallerId=null;
    incomingOffer=null;
  }).catch(function(err){
    showCallToast('Could not access camera/microphone');
    endCall();
  });
}

function declineCall(){
  document.getElementById('callIncoming').classList.remove('active');
  if(incomingMissedTimeout){clearTimeout(incomingMissedTimeout);incomingMissedTimeout=null;}
  if(incomingCallerId){
    fetch('/chatx/call/signal/'+incomingCallerId+'/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken': getCSRFToken()},body:JSON.stringify({type:'end',data:''})}).catch(function(){});
  }
  incomingCallerId=null;
  incomingOffer=null;
  pendingIceCandidates=[];
}

// ── DRAGGABLE PIP ──
(function(){
  var pip=document.getElementById('callPip');
  if(!pip)return;
  var offsetX=0,offsetY=0,mouseX=0,mouseY=0;
  pip.addEventListener('mousedown',function(e){
    if(e.target.closest('button'))return;
    e.preventDefault();
    var rect=pip.getBoundingClientRect();
    offsetX=e.clientX-rect.left;
    offsetY=e.clientY-rect.top;
    pip.classList.add('dragging');
    function onMove(ev){
      var x=ev.clientX-offsetX;
      var y=ev.clientY-offsetY;
      x=Math.max(0,Math.min(x,window.innerWidth-pip.offsetWidth));
      y=Math.max(0,Math.min(y,window.innerHeight-pip.offsetHeight));
      pip.style.left=x+'px';
      pip.style.right='auto';
      pip.style.top=y+'px';
      pip.style.bottom='auto';
    }
    function onUp(){
      pip.classList.remove('dragging');
      document.removeEventListener('mousemove',onMove);
      document.removeEventListener('mouseup',onUp);
    }
    document.addEventListener('mousemove',onMove);
    document.addEventListener('mouseup',onUp);
  });
  pip.addEventListener('touchstart',function(e){
    if(e.target.closest('button'))return;
    var t=e.touches[0];
    var rect=pip.getBoundingClientRect();
    offsetX=t.clientX-rect.left;
    offsetY=t.clientY-rect.top;
    function onTouchMove(ev){
      var ct=ev.touches[0];
      var x=ct.clientX-offsetX;
      var y=ct.clientY-offsetY;
      x=Math.max(0,Math.min(x,window.innerWidth-pip.offsetWidth));
      y=Math.max(0,Math.min(y,window.innerHeight-pip.offsetHeight));
      pip.style.left=x+'px';
      pip.style.right='auto';
      pip.style.top=y+'px';
      pip.style.bottom='auto';
    }
    function onTouchEnd(){
      document.removeEventListener('touchmove',onTouchMove);
      document.removeEventListener('touchend',onTouchEnd);
    }
    document.addEventListener('touchmove',onTouchMove,{passive:true});
    document.addEventListener('touchend',onTouchEnd);
  },{passive:true});
})();

// ── BEFOREUNLOAD — warn if navigating away during active call ──
window.addEventListener('beforeunload',function(e){
  if(pc){
    e.preventDefault();
    e.returnValue='You have an active call. Are you sure you want to leave?';
  }
});

// ── SPA NAVIGATION — keep call alive across page changes ──
(function(){
  var app=document.getElementById('app');
  if(!app){
    // No #app container — create one wrapping body content
    // so SPA nav works on any page during an active call
    var children=[].slice.call(document.body.children);
    var wrapper=document.createElement('div');
    wrapper.id='app';
    for(var i=0;i<children.length;i++){
      var el=children[i];
      if(el.id==='callOverlay'||el.id==='callIncoming'||el.id==='callPip')continue;
      wrapper.appendChild(el);
    }
    document.body.insertBefore(wrapper,document.body.firstChild);
    app=wrapper;
  }
  var isNavigating=false;

  function isInternalLink(a){
    if(!a||!a.href)return false;
    if(a.target&&a.target!=='_self')return false;
    if(a.href.indexOf(location.origin)!==0)return false;
    if(a.href.indexOf('/admin/')!==-1)return false;
    if(a.pathname&&a.pathname.indexOf('/multiplayer-game/')!==-1)return false;
    return true;
  }

  function reRunScripts(container){
    var loaded={};
    var pageInts=[];
    var origSI=window.setInterval;
    // Re-wrap temporarily so intervals from re-run scripts are tracked separately
    window.setInterval=function(fn,ms){
      var id=origSI(fn,ms);
      pageInts.push(id);
      return id;
    };
    container.querySelectorAll('script').forEach(function(old){
      try {
        var neu=document.createElement('script');
        for(var i=0;i<old.attributes.length;i++){
          var a=old.attributes[i];
          if(a.name==='src')continue;
          neu.setAttribute(a.name,a.value);
        }
        if(old.src){
          if(loaded[old.src])return;
          loaded[old.src]=true;
          neu.src=old.src;
        }else{
          neu.textContent=old.textContent;
        }
        if(old.parentNode)old.parentNode.replaceChild(neu,old);
      }catch(e){
        console.error('Script re-run error',e);
      }
    });
    window.setInterval=origSI;
    return pageInts;
  }

  function mergeHead(doc,callback){
    var newHead=doc.querySelector('head');
    if(!newHead){callback();return;}
    var cur=document.head;
    var existing={};
    cur.querySelectorAll('link').forEach(function(l){
      var h=l.getAttribute('href');
      if(h)existing['link:'+h]=true;
    });
    cur.querySelectorAll('script[src]').forEach(function(s){
      var src=s.getAttribute('src');
      if(src)existing['script:'+src]=true;
    });
    var pending=0;
    var loaded=0;
    function onScriptLoad(){
      loaded++;
      if(loaded>=pending)callback();
    }
    // Add stylesheets not already present
    newHead.querySelectorAll('link[rel="stylesheet"]').forEach(function(link){
      var href=link.getAttribute('href');
      if(href&&!existing['link:'+href]){
        var el=document.createElement('link');
        el.rel='stylesheet';
        el.href=href;
        cur.appendChild(el);
        existing['link:'+href]=true;
      }
    });
    // Add inline styles not already present — FIRST so CSS is ready
    newHead.querySelectorAll('style').forEach(function(style){
      var txt=style.textContent;
      var dup=false;
      cur.querySelectorAll('style').forEach(function(s){
        if(s.textContent===txt)dup=true;
      });
      if(!dup){
        var el=document.createElement('style');
        el.textContent=txt;
        cur.appendChild(el);
      }
    });
    // Add scripts not already present (e.g. React, Babel CDN)
    newHead.querySelectorAll('script[src]').forEach(function(script){
      var src=script.getAttribute('src');
      if(src&&!existing['script:'+src]){
        pending++;
        var el=document.createElement('script');
        el.src=src;
        el.async=false; // ensure insertion order (React before ReactDOM before Babel)
        el.onload=onScriptLoad;
        el.onerror=onScriptLoad;
        cur.appendChild(el);
        existing['script:'+src]=true;
      }
    });
    // Update title
    var newTitle=newHead.querySelector('title');
    if(newTitle)document.title=newTitle.textContent;
    if(pending===0)callback();
  }

  var _pageInts=[];

  function clearPageIntervals(){
    // Clear initial page intervals (tracked before script.js loaded)
    if(window.__spaIntervalIds){
      window.__spaIntervalIds.forEach(function(id){
        if(_callInts.indexOf(id)<0)clearInterval(id);
      });
      window.__spaIntervalIds=[];
    }
    // Clear intervals from previous reRunScripts
    _pageInts.forEach(function(id){clearInterval(id);});
    _pageInts=[];
  }

  function navigateTo(url,push){
    if(isNavigating)return;
    if(!pc){location.href=url;return;}
    isNavigating=true;
    clearPageIntervals();
    fetch(url,{credentials:'same-origin',headers:{'X-Requested-With':'XMLHttpRequest'}}).then(function(r){
      if(!r.ok)throw new Error('Nav '+r.status);
      return r.text();
    }).then(function(html){
      var parser=new DOMParser();
      var doc=parser.parseFromString(html,'text/html');
      var newApp=doc.getElementById('app');
      if(!newApp){
        if(pc&&confirm('Navigating away will end your call. Continue?')){
          endCall();
          location.href=url;
        }else if(!pc){
          location.href=url;
        }else{
          isNavigating=false;
        }
        return;
      }
      // Merge head FIRST so CSS is ready before content appears
      mergeHead(doc,function(){
        app.innerHTML=newApp.innerHTML;
        if(push!==false)history.pushState({spa:true},'',url);
        window.scrollTo(0,0);
        try{_pageInts=reRunScripts(app)||[];}catch(e){console.error('Script re-run error',e);}
        isNavigating=false;
      });
      // Safety: fallback to full nav if mergeHead takes >8s
      setTimeout(function(){
        if(isNavigating){
          if(pc)endCall();
          location.href=url;
        }
      },8000);
    }).catch(function(e){
      console.error('SPA nav error',e);
      if(pc&&!confirm('Navigation failed but you have an active call. End call and reload?')){
        isNavigating=false;
        return;
      }
      if(pc)endCall();
      location.href=url;
    });
  }

  document.addEventListener('click',function(e){
    var a=e.target.closest('a');
    if(!a||!isInternalLink(a))return;
    if(a.closest('#callPip')||a.closest('#callOverlay')||a.closest('#callIncoming'))return;
    e.preventDefault();
    navigateTo(a.href);
  });

  window.addEventListener('popstate',function(e){
    if(pc&&e.state&&e.state.spa){navigateTo(location.href,false);}
  });
})();

}
