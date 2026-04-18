# Process 

In the creation of this take home assignment, I'll be detailing my process of building it here. I'll be using AI tools like OpenCode and Claude Code to assist in the planning and implementation of this.

The first step was to put the spec through Claude and to identify certain frameworks I could use. I knew I had to use FastAPI, and some kind of agentic framework. Mastra has been an up and coming TypeScript framework, as well as LangGraph, so I was deciding between them.

Otherwise, I did some research:
- https://www.anthropic.com/engineering/multi-agent-research-system
- Used `/last30days` skill in Claude to find best AI search engines 

And then, started planning with the `/brainstorming` skill in Claude.

Claude proposed some design plans, and I made the decisions. 
I decided to do a tree research system, with parallel LLM calls along with LLM calls that recursed deeper into certain details.

After that, I used `/impeccable` for designing the frontend.

After answering many design questions, I approved the spec document and Claude went ahead to write the implementation plan.

45 minutes later, the first iteration was born.

## Iteration 1 

The first iteration turned out better than expected! After adding my API keys, and fixing some small bug, the program worked as intended. However, I wasn't satisfied with the way it looked and the results. The different agents were giving their own summaries but there wasn't any consolidation of answers.



