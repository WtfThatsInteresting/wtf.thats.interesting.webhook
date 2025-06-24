import requests
import pandas as pd
import os

# File to store comment IDs and media IDs
DATA_FILE = "comments_data.csv"

# Instagram API credentials
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_API_URL = "https://graph.facebook.com"

# Gemini API credentials
GEMINI_API_URL = "https://api.gemini.com/reply"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

print ("INSTAGRAM_ACCESS_TOKEN: ", INSTAGRAM_ACCESS_TOKEN)
print ("GEMINI_API_KEY: ", GEMINI_API_KEY)

# Function to fetch comments for all media
def fetch_comments():
    media_url = f"{INSTAGRAM_API_URL}/me/media?fields=id&access_token={INSTAGRAM_ACCESS_TOKEN}"
    media_response = requests.get(media_url)
    media_data = media_response.json()

    comments = []

    for media in media_data.get("data", []):
        media_id = media["id"]
        comments_url = f"{INSTAGRAM_API_URL}/{media_id}/comments?fields=id,text&access_token={INSTAGRAM_ACCESS_TOKEN}"
        comments_response = requests.get(comments_url)
        comments_data = comments_response.json()

        for comment in comments_data.get("data", []):
            comments.append({"media_id": media_id, "comment_id": comment["id"], "text": comment["text"]})

    return comments

def get_gemini_reply(user_comment):
    """
    Uses Google Gemini API to generate text based on the input prompt.
    Returns the generated text as a string.
    """
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": f"send a very nice 5 words reply to this instagram comment: '{user_comment}'"}]}
        ]
    }
    params = {"key": GEMINI_API_KEY}
    response = requests.post(url, headers=headers, params=params, json=payload)
    print("response", response)
    if response.status_code == 200:
        result = response.json()
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "Thank you for your comment! 🙏"
    else:
        return "Thank you for your comment! 🙏"
    
# Function to reply to comments using Gemini API
def reply_to_comments(comments):
    replied_comments = []

    for comment in comments:
        gemini_reply = get_gemini_reply(comment["text"])

        if gemini_reply:
            reply_url = f"{INSTAGRAM_API_URL}/{comment['comment_id']}/replies?access_token={INSTAGRAM_ACCESS_TOKEN}"
            reply_payload = {"text": gemini_reply}
            requests.post(reply_url, json=reply_payload)
            replied_comments.append(comment)

    return replied_comments

# Function to load existing data
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["media_id", "comment_id"])

# Function to save data
def save_data(data):
    pd.DataFrame(data).to_csv(DATA_FILE, index=False)

# Main function
def main():
    existing_data = load_data()
    existing_ids = set(existing_data["comment_id"])

    comments = fetch_comments()
    new_comments = [comment for comment in comments if comment["comment_id"] not in existing_ids]

    replied_comments = reply_to_comments(new_comments)

    save_data(replied_comments)

if __name__ == "__main__":
    main()
