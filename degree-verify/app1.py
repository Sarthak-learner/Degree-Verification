"""
app.py — Degree Verification with separate University + Company dashboards
Credentials:
  University → admin / uni123
  Company    → company / corp123
"""
import hashlib, secrets
from flask import Flask, request, jsonify, render_template_string, session, redirect
from ai_monitor import detector   # ← AI anomaly detection

app = Flask(__name__)
app.secret_key = "degreechainFY2024"

# ── simple credentials (no DB needed for FY) ─────────────────────────────
USERS = {
    "admin":   {"password": "uni123",  "role": "university"},
    "company": {"password": "corp123", "role": "company"},
}

# ── blockchain boot ───────────────────────────────────────────────────────
from web3 import Web3
from solcx import compile_standard, install_solc

def boot():
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
    assert w3.is_connected(), "Start Ganache first: ganache --port 7545"
    install_solc("0.8.0")
    src = open("DegreeVerification.sol").read()
    out = compile_standard({
        "language":"Solidity",
        "sources":{"D.sol":{"content":src}},
        "settings":{"outputSelection":{"*":{"*":["abi","evm.bytecode"]}}},
    }, solc_version="0.8.0")
    d  = out["contracts"]["D.sol"]["DegreeVerification"]
    C  = w3.eth.contract(abi=d["abi"], bytecode=d["evm"]["bytecode"]["object"])
    rx = w3.eth.wait_for_transaction_receipt(C.constructor().transact({"from":w3.eth.accounts[0]}))
    ct = w3.eth.contract(address=rx.contractAddress, abi=d["abi"])
    print(f"✅ Contract: {rx.contractAddress}")
    return w3, ct, w3.eth.accounts[0]

W3, CONTRACT, OWNER = boot()

def pdf_hash(f):
    h = hashlib.sha256()
    while chunk := f.read(4096): h.update(chunk)
    return h.digest()

# ─────────────────────────────────────────────────────────────────────────
# SHARED STYLES (used across all pages)
# ─────────────────────────────────────────────────────────────────────────
_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#04080f;--s1:rgba(13,20,32,.85);--s2:rgba(18,26,40,.9);--a:#00d4aa;--b:#0099ff;--r:#f43f5e;--t:#e8f0fe;--m:#5a7090;--bd:rgba(255,255,255,.08)}

/* ── Animated background ── */
body{background:var(--bg);color:var(--t);font-family:'Syne',sans-serif;min-height:100vh;overflow-x:hidden}
#bg-canvas{position:fixed;inset:0;z-index:0;pointer-events:none}

/* ── Glassmorphism base ── */
.glass{background:rgba(13,20,32,.75);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:.5px solid rgba(255,255,255,.09)}

