import requests
import pandas as pd
import os
import random

DATA_FILE = "comments_data.csv"
GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS", "").split(",")
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS if k.strip()]
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_API_URL = "https://graph.facebook.com"

print("[INFO] GEMINI_API_KEYS loaded:", bool(GEMINI_API_KEYS))
print("[INFO] INSTAGRAM_ACCESS_TOKEN loaded:", bool(INSTAGRAM_ACCESS_TOKEN))

def get_gemini_reply(user_comment):
    print(f"[INFO] Generating Gemini reply for comment: {user_comment}")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"You are a witty, human-sounding Instagram creator. "
                            f"Reply naturally and politely to this comment: '{user_comment}'. "
                            "Your reply should sound like a real human wrote it, match the tone of the comment, "
                            "and be short (under 10 words), kind, and emotionally intelligent. "
                            "Do not give multiple options or explanations. Just return the final reply text only."
                        )
                    }
                ]
            }
        ]
    }
    # Choose a random Gemini API key for each request
    if not GEMINI_API_KEYS:
        print("[ERROR] No Gemini API keys provided!")
        return "Thank you for your comment! 🙏"
    gemini_key = random.choice(GEMINI_API_KEYS)
    params = {"key": gemini_key}
    response = requests.post(url, headers=headers, params=params, json=payload)
    print("[DEBUG] Gemini API response status:", response.status_code)
    if response.status_code == 200:
        result = response.json()
        print(f"[DEBUG] Gemini API result: {result}")
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            print("[WARN] Unexpected Gemini API response structure.")
            return "Thank you for your comment! 🙏"
    else:
        print(f"[ERROR] Gemini API call failed: {response.text}")
        return "Thank you for your comment! 🙏"

def load_data():
    print(f"[INFO] Loading data from {DATA_FILE} ...")
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if df.empty or list(df.columns) == [0]:
                print("[WARN] Data file is empty. Initializing new DataFrame.")
                return pd.DataFrame(columns=["media_id", "comment_id", "text", "replied"])
            print(f"[INFO] Loaded {len(df)} records from data file.")
            return df
        except pd.errors.EmptyDataError:
            print("[WARN] Data file is empty or invalid. Initializing new DataFrame.")
            return pd.DataFrame(columns=["media_id", "comment_id", "text", "replied"])
    print("[INFO] Data file does not exist. Initializing new DataFrame.")
    return pd.DataFrame(columns=["media_id", "comment_id", "text", "replied"])

def reply_to_comments(comments, df):
    replied_comments = []
    for comment in comments:
        print(f"[INFO] Replying to comment_id: {comment['comment_id']} on media_id: {comment['media_id']}")
        gemini_reply = get_gemini_reply(comment["text"])
        print(f"[INFO] Gemini reply: {gemini_reply}")
        if gemini_reply:
            reply_url = f"{INSTAGRAM_API_URL}/v23.0/{comment['comment_id']}/replies?access_token={INSTAGRAM_ACCESS_TOKEN}"
            reply_payload = {"message": gemini_reply}
            reply_response = requests.post(reply_url, data=reply_payload)
            print(f"[DEBUG] Instagram reply response status: {reply_response.status_code}")
            if reply_response.status_code == 200:
                print(f"[INFO] Successfully replied to comment_id: {comment['comment_id']}")
                # Mark as replied in DataFrame
                df.loc[df['comment_id'] == comment['comment_id'], 'replied'] = True
            else:
                print(f"[ERROR] Failed to reply to comment_id: {comment['comment_id']}. Response: {reply_response.text}")
            replied_comments.append(comment)
    print(f"[INFO] Total comments replied: {len(replied_comments)}")
    return replied_comments

def main():
    print("[INFO] Starting Instagram comments reply workflow...")
    df = load_data()
    # Only reply to comments where replied is False
    new_comments = [row for row in df.to_dict(orient="records") if not row.get("replied", False)]
    print(f"[INFO] New comments to reply: {new_comments}")
    reply_to_comments(new_comments, df)
    # Save updated DataFrame
    print(f"[INFO] Updating replied status in {DATA_FILE} ...")
    df.to_csv(DATA_FILE, index=False)
    print("[INFO] Reply workflow completed.")

if __name__ == "__main__":
    main()
