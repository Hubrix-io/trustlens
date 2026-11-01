import streamlit as st
from audit import run_audit
from rbi_list import load_list
from tinyfish_client import USAGE

st.set_page_config(page_title="TrustLens", page_icon="🔍", layout="wide")

st.title("🔍 TrustLens")
st.caption("Check a loan app or offer before you share your documents. "
           "Live web evidence + RBI's public directory. We never ask for PAN, Aadhaar or bank details.")

EXAMPLES = {
    "Custom": ("", "", ""),
    "Listed app (GeM Sahay)": ("GeM Sahay", "", "Instant loan in 2 days, apply now!"),
    "Suspicious offer": ("FastCashNow99", "",
                         "Get a loan in 2 days, no documents needed! Pay Rs 999 processing fee first. Urgent, limited time!"),
}

with st.sidebar:
    st.header("The offer")
    choice = st.selectbox("Load an example", list(EXAMPLES.keys()))
    ex = EXAMPLES[choice]
    app_name = st.text_input("Loan app or lender name", value=ex[0], key=f"a{choice}")
    website = st.text_input("Lender website (optional)", value=ex[1], key=f"w{choice}")
    message = st.text_area("Paste the message or ad (optional)", value=ex[2],
                           height=140, key=f"m{choice}")
    go = st.button("🔎 Audit this offer", type="primary", use_container_width=True)
    try:
        st.caption(f"RBI list: {len(load_list())} entries (downloaded snapshot)")
    except Exception:
        st.caption("RBI list not loaded")

if go and app_name.strip():
    with st.status("Agents are checking live sources...", expanded=True) as status:
        st.write("📂 Checking the RBI directory list")
        st.write("🌐 TinyFish Agent reading the lender's website")
        st.write("🔎 TinyFish Search looking for reputation and complaints")
        st.write("💬 Scanning the message for scam patterns")
        result = run_audit(app_name.strip(), website.strip(), message.strip())
        status.update(label="Audit complete", state="complete", expanded=False)

    score = result["score"]
    c1, c2 = st.columns([1, 2])
    c1.metric("Trust score", f"{score}/100")
    c1.progress(score / 100)
    c2.subheader(result["verdict"])
    c2.caption("Based on the public sources we checked. Not proof either way. "
               "Information only, not financial advice.")

    st.subheader("What we found")
    icon = {"good": "✅", "warn": "⚠️", "bad": "🔴", "unknown": "❔"}
    for c in result["checks"]:
        with st.container(border=True):
            st.markdown(f"**{icon.get(c['status'], '❔')} {c['name']}**  ·  "
                        f"`{c['tool']}`  ·  score effect: **{c['points']:+d}**")
            st.write(c["summary"])
            for s in c["sources"][:5]:
                st.markdown(f"- [{s['title'][:80]}]({s['url']})")

    with st.expander("How the score is calculated"):
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
    st.warning("Enter an app or lender name first.")
else:
    st.info("👈 Pick an example or enter an app name, then press **Audit this offer**.")