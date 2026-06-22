import json
import logging

from groq import Groq
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)


class ManuscriptProfile(BaseModel):
    title: str
    abstract: str
    keywords: List[str]
    article_type: str


class AIAnalysisProfile(BaseModel):
    compatibility_reason: str
    predatory_risk: str
    submission_strategy: str


class LLMService:
    def __init__(self):
        from app.core.config import settings

        self.api_key = settings.GROQ_API_KEY

    async def extract_manuscript_profile(self, text: str) -> dict:
        """Extract structural profile from raw manuscript text using Groq."""
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set. Returning dummy data.")
            return {
                "title": "Extracted Title (Dummy Data)",
                "abstract": "This is a placeholder abstract returned because no API key was configured.",
                "keywords": ["dummy", "data", "no-api-key"],
                "article_type": "Original Research",
            }

        try:
            client = Groq(api_key=self.api_key)
            prompt = f"""
            Extract the following metadata from the provided manuscript text.
            Return ONLY a valid JSON object with these keys: title, abstract, keywords (array of strings), and article_type.

            Here is the manuscript:
            <manuscript>
            {text[:15000]}
            </manuscript>
            """

            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful data extraction assistant. You output strictly valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error in Groq extraction: {e}", exc_info=True)
            raise e

    async def analyze_journal_compatibility(
        self, manuscript_abstract: str, journal_data: dict
    ) -> dict:
        """Acts as an academic editor to evaluate the journal match using Groq."""
        if not self.api_key:
            return {
                "compatibility_reason": "Dummy explanation: The journal's scope visually aligns with the provided abstract keywords.",
                "predatory_risk": "Low (Dummy)",
                "submission_strategy": "Ensure formatting matches the author guidelines.",
            }

        try:
            client = Groq(api_key=self.api_key)
            prompt = f"""
            You are an expert academic editor. Evaluate the compatibility between the following manuscript abstract and the target journal.
            Also, assess if the journal displays any common predatory signals (e.g. unknown publisher with high APC, overly broad scope).
            Finally, provide a brief submission strategy (e.g. highlight X in the cover letter).

            Return ONLY a valid JSON object with these keys: compatibility_reason, predatory_risk, submission_strategy.

            Manuscript Abstract: {manuscript_abstract}

            Target Journal:
            Name: {journal_data.get('name')}
            Publisher: {journal_data.get('publisher')}
            Open Access: {journal_data.get('open_access')}
            APC Cost: ${journal_data.get('apc_usd')}
            """

            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful data extraction assistant. You output strictly valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error in Groq compatibility analysis: {e}", exc_info=True)
            return {
                "compatibility_reason": "Analysis failed.",
                "predatory_risk": "Unknown",
                "submission_strategy": "N/A",
            }
