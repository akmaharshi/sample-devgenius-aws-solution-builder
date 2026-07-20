"""
Terraform Generation Widget (Cost-Optimized)
Uses template-based generation instead of LLM - 90% cost reduction!
"""

import streamlit as st
import json
import os
import tempfile
import base64
from datetime import datetime
from pathlib import Path

from iac_orchestrator import IaCOrchestrator
from dynamodb import save_conversation_to_dynamodb


def generate_terraform_widget(conversation_id, s3_client, bucket_name, uploaded_image_key=None):
    """
    Generate Terraform using cost-optimized template-based approach

    Args:
        conversation_id: Unique conversation ID
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        uploaded_image_key: S3 key of uploaded architecture diagram
    """

    st.markdown("### 🔧 Generate Terraform (Cost-Optimized)")

    # Show cost savings banner
    st.info("""
    ✨ **New! Template-Based Terraform Generation**

    This uses our cost-optimized approach:
    - 90% reduction in Bedrock costs (from ~$0.53 to ~$0.03 per diagram)
    - Deterministic outputs (same input → same Terraform)
    - Production-ready code with security built-in
    - Automatic validation and security scanning
    """)

    # Check if image is uploaded
    if not uploaded_image_key:
        st.warning("⚠️ Please upload an architecture diagram first to generate Terraform.")
        return

    # Configuration inputs
    st.markdown("#### Configuration")

    col1, col2 = st.columns(2)

    with col1:
        architecture_name = st.text_input(
            "Architecture Name",
            value=f"architecture-{datetime.now().strftime('%Y%m%d')}",
            help="Name for your architecture (used for resource naming)"
        )

        environment = st.selectbox(
            "Environment",
            options=["dev", "staging", "prod"],
            index=0,
            help="Environment affects resource sizing, HA, and cost"
        )

    with col2:
        aws_region = st.selectbox(
            "AWS Region",
            options=[
                "us-east-1", "us-east-2", "us-west-1", "us-west-2",
                "eu-west-1", "eu-central-1", "ap-southeast-1", "ap-northeast-1"
            ],
            index=0
        )

        vpc_cidr = st.text_input(
            "VPC CIDR",
            value="10.0.0.0/16",
            help="CIDR block for VPC"
        )

    # Advanced options (collapsible)
    with st.expander("⚙️ Advanced Configuration"):
        enable_nat_gateway = st.checkbox("Enable NAT Gateway", value=True)
        enable_vpn = st.checkbox("Enable VPN Gateway", value=False)
        availability_zones = st.slider("Number of Availability Zones", 1, 6, 2)

        enable_encryption_at_rest = st.checkbox("Enable Encryption at Rest", value=True)
        enable_encryption_in_transit = st.checkbox("Enable Encryption in Transit", value=True)
        enable_logging = st.checkbox("Enable Logging", value=True)

        budget_limit = st.number_input(
            "Monthly Budget Limit (USD)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help="Set to 0 for no limit"
        )

    # Validation options
    col3, col4 = st.columns(2)
    with col3:
        validate_terraform = st.checkbox("Run Terraform Validation", value=True)
    with col4:
        run_security_scan = st.checkbox("Run Security Scan (Checkov)", value=True)

    # Generate button
    if st.button("🚀 Generate Terraform", type="primary", use_container_width=True):

        # Prepare user clarifications
        user_clarifications = {
            "environment": environment,
            "aws_region": aws_region,
            "vpc_cidr": vpc_cidr,
            "availability_zones": availability_zones,
            "enable_nat_gateway": enable_nat_gateway,
            "enable_vpn": enable_vpn,
            "enable_encryption_at_rest": enable_encryption_at_rest,
            "enable_encryption_in_transit": enable_encryption_in_transit,
            "enable_logging": enable_logging,
        }

        if budget_limit > 0:
            user_clarifications["budget_limit"] = budget_limit

        # Progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Download image from S3
            status_text.text("📥 Downloading diagram from S3...")
            progress_bar.progress(10)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                s3_client.download_file(bucket_name, uploaded_image_key, tmp_file.name)
                image_path = tmp_file.name

            # Initialize orchestrator
            status_text.text("🔧 Initializing IaC Orchestrator...")
            progress_bar.progress(20)

            orchestrator = IaCOrchestrator(
                aws_region=aws_region,
                output_base_dir=tempfile.mkdtemp()
            )

            # Process diagram
            status_text.text("📷 Analyzing diagram with Vision AI...")
            progress_bar.progress(30)

            results = orchestrator.process_diagram(
                image_path=image_path,
                architecture_name=architecture_name,
                user_clarifications=user_clarifications,
                validate_terraform=validate_terraform,
                run_security_scan=run_security_scan
            )

            progress_bar.progress(100)
            status_text.text("✅ Complete!")

            # Display results
            if results["success"]:
                st.success(f"✅ {results['message']}")

                # Cost breakdown
                with st.expander("💰 Cost Breakdown", expanded=True):
                    cost_data = results["cost_breakdown"]

                    col_cost1, col_cost2, col_cost3 = st.columns(3)
                    with col_cost1:
                        st.metric(
                            "Vision AI Cost",
                            f"${cost_data.get('vision_ai', 0):.4f}"
                        )
                    with col_cost2:
                        st.metric(
                            "Terraform Gen Cost",
                            "$0.0000",
                            delta="Template-based!",
                            delta_color="normal"
                        )
                    with col_cost3:
                        st.metric(
                            "Total Cost",
                            f"${cost_data.get('total_usd', 0):.4f}",
                            delta="-90% vs LLM",
                            delta_color="normal"
                        )

                    st.markdown("**Old Approach (LLM-based):** ~$0.53 per diagram")
                    st.markdown("**New Approach (Template-based):** ~$0.03 per diagram")
                    st.markdown("**Savings:** ~94% cost reduction! 🎉")

                # Architecture Intent
                if results.get("architecture_intent"):
                    with st.expander("🎯 Normalized Architecture Intent"):
                        st.json(results["architecture_intent"])

                # Generated files
                if results.get("terraform_files"):
                    with st.expander("📁 Generated Terraform Files", expanded=True):
                        st.write(f"Output directory: `{results['output_directory']}`")
                        st.write("Files generated:")
                        for filename in results["terraform_files"]:
                            st.write(f"- `{filename}`")

                        # Upload to S3
                        st.markdown("#### Upload to S3")
                        output_dir = results["output_directory"]

                        for filename in results["terraform_files"]:
                            file_path = os.path.join(output_dir, filename)
                            if os.path.exists(file_path):
                                with open(file_path, 'r') as f:
                                    content = f.read()

                                # Upload to S3
                                s3_key = f"{conversation_id}/terraform/{filename}"
                                s3_client.put_object(
                                    Bucket=bucket_name,
                                    Key=s3_key,
                                    Body=content,
                                    ContentType='text/plain'
                                )

                        st.success(f"✅ Uploaded {len(results['terraform_files'])} files to S3")

                        # Download button for all files
                        st.markdown("#### Download Terraform Package")

                        # Create zip file
                        import zipfile
                        import io

                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for filename in results["terraform_files"]:
                                file_path = os.path.join(output_dir, filename)
                                if os.path.exists(file_path):
                                    zip_file.write(file_path, arcname=filename)

                        zip_buffer.seek(0)

                        st.download_button(
                            label="📦 Download Terraform Package (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name=f"{architecture_name}-terraform.zip",
                            mime="application/zip",
                            use_container_width=True
                        )

                # Validation results
                if results.get("validation_result"):
                    validation = results["validation_result"]

                    with st.expander("✅ Terraform Validation", expanded=not validation["is_valid"]):
                        if validation["is_valid"]:
                            st.success("✅ Terraform validation passed!")
                        else:
                            st.error("❌ Terraform validation failed!")

                            if validation["errors"]:
                                st.markdown("**Errors:**")
                                for error in validation["errors"]:
                                    st.error(error)

                        if validation["warnings"]:
                            st.markdown("**Warnings:**")
                            for warning in validation["warnings"]:
                                st.warning(warning)

                        if validation["info"]:
                            st.markdown("**Info:**")
                            for info in validation["info"]:
                                st.info(info)

                # Security scan results
                if results.get("security_result"):
                    security = results["security_result"]

                    with st.expander("🔒 Security Scan Results", expanded=security["failed_checks"] > 0):
                        col_sec1, col_sec2, col_sec3 = st.columns(3)

                        with col_sec1:
                            st.metric("Passed Checks", security["passed_checks"])
                        with col_sec2:
                            st.metric("Failed Checks", security["failed_checks"])
                        with col_sec3:
                            if security["passed"]:
                                st.success("✅ Scan Passed")
                            else:
                                st.error("❌ Issues Found")

                        # Severity breakdown
                        st.markdown("**Severity Breakdown:**")
                        severity_data = security["severity_breakdown"]
                        for severity, count in severity_data.items():
                            if count > 0:
                                color = {
                                    "CRITICAL": "🔴",
                                    "HIGH": "🟠",
                                    "MEDIUM": "🟡",
                                    "LOW": "🟢"
                                }.get(severity, "⚪")
                                st.write(f"{color} {severity}: {count}")

                        # Critical/High issues
                        if security["critical_issues"]:
                            st.markdown("**Critical/High Issues (First 10):**")
                            for issue in security["critical_issues"]:
                                with st.container():
                                    st.markdown(f"""
                                    **[{issue.get('severity')}]** {issue.get('check_name', 'Unknown')}
                                    - File: `{issue.get('file', 'N/A')}`
                                    - Resource: `{issue.get('resource', 'N/A')}`
                                    """)

                # Save to DynamoDB
                save_conversation_to_dynamodb(
                    conversation_id=conversation_id,
                    conversation_name="terraform_generation",
                    user_message="Generate Terraform (Template-based)",
                    bot_response=json.dumps({
                        "architecture_name": architecture_name,
                        "environment": environment,
                        "cost": results["cost_breakdown"],
                        "status": results["status"]
                    }),
                    citations=[],
                    response_body=""
                )

            elif results["status"] == "needs_clarification":
                st.warning("⚠️ Additional information needed")

                st.markdown("**Please provide answers to the following questions:**")
                for i, question in enumerate(results["questions"]):
                    st.write(f"{i+1}. {question}")

            else:
                st.error(f"❌ Error: {results['message']}")

        except Exception as e:
            st.error(f"❌ Error generating Terraform: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

        finally:
            # Cleanup temporary files
            if 'image_path' in locals():
                try:
                    os.unlink(image_path)
                except:
                    pass

            progress_bar.empty()
            status_text.empty()

    # Show cost comparison
    st.markdown("---")
    with st.expander("📊 Cost Comparison: Old vs New Approach"):
        orchestrator = IaCOrchestrator()
        comparison = orchestrator.cost_comparison(num_diagrams=100)

        col_comp1, col_comp2, col_comp3 = st.columns(3)

        with col_comp1:
            st.markdown("**Old Approach (LLM)**")
            st.metric("Per Diagram", f"${comparison['old_approach']['per_diagram_usd']}")
            st.metric("100 Diagrams", f"${comparison['old_approach']['total_usd']}")

        with col_comp2:
            st.markdown("**New Approach (Templates)**")
            st.metric("Per Diagram", f"${comparison['new_approach']['per_diagram_usd']}")
            st.metric("100 Diagrams", f"${comparison['new_approach']['total_usd']}")

        with col_comp3:
            st.markdown("**💰 Savings**")
            st.metric(
                "Per Diagram",
                f"${comparison['savings']['per_diagram_usd']}",
                delta=f"{comparison['savings']['percentage']}%"
            )
            st.metric(
                "100 Diagrams",
                f"${comparison['savings']['total_usd']}"
            )

        st.success(f"🎉 **{comparison['savings']['percentage']}% cost reduction!**")
