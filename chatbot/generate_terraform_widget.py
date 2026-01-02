import streamlit as st
from utils import BEDROCK_MODEL_ID
from utils import store_in_s3
from utils import save_conversation
from utils import collect_feedback
from utils import invoke_bedrock_model_streaming
import uuid


# Generate Terraform
@st.fragment
def generate_terraform(terraform_messages):

    terraform_messages = terraform_messages[:]

    # Retain messages and previous insights in the chat section
    if 'terraform_messages' not in st.session_state:
        st.session_state.terraform_messages = []

    # Create the radio button for terraform selection
    if 'terraform_user_select' not in st.session_state:
        st.session_state.terraform_user_select = False  # Initialize the value if it doesn't exist

    left, middle, right = st.columns([3, 1, 0.5])

    with left:
        st.markdown(
            "<div style='font-size: 18px'><b>Use the checkbox below to generate Terraform code as Infrastructure as Code for the proposed solution</b></div>",  # noqa
            unsafe_allow_html=True)
        st.divider()
        st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
        select_terraform = st.checkbox(
            "Check this box to generate Terraform code",
            key="terraform",
            help="Terraform enables you to define and provision AWS infrastructure using declarative configuration files"
        )
        # Only update the session state when the checkbox value changes
        if select_terraform != st.session_state.terraform_user_select:
            st.session_state.terraform_user_select = select_terraform
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        if st.session_state.terraform_user_select:
            st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry-terraform", type="secondary"):
                st.session_state.terraform_user_select = True  # Probably redundant
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.terraform_user_select:
        terraform_prompt = """
            For the given solution, generate Terraform configuration files (in HCL format) to automate and deploy the required AWS resources.
            Provide the actual source code for all jobs wherever applicable.
            The Terraform code should provision all resources and components using the AWS provider.
            Include proper variable definitions, outputs, and backend configuration.
            If Python code or other application code is needed, generate a "Hello, World!" code example.
            At the end, generate sample commands to initialize, plan, and apply the Terraform configuration.
            Organize the code into appropriate files (main.tf, variables.tf, outputs.tf, etc.) where relevant.
        """  # noqa

        # Append the prompt to the session state and messages
        st.session_state.terraform_messages.append({"role": "user", "content": terraform_prompt})
        terraform_messages.append({"role": "user", "content": terraform_prompt})

        # Invoke the Bedrock model to get the Terraform response
        terraform_response, stop_reason = invoke_bedrock_model_streaming(terraform_messages)
        st.session_state.terraform_messages.append({"role": "assistant", "content": terraform_response})

        # Display the Terraform response
        with st.container(height=350):
            st.markdown(terraform_response)

        st.session_state.interaction.append({"type": "Terraform Template", "details": terraform_response})
        store_in_s3(content=terraform_response, content_type='terraform')
        save_conversation(st.session_state['conversation_id'], terraform_prompt, terraform_response)
        collect_feedback(str(uuid.uuid4()), terraform_response, "generate_terraform", BEDROCK_MODEL_ID)
