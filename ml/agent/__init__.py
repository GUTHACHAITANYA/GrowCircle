"""
ML-6 Natural Speech Voice and Chat Agent Package.
Speaking as 'GrowCircle'.
"""

from ml.agent.eval_harness import AgentEvaluationHarness, EvalTestCase, generate_evaluation_dataset
from ml.agent.pipeline import SpeechAgentPipeline, get_or_create_session
from ml.agent.rag import CURATED_CORPUS, CuratedAgriculturalRAG, CuratedDocument
from ml.agent.safety import SafetyGuardrails
from ml.agent.tools import TOOL_SCHEMAS, ToolExecutor, validate_grounding

__all__ = [
    "AgentEvaluationHarness",
    "EvalTestCase",
    "generate_evaluation_dataset",
    "SpeechAgentPipeline",
    "get_or_create_session",
    "CuratedAgriculturalRAG",
    "CuratedDocument",
    "CURATED_CORPUS",
    "SafetyGuardrails",
    "TOOL_SCHEMAS",
    "ToolExecutor",
    "validate_grounding",
]
