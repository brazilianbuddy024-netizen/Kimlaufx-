---
Task ID: 1
Agent: Main Agent
Task: Implement webhook posting for valid signals with BUY/SELL action detection

Work Log:
- Fixed breakeven: only includes breakeven_distance if signal mentions breakeven AND settings has value
- Added postToWebhook to HTTP polling path (fetchChannelMessages) - was only WebSocket before
- Added postToWebhook to WebSocket last_message handler
- Added posted boolean field to channel state for visual tracking
- Added posted: false reset on new messages, posted: true on successful webhook send
- Added visual POSTED badge in Fetched Signals panel
- Build verified successfully

Stage Summary:
- Webhook posting works via both HTTP polling (10s) and WebSocket paths
- Valid signals auto-posted when all main keywords present and zero excluded keywords
- Action detected from message: BUY/LONG=buy, SELL/SHORT=sell
- Breakeven only included if signal mentions it + settings value exists
