from typing import TypedDict, Literal, List, Dict, Any
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

# Load environment variables (useful for local development)
load_dotenv(override=True)

class SentimentSchema(BaseModel):
    sentiment: Literal["positive", "negative"] = Field(description="sentiment of the review")

class DiagnosisSchema(BaseModel):
    issue_type: Literal['UX/UI', 'performance', 'Bug', 'support', 'other'] = Field(description="The category of issue mentioned in the review")
    tone_type: Literal['angery', 'frustated', 'disspointed', 'calm'] = Field(description="Emotional tone expressed by the user in the review")
    urgency: Literal['Low', 'medium', 'High'] = Field(description="How urgent or critical the issue appears to be?")

class ReviewState(TypedDict):
    review: str
    sentiment: Literal['positive', 'negative']
    diagnosis: dict
    response: str
    history: List[str]  # Trace of executed node names

def get_review_agent_graph(api_key: str = None, model_name: str = "openai/gpt-oss-120b", base_url: str = "https://api.groq.com/openai/v1"):
    """
    Constructs the LangGraph state machine workflow using the specified LLM credentials and model.
    """
    # Use provided API key or fallback to environment variables
    effective_api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not effective_api_key:
        raise ValueError("API Key (GROQ_API_KEY or OPENAI_API_KEY) is required.")

    # Initialize the LLM
    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=effective_api_key,
        max_tokens=80
    )

    # Choose structured output method dynamically based on model provider
    method = None
    if model_name and not model_name.startswith("openai/"):
        method = "function_calling"

    # Bind structured outputs
    sentiment_model = llm.with_structured_output(SentimentSchema, method=method)
    diagnosis_model = llm.with_structured_output(DiagnosisSchema, method=method)

    # Node 1: Sentiment Analysis
    def find_sentiment(state: ReviewState):
        prompt = f"For the following review, analyze and determine the sentiment:\n\n{state['review']}"
        result = sentiment_model.invoke(prompt)
        current_history = state.get('history', []) + ['find_sentiment']
        return {
            'sentiment': result.sentiment,
            'history': current_history
        }

    # Conditional Routing Edge
    def check_sentiment(state: ReviewState) -> Literal['positive_response', 'run_diagnosis']:
        if state['sentiment'] == 'positive':
            return 'positive_response'
        else:
            return 'run_diagnosis'

    # Node 2A: Positive Review Path (Thank-you response)
    def positive_response(state: ReviewState):
        prompt = f"""You are a customer support agent. Write a direct thank-you comment in response to this positive product review:
"{state['review']}"

CRITICAL RULES:
1. Output MUST be exactly TWO sentences and under 50 words total.
2. Output MUST be a single line/paragraph. Do NOT use multiple paragraphs, lists, or line breaks.
3. Do NOT write it like an email. Do NOT include greetings (e.g., "Dear Customer"), placeholders (e.g., "[Customer Name]"), signatures, or closing warm regards.
4. Start the response directly.
"""
        result = llm.invoke(prompt)
        current_history = state.get('history', []) + ['positive_response']
        return {
            'response': result.content,
            'history': current_history
        }

    # Node 2B: Negative Review Path (Diagnosis)
    def run_diagnosis(state: ReviewState):
        prompt = f"Diagnose this negative customer review to extract metadata:\n\n{state['review']}"
        result = diagnosis_model.invoke(prompt)
        current_history = state.get('history', []) + ['run_diagnosis']
        return {
            'diagnosis': result.model_dump(),
            'history': current_history
        }

    # Node 3: Negative Review Response
    def negative_response(state: ReviewState):
        diagnosis = state['diagnosis']
        prompt = f"""You are an empathetic, helpful customer support assistant for a premium clothing brand.
A customer has left a negative review:
"{state['review']}"

Our diagnosis of the review is:
- Issue Category: {diagnosis['issue_type']}
- Emotional Tone: {diagnosis['tone_type']}
- Urgency Level: {diagnosis['urgency']}

Write a direct website reply addressing their concern.

CRITICAL RULES:
1. Output MUST be exactly TWO sentences and under 50 words total.
2. Output MUST be a single line/paragraph. Do NOT use multiple paragraphs, lists, line breaks, or bullet points.
3. Do NOT write it like an email. Do NOT include greetings (e.g., "Dear Valued Customer"), placeholders (e.g., "[Customer Name]", "[Your Name]"), signatures, or closing salutations (e.g., "Warm regards" or "Sincerely").
4. Start the response directly.
"""
        result = llm.invoke(prompt)
        current_history = state.get('history', []) + ['negative_response']
        return {
            'response': result.content,
            'history': current_history
        }

    # Construct and compile graph
    workflow = StateGraph(ReviewState)
    
    workflow.add_node('find_sentiment', find_sentiment)
    workflow.add_node('positive_response', positive_response)
    workflow.add_node('run_diagnosis', run_diagnosis)
    workflow.add_node('negative_response', negative_response)
    
    workflow.add_edge(START, 'find_sentiment')
    workflow.add_conditional_edges('find_sentiment', check_sentiment)
    workflow.add_edge('positive_response', END)
    workflow.add_edge('run_diagnosis', 'negative_response')
    workflow.add_edge('negative_response', END)
    
    return workflow.compile()

def run_review_flow(review_text: str, api_key: str = None, model_name: str = "openai/gpt-oss-120b", base_url: str = "https://api.groq.com/openai/v1") -> Dict[str, Any]:
    """
    Convenience function to run the full review flow graph for a single input review.
    """
    graph = get_review_agent_graph(api_key, model_name, base_url)
    initial_state = {
        'review': review_text,
        'history': []
    }
    final_state = graph.invoke(initial_state)
    return final_state
