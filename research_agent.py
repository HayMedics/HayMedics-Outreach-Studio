# research_agent.py
# Stage 1: research ONE lead using the OpenAI Agents SDK + OpenRouter (free model).
from agents import enable_verbose_stdout_logging
enable_verbose_stdout_logging()
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    function_tool,
    set_tracing_disabled,
)
from ddgs import DDGS

load_dotenv()  # reads OPENROUTER_API_KEY from your .env file

# --- Point the OpenAI Agents SDK at OpenRouter (it's OpenAI-compatible) ---
set_tracing_disabled(True)  # tracing needs an OpenAI key; we don't have one

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# Any free model that supports tools. Change this ONE line to swap models.
MODEL_NAME = "openrouter/free"
model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)


# --- A free web-search tool the agent can call ---
@function_tool
def search_web(query: str) -> str:
    """Search the web and return the top results as text.
    Use this to look up a lead's company, role, and recent news."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    return "\n".join(
        f"- {r.get('title','')}: {r.get('body','')} ({r.get('href','')})"
        for r in results
    )


# --- The Researcher agent ---
researcher = Agent(
    name="Lead Researcher",   # Change line 53 to:
    model=model,
    instructions=(
        "You research a sales lead so we can write a personalised cold email. "
        "Use the search_web tool to find:\n"
        "1. What the company does (one sentence).\n"
        "2. The person's likely responsibilities.\n"
        "3. ONE recent, specific hook (news, launch, hiring, funding) we can "
        "genuinely reference.\n"
        "4. A likely pain point our product could help with.\n\n"
        "Search first, then write. Only state what the search supports. If there "
        "is no real hook, say so - do NOT invent one. Under 150 words, in bullets."
    ),
    tools=[search_web],
)


def research_lead(name: str, role: str, company: str) -> str:
    """Research one lead and return the brief as text."""
    prompt = f"Research this lead:\nName: {name}\nRole: {role}\nCompany: {company}"
    result = Runner.run_sync(researcher, prompt)
    return result.final_output


# Run this file directly to test your setup.
if __name__ == "__main__":
    brief = research_lead("Shola Akinlade", "CEO", "Paystack")
    print("\n--- RESEARCH BRIEF ---\n")
    print(brief)