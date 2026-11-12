#Imports
import os
import gradio as gr
from openrouter import OpenRouter
from dotenv import load_dotenv

load_dotenv()
MODEL = 'meta-llama/llama-3.2-3b-instruct'
SYSTEM_PROMPT = """You are a helpful, friendly AI assistant.
Guidelines:
- Give clear, concise answers. Skip filler like "Great question!" or "Certainly!".
- If the user's request is ambiguous, ask one short clarifying question instead of guessing.
- When you don't know something or aren't sure, say so — don't invent facts.
- Format responses in Markdown: use code blocks for code, bullet lists for steps.
- Match the user's tone: casual if they're casual, precise if they're technical.
"""

client = OpenRouter(api_key=os.getenv("OPEN_ROUTER_API_KEY"))

def chat(message,history):
    messages = [{'role':'system', 'content':SYSTEM_PROMPT}]
    messages.extend([
        {'role' : row['role'],'content':row['content']}
        for row in history if row.get('role') and row.get('content')
    ])
    messages.append({'role':'user','content':message})
    resp = client.chat.send(
        model=MODEL,
        messages=messages,
        stream=True
    )
    reply = ""
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            reply += chunk.choices[0].delta.content
            yield reply

gr.ChatInterface(chat, title='ChatBot').launch()
