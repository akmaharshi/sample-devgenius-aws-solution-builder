import streamlit as st
from utils import BEDROCK_MODEL_ID
from utils import store_in_s3
from utils import save_conversation
from utils import collect_feedback
from utils import invoke_bedrock_model_streaming
from diagram_parser import DiagramParser
from terraform_security import TerraformSecurityScanner
import uuid
import json


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

    # Initialize security scanner option
    if 'terraform_security_scan' not in st.session_state:
        st.session_state.terraform_security_scan = True  # Enable by default

    # Initialize modular structure option
    if 'terraform_modular' not in st.session_state:
        st.session_state.terraform_modular = True  # Enable by default

    left, middle, right = st.columns([3, 1, 0.5])

    with left:
        st.markdown(
            "<div style='font-size: 18px'><b>Generate Modular Terraform Code with Security Scanning</b></div>",  # noqa
            unsafe_allow_html=True)
        st.divider()
        st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
        select_terraform = st.checkbox(
            "✅ Generate Terraform code",
            key="terraform",
            help="Generate modular Terraform configuration with automatic security scanning"
        )
        # Only update the session state when the checkbox value changes
        if select_terraform != st.session_state.terraform_user_select:
            st.session_state.terraform_user_select = select_terraform
        st.markdown("</div>", unsafe_allow_html=True)

        # Additional options
        if st.session_state.terraform_user_select:
            col1, col2 = st.columns(2)
            with col1:
                modular = st.checkbox(
                    "🏗️ Modular structure",
                    value=True,
                    help="Generate Terraform code with modular structure (separate modules for each service)"
                )
                st.session_state.terraform_modular = modular

            with col2:
                security_scan = st.checkbox(
                    "🔒 Security scanning & auto-fix",
                    value=True,
                    help="Scan for security vulnerabilities and automatically fix them"
                )
                st.session_state.terraform_security_scan = security_scan

    with right:
        if st.session_state.terraform_user_select:
            st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry-terraform", type="secondary"):
                st.session_state.terraform_user_select = True  # Probably redundant
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.terraform_user_select:
        # Enhanced prompt for modular Terraform generation
        if st.session_state.terraform_modular:
            terraform_prompt = """
            For the given solution, generate a MODULAR Terraform configuration with the following structure:

            1. **main.tf** - Main configuration with module calls
            2. **variables.tf** - Input variables
            3. **outputs.tf** - Output values
            4. **terraform.tfvars.example** - Example variable values
            5. **modules/** - Separate modules for each service type:
               - modules/vpc/
               - modules/ec2/
               - modules/s3/
               - modules/rds/
               - modules/lambda/
               (Create modules based on the architecture)

            Each module should have:
            - main.tf (resource definitions)
            - variables.tf (module inputs)
            - outputs.tf (module outputs)
            - README.md (usage documentation)

            Requirements:
            - Use AWS provider ~> 5.0
            - Include comprehensive comments
            - Follow Terraform best practices
            - Use meaningful variable names
            - Include validation rules
            - Add default tags
            - Enable encryption where applicable
            - Follow security best practices
            - Generate actual working code, not placeholders

            At the end, provide:
            1. File structure diagram
            2. Deployment commands
            3. Example usage
            """  # noqa
        else:
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

        # Show progress
        with st.spinner("🔄 Generating modular Terraform code..."):
            # Invoke the Bedrock model to get the Terraform response
            terraform_response, stop_reason = invoke_bedrock_model_streaming(terraform_messages)
            st.session_state.terraform_messages.append({"role": "assistant", "content": terraform_response})

        # Security scanning if enabled
        security_report = ""
        fixed_code = terraform_response

        if st.session_state.terraform_security_scan:
            with st.spinner("🔍 Scanning for security vulnerabilities..."):
                try:
                    scanner = TerraformSecurityScanner()
                    vulnerabilities = scanner.scan_terraform_code(terraform_response)

                    if vulnerabilities:
                        st.warning(f"⚠️ Found {len(vulnerabilities)} security issues. Auto-fixing...")

                        # Auto-fix vulnerabilities
                        fixed_code, applied_fixes = scanner.auto_fix_vulnerabilities(
                            terraform_response,
                            vulnerabilities
                        )

                        # Generate security report
                        security_report = scanner.generate_security_report(
                            vulnerabilities,
                            applied_fixes
                        )

                        # Update session state with fixed code
                        st.session_state.terraform_messages[-1]['content'] = fixed_code

                        # Show summary
                        severity_counts = {}
                        for vuln in vulnerabilities:
                            severity = vuln['severity']
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1

                        st.success(f"✅ Automatically fixed {len(applied_fixes)} vulnerabilities!")

                        # Display severity badges
                        cols = st.columns(4)
                        for idx, (severity, color) in enumerate([
                            ('CRITICAL', '🔴'),
                            ('HIGH', '🟠'),
                            ('MEDIUM', '🟡'),
                            ('LOW', '🔵')
                        ]):
                            if severity in severity_counts:
                                with cols[idx]:
                                    st.metric(
                                        f"{color} {severity}",
                                        severity_counts[severity]
                                    )
                    else:
                        st.success("✅ No security vulnerabilities found!")

                except Exception as e:
                    st.error(f"Error during security scan: {str(e)}")

        # Display the Terraform response
        st.markdown("### 📄 Generated Terraform Code")

        # Show tabs for code and security report
        if security_report:
            tab1, tab2 = st.tabs(["💻 Terraform Code", "🔒 Security Report"])

            with tab1:
                with st.container(height=400):
                    st.markdown(fixed_code)

            with tab2:
                with st.container(height=400):
                    st.markdown(security_report)
        else:
            with st.container(height=400):
                st.markdown(fixed_code)

        # Download buttons
        if st.session_state.terraform_modular:
            st.download_button(
                label="📥 Download Complete Terraform Project",
                data=fixed_code,
                file_name="terraform_infrastructure.zip",
                mime="application/zip",
                help="Download the complete modular Terraform project as a ZIP file"
            )
        else:
            st.download_button(
                label="📥 Download Terraform Code",
                data=fixed_code,
                file_name="main.tf",
                mime="text/plain",
                help="Download the Terraform configuration file"
            )

        # Save to storage
        st.session_state.interaction.append({
            "type": "Terraform Template (Modular)" if st.session_state.terraform_modular else "Terraform Template",
            "details": fixed_code
        })

        if security_report:
            st.session_state.interaction.append({
                "type": "Security Report",
                "details": security_report
            })

        store_in_s3(content=fixed_code, content_type='terraform')
        if security_report:
            store_in_s3(content=security_report, content_type='terraform-security-report')

        save_conversation(st.session_state['conversation_id'], terraform_prompt, fixed_code)
        collect_feedback(str(uuid.uuid4()), fixed_code, "generate_terraform", BEDROCK_MODEL_ID)

        # Show deployment instructions
        with st.expander("📖 Deployment Instructions"):
            st.markdown("""
            ### How to deploy this Terraform configuration:

            1. **Install Terraform**:
               ```bash
               # Download from https://www.terraform.io/downloads
               terraform --version
               ```

            2. **Initialize Terraform**:
               ```bash
               terraform init
               ```

            3. **Review the plan**:
               ```bash
               terraform plan
               ```

            4. **Apply the configuration**:
               ```bash
               terraform apply
               ```

            5. **Destroy resources when done**:
               ```bash
               terraform destroy
               ```

            ### Best Practices:
            - Always review `terraform plan` output before applying
            - Use remote state backend (S3 + DynamoDB) for team collaboration
            - Enable state locking to prevent concurrent modifications
            - Use workspaces for multiple environments
            - Tag all resources appropriately
            - Enable detailed logging for troubleshooting
            """)
