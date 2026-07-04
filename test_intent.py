import re
from app.services.ai_service import _parse_preferences, _classify_intent, _decide_conversation
message = "我想找一个适合商务聚餐的地方"
pref = _parse_preferences(message)
print("pref:", pref)
intent = _classify_intent(message, "normal_agent", pref, {}, {})
print("intent:", intent)
decision, _ = _decide_conversation(message, "normal_agent", pref, {}, {})
print("decision:", decision)
