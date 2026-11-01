import re

# phrase -> (label, risk points)
RED_FLAGS = {
    r"no documents? (needed|required)|without documents?": ("Claims no documents needed", 15),
    r"guaranteed (approval|loan)|100% approval": ("Guaranteed approval claim", 20),
    r"(pay|deposit|send).{0,25}(fee|charges?|amount|advance)|processing fee first|registration fee": ("Asks for an upfront fee", 30),
    r"urgent|limited time|last chance|expires (today|soon)|act now": ("Pressure or urgency wording", 10),
    r"no (cibil|credit) (check|score)|bad (cibil|credit) accepted": ("Claims no credit check", 15),
    r"(share|send).{0,20}(otp|pin|password|cvv)": ("Asks for OTP, PIN or password", 40),
    r"whatsapp|telegram": ("Uses a chat app for the offer", 10),
    r"(in|within) (\d+|one|two|few) (minutes?|hours?|days?)": ("Promises very fast money", 5),
}


def analyze_message(text):
    found = []
    risk = 0
    low = text.lower()
    for pattern, (label, pts) in RED_FLAGS.items():
        m = re.search(pattern, low)
        if m:
            found.append({"flag": label, "match": text[m.start():m.end()], "points": pts})
            risk += pts

    speed = re.search(r"(in|within) (\d+|one|two|few) (minutes?|hours?|days?)", low)
    amount = re.search(r"(rs\.?|₹|inr)\s?([\d,]+)", low)
    return {
        "red_flags": found,
        "risk_points": min(risk, 100),
        "claimed_speed": speed.group(0) if speed else None,
        "amount_mentioned": amount.group(0) if amount else None,
    }