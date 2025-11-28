import os
import json
import logging
from typing import Dict, Any, Optional, Literal

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from jobly.config import settings
from jobly.analyzers.prompts import ANALYZER_INSTRUCTIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JobAnalyzer")

class JobAnalyzer:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.parser = JsonOutputParser()
        self.prompt = self._create_prompt()

    def _initialize_llm(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. OpenAI model may fail.")
        return ChatOpenAI(
            model=settings.models.job_analyzer_model,
            temperature=settings.models.job_analyzer_temperature,
            api_key=api_key
        )

    def _create_prompt(self):
        return ChatPromptTemplate.from_template(ANALYZER_INSTRUCTIONS)

    def analyze_job_description(self, description: str) -> Dict[str, Any]:
        """
        Analyzes the job description and returns structured data.
        """
        if not description:
            return {}

        try:
            chain = self.prompt | self.llm | self.parser
            result = chain.invoke({"description": description})
            return result
        except OutputParserException as e:
            logger.error(f"Error parsing LLM output: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error during LLM analysis: {e}")
            return {}

    async def analyze_job_description_async(self, description: str) -> Dict[str, Any]:
        """
        Analyzes the job description asynchronously and returns structured data.
        """
        if not description:
            return {}

        try:
            chain = self.prompt | self.llm | self.parser
            result = await chain.ainvoke({"description": description})
            return result
        except OutputParserException as e:
            logger.error(f"Error parsing LLM output: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error during async LLM analysis: {e}")
            return {}

if __name__ == "__main__":
    # Simple test
    analyzer = JobAnalyzer()
    sample_description = """
    We are looking for a Senior Software Engineer with 5+ years of experience in Python and AWS.
    You should have strong communication skills and be able to work in a cross-functional team.
    Responsibilities include building scalable APIs and mentoring junior developers.
    """
    print(json.dumps(analyzer.analyze_job_description(sample_description), indent=2))
