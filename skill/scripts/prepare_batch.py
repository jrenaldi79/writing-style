import json
import argparse
from pathlib import Path

DATA_DIR = Path.home() / "Documents" / "my-writing-style"
RAW_DIR = DATA_DIR / "raw_samples"
SAMPLES_DIR = DATA_DIR / "samples"

def get_processed_ids():
    """Return set of IDs that have already been processed."""
    if not SAMPLES_DIR.exists():
        return set()
    return {f.stem for f in SAMPLES_DIR.glob("*.json")}

def clean_body(body):
    """Clean up email body text."""
    if not body:
        return "[No Body]"
    # Remove excessive newlines
    lines = [line.strip() for line in body.splitlines()]
    return "\n".join(line for line in lines if line)

def prepare_batch(count=40):
    """Fetch next batch of unprocessed emails and format for analysis."""
    processed = get_processed_ids()
    all_raw = sorted(list(RAW_DIR.glob("email_*.json")))
    
    to_process = []
    for f in all_raw:
        email_id = f.stem.replace("email_", "")
        if email_id not in processed:
            to_process.append(f)
            if len(to_process) >= count:
                break
    
    if not to_process:
        print("NO_NEW_EMAILS")
        return

    print(f"--- BATCH PREPARED: {len(to_process)} EMAILS ---\n")
    
    for f in to_process:
        with open(f) as file:
            data = json.load(file)
            
        print(f"=== ID: {data.get('id')} ===")
        print(f"From: {data.get('from')}")
        print(f"To: {data.get('to')}")
        print(f"Subject: {data.get('subject')}")
        print(f"Date: {data.get('date')}")
        print("\nBody:")
        print(clean_body(data.get('body')))
        print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=40, help="Number of emails to prepare")
    args = parser.parse_args()
    prepare_batch(args.count)
