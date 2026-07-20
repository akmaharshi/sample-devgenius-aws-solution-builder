"""
Terraform Validation and Security Scanning
Ensures generated Terraform code is valid and secure
"""

import subprocess
import json
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of Terraform validation"""
    is_valid: bool
    error_messages: List[str]
    warning_messages: List[str]
    info_messages: List[str]


@dataclass
class SecurityScanResult:
    """Result of security scanning"""
    passed: bool
    failed_checks: int
    passed_checks: int
    skipped_checks: int
    issues: List[Dict]
    severity_breakdown: Dict[str, int]


class TerraformValidator:
    """
    Validates and scans Terraform code for errors and security issues
    """

    def __init__(self, terraform_dir: str):
        """Initialize validator with Terraform directory"""
        self.terraform_dir = Path(terraform_dir)

        # Check if terraform is installed
        self._check_terraform_installed()

    def _check_terraform_installed(self) -> bool:
        """Check if Terraform is installed"""
        try:
            result = subprocess.run(
                ['terraform', 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise Exception("Terraform is not installed. Please install Terraform >= 1.0")
        except subprocess.TimeoutExpired:
            raise Exception("Terraform version check timed out")

    def validate(self) -> ValidationResult:
        """
        Run terraform init and terraform validate

        Returns:
            ValidationResult with validation status and messages
        """

        error_messages = []
        warning_messages = []
        info_messages = []

        try:
            # Step 1: Terraform fmt check
            fmt_result = self._run_terraform_fmt()
            if not fmt_result['is_formatted']:
                warning_messages.append("Terraform files are not properly formatted")
                info_messages.extend(fmt_result['unformatted_files'])

            # Step 2: Terraform init
            init_success, init_output = self._run_terraform_init()
            if not init_success:
                error_messages.append("Terraform init failed")
                error_messages.append(init_output)
                return ValidationResult(
                    is_valid=False,
                    error_messages=error_messages,
                    warning_messages=warning_messages,
                    info_messages=info_messages
                )

            info_messages.append("Terraform initialization successful")

            # Step 3: Terraform validate
            validate_success, validate_output = self._run_terraform_validate()
            if not validate_success:
                error_messages.append("Terraform validation failed")
                error_messages.extend(self._parse_validation_errors(validate_output))
                return ValidationResult(
                    is_valid=False,
                    error_messages=error_messages,
                    warning_messages=warning_messages,
                    info_messages=info_messages
                )

            info_messages.append("Terraform validation successful")

            return ValidationResult(
                is_valid=True,
                error_messages=error_messages,
                warning_messages=warning_messages,
                info_messages=info_messages
            )

        except Exception as e:
            error_messages.append(f"Validation error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                error_messages=error_messages,
                warning_messages=warning_messages,
                info_messages=info_messages
            )

    def _run_terraform_fmt(self) -> Dict:
        """Run terraform fmt -check"""
        try:
            result = subprocess.run(
                ['terraform', 'fmt', '-check', '-recursive'],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            unformatted_files = []
            if result.returncode != 0:
                # Files listed in stdout are not properly formatted
                unformatted_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

            return {
                'is_formatted': result.returncode == 0,
                'unformatted_files': unformatted_files
            }

        except Exception as e:
            return {
                'is_formatted': False,
                'unformatted_files': [],
                'error': str(e)
            }

    def _run_terraform_init(self) -> Tuple[bool, str]:
        """Run terraform init"""
        try:
            result = subprocess.run(
                ['terraform', 'init', '-no-color'],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for init
            )

            return result.returncode == 0, result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return False, "Terraform init timed out after 5 minutes"
        except Exception as e:
            return False, f"Error running terraform init: {str(e)}"

    def _run_terraform_validate(self) -> Tuple[bool, str]:
        """Run terraform validate"""
        try:
            result = subprocess.run(
                ['terraform', 'validate', '-json'],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse JSON output
            try:
                output = json.loads(result.stdout)
                return output.get('valid', False), result.stdout
            except json.JSONDecodeError:
                return result.returncode == 0, result.stdout

        except subprocess.TimeoutExpired:
            return False, "Terraform validate timed out"
        except Exception as e:
            return False, f"Error running terraform validate: {str(e)}"

    def _parse_validation_errors(self, output: str) -> List[str]:
        """Parse validation errors from JSON output"""
        errors = []

        try:
            output_json = json.loads(output)

            if 'diagnostics' in output_json:
                for diagnostic in output_json['diagnostics']:
                    severity = diagnostic.get('severity', 'error')
                    summary = diagnostic.get('summary', 'Unknown error')
                    detail = diagnostic.get('detail', '')

                    error_msg = f"[{severity.upper()}] {summary}"
                    if detail:
                        error_msg += f": {detail}"

                    errors.append(error_msg)

        except json.JSONDecodeError:
            errors.append(output)

        return errors

    def scan_security(
        self,
        framework: str = "checkov",
        fail_on_severity: Optional[str] = "HIGH"
    ) -> SecurityScanResult:
        """
        Run security scanning on Terraform code

        Args:
            framework: Security scanning framework ("checkov" or "tfsec")
            fail_on_severity: Fail if issues of this severity or higher found

        Returns:
            SecurityScanResult with scan results
        """

        if framework == "checkov":
            return self._run_checkov(fail_on_severity)
        elif framework == "tfsec":
            return self._run_tfsec(fail_on_severity)
        else:
            raise ValueError(f"Unsupported security framework: {framework}")

    def _run_checkov(self, fail_on_severity: Optional[str] = "HIGH") -> SecurityScanResult:
        """Run Checkov security scan"""

        try:
            # Check if Checkov is installed
            subprocess.run(
                ['checkov', '--version'],
                capture_output=True,
                timeout=10
            )
        except FileNotFoundError:
            return SecurityScanResult(
                passed=False,
                failed_checks=0,
                passed_checks=0,
                skipped_checks=0,
                issues=[{"error": "Checkov is not installed. Install with: pip install checkov"}],
                severity_breakdown={}
            )

        try:
            # Run Checkov with JSON output
            cmd = [
                'checkov',
                '-d', str(self.terraform_dir),
                '--framework', 'terraform',
                '--output', 'json',
                '--quiet'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Parse JSON output
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Checkov might output to stderr
                try:
                    output = json.loads(result.stderr)
                except json.JSONDecodeError:
                    return SecurityScanResult(
                        passed=False,
                        failed_checks=0,
                        passed_checks=0,
                        skipped_checks=0,
                        issues=[{"error": "Failed to parse Checkov output"}],
                        severity_breakdown={}
                    )

            # Extract results
            summary = output.get('summary', {})
            failed_checks = summary.get('failed', 0)
            passed_checks = summary.get('passed', 0)
            skipped_checks = summary.get('skipped', 0)

            # Extract failed check details
            issues = []
            severity_breakdown = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'UNKNOWN': 0}

            for result_type in ['results', 'check_type_to_results']:
                if result_type in output:
                    results_data = output[result_type]
                    if isinstance(results_data, dict):
                        for check_type, checks in results_data.items():
                            failed = checks.get('results', {}).get('failed_checks', [])
                            for check in failed:
                                severity = check.get('severity', 'UNKNOWN').upper()
                                if severity not in severity_breakdown:
                                    severity = 'UNKNOWN'
                                severity_breakdown[severity] += 1

                                issues.append({
                                    'check_id': check.get('check_id'),
                                    'check_name': check.get('check_name'),
                                    'severity': severity,
                                    'file': check.get('file_path'),
                                    'resource': check.get('resource'),
                                    'guideline': check.get('guideline')
                                })

            # Determine if scan passed
            passed = failed_checks == 0

            if fail_on_severity and not passed:
                # Check if there are issues at or above the threshold
                severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
                if fail_on_severity.upper() in severity_order:
                    threshold_idx = severity_order.index(fail_on_severity.upper())
                    high_severity_count = sum(
                        severity_breakdown[sev]
                        for sev in severity_order[:threshold_idx + 1]
                    )
                    passed = high_severity_count == 0

            return SecurityScanResult(
                passed=passed,
                failed_checks=failed_checks,
                passed_checks=passed_checks,
                skipped_checks=skipped_checks,
                issues=issues,
                severity_breakdown=severity_breakdown
            )

        except subprocess.TimeoutExpired:
            return SecurityScanResult(
                passed=False,
                failed_checks=0,
                passed_checks=0,
                skipped_checks=0,
                issues=[{"error": "Checkov scan timed out"}],
                severity_breakdown={}
            )
        except Exception as e:
            return SecurityScanResult(
                passed=False,
                failed_checks=0,
                passed_checks=0,
                skipped_checks=0,
                issues=[{"error": f"Checkov error: {str(e)}"}],
                severity_breakdown={}
            )

    def _run_tfsec(self, fail_on_severity: Optional[str] = "HIGH") -> SecurityScanResult:
        """Run tfsec security scan"""

        try:
            # Check if tfsec is installed
            subprocess.run(
                ['tfsec', '--version'],
                capture_output=True,
                timeout=10
            )
        except FileNotFoundError:
            return SecurityScanResult(
                passed=False,
                failed_checks=0,
                passed_checks=0,
                skipped_checks=0,
                issues=[{"error": "tfsec is not installed. Install from https://github.com/aquasecurity/tfsec"}],
                severity_breakdown={}
            )

        try:
            cmd = [
                'tfsec',
                str(self.terraform_dir),
                '--format', 'json',
                '--no-color'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Parse JSON output
            output = json.loads(result.stdout)

            results = output.get('results', [])
            failed_checks = len(results)

            # Extract issues
            issues = []
            severity_breakdown = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}

            for check in results:
                severity = check.get('severity', 'UNKNOWN').upper()
                if severity in severity_breakdown:
                    severity_breakdown[severity] += 1

                issues.append({
                    'rule_id': check.get('rule_id'),
                    'description': check.get('description'),
                    'severity': severity,
                    'file': check.get('location', {}).get('filename'),
                    'line': check.get('location', {}).get('start_line'),
                    'resource': check.get('resource')
                })

            passed = failed_checks == 0

            return SecurityScanResult(
                passed=passed,
                failed_checks=failed_checks,
                passed_checks=0,  # tfsec doesn't report passed checks
                skipped_checks=0,
                issues=issues,
                severity_breakdown=severity_breakdown
            )

        except subprocess.TimeoutExpired:
            return SecurityScanResult(
                passed=False,
                failed_checks=0,
                passed_checks=0,
                skipped_checks=0,
                issues=[{"error": "tfsec scan timed out"}],
                severity_breakdown={}
            )
        except Exception as e:
            return SecurityScanResult(
                passed=False,
                failed_checks=0,
                passed_checks=0,
                skipped_checks=0,
                issues=[{"error": f"tfsec error: {str(e)}"}],
                severity_breakdown={}
            )


# Example usage
if __name__ == "__main__":
    # Validate Terraform code
    validator = TerraformValidator("./test_terraform_output")

    print("Running Terraform validation...")
    validation_result = validator.validate()

    if validation_result.is_valid:
        print("✅ Terraform validation passed!")
    else:
        print("❌ Terraform validation failed!")
        for error in validation_result.error_messages:
            print(f"  ERROR: {error}")

    for warning in validation_result.warning_messages:
        print(f"  WARNING: {warning}")

    for info in validation_result.info_messages:
        print(f"  INFO: {info}")

    # Run security scan
    print("\nRunning security scan (Checkov)...")
    security_result = validator.scan_security(framework="checkov", fail_on_severity="HIGH")

    if security_result.passed:
        print("✅ Security scan passed!")
    else:
        print(f"❌ Security scan found {security_result.failed_checks} issues")

    print(f"  Passed: {security_result.passed_checks}")
    print(f"  Failed: {security_result.failed_checks}")
    print(f"  Skipped: {security_result.skipped_checks}")
    print(f"  Severity breakdown: {security_result.severity_breakdown}")
