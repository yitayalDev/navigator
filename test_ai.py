# Test script for AI - bypass Unicode console issues
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.ai_service_template import AICampusAssistant

# Test the AI
assistant = AICampusAssistant(provider="aipipe")
print(f"Provider: {assistant.provider}")

# Test questions
questions = [
    "Where is the cafeteria?",
    "How to get to Science Campus?",
    "Where can I find WiFi?"
]

for q in questions:
    result = assistant.chat(q)
    print(f"\nQ: {q}")
    print(f"A: {result['response']}")
    print("-" * 50)
