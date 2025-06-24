import requests
import pandas as pd
import os

# File to store comment IDs and media IDs
DATA_FILE = "comments_data.csv"

# Instagram API credentials
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_API_URL = "https://graph.facebook.com"
INSTAGRAM_ID = os.environ.get("INSTAGRAM_ID")

# Gemini API credentials
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

print("[INFO] INSTAGRAM_ACCESS_TOKEN loaded:", bool(INSTAGRAM_ACCESS_TOKEN))
print("[INFO] GEMINI_API_KEY loaded:", bool(GEMINI_API_KEY))
print("[INFO] INSTAGRAM_ID loaded:", bool(INSTAGRAM_ID))

# Function to fetch comments for all media
def fetch_comments():
    print("[INFO] Fetching media IDs from Instagram...")
    media_url = f"{INSTAGRAM_API_URL}/v23.0/{INSTAGRAM_ID}/media?fields=id&access_token={INSTAGRAM_ACCESS_TOKEN}"
    media_response = requests.get(media_url)
    media_data = media_response.json()
    print(f"[DEBUG] Media response: {media_data}")

    comments = []

    for media in media_data.get("data", []):
        media_id = media["id"]
        print(f"[INFO] Fetching comments for media_id: {media_id}")
        comments_url = f"{INSTAGRAM_API_URL}/v23.0/{media_id}/comments?fields=id,text&access_token={INSTAGRAM_ACCESS_TOKEN}"
        comments_response = requests.get(comments_url)
        comments_data = comments_response.json()
        print(f"[DEBUG] Comments for media {media_id}: {comments_data}")

        for comment in comments_data.get("data", []):
            comments.append({"media_id": media_id, "comment_id": comment["id"], "text": comment["text"]})

    print(f"[INFO] Total comments fetched: {len(comments)}")
    return comments

def get_gemini_reply(user_comment):
    """
    Uses Google Gemini API to generate text based on the input prompt.
    Returns the generated text as a string.
    """
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

    params = {"key": GEMINI_API_KEY}
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
    
# Function to reply to comments using Gemini API
def reply_to_comments(comments):
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
            else:
                print(f"[ERROR] Failed to reply to comment_id: {comment['comment_id']}. Response: {reply_response.text}")
            replied_comments.append(comment)

    print(f"[INFO] Total comments replied: {len(replied_comments)}")
    return replied_comments

# Function to load existing data
def load_data():
    print(f"[INFO] Loading data from {DATA_FILE} ...")
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # If file is empty, create new DataFrame
            if df.empty or list(df.columns) == [0]:
                print("[WARN] Data file is empty. Initializing new DataFrame.")
                return pd.DataFrame(columns=["media_id", "comment_id"])
            print(f"[INFO] Loaded {len(df)} records from data file.")
            return df
        except pd.errors.EmptyDataError:
            print("[WARN] Data file is empty or invalid. Initializing new DataFrame.")
            return pd.DataFrame(columns=["media_id", "comment_id"])
    print("[INFO] Data file does not exist. Initializing new DataFrame.")
    return pd.DataFrame(columns=["media_id", "comment_id"])

# Function to save data
def save_data(data):
    print(f"[INFO] Saving {len(data)} replied comments to {DATA_FILE} ...")
    pd.DataFrame(data).to_csv(DATA_FILE, index=False)
    print("[INFO] Data saved.")

# Main function
def main():
    print("[INFO] Starting Instagram comments polling workflow...")
    existing_data = load_data()
    existing_ids = set(str(cid) for cid in existing_data["comment_id"])

    comments = fetch_comments()
    print(comments)
    print(f"[INFO] Filtering new comments...")
    new_comments = []
    for comment in comments:
        comment_id = str(comment["comment_id"])
        print(f"[DEBUG] Comparing comment_id: {comment_id} with existing_ids: {existing_ids}")
        if comment_id not in existing_ids:
            new_comments.append(comment)
        else:
            print(f"[INFO] Skipping already replied comment_id: {comment_id}")
    print(f"[INFO] New comments to reply: {new_comments}")

    replied_comments = reply_to_comments(new_comments)

    save_data(replied_comments)
    print("[INFO] Polling workflow completed.")

if __name__ == "__main__":
    main()
