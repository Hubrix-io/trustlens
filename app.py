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
.stButton > button { transition: transform .15s ease; }
.stButton > button:hover { transform: scale(1.03); }

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


def back_button():
    st.button("← Back to home", on_click=go, args=("home",))
    
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
                      use_container_width=True, on_click=go, args=("emi",))

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

# ======================= PAGE 2: EMI + COMPARE =======================
def page_emi():
    back_button()
    st.title("💰 EMI calculator & loan app comparison")

    a, b = st.columns(2)
    amount = a.number_input("Loan amount (₹)", 1000, 5000000, 50000, 1000)
    months = b.slider("Tenure (months)", 3, 60, 12)

    tab_calc, tab_cmp = st.tabs(["🧮 EMI calculator", "🏦 Live lender comparison"])

    # ---- calculator ----
    with tab_calc:
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

       # ---- live lender comparison ----
    with tab_cmp:
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

{"home": page_home, "message": page_message, "emi": page_emi}[st.session_state.page]()