"""
Live Discord Webhook Test for Material Science Papers
"""

import asyncio
from discord_notifier import send_discord_paper_notifications
from paper_extractor import search_all_sources

WEBHOOK_URL = "https://discord.com/api/webhooks/1543897278241308722/9kd-JtRzHIINkdFeX-u1EgNtA7QQYYw10fufN7LAxf-vDnRptTa_4VOPwHo9h309JzjR"

async def test_live_webhook():
    print("Extracting live Material Science papers to send to Discord...")
    papers = await search_all_sources(query="perovskite solar cells", limit=3)
    print(f"Extracted {len(papers)} papers. Sending to Discord webhook...")

    success = await send_discord_paper_notifications(papers, webhook_url=WEBHOOK_URL, limit=3)
    if success:
        print("[SUCCESS] Live Discord notification sent to your channel!")
    else:
        print("[FAILED] to send Discord notification.")

if __name__ == "__main__":
    asyncio.run(test_live_webhook())
