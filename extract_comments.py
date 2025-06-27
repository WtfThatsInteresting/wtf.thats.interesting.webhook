import requests
import pandas as pd
import os

DATA_FILE = "comments_data.csv"
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_API_URL = "https://graph.facebook.com"
INSTAGRAM_ID = os.environ.get("INSTAGRAM_ID")

print("[INFO] INSTAGRAM_ACCESS_TOKEN loaded:", bool(INSTAGRAM_ACCESS_TOKEN))
print("[INFO] INSTAGRAM_ID loaded:", bool(INSTAGRAM_ID))

def load_existing_data():
    print(f"[INFO] Loading existing data from {DATA_FILE} ...")
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            print(f"[INFO] Loaded {len(df)} existing records.")
            return df
        except pd.errors.EmptyDataError:
            print("[WARN] Existing data file is empty.")
            return pd.DataFrame(columns=["media_id", "comment_id", "text", "replied"])
    print("[INFO] No existing data file found.")
    return pd.DataFrame(columns=["media_id", "comment_id", "text", "replied"])

def fetch_comments():
    print("[INFO] Fetching media IDs from Instagram (with pagination)...")
    media_url = f"{INSTAGRAM_API_URL}/v23.0/{INSTAGRAM_ID}/media?fields=id&access_token={INSTAGRAM_ACCESS_TOKEN}"
    existing_data = load_existing_data()
    comments = existing_data.to_dict(orient="records") if not existing_data.empty else []
    existing_comment_ids = set(existing_data["comment_id"].astype(str)) if not existing_data.empty else set()

    while media_url:
        media_response = requests.get(media_url)
        if media_response.status_code != 200:
            print(f"[ERROR] Failed to fetch media: {media_response.status_code} {media_response.text}")
            break

        media_data = media_response.json()
        print(f"[DEBUG] Media response: {media_data}")

        for media in media_data.get("data", []):
            media_id = media.get("id")
            print(f"[INFO] Fetching comments for media_id: {media_id}")
            comments_url = f"{INSTAGRAM_API_URL}/v23.0/{media_id}/comments?fields=id,text&access_token={INSTAGRAM_ACCESS_TOKEN}"
            comments_response = requests.get(comments_url)

            if comments_response.status_code != 200:
                print(f"[ERROR] Failed to fetch comments for media {media_id}: {comments_response.text}")
                continue

            comments_data = comments_response.json()
            print(f"[DEBUG] Comments for media {media_id}: {comments_data}")

            for comment in comments_data.get("data", []):
                comment_id = str(comment.get("id"))
                text = comment.get("text")
                # Only add if comment_id does not exist
                if comment_id not in existing_comment_ids:
                    comments.append({
                        "media_id": media_id,
                        "comment_id": comment_id,
                        "text": text,
                        "replied": False
                    })
                    print(f"[INFO] New comment found: {comment_id} for text {text} in media {media_id}")
                    existing_comment_ids.add(comment_id)

        # Move to next page
        media_url = media_data.get("paging", {}).get("next")

    print(f"[INFO] Total comments fetched: {len(comments)}")
    return comments

def save_data(data):
    print(f"[INFO] Saving {len(data)} comments to {DATA_FILE} ...")
    pd.DataFrame(data).to_csv(DATA_FILE, index=False)
    print("[INFO] Data saved.")

def main():
    comments = fetch_comments()
    save_data(comments)
    print("[INFO] Extraction workflow completed.")

if __name__ == "__main__":
    main()
