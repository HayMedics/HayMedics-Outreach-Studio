# outreach_crew.py
# Stage 2: turn a research brief into a polished cold email using CrewAI
# (Copywriter + Reviewer), wired to your same free OpenRouter model.

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()  # reads OPENROUTER_API_KEY from your .env file

# --- Point CrewAI at the same free OpenRouter model ---
# The double "openrouter/" is intentional: the first tells LiteLLM the provider,
# and "openrouter/free" is the model slug (the auto-router).
llm = LLM(
    model="openrouter/openrouter/free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


# --- Agent 1: the Copywriter ---
copywriter = Agent(
    role="Cold Email Copywriter",
    goal="Write a short, personalised cold email that earns a reply",
    backstory=(
        "You are a B2B copywriter who writes warm, human, specific emails. "
        "You avoid generic templates and spammy hype. You use the given research "
        "to reference something real about the lead, tie it to how the sender can "
        "help, and end with one clear, low-pressure ask."
    ),
    llm=llm,
    verbose=True,
)

# --- Agent 2: the Reviewer / deliverability + compliance check ---
reviewer = Agent(
    role="Email Reviewer and Deliverability Checker",
    goal="Make the email honest, tight, and safe to send",
    backstory=(
        "You are picky about quality and compliance. You cut fluff and spam-trigger "
        "words, keep it under 130 words, make sure every claim matches the research "
        "(no invented facts), and ensure the sender is identified with a polite "
        "opt-out line. You output the FINAL email only."
    ),
    llm=llm,
    verbose=True,
)


# --- Task 1: write the draft ---
write_task = Task(
    description=(
        "Write a personalised cold email to {name} at {company}.\n\n"
        "Research about the lead:\n{research}\n\n"
        "Goal of this email: {goal}\n"
        "We are: {sender_name} from {sender_company}, offering {sender_offer}.\n\n"
        "Rules: a subject line + short body. Reference ONE real detail from the "
        "research. One clear ask. Friendly and human, no hype."
    ),
    expected_output="A subject line and a short email body (under 150 words).",
    agent=copywriter,
)

# --- Task 2: review and finalise ---
review_task = Task(
    description=(
        "Review and improve the draft email. Cut fluff and spam-trigger words, "
        "keep it under 130 words, check every claim matches the research, and make "
        "sure it identifies {sender_name} from {sender_company} and includes a "
        "one-line polite opt-out (e.g. 'reply STOP and I won't email you again')."
    ),
    expected_output="The final, ready-to-send email: subject line + body.",
    agent=reviewer,
    context=[write_task],  # gives the reviewer the copywriter's draft
)


# --- The crew ---
outreach_crew = Crew(
    agents=[copywriter, reviewer],
    tasks=[write_task, review_task],
    process=Process.sequential,
    verbose=True,
    # No memory=True on purpose (see the note above about embeddings).
)


def write_outreach_email(research, name, company, goal,
                         sender_name, sender_company, sender_offer):
    """Run the crew and return the final email as text."""
    result = outreach_crew.kickoff(inputs={
        "research": research,
        "name": name,
        "company": company,
        "goal": goal,
        "sender_name": sender_name,
        "sender_company": sender_company,
        "sender_offer": sender_offer,
    })
    return result.raw


# Run this file directly to test the crew on a sample brief.
if __name__ == "__main__":
    sample_research = (
        "- Paystack is a Nigerian payments company (acquired by Stripe).\n"
        "- As CEO, the lead focuses on growth and partnerships across Africa.\n"
        "- Recent hook: expanding merchant tools for African businesses.\n"
        "- Possible pain point: onboarding new merchants quickly at scale."
    )
    email = write_outreach_email(
        research=sample_research,
        name="Shola Akinlade",
        company="Paystack",
        goal="Book a 15-minute intro call",
        sender_name="Ada",
        sender_company="Northwind Labs",
        sender_offer="an AI tool that automates customer onboarding",
    )
    print("\n--- FINAL EMAIL ---\n")
    print(email)