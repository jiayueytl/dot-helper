API_BASE_URL = "https://dot.ytlailabs.tech"
PREFIX = "LF"
SFT_ROUND = "SFT-LF"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqeSIsImV4cCI6MTc2MTAyMzE3NX0.aSXvvONVHKD2Jvp9C3QJxuELHUhcdAZ9bmV8_L1_i38"
COMPLETED_STATUS = ['annotation_complete','ready_for_qa','qa_approve']
INCOMPLETE_STATUS = ['not_started','in_progress','rework']
QA_DONE_STATUS = ['qa_approve']

BASE_COLUMNS = ['id','pipeline_run_id','assignee','reviewer','status','task','uuid','answer','domain','reason','metadata','question','sft_round','original_id','qa_flag','qa_feedback','corrected_answer','corrected_question',]

#Will change based on ongoing projects
USABLE_COLUMNS = ['justification','prompt_status','rewrite_degree','[fail]_not_adhere_to_prompt_specification_','[fail]_illogical/incoherent_prompt_','[fail]_lacks_naturalness_']

DUMMY_USERS = ['anno1','anno2','anno3','anno4']