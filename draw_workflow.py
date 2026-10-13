"""מייצר את workflow_all_flows.html: תרשים של כל המסלולים האפשריים ב-RagWorkflow."""
from llama_index.utils.workflow import draw_all_possible_flows

from workflow_agent import RagWorkflow

if __name__ == "__main__":
    draw_all_possible_flows(RagWorkflow, filename="workflow_all_flows.html")
    print("נוצר workflow_all_flows.html")