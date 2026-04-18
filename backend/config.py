from pydantic_settings import BaseSettings, SettingsConfigDict
from .models.types import ResearchConfig, DEFAULT_CONFIG


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    tavily_api_key: str = ""
    langsmith_api_key: str = ""

    default_planner_model: str = "gpt-4o"
    default_researcher_model: str = "gpt-4o-mini"
    default_synthesizer_model: str = "gpt-5-mini-2025-08-07"
    default_max_branches: int = 3
    default_max_depth: int = 1
    default_tavily_max_results: int = 2

    def research_config(self) -> ResearchConfig:
        return ResearchConfig(
            max_branches=self.default_max_branches,
            max_depth=self.default_max_depth,
            planner_model=self.default_planner_model,
            researcher_model=self.default_researcher_model,
            synthesizer_model=self.default_synthesizer_model,
            tavily_max_results=self.default_tavily_max_results,
        )


settings = Settings()

import os as _os
if settings.openai_api_key:
    _os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
if settings.tavily_api_key:
    _os.environ.setdefault("TAVILY_API_KEY", settings.tavily_api_key)
if settings.langsmith_api_key:
    _os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
