from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def get_list(var_name, default=None):
    """Helper to parse comma-separated lists from env variables."""
    value = os.getenv(var_name)
    if value:
        return [v.strip() for v in value.split(',')]
    return default or []

API_BASE_URL = os.getenv("API_BASE_URL", "https://dot.ytlailabs.tech")
PREFIX = os.getenv("PREFIX", "LF")
SFT_ROUND = os.getenv("SFT_ROUND", "SFT-LF")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")

COMPLETED_STATUS = get_list("COMPLETED_STATUS", ['annotation_complete', 'ready_for_qa', 'qa_approve'])
INCOMPLETE_STATUS = get_list("INCOMPLETE_STATUS", ['not_started', 'in_progress', 'rework'])
QA_STATUS = get_list("INCOMPLETE_STATUS", ['ready_for_qa', 'qa_approve'])
QA_DONE_STATUS = get_list("QA_DONE_STATUS", ['qa_approve'])

BASE_COLUMNS = get_list("BASE_COLUMNS", [
    'id','pipeline_run_id','assignee','assignee_name','reviewer','status','task','uuid','answer','domain',
    'reason','metadata','question','sft_round','original_id','qa_flag','qa_feedback','corrected_answer',
    'corrected_question','package_id'
])

USABLE_COLUMNS = get_list("USABLE_COLUMNS", [
    'justification','prompt_status','rewrite_degree','[fail]_not_adhere_to_prompt_specification_',
    '[fail]_illogical/incoherent_prompt_','[fail]_lacks_naturalness_'
])

DUMMY_USERS = get_list("DUMMY_USERS", ['anno1','anno2','anno3','anno4'])
