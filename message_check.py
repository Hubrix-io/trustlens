import re

# pattern -> (label, risk points). \s* lets it survive typos like "need ed"
RED_FLAGS = {
    r"\bno\s*documents?\s*(need\s*ed|required|req)|without\s*(any\s*)?documents?|no\s*paperwork|no\s*document\s*verification":
        ("Claims no documents needed", 25),
    r"guaranteed\s*(approval|loan)|100%\s*approval|sure\s*approval":
        ("Guaranteed approval claim", 20),
    r"(pay|deposit|send).{0,25}(fee|charges?|amount|advance)|processing\s*fee\s*first|registration\s*fee":
        ("Asks for an upfront fee", 30),
    r"urgent|limited\s*time|last\s*chance|expires\s*(today|soon)|act\s*now|hurry":
        ("Pressure or urgency wording", 10),
    r"no\s*(cibil|credit)\s*(check|score)|bad\s*(cibil|credit)\s*accepted|without\s*(cibil|credit)":
        ("Claims no credit check", 15),
    r"(share|send).{0,20}(otp|pin|password|cvv)":
        ("Asks for OTP, PIN or password", 40),
    r"whatsapp|telegram":
        ("Uses a chat app for the offer", 10),
    r"\b(in|within)\s*(\d+|one|two|few)\s*(minutes?|mins?|hours?|hrs?|days?)":
        ("Promises very fast money", 10),
    r"instant\s*(loan|cash|approval)|pre-?approved":
        ("Instant or pre-approved loan claim", 10),
    r"bit\.ly|tinyurl|t\.me/|wa\.me/|click\s*(the\s*)?link":
        ("Pushes a link", 10),
}


def analyze_message(text):
    found, risk = [], 0
    low = " ".join(text.lower().split())   # lowercase + collapse spaces

    for pattern, (label, pts) in RED_FLAGS.items():
        m = re.search(pattern, low)
        if m:
            found.append({"flag": label, "match": m.group(0), "points": pts})
            risk += pts

    labels = {f["flag"] for f in found}
    if "Claims no documents needed" in labels and "Promises very fast money" in labels:
        found.append({"flag": "Fast money with no documents (classic scam combo)",
                      "match": "", "points": 10})
        risk += 10

    speed = re.search(r"\b(in|within)\s*(\d+|one|two|few)\s*(minutes?|mins?|hours?|hrs?|days?)", low)
    amount = re.search(r"(rs\.?|₹|inr)\s?([\d,]+)", low)
    return {
        "red_flags": found,
        "risk_points": min(risk, 100),
        "claimed_speed": speed.group(0) if speed else None,
        "amount_mentioned": amount.group(0) if amount else None,
    }