/* ── Nav ── */
nav{background:rgba(8,12,20,.8);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-bottom:.5px solid rgba(255,255,255,.07);padding:0 32px;display:flex;align-items:center;height:56px;position:sticky;top:0;z-index:100;animation:slideDown .5s ease both}
.nav-logo{display:flex;align-items:center;gap:10px;flex:1}
.nav-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px}
.nav-icon.u{background:linear-gradient(135deg,var(--a),var(--b))}
.nav-icon.c{background:linear-gradient(135deg,var(--b),#7c3aed)}
.nav-title{font-size:14px;font-weight:700}
.nav-badge{font-size:10px;font-family:'DM Mono',monospace;padding:2px 8px;border-radius:20px;margin-left:8px}
.nav-badge.u{background:rgba(0,212,170,.12);color:var(--a);border:.5px solid rgba(0,212,170,.25)}
.nav-badge.c{background:rgba(0,153,255,.12);color:var(--b);border:.5px solid rgba(0,153,255,.25)}
.nav-user{font-size:12px;font-family:'DM Mono',monospace;color:var(--m);margin-right:16px}
.nav-out{font-size:12px;font-family:'DM Mono',monospace;color:var(--r);text-decoration:none;padding:5px 12px;border:.5px solid rgba(244,63,94,.25);border-radius:6px;transition:all .2s}
.nav-out:hover{background:rgba(244,63,94,.1);border-color:rgba(244,63,94,.5)}

/* ── Wrap ── */
.wrap{max-width:900px;margin:0 auto;padding:32px 24px 60px;position:relative;z-index:1}

/* ── Hero ── */
.hero{margin-bottom:28px;animation:fadeUp .6s .1s ease both}
.hero-title{font-size:22px;font-weight:800;letter-spacing:-.8px;margin-bottom:4px}
.hero-sub{font-size:11px;color:var(--m);font-family:'DM Mono',monospace}

/* ── Steps banner ── */
.steps-banner{background:rgba(13,20,32,.7);backdrop-filter:blur(16px);border:.5px solid var(--bd);border-radius:14px;padding:20px 24px;margin-bottom:24px;display:flex;align-items:flex-start;animation:fadeUp .6s .2s ease both}
.stp{flex:1;display:flex;flex-direction:column;align-items:center;text-align:center;position:relative;padding:0 8px}
.stp:not(:last-child)::after{content:'→';position:absolute;right:-10px;top:12px;color:rgba(255,255,255,.12);font-size:14px}
.stp-num{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;font-family:'DM Mono',monospace;margin-bottom:8px;transition:transform .2s,box-shadow .2s}
.stp:hover .stp-num{transform:scale(1.15)}
.stp-num.u{background:rgba(0,212,170,.12);color:var(--a);border:.5px solid rgba(0,212,170,.3);box-shadow:0 0 12px rgba(0,212,170,.1)}
.stp-num.c{background:rgba(0,153,255,.12);color:var(--b);border:.5px solid rgba(0,153,255,.3);box-shadow:0 0 12px rgba(0,153,255,.1)}
.stp-label{font-size:11px;font-weight:700;margin-bottom:3px}
.stp-desc{font-size:10px;color:var(--m);font-family:'DM Mono',monospace;line-height:1.4}

/* ── Info box ── */
.info{background:rgba(0,212,170,.05);border:.5px solid rgba(0,212,170,.15);border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:12px;color:rgba(0,212,170,.85);font-family:'DM Mono',monospace;line-height:1.6;animation:fadeUp .6s .3s ease both}
.info.blue{background:rgba(0,153,255,.05);border-color:rgba(0,153,255,.15);color:rgba(100,180,255,.85)}

/* ── Cards ── */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:rgba(13,20,32,.75);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:.5px solid var(--bd);border-radius:16px;padding:24px;position:relative;overflow:hidden;transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;animation:fadeUp .6s ease both}
.card:nth-child(1){animation-delay:.15s}.card:nth-child(2){animation-delay:.25s}
.card:hover{transform:translateY(-4px);box-shadow:0 20px 60px rgba(0,0,0,.5);border-color:rgba(255,255,255,.14)}
/* shimmer on hover */
.card::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(255,255,255,.03),transparent 60%);opacity:0;transition:opacity .3s;pointer-events:none;border-radius:16px}
.card:hover::before{opacity:1}
/* top glow line */
.card::after{content:'';position:absolute;top:0;left:20px;right:20px;height:1px;transition:opacity .3s}
.ca::after{background:linear-gradient(90deg,transparent,var(--a),transparent)}
.cb::after{background:linear-gradient(90deg,transparent,var(--b),transparent)}
.cr2::after{background:linear-gradient(90deg,transparent,var(--r),transparent)}
.c-num{font-size:10px;font-family:'DM Mono',monospace;margin-bottom:8px;letter-spacing:1.5px;opacity:.7}
.ca .c-num{color:var(--a)}.cb .c-num{color:var(--b)}.cr2 .c-num{color:var(--r)}
.c-icon{width:42px;height:42px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:19px;margin-bottom:12px;transition:transform .2s}
.card:hover .c-icon{transform:scale(1.08)}
.ca .c-icon{background:rgba(0,212,170,.12);box-shadow:0 4px 16px rgba(0,212,170,.1)}
.cb .c-icon{background:rgba(0,153,255,.12);box-shadow:0 4px 16px rgba(0,153,255,.1)}
.cr2 .c-icon{background:rgba(244,63,94,.1);box-shadow:0 4px 16px rgba(244,63,94,.08)}
.ct{font-size:14px;font-weight:700;margin-bottom:4px}
.ca .ct{color:var(--a)}.cb .ct{color:var(--b)}.cr2 .ct{color:var(--r)}
.cd{font-size:11px;color:var(--m);margin-bottom:16px;font-family:'DM Mono',monospace;line-height:1.5}

