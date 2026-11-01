# TrustLens
Check a loan app or offer before you share your documents.

## What it does
Enter an app name (and optionally paste the offer message). TrustLens checks:
1. **RBI DLA directory** (downloaded public list) for the app and its regulated lender
2. **Lender's own website** via a TinyFish Agent (does it list the app? grievance contact?)
3. **Reputation** via TinyFish Search (complaint-type results, with links)
4. **Message red flags** (upfront fee, "no documents", urgency)

It then shows a trust score with every reason and source.

## TinyFish usage
- **Search**: reputation sources
- **Agent**: reads the lender's website and finds evidence
- A live usage counter is shown in the app

## Privacy
Never asks for PAN, Aadhaar, CIBIL or bank details.

## Limits
Not found in the RBI list is not proof of fraud. Scores come from public
sources and rules, and are not financial advice. The RBI list is a downloaded snapshot.

## Run
pip install -r requirements.txt
Create a .env file with TINYFISH_API_KEY=your-key (see .env.example)
streamlit run app.py
