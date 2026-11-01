import math

import pandas as pd
import streamlit as st

from message_check import analyze_message
from finance import cost_for, RATE_TYPES
from rbi_list import search_rbi_list

st.set_page_config(page_title="TrustLens", page_icon="🔍", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container { max-width: 1000px; padding-top: 2rem; }
[data-testid="stMetric"] { background: rgba(128,128,128,0.15); padding:14px; border-radius:12px; }

/* ---------- open / page-change animations ---------- */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(26px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes popIn {
  from { opacity: 0; transform: scale(0.94); }
  to   { opacity: 1; transform: scale(1); }
}
.block-container h1 { animation: fadeUp .6s ease-out both; }
.block-container h3, .block-container h2 { animation: fadeUp .6s ease-out .1s both; }

/* the two home cards slide up one after the other */
[data-testid="stColumn"]:nth-child(1) [data-testid="stVerticalBlockBorderWrapper"] {
  animation: fadeUp .7s ease-out .25s both;
}
[data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"] {
  animation: fadeUp .7s ease-out .45s both;
}

/* cards lift when you hover */
[data-testid="stVerticalBlockBorderWrapper"] {
  transition: transform .25s ease, box-shadow .25s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 28px rgba(0,0,0,0.25);
}

[data-testid="stMetric"] { animation: popIn .5s ease-out both; }
/* ---------- techy animated buttons ---------- */
@keyframes btnGlow {
  0%,100% { box-shadow: 0 0 8px rgba(34,197,94,.35), 0 0 0 0 rgba(34,197,94,.45); }
  50%     { box-shadow: 0 0 20px rgba(34,197,94,.75), 0 0 0 7px rgba(34,197,94,0); }
}
@keyframes btnFlow {
  from { background-position: 0% 50%; }
  to   { background-position: 300% 50%; }
}
@keyframes btnShimmer {
  from { transform: translateX(-130%) skewX(-20deg); }
  to   { transform: translateX(330%) skewX(-20deg); }
}

.stButton > button, .stDownloadButton > button {
  position: relative; overflow: hidden;
  border-radius: 10px; font-weight: 600; letter-spacing: .3px;
  transition: transform .18s ease, box-shadow .25s ease,
              border-color .25s ease, background-color .25s ease;
}

/* primary buttons: flowing gradient + pulsing glow + light sweep */
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(120deg,#16a34a,#22c55e,#06b6d4,#22c55e,#16a34a) !important;
  background-size: 300% 100% !important;
  border: none !important;
  animation: btnFlow 6s linear infinite, btnGlow 2.8s ease-in-out infinite;
}
[data-testid="stBaseButton-primary"] p { color: #04130a !important; }
[data-testid="stBaseButton-primary"]::after {
  content: ""; position: absolute; top: 0; left: 0; width: 35%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.5), transparent);
  transform: translateX(-130%) skewX(-20deg);
  animation: btnShimmer 3.5s ease-in-out infinite;
  pointer-events: none;
}
[data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-3px) scale(1.04);
  box-shadow: 0 0 26px rgba(34,197,94,.9), 0 8px 22px rgba(0,0,0,.4);
}

/* secondary buttons (like Back to home): outlined, glow on hover */
[data-testid="stBaseButton-secondary"] {
  background: rgba(34,197,94,.06) !important;
  border: 1px solid rgba(34,197,94,.45) !important;
}
[data-testid="stBaseButton-secondary"]:hover {
  background: rgba(34,197,94,.16) !important;
  border-color: #22c55e !important;
  transform: translateY(-2px);
  box-shadow: 0 0 18px rgba(34,197,94,.55), inset 0 0 12px rgba(34,197,94,.2);
}

/* press effect for every button */
.stButton > button:active, .stDownloadButton > button:active {
  transform: scale(.95) !important;
  box-shadow: 0 0 6px rgba(34,197,94,.9) !important;
}

