"""AI adapter. Mock mode is explicit and must not be represented as a real model evaluation."""
from django.conf import settings

def answer_task_question(assignment, question):
    if settings.AI_MODE != 'live' or not settings.AI_API_KEY:
        return {'mode':'mock','answer':f'Development assistant: your active task is “{assignment.task.title}”. Review the task instructions and deliverables on this page. Your question has not been sent to a live AI provider. If it depends on project-specific requirements, contact your mentor.','escalate':True}
    # Deliberately fail closed until a provider-specific, tested prompt and privacy policy are configured.
    return {'mode':'live-configured-but-unimplemented','answer':'The AI provider credentials are present, but the production adapter has not been enabled in this build. Please contact your mentor.','escalate':True}

def evaluate_submission(assignment, submission):
    return {'mode':'mock','score':None,'criteria':[],'strengths':[],'improvements':['AI evaluation is in mock mode; no score has been generated.'], 'limitations':['Submission contents have not been analyzed by a live AI model or executed.'], 'requires_human_review':True}
