import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

from audit import prepare, finalize, unknown
from finance import cost_for, timing_view, RATE_TYPES
from rbi_list import load_list
from tinyfish_client import USAGE

st.set_page_config(page_title="TrustLens", page_icon="🔍", layout="wide")

st.title("🔍 TrustLens")
st.caption("Check a loan app or offer before you share your documents. "
           "Live web evidence + RBI's public directory.")

EXAMPLES = {
    "Custom": ("", "", ""),
    "Listed app (GeM Sahay)": ("GeM Sahay", "", "Instant loan in 2 days, apply now!"),
    "Suspicious offer": ("FastCashNow99", "",
                         "Get a loan in 2 days, no documents needed! Pay Rs 999 processing fee first. Urgent, limited time!"),
}
ICON = {"good": "✅", "warn": "⚠️", "bad": "🔴", "unknown": "❔"}
TIMEOUT_SECONDS = 150

with st.sidebar:
    st.header("The offer")
    choice = st.selectbox("Load an example", list(EXAMPLES.keys()))
    ex = EXAMPLES[choice]
    app_name = st.text_input("Loan app or lender name", value=ex[0], key=f"a{choice}")
    website = st.text_input("Lender website (optional)", value=ex[1], key=f"w{choice}")
    message = st.text_area("Paste the message or ad (optional)", value=ex[2],
                           height=130, key=f"m{choice}")
    with st.expander("Cost details (optional)", expanded=True):
        amount = st.number_input("Loan amount (₹)", 1000, 5000000, 50000, 1000)
        months = st.slider("Tenure (months)", 3, 60, 12)
        quoted = st.number_input("Rate you were quoted (0 = don't know)", 0.0, 100.0, 0.0, 0.5)
        rate_type = st.selectbox("The quoted rate is", RATE_TYPES)
        fee_pct = st.number_input("Processing fee (% of amount)", 0.0, 20.0, 0.0, 0.5)
    use_research = st.checkbox("Include deep Research report (slower)", value=True)
    go = st.button("🔎 Audit this offer", type="primary", use_container_width=True)
    st.info("🔒 TrustLens never asks for your PAN, Aadhaar, CIBIL score or bank details.")
    try:
        st.caption(f"RBI list: {len(load_list())} entries (downloaded snapshot)")
    except Exception:
        st.caption("RBI list not loaded")


def show_card(slot, c):
    with slot.container(border=True):
        st.markdown(f"**{ICON.get(c['status'], '❔')} {c['name']}**  ·  `{c['tool']}`  ·  "
                    f"score effect: **{c['points']:+d}**")
        st.write(c["summary"])
        for s in c["sources"][:5]:
            st.markdown(f"- [{str(s['title'])[:80]}]({s['url']})")


def find(checks, name):
    for c in checks:
        if c["name"] == name:
            return c
    return None


if go and app_name.strip():
    plan = prepare(app_name.strip(), website.strip(), message.strip(), use_research)
    checks = list(plan["instant"])
    jobs = plan["jobs"]

    st.subheader("Agents at work")
    slots = {}
    for c in plan["instant"]:
        slots[c["name"]] = st.empty()
        show_card(slots[c["name"]], c)
    for name in jobs:
        slots[name] = st.empty()
        slots[name].info(f"⏳ **{name}**: agent running...")

    pool = ThreadPoolExecutor(max_workers=max(1, len(jobs)))
    futures = {pool.submit(fn): name for name, fn in jobs.items()}
    done_names = set()
    try:
        for f in as_completed(futures, timeout=TIMEOUT_SECONDS):
            name = futures[f]
            try:
                c = f.result()
            except Exception as e:
                c = unknown(name, "TinyFish", f"Check failed: {str(e)[:100]}")
            checks.append(c)
            done_names.add(name)
            show_card(slots[name], c)
    except FuturesTimeout:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    for name in jobs:
        if name not in done_names:
            c = unknown(name, "TinyFish", "Timed out. Skipped so the audit could finish.")
            checks.append(c)
            show_card(slots[name], c)

    result = finalize(checks)
    score = result["score"]

    st.divider()
    c1, c2 = st.columns([1, 2])
    c1.metric("Trust score", f"{score}/100")
    c1.progress(score / 100)
    c2.subheader(result["verdict"])
    c2.caption("Based on the public sources we checked. Not proof either way. "
               "Information only, not financial advice.")

    # ---------- COST ----------
    st.subheader("Cost: what you would really pay")
    if quoted > 0:
        k = cost_for(amount, months, quoted, rate_type, fee_pct)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Monthly EMI", f"₹{k['emi']:,.0f}")
        m2.metric("Total repayment", f"₹{k['total']:,.0f}")
        m3.metric("Extra paid over what you get", f"₹{k['extra_cost']:,.0f}")
        m4.metric("Effective yearly rate", f"{k['apr']:.1f}%")
        st.caption(f"You borrow ₹{amount:,.0f}, pay a fee of ₹{k['fee']:,.0f}, and receive "
                   f"₹{k['received']:,.0f}. Quoted: {quoted}% ({rate_type.lower()}). "
                   "GST and other charges are not included.")
    else:
        rows = []
        for label, r in (("Best case", 14.0), ("Typical", 24.0), ("Worst case", 36.0)):
            k = cost_for(amount, months, r, RATE_TYPES[0], fee_pct)
            rows.append({"Scenario": label, "Assumed rate": f"{r:.0f}% per year",
                         "EMI": f"₹{k['emi']:,.0f}",
                         "Total repayment": f"₹{k['total']:,.0f}"})
        st.table(rows)
        st.caption("These rates are assumed examples, not the lender's rates. "
                   "Your real rate depends on your credit profile, which we never access. "
                   "Enter the quoted rate in the sidebar for an exact figure.")

    # ---------- TIMING ----------
    st.subheader("Timing: claimed vs. reported")
    msg_c = find(checks, "Message red flags")
    fee_c = find(checks, "Fees & privacy")
    rep_c = find(checks, "Reputation (Search)")
    claimed = (msg_c or {}).get("data", {}).get("claimed_speed")
    stated = (fee_c or {}).get("data", {}).get("disbursal_time_stated")
    snippets = (rep_c or {}).get("data", {}).get("snippets", [])
    t = timing_view(claimed, stated, snippets)
    st.markdown(f"- **The message claims:** {t['claimed']}")
    st.markdown(f"- **The lender's own pages say:** {t['lender']}")
    if t["reviews"]:
        st.markdown("- **Search results mention timing:**")
        for h in t["reviews"]:
            st.markdown(f"  - _{h}_")
    else:
        st.markdown("- **Search results:** no clear timing reports found.")
    st.caption("Treat fast-money claims with care, especially with an upfront fee. "
               "Approval and payout time depends on the lender's checks.")

    with st.expander("How the trust score is calculated"):
        st.write("Starts at 50. " + " ".join(
            f"{c['name']}: {c['points']:+d}." for c in result["checks"]))

    st.subheader("What to do next")
    st.markdown(
        "- Never pay a fee before a loan is approved and the agreement is in writing.\n"
        "- Never share OTPs, PINs or passwords.\n"
        "- Ask the lender for the name of its regulated bank or NBFC, and check it on RBI's website.\n"
        "- Be careful with apps that ask for your contacts or gallery.")

    st.caption("TinyFish usage so far: " +
               " · ".join(f"{k.title()} {v}" for k, v in USAGE.items() if v))
elif go:
    st.warning("Enter an app name first.")
else:
    st.info("👈 Pick an example or enter an app name, then press **Audit this offer**.")