/* ── Field ── */
.fld{margin-bottom:12px}
.fld label{display:block;font-size:10px;font-family:'DM Mono',monospace;color:var(--m);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.fld input{width:100%;background:rgba(18,26,40,.8);border:.5px solid var(--bd);border-radius:8px;padding:9px 12px;color:var(--t);font-family:'DM Mono',monospace;font-size:12px;outline:none;transition:border-color .2s,box-shadow .2s}
.fld input:focus{border-color:rgba(0,212,170,.5);box-shadow:0 0 0 3px rgba(0,212,170,.07)}
.fld input::placeholder{color:var(--m)}

/* ── Drop zone ── */
.drop{border:1.5px dashed rgba(255,255,255,.1);border-radius:10px;padding:18px 10px;text-align:center;cursor:pointer;transition:all .25s;position:relative;overflow:hidden;margin-bottom:12px;background:rgba(255,255,255,.01)}
.drop:hover,.drop.over{background:rgba(255,255,255,.03);transform:scale(1.01)}
.ca .drop:hover,.ca .drop.over{border-color:rgba(0,212,170,.4);box-shadow:0 0 20px rgba(0,212,170,.07)}
.cb .drop:hover,.cb .drop.over{border-color:rgba(0,153,255,.4);box-shadow:0 0 20px rgba(0,153,255,.07)}
.cr2 .drop:hover,.cr2 .drop.over{border-color:rgba(244,63,94,.35)}
.drop p{font-size:11px;color:var(--m);font-family:'DM Mono',monospace}
.fn{font-size:11px;margin-top:5px;font-family:'DM Mono',monospace;min-height:14px;transition:color .2s}
.ca .fn{color:var(--a)}.cb .fn{color:var(--b)}.cr2 .fn{color:var(--r)}
.drop input{position:absolute;inset:0;opacity:0;cursor:pointer}

/* ── Buttons ── */
.btn{width:100%;padding:11px;border:none;border-radius:10px;font-family:'Syne',sans-serif;font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.btn:hover{transform:translateY(-1px)}.btn:active{transform:scale(.98)}.btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn-a{background:linear-gradient(135deg,rgba(0,212,170,.22),rgba(0,212,170,.1));color:var(--a);border:.5px solid rgba(0,212,170,.35);box-shadow:0 4px 20px rgba(0,212,170,.1)}
.btn-a:hover{box-shadow:0 6px 28px rgba(0,212,170,.2)}
.btn-b{background:linear-gradient(135deg,rgba(0,153,255,.22),rgba(0,153,255,.1));color:var(--b);border:.5px solid rgba(0,153,255,.35);box-shadow:0 4px 20px rgba(0,153,255,.1)}
.btn-b:hover{box-shadow:0 6px 28px rgba(0,153,255,.2)}
.btn-r{background:linear-gradient(135deg,rgba(244,63,94,.18),rgba(244,63,94,.08));color:var(--r);border:.5px solid rgba(244,63,94,.35)}
.sp{display:none;width:13px;height:13px;border:2px solid rgba(255,255,255,.2);border-top-color:currentColor;border-radius:50%;animation:spin .6s linear infinite;margin:0 auto}
.btn.ld .bl{display:none}.btn.ld .sp{display:block}

/* ── Result ── */
.res{margin-top:12px;border-radius:10px;padding:13px 15px;font-family:'DM Mono',monospace;font-size:11px;display:none;animation:fadeUp .3s ease;line-height:1.7}
.ok{background:rgba(0,212,170,.08);border:.5px solid rgba(0,212,170,.25);color:var(--a)}
.fail{background:rgba(244,63,94,.08);border:.5px solid rgba(244,63,94,.25);color:#f87171}
.warn{background:rgba(251,191,36,.08);border:.5px solid rgba(251,191,36,.25);color:#fbbf24}
.ri{font-size:17px;margin-bottom:4px;display:block}
.rt{font-size:13px;font-weight:700;font-family:'Syne',sans-serif;margin-bottom:3px}
.rd{color:rgba(255,255,255,.28);word-break:break-all}

/* ── Animations ── */
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes slideDown{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}
@keyframes float{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-20px) scale(1.02)}}
</style>
<script>
// Animated particle canvas background
window.addEventListener('DOMContentLoaded',()=>{
  const c=document.getElementById('bg-canvas');
  if(!c)return;
  const ctx=c.getContext('2d');
  let W,H,pts=[];
  function resize(){W=c.width=window.innerWidth;H=c.height=window.innerHeight}
  resize();window.addEventListener('resize',resize);
  const COLORS=['rgba(0,212,170,','rgba(0,153,255,','rgba(124,58,237,'];
  for(let i=0;i<55;i++)pts.push({
    x:Math.random()*window.innerWidth,y:Math.random()*window.innerHeight,
    r:Math.random()*1.5+.3,vx:(Math.random()-.5)*.25,vy:(Math.random()-.5)*.25,
    c:COLORS[Math.floor(Math.random()*COLORS.length)],o:Math.random()*.4+.1
  });
  function draw(){
    ctx.clearRect(0,0,W,H);
    // draw blobs
    [[W*.2,H*.25,280,'rgba(0,212,170,',.045],[W*.75,H*.7,340,'rgba(0,153,255,',.04],[W*.5,H*.4,200,'rgba(124,58,237,',.035]].forEach(([x,y,r,cl,a])=>{
      const g=ctx.createRadialGradient(x,y,0,x,y,r);
      g.addColorStop(0,cl+a+')');g.addColorStop(1,'transparent');
      ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
    });
    // draw particles + connections
    pts.forEach((p,i)=>{
      p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle=p.c+p.o+')';ctx.fill();
      for(let j=i+1;j<pts.length;j++){
        const dx=pts[j].x-p.x,dy=pts[j].y-p.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d<120){ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(pts[j].x,pts[j].y);
          ctx.strokeStyle='rgba(255,255,255,'+(0.04*(1-d/120))+')';ctx.lineWidth=.4;ctx.stroke();}
      }
    });
    requestAnimationFrame(draw);
  }
  draw();
});
</script>"""

_JS = """<script>
function sfn(id,fn){const f=document.getElementById(id).files[0];document.getElementById(fn).textContent=f?f.name:'no file selected'}
function dov(e,el){e.preventDefault();el.classList.add('over')}
function dlv(el){el.classList.remove('over')}
function ddrop(e,fid,el,fnid){e.preventDefault();dlv(el);const f=e.dataTransfer.files[0];if(!f)return;const i=document.getElementById(fid);const d=new DataTransfer();d.items.add(f);i.files=d.files;document.getElementById(fnid).textContent=f.name}
function show(id,t,icon,title,detail){const el=document.getElementById(id);el.className='res '+t;el.style.display='block';el.innerHTML='<span class=ri>'+icon+'</span><div class=rt>'+title+'</div><div class=rd>'+detail+'</div>'}
async function go(url,fid,extra,rid,btn){
  const f=document.getElementById(fid).files[0];
  if(!f){show(rid,'fail','⚠','No file selected','Please choose a PDF file first.');return}
  const fd=new FormData();fd.append('pdf',f);
  for(const[k,v]of Object.entries(extra))fd.append(k,typeof v==='function'?v():v);
  btn.classList.add('ld');btn.disabled=true;
  try{
    const r=await fetch(url,{method:'POST',body:fd});const d=await r.json();const s=d.status||'';
    if(s.includes('issued'))show(rid,'ok','✅','Degree Registered!','Student ID: '+d.student_id+'\\nHash: '+d.hash+'\\nBlock #'+d.block+' on Ganache blockchain');
    else if(s.includes('revoked')&&url==='/revoke')show(rid,'warn','🚫','Degree Revoked','This certificate is now marked invalid on the blockchain.\\nHash: '+d.hash);
    else if(s.includes('verified'))show(rid,'ok','✅','Verified — Authentic','This certificate is genuine and registered on the blockchain.\\nHash: '+d.hash);
    else if(s.includes('revoked'))show(rid,'warn','⚠️','Certificate Revoked','This degree was revoked by the university. Do not accept.\\nHash: '+d.hash);
    else show(rid,'fail','❌',d.error||'Not Found / Invalid','This PDF is not registered or has been tampered with.\\nHash: '+(d.hash||'—'));
  }catch(e){show(rid,'fail','❌','Connection Error',e.message)}
  btn.classList.remove('ld');btn.disabled=false;
}
</script>"""

# ─────────────────────────────────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────────────────────────────────

LOGIN_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>DegreeChain — Login</title>""" + _CSS + """
<style>
body{display:flex;align-items:center;justify-content:center;padding:24px;flex-direction:column;gap:24px}
.how-it-works{width:100%;max-width:820px;background:rgba(13,20,32,.7);backdrop-filter:blur(20px);border:.5px solid var(--bd);border-radius:14px;padding:24px 28px;animation:fadeUp .6s ease both}
.how-title{font-size:10px;font-family:'DM Mono',monospace;color:var(--m);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:16px}
.flow{display:flex;align-items:flex-start;gap:0;flex-wrap:wrap}
.fstep{flex:1;min-width:120px;text-align:center;padding:0 8px;position:relative}
.fstep:not(:last-child)::after{content:'→';position:absolute;right:-10px;top:14px;color:var(--bd);font-size:14px}
.fstep-icon{font-size:20px;margin-bottom:6px}
.fstep-title{font-size:11px;font-weight:700;margin-bottom:3px}
.fstep-desc{font-size:10px;color:var(--m);font-family:'DM Mono',monospace;line-height:1.4}
.box{background:rgba(13,20,32,.8);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border:.5px solid rgba(255,255,255,.1);border-radius:18px;padding:36px;width:100%;max-width:420px;position:relative;z-index:1;animation:fadeUp .6s .1s ease both;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.logo{text-align:center;margin-bottom:24px}
.logo-icon{width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,#00d4aa,#0099ff);display:flex;align-items:center;justify-content:center;font-size:22px;margin:0 auto 10px;box-shadow:0 0 24px rgba(0,212,170,.3)}
h1{font-size:20px;font-weight:800;text-align:center;margin-bottom:3px}
.sub{font-size:11px;color:var(--m);text-align:center;font-family:'DM Mono',monospace;margin-bottom:6px}
.tagline{font-size:11px;color:rgba(0,212,170,.6);text-align:center;font-family:'DM Mono',monospace;margin-bottom:24px}
.roles{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}
.role{border:.5px solid var(--bd);border-radius:10px;padding:14px;text-align:center;cursor:pointer;transition:all .2s}
.role:hover{border-color:rgba(255,255,255,.15);background:rgba(255,255,255,.02)}
.role.active-uni{border-color:rgba(0,212,170,.4);background:rgba(0,212,170,.06)}
.role.active-comp{border-color:rgba(0,153,255,.4);background:rgba(0,153,255,.06)}
.role-icon{font-size:20px;margin-bottom:5px}
.role-name{font-size:12px;font-weight:700;margin-bottom:2px}
.role-can{font-size:10px;color:var(--m);font-family:'DM Mono',monospace}
.role.active-uni .role-can{color:var(--a)}
.role.active-comp .role-can{color:var(--b)}
.fld-l{display:block;font-size:10px;font-family:'DM Mono',monospace;color:var(--m);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.inp{width:100%;background:var(--s2);border:.5px solid var(--bd);border-radius:8px;padding:9px 12px;color:var(--t);font-family:'DM Mono',monospace;font-size:12px;outline:none;margin-bottom:12px;transition:border-color .2s}
.inp:focus{border-color:rgba(0,212,170,.4)}
.inp::placeholder{color:var(--m)}
.login-btn{width:100%;padding:11px;border:none;border-radius:9px;font-family:'Syne',sans-serif;font-size:14px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,#00d4aa,#0099ff);color:#080c14;transition:filter .2s}
.login-btn:hover{filter:brightness(1.08)}
.err{background:rgba(244,63,94,.1);border:.5px solid rgba(244,63,94,.3);border-radius:8px;padding:9px 12px;font-size:11px;color:#f87171;margin-bottom:12px;font-family:'DM Mono',monospace;display:none}
</style></head><body>
<canvas id="bg-canvas"></canvas>

<div class="how-it-works">
  <div class="how-title">// how degreechain works</div>
  <div class="flow">
    <div class="fstep"><div class="fstep-icon">🏛</div><div class="fstep-title">University Issues</div><div class="fstep-desc">Uploads degree PDF + student ID</div></div>
    <div class="fstep"><div class="fstep-icon">#️⃣</div><div class="fstep-title">SHA-256 Hash</div><div class="fstep-desc">PDF fingerprint computed</div></div>
    <div class="fstep"><div class="fstep-icon">⛓</div><div class="fstep-title">Stored On-Chain</div><div class="fstep-desc">Hash saved to blockchain permanently</div></div>
    <div class="fstep"><div class="fstep-icon">🏢</div><div class="fstep-title">Company Verifies</div><div class="fstep-desc">Uploads candidate's PDF</div></div>
    <div class="fstep"><div class="fstep-icon">🔍</div><div class="fstep-title">Hash Matched</div><div class="fstep-desc">System checks blockchain</div></div>
    <div class="fstep"><div class="fstep-icon">✅</div><div class="fstep-title">Result</div><div class="fstep-desc">Authentic or tampered — instant answer</div></div>
  </div>
</div>

<div class="box">
  <div class="logo">
    <div class="logo-icon">🎓</div>
    <h1>DegreeChain</h1>
    <p class="sub">// blockchain degree verification</p>
    <p class="tagline">Select your role and sign in below</p>
  </div>
  <div class="roles">
    <div class="role active-uni" id="r-uni" onclick="pick('uni')">
      <div class="role-icon">🏛</div>
      <div class="role-name">University</div>
      <div class="role-can">Issue &amp; Revoke degrees</div>
    </div>
    <div class="role" id="r-comp" onclick="pick('comp')">
      <div class="role-icon">🏢</div>
      <div class="role-name">Company</div>
      <div class="role-can">Verify certificates</div>
    </div>
  </div>
  <div class="err" id="err">{{ error }}</div>
  <form method="POST" action="/login">
    <input type="hidden" name="role" id="role-inp" value="uni">
    <label class="fld-l">Username</label>
    <input class="inp" type="text" name="username" placeholder="Enter username" autocomplete="off">
    <label class="fld-l">Password</label>
    <input class="inp" type="password" name="password" placeholder="••••••••">
    <button class="login-btn" type="submit">Sign In →</button>
  </form>
</div>
<script>
function pick(r){
  document.getElementById('role-inp').value=r;
  document.getElementById('r-uni').className='role'+(r==='uni'?' active-uni':'');
  document.getElementById('r-comp').className='role'+(r==='comp'?' active-comp':'');
}
{% if error %}document.getElementById('err').style.display='block';{% endif %}
</script></body></html>"""

UNI_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>University Dashboard — DegreeChain</title>""" + _CSS + """
</head><body>
<canvas id="bg-canvas"></canvas>
<nav>
  <div class="nav-logo">
    <div class="nav-icon u">🎓</div>
    <span class="nav-title">DegreeChain</span>
    <span class="nav-badge u">University Portal</span>
  </div>
  <span class="nav-user">🏛 admin</span>
  <a class="nav-out" href="/logout">Sign out</a>
</nav>
<div class="wrap">
  <div class="hero">
    <div class="hero-title">University Dashboard</div>
    <div class="hero-sub">// register and manage degree certificates on the blockchain</div>
  </div>

  <!-- Step guide -->
  <div class="steps-banner">
    <div class="stp">
      <div class="stp-num u">01</div>
      <div class="stp-label">Get the PDF</div>
      <div class="stp-desc">Have the student's degree certificate PDF ready on your computer</div>
    </div>
    <div class="stp">
      <div class="stp-num u">02</div>
      <div class="stp-label">Enter Student ID</div>
      <div class="stp-desc">Type the official student roll number or ID assigned by your institution</div>
    </div>
    <div class="stp">
      <div class="stp-num u">03</div>
      <div class="stp-label">Upload &amp; Register</div>
      <div class="stp-desc">Drop the PDF in the box and click Register — the SHA-256 hash gets stored on Ganache blockchain</div>
    </div>
    <div class="stp">
      <div class="stp-num u">04</div>
      <div class="stp-label">Done ✓</div>
      <div class="stp-desc">The certificate is now permanently verifiable by any employer worldwide</div>
    </div>
  </div>

  <div class="info">
    ℹ️ &nbsp;Only the cryptographic hash of the PDF is stored — no personal data ever touches the blockchain. Keep the original PDF safe; employers will need it to verify.
  </div>

  <div class="grid2">
    <!-- Issue -->
    <div class="card ca">
      <div class="c-num">STEP 01–03</div>
      <div class="c-icon">📄</div>
      <div class="ct">Issue a Degree</div>
      <div class="cd">Upload the degree PDF and enter the student's ID.<br>This permanently registers it on the blockchain.</div>
      <div class="drop" ondragover="dov(event,this)" ondragleave="dlv(this)" ondrop="ddrop(event,'fi',this,'fni')">
        <p>⬆ Drop PDF here or click to browse</p>
        <div class="fn ca" id="fni">no file selected</div>
        <input type="file" id="fi" accept=".pdf" onchange="sfn('fi','fni')">
      </div>
      <div class="fld">
        <label>Student ID — e.g. CS-2024-0042</label>
        <input type="text" id="sid" placeholder="Enter official student roll number">
      </div>
      <button class="btn btn-a" onclick="go('/issue','fi',{student_id:()=>sid.value},'ir',this)">
        <span class="bl">Register on Blockchain →</span><span class="sp"></span>
      </button>
      <div class="res" id="ir"></div>
    </div>

    <!-- Revoke -->
    <div class="card cr2">
      <div class="c-num">EMERGENCY USE</div>
      <div class="c-icon">🚫</div>
      <div class="ct">Revoke a Degree</div>
      <div class="cd">Use this only if a certificate was issued by mistake or fraud is detected. Revocation is permanent and visible to employers.</div>
      <div class="drop" ondragover="dov(event,this)" ondragleave="dlv(this)" ondrop="ddrop(event,'fr',this,'fnr')">
        <p>⛔ Drop the PDF to revoke</p>
        <div class="fn cr2" id="fnr">no file selected</div>
        <input type="file" id="fr" accept=".pdf" onchange="sfn('fr','fnr')">
      </div>
      <div class="info" style="background:rgba(244,63,94,.05);border-color:rgba(244,63,94,.15);color:rgba(244,63,94,.7);margin-bottom:12px">
        ⚠️ &nbsp;This action cannot be undone. The degree will appear as REVOKED to employers.
      </div>
      <button class="btn btn-r" onclick="go('/revoke','fr',{},'rr',this)">
        <span class="bl">Revoke Certificate →</span><span class="sp"></span>
      </button>
      <div class="res" id="rr"></div>
    </div>
  </div>
</div>
  <!-- AI Monitoring Panel -->
  <div class="card ca" style="margin-top:16px;animation-delay:.35s">
    <div class="c-num">AI LAYER — ISOLATION FOREST</div>
    <div class="c-icon">🤖</div>
    <div class="ct">AI Anomaly Monitor</div>
    <div class="cd">Unsupervised ML watches every verification attempt and flags suspicious patterns — bots, forgery attempts, off-hours spikes.</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
      <div style="background:rgba(0,212,170,.06);border:.5px solid rgba(0,212,170,.15);border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:20px;font-weight:800;color:#00d4aa" id="ai-total">—</div>
        <div style="font-size:10px;color:var(--m);font-family:'DM Mono',monospace;margin-top:3px">Total Verifications</div>
      </div>
      <div style="background:rgba(251,191,36,.06);border:.5px solid rgba(251,191,36,.15);border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:20px;font-weight:800;color:#fbbf24" id="ai-alerts">—</div>
        <div style="font-size:10px;color:var(--m);font-family:'DM Mono',monospace;margin-top:3px">Anomalies Flagged</div>
      </div>
      <div style="background:rgba(0,153,255,.06);border:.5px solid rgba(0,153,255,.15);border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:13px;font-weight:700;color:#4d9fff" id="ai-status">—</div>
        <div style="font-size:10px;color:var(--m);font-family:'DM Mono',monospace;margin-top:3px">Model Status</div>
      </div>
    </div>
    <div id="ai-log" style="font-size:11px;font-family:'DM Mono',monospace;color:var(--m);min-height:20px;line-height:1.8"></div>
    <button class="btn btn-a" style="margin-top:12px" onclick="loadAI()"><span class="bl">Refresh AI Stats ↻</span><span class="sp"></span></button>
  </div>
</div>
<script>
async function loadAI(){
  try{
    const r=await fetch('/ai/stats');const d=await r.json();
    document.getElementById('ai-total').textContent=d.total_verifications;
    document.getElementById('ai-alerts').textContent=d.total_alerts;
    document.getElementById('ai-status').textContent=d.model_trained?'✅ Trained':'⏳ Collecting data ('+d.training_samples+'/'+d.min_for_training+')';
    const log=document.getElementById('ai-log');
    if(d.recent_alerts&&d.recent_alerts.length){
      log.innerHTML='<div style="color:#fbbf24;margin-bottom:6px;font-weight:700">⚠ Recent Alerts:</div>'+
        d.recent_alerts.map(a=>`<div style="padding:4px 0;border-bottom:.5px solid rgba(255,255,255,.05)">🚨 ${a.time} · ${a.ip} · ${a.reason} · Risk: ${a.risk_score}%</div>`).join('');
    } else {
      log.innerHTML='<span style="color:#00d4aa">✅ No anomalies detected — all activity appears normal.</span>';
    }
  }catch(e){document.getElementById('ai-log').textContent='Could not load AI stats: '+e.message}
}
loadAI();
</script>
""" + _JS + """</body></html>""" = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Company Dashboard — DegreeChain</title>""" + _CSS + """
</head><body>
<canvas id="bg-canvas"></canvas>
<nav>
  <div class="nav-logo">
    <div class="nav-icon c">🏢</div>
    <span class="nav-title">DegreeChain</span>
    <span class="nav-badge c">Company Portal</span>
  </div>
  <span class="nav-user">🏢 company</span>
  <a class="nav-out" href="/logout">Sign out</a>
</nav>
<div class="wrap" style="max-width:680px">
  <div class="hero">
    <div class="hero-title">Verify a Degree Certificate</div>
    <div class="hero-sub">// instantly check if a candidate's certificate is genuine</div>
  </div>

  <!-- Step guide -->
  <div class="steps-banner">
    <div class="stp">
      <div class="stp-num c">01</div>
      <div class="stp-label">Get the PDF</div>
      <div class="stp-desc">Ask the candidate to send you their original degree certificate PDF</div>
    </div>
    <div class="stp">
      <div class="stp-num c">02</div>
      <div class="stp-label">Upload it here</div>
      <div class="stp-desc">Drop or browse the PDF in the box below — no account needed for this step</div>
    </div>
    <div class="stp">
      <div class="stp-num c">03</div>
      <div class="stp-label">Click Verify</div>
      <div class="stp-desc">The system computes a SHA-256 hash and checks it against the blockchain</div>
    </div>
    <div class="stp">
      <div class="stp-num c">04</div>
      <div class="stp-label">Read the result</div>
      <div class="stp-desc">✅ Authentic · ⚠️ Revoked · ❌ Not found or tampered</div>
    </div>
  </div>

  <div class="info blue">
    ℹ️ &nbsp;The PDF is never uploaded to any server — only its hash is computed and checked. Your candidate's document stays private.
  </div>

  <div class="card cb">
    <div class="c-num">VERIFICATION TOOL</div>
    <div class="c-icon">🔍</div>
    <div class="ct">Certificate Authenticity Check</div>
    <div class="cd">Upload the exact PDF the candidate gave you. If even one character was changed, the hash will differ and verification will fail.</div>
    <div class="drop" ondragover="dov(event,this)" ondragleave="dlv(this)" ondrop="ddrop(event,'fv',this,'fnv')">
      <p>🔍 Drop PDF here or click to browse</p>
      <div class="fn cb" id="fnv">no file selected</div>
      <input type="file" id="fv" accept=".pdf" onchange="sfn('fv','fnv')">
    </div>
    <button class="btn btn-b" onclick="go('/verify','fv',{},'vr',this)">
      <span class="bl">Verify Certificate →</span><span class="sp"></span>
    </button>
    <div class="res" id="vr"></div>
  </div>

  <!-- What results mean -->
  <div class="card" style="margin-top:16px;background:var(--s1)">
    <div class="c-num" style="color:var(--m)">UNDERSTANDING RESULTS</div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:12px">
      <div style="background:rgba(0,212,170,.06);border:.5px solid rgba(0,212,170,.15);border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:20px;margin-bottom:6px">✅</div>
        <div style="font-size:11px;font-weight:700;color:#00d4aa;margin-bottom:3px">Verified</div>
        <div style="font-size:10px;color:var(--m);font-family:'DM Mono',monospace;line-height:1.4">Certificate is genuine and registered on the blockchain by the university</div>
      </div>
      <div style="background:rgba(251,191,36,.06);border:.5px solid rgba(251,191,36,.15);border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:20px;margin-bottom:6px">⚠️</div>
        <div style="font-size:11px;font-weight:700;color:#fbbf24;margin-bottom:3px">Revoked</div>
        <div style="font-size:10px;color:var(--m);font-family:'DM Mono',monospace;line-height:1.4">Certificate was issued but later revoked by the university — do not accept</div>
      </div>
      <div style="background:rgba(244,63,94,.06);border:.5px solid rgba(244,63,94,.15);border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:20px;margin-bottom:6px">❌</div>
        <div style="font-size:11px;font-weight:700;color:#f87171;margin-bottom:3px">Invalid</div>
        <div style="font-size:10px;color:var(--m);font-family:'DM Mono',monospace;line-height:1.4">Not found on blockchain — either fake, tampered, or from an unregistered institution</div>
      </div>
    </div>
  </div>
</div>
""" + _JS + """</body></html>"""

# ─────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "role" not in session: return redirect("/login")
    return redirect("/university" if session["role"]=="university" else "/company")

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        r = request.form.get("role","uni")
        user = USERS.get(u)
        expected_role = "university" if r=="uni" else "company"
        if user and user["password"]==p and user["role"]==expected_role:
            session["user"] = u
            session["role"] = user["role"]
            return redirect("/university" if user["role"]=="university" else "/company")
        error = "Invalid credentials or wrong role selected."
    return render_template_string(LOGIN_PAGE, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/university")
def university():
    if session.get("role") != "university": return redirect("/login")
    return UNI_PAGE

@app.route("/company")
def company():
    if session.get("role") != "company": return redirect("/login")
    return COMP_PAGE

@app.route("/issue", methods=["POST"])
def issue():
    if session.get("role") != "university": return jsonify(error="Unauthorised"), 403
    if "pdf" not in request.files or not request.form.get("student_id"):
        return jsonify(error="Send pdf + student_id"), 400
    h = pdf_hash(request.files["pdf"])
    sid = request.form["student_id"].strip()
    try:
        tx = CONTRACT.functions.issueDegree(h, sid).transact({"from": OWNER})
        r  = W3.eth.wait_for_transaction_receipt(tx)
        return jsonify(status="issued", student_id=sid, hash=h.hex(), block=r.blockNumber)
    except Exception as e:
        msg = str(e)
        return jsonify(error="Already registered" if "Already" in msg else msg), 409

@app.route("/verify", methods=["POST"])
def verify():
    if "role" not in session: return jsonify(error="Unauthorised"), 403
    if "pdf" not in request.files: return jsonify(error="Send pdf"), 400
    h = pdf_hash(request.files["pdf"])
    valid, rev = CONTRACT.functions.verifyDegree(h).call()

    # ── AI: log this verification and check for anomaly ──
    result_str = "verified" if valid else ("revoked" if rev else "invalid")
    ip         = request.remote_addr or "unknown"
    ai_result  = detector.log_verification(ip, result_str)

    if rev:   return jsonify(status="revoked",  hash=h.hex(), valid=False,  ai=ai_result)
    if valid: return jsonify(status="verified", hash=h.hex(), valid=True,   ai=ai_result)
    return    jsonify(status="invalid",  hash=h.hex(), valid=False, ai=ai_result), 404

@app.route("/revoke", methods=["POST"])
def revoke():
    if session.get("role") != "university": return jsonify(error="Unauthorised"), 403
    if "pdf" not in request.files: return jsonify(error="Send pdf"), 400
    h = pdf_hash(request.files["pdf"])
    try:
        tx = CONTRACT.functions.revokeDegree(h).transact({"from": OWNER})
        W3.eth.wait_for_transaction_receipt(tx)
        return jsonify(status="revoked", hash=h.hex())
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route("/ai/stats")
def ai_stats():
    if session.get("role") != "university": return jsonify(error="Unauthorised"), 403
    return jsonify(detector.get_stats())

if __name__ == "__main__":
    print("\n🎓  Open http://127.0.0.1:5000\n")
    app.run(port=5000, debug=False)
