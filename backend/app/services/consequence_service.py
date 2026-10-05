HEADLINES = {
    "SAFE": "This transfer matches your normal activity.",
    "CAUTION": "This transfer has some unusual characteristics.",
    "VERIFY": "This transfer needs extra verification.",
    "HIGH_RISK": "This transfer is high risk.",
    "CRITICAL": "This transfer shows strong signs of fraud.",
}

# (text found in a reason, what it means for the customer)
CONSEQUENCES = [
    ("fraud watchlist", "The recipient account is flagged as high-risk. Completed transfers to flagged accounts are very hard to recover."),
    ("watchlisted", "The recipient account has been reported before. If this is a scam, the money may not be recoverable."),
    ("far above", "This amount is far above your usual range. If you didn't intend it, your balance will drop sharply and the funds may be unrecoverable."),
    ("somewhat above", "This amount is higher than you normally send, so your available balance will drop noticeably."),
    ("unrecognised device", "This device and location are new to your account. If someone else is using your account, the transfer goes out under your name."),
    ("new device", "This device or location is new to your account. Make sure it is really you making this transfer."),
    ("never paid before", "Large transfers to first-time recipients are the most common scam pattern. Confirm the account name and number with the recipient."),
    ("first transaction to this recipient", "You have never paid this recipient before. Double-check the account details, because transfers cannot easily be reversed."),
    ("high number of transactions", "Many transfers in a short time can indicate account takeover. Check your recent activity."),
    ("unusual time", "This is outside the hours you normally transact."),
    ("nearly all of the account balance", "This transfer uses almost your entire balance, leaving you little available for other needs."),
    ("proceeded despite", "You chose to continue after a recipient risk warning, so any loss may be harder to dispute."),
]


def build_consequence(level: str, reasons: list) -> dict:
    level = (level or "SAFE").upper()
    consequences = []
    for reason in reasons or []:
        low = reason.lower()
        for key, text in CONSEQUENCES:
            if key in low and text not in consequences:
                consequences.append(text)
                break
    if level == "SAFE":
        consequences = []
    return {
        "headline": HEADLINES.get(level, HEADLINES["SAFE"]),
        "scenario": reasons or ["No anomalies detected. This transfer matches your established behaviour."],
        "consequences": consequences,
    }