/* tabs */
button[data-baseweb="tab"] { transition: color .2s ease, transform .2s ease, text-shadow .2s ease; }
button[data-baseweb="tab"]:hover { transform: translateY(-2px); text-shadow: 0 0 10px rgba(34,197,94,.8); }
[data-baseweb="tab-highlight"] {
  background: linear-gradient(90deg,#22c55e,#06b6d4) !important;
  box-shadow: 0 0 12px rgba(34,197,94,.9);
}

/* input boxes glow when you click into them */
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
[data-baseweb="select"]:focus-within {
  box-shadow: 0 0 0 1px #22c55e, 0 0 16px rgba(34,197,94,.45) !important;
  border-color: #22c55e !important;
  transition: box-shadow .25s ease;
}

/* ---------- POP-OUT BUTTONS ---------- */
@keyframes ringPulse {
  0%   { box-shadow: 0 6px 0 #0b7a35, 0 10px 22px rgba(0,0,0,.45), 0 0 0 0 rgba(34,197,94,.65); }
  70%  { box-shadow: 0 6px 0 #0b7a35, 0 10px 22px rgba(0,0,0,.45), 0 0 0 16px rgba(34,197,94,0); }
  100% { box-shadow: 0 6px 0 #0b7a35, 0 10px 22px rgba(0,0,0,.45), 0 0 0 0 rgba(34,197,94,0); }
}
@keyframes floaty {
  0%,100% { translate: 0 0; }
  50%     { translate: 0 -4px; }
}

/* every primary button: bigger, 3D, pulsing neon ring */
[data-testid="stBaseButton-primary"] {
  min-height: 3.1rem;
  padding: .7rem 1.6rem !important;
  font-size: 1.05rem !important;
  font-weight: 800 !important;
  border-radius: 14px !important;
  border: 2px solid rgba(255,255,255,.35) !important;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 0 6px 0 #0b7a35, 0 10px 22px rgba(0,0,0,.45);
  animation: btnFlow 5s linear infinite, ringPulse 2.2s ease-out infinite, floaty 3.2s ease-in-out infinite;
}
[data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-5px) scale(1.06) !important;
  box-shadow: 0 10px 0 #0b7a35, 0 0 34px rgba(34,197,94,.95), 0 16px 30px rgba(0,0,0,.5) !important;
  filter: brightness(1.12);
}
[data-testid="stBaseButton-primary"]:active {
  transform: translateY(5px) scale(.97) !important;
  box-shadow: 0 1px 0 #0b7a35, 0 0 14px rgba(34,197,94,.9) !important;
}

/* the two big home buttons: extra large */
.st-key-h1 button, .st-key-h2 button, .st-key-s1 button, .st-key-s2 button {
  min-height: 4.4rem !important;
  font-size: 1.3rem !important;
  border-radius: 18px !important;
  letter-spacing: 1.5px;
}

/* EMI menu: the two tool buttons fly in from opposite sides, then float */
@keyframes slideInL { from {opacity:0; transform:translateX(-70px);} to {opacity:1; transform:none;} }
@keyframes slideInR { from {opacity:0; transform:translateX(70px);}  to {opacity:1; transform:none;} }
.st-key-s1 { animation: slideInL .8s cubic-bezier(.2,.9,.3,1.2) .35s both; }
.st-key-s2 { animation: slideInR .8s cubic-bezier(.2,.9,.3,1.2) .55s both; }
.st-key-s2 button { animation-delay: 0s, .6s, 1.2s !important; }

/* secondary buttons (Back to home): neon outline that fills on hover */
[data-testid="stBaseButton-secondary"] {
  min-height: 2.7rem;
  padding: .5rem 1.3rem !important;
  font-weight: 700 !important;
  border-radius: 12px !important;
  border: 2px solid #22c55e !important;
  box-shadow: 0 0 12px rgba(34,197,94,.35), inset 0 0 10px rgba(34,197,94,.12);
}
[data-testid="stBaseButton-secondary"]:hover {
  background: linear-gradient(120deg,#16a34a,#22c55e) !important;
  transform: translateY(-3px) scale(1.05) !important;
  box-shadow: 0 0 28px rgba(34,197,94,.9), 0 8px 18px rgba(0,0,0,.4) !important;
}
[data-testid="stBaseButton-secondary"]:hover p { color: #04130a !important; }
[data-testid="stBaseButton-secondary"]:active { transform: scale(.96) !important; }

/* respect people who turned animations off in their OS */
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "home"


def go(page):
    st.session_state.page = page
    st.session_state.pop("meter_prev", None)   # meter rises from empty when a page opens


def back_button(target="home", label="← Back to home"):
    st.button(label, on_click=go, args=(target,))
    
def risk_gauge(score, size=220):
    """Full-circle animated gauge. score is 0-100."""
    score = max(0, min(100, int(score)))
    r = 80
    circ = 2 * 3.14159265 * r                  # circumference of the ring
    offset = circ * (1 - score / 100)          # where the arc should stop
    if score >= 30:
        color, label = "#ef4444", "HIGH RISK"
    elif score > 0:
        color, label = "#f59e0b", "SUSPICIOUS"
    else:
        color, label = "#22c55e", "NO FLAGS"

    # note: no blank lines or indented lines in this string (Markdown would break it)
    return (
        "<style>"
        "@property --n{syntax:'<integer>';inherits:false;initial-value:0;}"
        f"@keyframes fillring{{from{{stroke-dashoffset:{circ:.2f};}}}}"
        "@keyframes countup{from{--n:0;}}"
        ".gauge{position:relative;display:flex;justify-content:center;}"
        ".gauge-center{position:absolute;top:0;left:0;right:0;bottom:0;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;}"
        ".g-num{font-size:3rem;font-weight:700;line-height:1;"
        f"--n:{score};counter-reset:n var(--n);animation:countup 1.6s ease-out;color:{color};}}"
        ".g-num::after{content:counter(n);}"
        ".g-sub{font-size:.8rem;opacity:.7;margin-top:2px;}"
        ".g-label{font-size:.85rem;font-weight:700;letter-spacing:1px;margin-top:6px;"
        f"color:{color};}}"
        "</style>"
        f"<div class='gauge' style='width:{size}px;height:{size}px;margin:auto;'>"
        f"<svg viewBox='0 0 200 200' width='{size}' height='{size}' style='transform:rotate(-90deg);'>"
        f"<circle cx='100' cy='100' r='{r}' fill='none' stroke='rgba(128,128,128,0.25)' stroke-width='16'/>"
        f"<circle cx='100' cy='100' r='{r}' fill='none' stroke='{color}' stroke-width='16' "
        f"stroke-linecap='round' stroke-dasharray='{circ:.2f}' stroke-dashoffset='{offset:.2f}' "
        "style='animation:fillring 1.6s ease-out;'/>"
        "</svg>"
        "<div class='gauge-center'>"
        "<div class='g-num'></div>"
        "<div class='g-sub'>out of 100</div>"
        f"<div class='g-label'>{label}</div>"
        "</div></div>"
    )
def splash():
    """Logo screen that shows for ~2 seconds when the site first opens."""
    st.markdown(
"""<style>
@keyframes splashOut { 0%,65% {opacity:1; visibility:visible;} 100% {opacity:0; visibility:hidden;} }
@keyframes ringSpin { to { transform: rotate(360deg); } }
@keyframes logoPulse { 0%,100% {transform:scale(1);} 50% {transform:scale(1.12);} }
@keyframes textIn { from {opacity:0; transform:translateY(12px);} to {opacity:1; transform:none;} }
.splash { position:fixed; top:0; left:0; right:0; bottom:0; z-index:999999;
display:flex; flex-direction:column; align-items:center; justify-content:center;
background:#0e1117; animation:splashOut 2.2s ease forwards; }
.splash-ring { width:96px; height:96px; border-radius:50%;
border:6px solid rgba(255,255,255,0.12); border-top-color:#22c55e;
animation:ringSpin 1s linear infinite; display:flex; align-items:center; justify-content:center; }
.splash-logo { font-size:2.2rem; animation:logoPulse 1.2s ease-in-out infinite; }
.splash-title { color:#fff; font-size:2rem; font-weight:700; margin-top:22px;
animation:textIn .8s ease-out .2s both; }
.splash-sub { color:#9ca3af; margin-top:6px; animation:textIn .8s ease-out .5s both; }
</style>
<div class="splash">
<div class="splash-ring"><div class="splash-logo">🔍</div></div>
<div class="splash-title">TrustLens</div>
<div class="splash-sub">Checking loans, protecting you...</div>
</div>""",
        unsafe_allow_html=True,
    )
    
def background():
    """Techy animated background: moving grid, glowing orbs, scan line, rising particles."""
    particles = "".join(
        f"<span class='bg-p' style='left:{(i * 37) % 100}%;"
        f"animation-duration:{9 + (i * 5) % 11}s;animation-delay:-{(i * 3) % 12}s;'></span>"
        for i in range(16)
    )
    st.markdown(
"""<style>
@keyframes gridMove { from {background-position:0 0,0 0;} to {background-position:48px 48px,48px 48px;} }
@keyframes drift1 { 0%,100% {transform:translate(0,0) scale(1);} 50% {transform:translate(10vw,8vh) scale(1.25);} }
@keyframes drift2 { 0%,100% {transform:translate(0,0) scale(1.1);} 50% {transform:translate(-12vw,-6vh) scale(0.9);} }
@keyframes drift3 { 0%,100% {transform:translate(0,0);} 50% {transform:translate(6vw,-10vh);} }
@keyframes scan { from {top:-12%;} to {top:112%;} }
@keyframes riseUp { 0% {transform:translateY(0);opacity:0;} 10% {opacity:.9;} 90% {opacity:.9;} 100% {transform:translateY(-110vh);opacity:0;} }
.stApp { background:#070b14; }
[data-testid="stHeader"] { background:transparent; }
.block-container { position:relative; z-index:1; }
.bg-layer { position:fixed; top:0; left:0; right:0; bottom:0; z-index:0; pointer-events:none; overflow:hidden; }
.bg-grid { position:absolute; top:0; left:0; right:0; bottom:0;
background-image:linear-gradient(rgba(34,197,94,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(34,197,94,.08) 1px,transparent 1px);
background-size:48px 48px; animation:gridMove 5s linear infinite;
-webkit-mask-image:radial-gradient(ellipse at center,#000 30%,transparent 85%);
mask-image:radial-gradient(ellipse at center,#000 30%,transparent 85%); }
.bg-orb { position:absolute; border-radius:50%; filter:blur(70px); opacity:.35; }
.bg-orb.o1 { width:38vw; height:38vw; left:-8vw; top:-10vh; background:radial-gradient(circle,#22c55e,transparent 70%); animation:drift1 16s ease-in-out infinite; }
.bg-orb.o2 { width:34vw; height:34vw; right:-6vw; top:25vh; background:radial-gradient(circle,#3b82f6,transparent 70%); animation:drift2 20s ease-in-out infinite; }
.bg-orb.o3 { width:28vw; height:28vw; left:30vw; bottom:-14vh; background:radial-gradient(circle,#a855f7,transparent 70%); animation:drift3 24s ease-in-out infinite; }
.bg-scan { position:absolute; left:0; right:0; height:90px;
background:linear-gradient(to bottom,transparent,rgba(34,197,94,.10),transparent); animation:scan 7s linear infinite; }
.bg-p { position:absolute; bottom:-10px; width:3px; height:3px; border-radius:50%;
background:#22c55e; box-shadow:0 0 8px 2px rgba(34,197,94,.7); animation:riseUp 12s linear infinite; }
@media (prefers-reduced-motion: reduce) { .bg-layer * { animation:none !important; } }
</style>
<div class="bg-layer"><div class="bg-grid"></div><div class="bg-orb o1"></div><div class="bg-orb o2"></div><div class="bg-orb o3"></div><div class="bg-scan"></div>"""
        + particles + "</div>",
        unsafe_allow_html=True,
    )
    


# ======================= HOME =======================
def page_home():
    st.title("🔍 TrustLens")
    st.subheader("What would you like to do?")
    st.write("")
    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            st.markdown("### 🛡️ Check a message")
            st.write("Got a loan SMS, WhatsApp or ad? Paste it and find out "
                     "if it looks like spam or a scam.")
            st.button("Check message", key="h1", type="primary",
                      use_container_width=True, on_click=go, args=("message",))

    with c2:
        with st.container(border=True):
            st.markdown("### 💰 EMI & compare loan apps")
            st.write("Calculate your EMI and compare the real cost of loans "
                     "from different apps side by side.")
            st.button("Calculate & compare", key="h2", type="primary",
                      use_container_width=True, on_click=go, args=("emi_hub",))

    st.write("")
    st.info("🔒 TrustLens never asks for your PAN, Aadhaar, CIBIL score or bank details.")


# ======================= PAGE 1: MESSAGE CHECK =======================
def page_message():
    back_button()
    st.title("🛡️ Is this message spam?")
    text = st.text_area("Paste the SMS, WhatsApp message or ad here", height=180,
                        placeholder="e.g. Get a loan in 2 days, no documents needed! Pay Rs 999 fee first.")

    if st.button("Check message", type="primary"):
        if not text.strip():
            st.warning("Paste a message first.")
            return

        r = analyze_message(text)
        risk = r["risk_points"]

        if risk >= 30:
            verdict = "🔴 Very likely spam or a scam. Do not reply, pay or share anything."
        elif risk > 0:
            verdict = "🟡 Suspicious. Verify the sender before doing anything."
        else:
            verdict = "🟢 No common scam phrases found in this message. This does not prove it is safe."

        c1, c2 = st.columns([1, 2])
        c1.markdown(risk_gauge(risk), unsafe_allow_html=True)
        c2.subheader(verdict)
        c2.caption(f"Risk score: {risk}/100")

        if r["red_flags"]:
            st.markdown("**Red flags found:**")
            for f in r["red_flags"]:
                st.markdown(f"- 🚩 **{f['flag']}**: matched _“{f['match']}”_")
        if r["claimed_speed"]:
            st.markdown(f"**Speed claimed:** {r['claimed_speed']}")
        if r["amount_mentioned"]:
            st.markdown(f"**Amount mentioned:** {r['amount_mentioned']}")

        st.caption("Rule-based check on common scam phrases. Not proof either way.")
        st.markdown("**What to do:**\n"
                    "- Never pay a fee before the loan is approved and in writing.\n"
                    "- Never share OTPs, PINs or passwords.\n"
                    "- Check the lender on RBI's website.")

# ======================= EMI & COMPARE MENU =======================
def page_emi_hub():
    back_button()
    st.title("💰 EMI & compare loan apps")
    st.subheader("Pick a tool")
    st.write("")
    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            st.markdown("### 🧮 EMI calculator")
            st.write("Enter amount, rate and tenure to see your monthly EMI, "
                     "total repayment and the real yearly cost.")
            st.button("Open EMI calculator", key="s1", type="primary",
                      use_container_width=True, on_click=go, args=("calc",))

    with c2:
        with st.container(border=True):
            st.markdown("### 🏦 Compare loan apps")
            st.write("Fetch live data from lenders and compare EMI, RBI status, "
                     "privacy flags and more side by side.")
            st.button("Compare loan apps", key="s2", type="primary",
                      use_container_width=True, on_click=go, args=("compare",))


LOAN_MIN, LOAN_MAX = 1000, 5000000
METER_H = 280          # tube height in px
# labelled marks on the meter (log scale, so small and large loans both show up)
METER_TICKS = [(1000, "₹1K"), (10000, "₹10K"), (100000, "₹1L"),
               (1000000, "₹10L"), (5000000, "₹50L")]


def _meter_frac(v):
    """0..1 position on the meter. Log scale: ₹1K at the bottom, ₹50L at the top."""
    v = max(LOAN_MIN, min(LOAN_MAX, v))
    return math.log(v / LOAN_MIN) / math.log(LOAN_MAX / LOAN_MIN)


def loan_meter(amount):
    """Vertical strength-meter style gauge for the loan amount.
    The fill rises from its previous level to the new one every time the amount changes."""
    new = _meter_frac(amount) * 100
    old = st.session_state.get("meter_prev", 0.0)     # 0 on first open: rises from the bottom
    st.session_state["meter_prev"] = new
    uid = f"{int(old * 10)}_{int(new * 10)}"           # new keyframe name per change replays the animation
    hot = new >= 90

    ticks = "".join(
        f"<div class='m-tick' style='bottom:{_meter_frac(v) * 100:.1f}%'><span>{lab}</span><i></i></div>"
        for v, lab in METER_TICKS)

    return (
        "<style>"
        f"@keyframes mfill{uid}{{from{{height:{old:.2f}%;}}to{{height:{new:.2f}%;}}}}"
        f"@keyframes mtag{uid}{{from{{bottom:{old:.2f}%;}}to{{bottom:{new:.2f}%;}}}}"
        "@keyframes mstripe{from{background-position:0 0;}to{background-position:0 -40px;}}"
        "@keyframes mglow{0%,100%{box-shadow:0 0 14px rgba(34,197,94,.35),inset 0 0 12px rgba(0,0,0,.6);}"
        "50%{box-shadow:0 0 28px rgba(34,197,94,.8),inset 0 0 12px rgba(0,0,0,.6);}}"
        "@keyframes mhot{0%,100%{box-shadow:0 0 18px rgba(239,68,68,.5),inset 0 0 12px rgba(0,0,0,.6);}"
        "50%{box-shadow:0 0 42px rgba(239,68,68,1),inset 0 0 12px rgba(0,0,0,.6);}}"
        "@keyframes mpulse{0%,100%{transform:scaleY(1);opacity:.9;}50%{transform:scaleY(2.2);opacity:1;}}"
        "@keyframes mpop{0%{transform:scale(.6);opacity:0;}70%{transform:scale(1.15);opacity:1;}100%{transform:scale(1);}}"
        f".m-wrap{{position:relative;height:{METER_H + 40}px;width:100%;max-width:230px;margin:auto;padding-top:20px;}}"
        f".m-tube{{position:absolute;left:58px;top:20px;width:56px;height:{METER_H}px;border-radius:28px;"
        "background:rgba(255,255,255,.05);border:3px solid rgba(255,255,255,.28);overflow:hidden;"
        f"animation:{'mhot' if hot else 'mglow'} {'.7s' if hot else '2.6s'} ease-in-out infinite;}}"
        f".m-fill{{position:absolute;left:0;right:0;bottom:0;height:{new:.2f}%;"
        f"background:linear-gradient(to top,#22c55e 0%,#84cc16 35%,#f59e0b 65%,#ef4444 100%);"
        f"background-size:100% {METER_H}px;background-position:bottom;"
        f"animation:mfill{uid} 1.4s cubic-bezier(.34,1.45,.5,1) both;}}"
        ".m-fill::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;"
        "background:repeating-linear-gradient(to top,rgba(255,255,255,.22) 0 8px,transparent 8px 20px);"
        "background-size:100% 40px;animation:mstripe 1.2s linear infinite;}"
        ".m-fill::after{content:'';position:absolute;left:0;right:0;top:0;height:5px;"
        "background:#fff;box-shadow:0 0 14px 4px rgba(255,255,255,.9);animation:mpulse 1.1s ease-in-out infinite;}"
        ".m-tick{position:absolute;left:0;width:54px;height:0;display:flex;align-items:center;"
        "justify-content:flex-end;gap:4px;font-size:.7rem;opacity:.75;white-space:nowrap;}"
        ".m-tick i{display:block;width:8px;height:2px;background:rgba(255,255,255,.55);}"
        f".m-ticks{{position:absolute;left:0;top:20px;height:{METER_H}px;width:54px;}}"
        f".m-tagbox{{position:absolute;left:120px;top:20px;height:{METER_H}px;width:110px;}}"
        f".m-tag{{position:absolute;left:0;height:0;display:flex;align-items:center;bottom:{new:.2f}%;"
        f"animation:mtag{uid} 1.4s cubic-bezier(.34,1.45,.5,1) both;}}"
        ".m-tag b{display:inline-block;margin-left:2px;padding:3px 9px;border-radius:8px;font-size:.85rem;"
        "background:#22c55e;color:#04130a;white-space:nowrap;transform:translateY(0);"
        "animation:mpop .6s ease-out .9s both;}"
        ".m-tag::before{content:'';border:7px solid transparent;border-right-color:#22c55e;margin-right:-2px;}"
        "</style>"
        "<div class='m-wrap'>"
        f"<div class='m-ticks'>{ticks}</div>"
        f"<div class='m-tube'><div class='m-fill'></div></div>"
        f"<div class='m-tagbox'><div class='m-tag'><b>₹{amount:,.0f}</b></div></div>"
        "</div>"
    )


def _loan_inputs():
    meter_col, input_col = st.columns([1, 2])
    with input_col:
        st.write("")
        amount = st.number_input("Loan amount (₹)", LOAN_MIN, LOAN_MAX, 50000, 1000)
        months = st.slider("Tenure (months)", 3, 60, 12)
    with meter_col:
        st.markdown(loan_meter(amount), unsafe_allow_html=True)
    return amount, months


# ======================= PAGE 2a: EMI CALCULATOR =======================
def page_calc():
    back_button("emi_hub", "← Back to EMI & compare")
    st.title("🧮 EMI calculator")
    amount, months = _loan_inputs()

    c1, c2, c3 = st.columns(3)
    rate = c1.number_input("Interest rate (%)", 0.0, 100.0, 18.0, 0.5)
    rtype = c2.selectbox("Rate type", RATE_TYPES)
    fee = c3.number_input("Processing fee (% of amount)", 0.0, 20.0, 0.0, 0.5)
    k = cost_for(amount, months, rate, rtype, fee)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Monthly EMI", f"₹{k['emi']:,.0f}")
    m2.metric("Total repayment", f"₹{k['total']:,.0f}")
    m3.metric("Extra paid over what you get", f"₹{k['extra_cost']:,.0f}")
    m4.metric("Effective yearly rate", f"{k['apr']:.1f}%")
    st.caption(f"You borrow ₹{amount:,.0f}, pay a fee of ₹{k['fee']:,.0f} and "
               f"receive ₹{k['received']:,.0f}. GST and other charges not included.")


# ======================= PAGE 2b: COMPARE LOAN APPS =======================
def page_compare():
    back_button("emi_hub", "← Back to EMI & compare")
    st.title("🏦 Compare loan apps")
    amount, months = _loan_inputs()

    st.write("Fetches each lender's pages live with TinyFish every time you press the button.")

    if st.button("🌐 Fetch live data & compare", type="primary", key="cmp_btn"):
        from lenders import fetch_all_lenders, recommend
        with st.spinner("Fetching all lenders in parallel (this can take a minute)..."):
            results = fetch_all_lenders()

        # average of the rates that were actually found on the lenders' pages
        found_rates = [d["rate_avg"] for d in results if d["rate_avg"]]
        market_avg = round(sum(found_rates) / len(found_rates), 1) if found_rates else None

        if market_avg:
            st.metric("Average rate across lenders (from fetched pages)", f"{market_avg}%")
        else:
            st.warning("No interest rate was found on any lender's pages, so EMIs cannot be estimated. "
                       "Add each lender's personal-loan page URL in lenders.py.")

        rows = []
        for d in results:
            if d["rate_avg"]:
                rate, source = d["rate_avg"], "Average of rates on its pages"
            elif market_avg:
                rate, source = market_avg, "Average of all lenders"
            else:
                rate, source = None, "No rate found"

            if rate:
                k = cost_for(amount, months, rate, RATE_TYPES[0], d["fee_pct"] or 0.0)
                emi, total = round(k["emi"]), round(k["total"])
            else:
                emi, total = None, None
            label, why = recommend(d, rate, market_avg)

            rows.append({
                "Lender": d["name"],
                "Recommendation": label,
                "Why": why,
                "Type": d["kind"],
                "Rate used (%)": rate,
                "Rate source": source,
                "Monthly EMI (₹)": emi,
                "Total repayment (₹)": total,
                "PAN needed?": d["pan"],
                "RBI status": d["rbi"],
                "Privacy flags": len(d["privacy_flags"]) if d["privacy_scanned"] else "Not scanned",
                "Fetched": "✅" if d["fetched"] else "🔴",
            })
        st.dataframe(pd.DataFrame(rows).sort_values("Monthly EMI (₹)", na_position="last"),
                     use_container_width=True, hide_index=True)
        
        best = [r for r in rows if r["Recommendation"].startswith("✅") and r["Monthly EMI (₹)"]]
        if best:
            top = min(best, key=lambda r: r["Monthly EMI (₹)"])
            st.success(f"Best pick from this check: **{top['Lender']}** "
                       f"(EMI ₹{top['Monthly EMI (₹)']:,}). {top['Why']}.")
        else:
            st.info("No lender cleared every check this time. Read the details below before choosing.")

        st.subheader("Details per lender")

        st.subheader("Details per lender")
        for d in results:
            with st.expander(f"{d['name']}  ·  {d['rbi']}"):
                if not d["fetched"]:
                    st.error(f"Could not fetch: {d['error'] or 'unknown error'}")
                st.markdown(f"**PAN:** {d['pan']}")
                if d["pan_evidence"]:
                    st.caption(f"Page said: “{d['pan_evidence']}”")
                if d["rate_avg"]:
                    st.markdown(f"**Interest rates on page:** {d['rate_min']}% to {d['rate_max']}% "
                                f"(average {d['rate_avg']}%)")
                if d["fee_pct"] is not None:
                    st.markdown(f"**Processing fee on page:** {d['fee_pct']}%")
                if not d["privacy_scanned"]:
                    st.warning("No privacy policy text in the fetched pages. Add the privacy-policy URL in lenders.py.")
                elif d["privacy_flags"]:
                    st.markdown("**Privacy flags:**")
                    for f in d["privacy_flags"]:
                        st.markdown(f"- ⚠️ {f}")
                else:
                    st.markdown("**Privacy flags:** none found in the fetched text")
                for u in d["urls"]:
                    st.markdown(f"- Source: {u}")

        st.caption("Keyword scan of public pages, not a legal review. 'In RBI DLA list' means the "
                   "app is declared by a regulated entity. It is not an RBI approval of the app. "
                   "Rates are averages of percentages found near interest wording on the pages. "
                   "Your real rate depends on your profile.")


# ======================= ROUTER =======================


background()

if "splash_done" not in st.session_state:
    st.session_state.splash_done = True
    splash()

{"home": page_home, "message": page_message, "emi_hub": page_emi_hub,
 "calc": page_calc, "compare": page_compare}[st.session_state.page]()