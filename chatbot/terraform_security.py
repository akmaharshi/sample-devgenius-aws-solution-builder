"""
Terraform Security Scanner and Auto-Fix
Detects security vulnerabilities and automatically fixes them
"""
import re
import json
from typing import Dict, List, Tuple, Any


class TerraformSecurityScanner:
    """
    Scan Terraform code for security vulnerabilities and provide fixes
    """

    # Security rules database
    SECURITY_RULES = {
        'aws_s3_bucket': {
            'missing_encryption': {
                'severity': 'HIGH',
                'description': 'S3 bucket does not have server-side encryption enabled',
                'fix': 'Add server_side_encryption_configuration block',
                'cwe': 'CWE-311: Missing Encryption of Sensitive Data'
            },
            'public_access': {
                'severity': 'CRITICAL',
                'description': 'S3 bucket allows public access',
                'fix': 'Enable block_public_acls and block_public_policy',
                'cwe': 'CWE-264: Permissions, Privileges, and Access Controls'
            },
            'no_versioning': {
                'severity': 'MEDIUM',
                'description': 'S3 bucket versioning is not enabled',
                'fix': 'Enable versioning',
                'cwe': 'CWE-657: Violation of Secure Design Principles'
            }
        },
        'aws_security_group': {
            'open_ingress': {
                'severity': 'CRITICAL',
                'description': 'Security group allows ingress from 0.0.0.0/0',
                'fix': 'Restrict ingress to specific IP ranges',
                'cwe': 'CWE-284: Improper Access Control'
            },
            'unrestricted_egress': {
                'severity': 'MEDIUM',
                'description': 'Security group allows unrestricted egress',
                'fix': 'Limit egress to necessary destinations',
                'cwe': 'CWE-284: Improper Access Control'
            }
        },
        'aws_db_instance': {
            'public_access': {
                'severity': 'CRITICAL',
                'description': 'RDS instance is publicly accessible',
                'fix': 'Set publicly_accessible = false',
                'cwe': 'CWE-668: Exposure of Resource to Wrong Sphere'
            },
            'no_encryption': {
                'severity': 'HIGH',
                'description': 'RDS instance does not have encryption enabled',
                'fix': 'Enable storage_encrypted',
                'cwe': 'CWE-311: Missing Encryption of Sensitive Data'
            },
            'no_backup': {
                'severity': 'MEDIUM',
                'description': 'RDS instance does not have automated backups',
                'fix': 'Set backup_retention_period > 0',
                'cwe': 'CWE-693: Protection Mechanism Failure'
            }
        },
        'aws_instance': {
            'no_monitoring': {
                'severity': 'LOW',
                'description': 'EC2 instance does not have detailed monitoring',
                'fix': 'Enable monitoring = true',
                'cwe': 'CWE-778: Insufficient Logging'
            },
            'public_ip': {
                'severity': 'MEDIUM',
                'description': 'EC2 instance has public IP assignment',
                'fix': 'Use private subnets and NAT gateway',
                'cwe': 'CWE-668: Exposure of Resource to Wrong Sphere'
            }
        },
        'aws_iam_policy': {
            'wildcard_actions': {
                'severity': 'HIGH',
                'description': 'IAM policy uses wildcard (*) actions',
                'fix': 'Specify explicit actions',
                'cwe': 'CWE-269: Improper Privilege Management'
            },
            'wildcard_resources': {
                'severity': 'HIGH',
                'description': 'IAM policy uses wildcard (*) resources',
                'fix': 'Specify explicit resource ARNs',
                'cwe': 'CWE-269: Improper Privilege Management'
            }
        },
        'aws_lambda_function': {
            'no_tracing': {
                'severity': 'LOW',
                'description': 'Lambda function does not have X-Ray tracing',
                'fix': 'Enable tracing_config with mode = "Active"',
                'cwe': 'CWE-778: Insufficient Logging'
            },
            'no_vpc': {
                'severity': 'MEDIUM',
                'description': 'Lambda function not in VPC',
                'fix': 'Add vpc_config block',
                'cwe': 'CWE-668: Exposure of Resource to Wrong Sphere'
            }
        }
    }

    def __init__(self):
        """Initialize security scanner"""
        self.vulnerabilities = []

    def scan_terraform_code(
        self,
        terraform_code: str
    ) -> List[Dict[str, Any]]:
        """
        Scan Terraform code for security vulnerabilities

        Args:
            terraform_code: Terraform code to scan

        Returns:
            List of detected vulnerabilities
        """
        self.vulnerabilities = []

        # Parse resources from code
        resources = self._parse_resources(terraform_code)

        # Scan each resource type
        for resource in resources:
            resource_type = resource['type']
            resource_name = resource['name']
            resource_config = resource['config']

            if resource_type in self.SECURITY_RULES:
                vulns = self._scan_resource(
                    resource_type,
                    resource_name,
                    resource_config
                )
                self.vulnerabilities.extend(vulns)

        return self.vulnerabilities

    def _parse_resources(self, terraform_code: str) -> List[Dict]:
        """Parse Terraform resources from code"""
        resources = []

        # Find all resource blocks
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{([^}]+(?:\{[^}]+\}[^}]+)*)\}'
        matches = re.finditer(resource_pattern, terraform_code, re.DOTALL)

        for match in matches:
            resource_type = match.group(1)
            resource_name = match.group(2)
            resource_body = match.group(3)

            resources.append({
                'type': resource_type,
                'name': resource_name,
                'config': resource_body,
                'full_match': match.group(0)
            })

        return resources

    def _scan_resource(
        self,
        resource_type: str,
        resource_name: str,
        config: str
    ) -> List[Dict]:
        """Scan individual resource for vulnerabilities"""
        vulnerabilities = []
        rules = self.SECURITY_RULES.get(resource_type, {})

        # S3 bucket checks
        if resource_type == 'aws_s3_bucket':
            if 'server_side_encryption_configuration' not in config:
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'missing_encryption',
                    **rules['missing_encryption']
                })

            if 'block_public_acls' not in config or 'block_public_policy' not in config:
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'public_access',
                    **rules['public_access']
                })

            if 'versioning' not in config:
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'no_versioning',
                    **rules['no_versioning']
                })

        # Security group checks
        elif resource_type == 'aws_security_group':
            if re.search(r'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]', config):
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'open_ingress',
                    **rules['open_ingress']
                })

        # RDS checks
        elif resource_type == 'aws_db_instance':
            if re.search(r'publicly_accessible\s*=\s*true', config):
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'public_access',
                    **rules['public_access']
                })

            if 'storage_encrypted' not in config or re.search(r'storage_encrypted\s*=\s*false', config):
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'no_encryption',
                    **rules['no_encryption']
                })

        # EC2 checks
        elif resource_type == 'aws_instance':
            if 'monitoring' not in config:
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'no_monitoring',
                    **rules['no_monitoring']
                })

        # IAM policy checks
        elif resource_type == 'aws_iam_policy':
            if re.search(r'"Action"\s*:\s*"\*"', config) or re.search(r'"Action"\s*:\s*\[.*\*.*\]', config):
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'wildcard_actions',
                    **rules['wildcard_actions']
                })

            if re.search(r'"Resource"\s*:\s*"\*"', config):
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'wildcard_resources',
                    **rules['wildcard_resources']
                })

        # Lambda checks
        elif resource_type == 'aws_lambda_function':
            if 'tracing_config' not in config:
                vulnerabilities.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'rule': 'no_tracing',
                    **rules['no_tracing']
                })

        return vulnerabilities

    def auto_fix_vulnerabilities(
        self,
        terraform_code: str,
        vulnerabilities: List[Dict] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Automatically fix detected vulnerabilities

        Args:
            terraform_code: Original Terraform code
            vulnerabilities: List of vulnerabilities to fix (if None, scan first)

        Returns:
            Tuple of (fixed_code, applied_fixes)
        """
        if vulnerabilities is None:
            vulnerabilities = self.scan_terraform_code(terraform_code)

        fixed_code = terraform_code
        applied_fixes = []

        # Group vulnerabilities by resource
        resource_vulns = {}
        for vuln in vulnerabilities:
            key = f"{vuln['resource_type']}.{vuln['resource_name']}"
            if key not in resource_vulns:
                resource_vulns[key] = []
            resource_vulns[key].append(vuln)

        # Apply fixes for each resource
        for resource_key, vulns in resource_vulns.items():
            for vuln in vulns:
                fixed_code, fix_applied = self._apply_fix(
                    fixed_code,
                    vuln
                )
                if fix_applied:
                    applied_fixes.append({
                        'vulnerability': vuln,
                        'fix_applied': vuln['fix']
                    })

        return fixed_code, applied_fixes

    def _apply_fix(
        self,
        code: str,
        vulnerability: Dict
    ) -> Tuple[str, bool]:
        """Apply fix for a specific vulnerability"""
        resource_type = vulnerability['resource_type']
        resource_name = vulnerability['resource_name']
        rule = vulnerability['rule']

        # Find the resource block
        resource_pattern = f'resource\\s+"{resource_type}"\\s+"{resource_name}"\\s*{{([^}}]+(?:{{[^}}]+}}[^}}]+)*)}}'
        match = re.search(resource_pattern, code, re.DOTALL)

        if not match:
            return code, False

        resource_block = match.group(0)
        resource_body = match.group(1)

        # Apply specific fixes based on rule
        if resource_type == 'aws_s3_bucket':
            if rule == 'missing_encryption':
                encryption_config = """
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
"""
                new_body = resource_body + encryption_config
                new_block = resource_block.replace(resource_body, new_body)
                code = code.replace(resource_block, new_block)
                return code, True

            elif rule == 'public_access':
                public_access_block = """
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
"""
                new_body = resource_body + public_access_block
                new_block = resource_block.replace(resource_body, new_body)
                code = code.replace(resource_block, new_block)
                return code, True

            elif rule == 'no_versioning':
                versioning_config = """
  versioning {
    enabled = true
  }
"""
                new_body = resource_body + versioning_config
                new_block = resource_block.replace(resource_body, new_body)
                code = code.replace(resource_block, new_block)
                return code, True

        elif resource_type == 'aws_db_instance':
            if rule == 'public_access':
                code = re.sub(
                    r'publicly_accessible\s*=\s*true',
                    'publicly_accessible = false',
                    code
                )
                return code, True

            elif rule == 'no_encryption':
                if 'storage_encrypted' not in resource_body:
                    new_body = resource_body + "\n  storage_encrypted = true"
                    new_block = resource_block.replace(resource_body, new_body)
                    code = code.replace(resource_block, new_block)
                    return code, True

        elif resource_type == 'aws_instance':
            if rule == 'no_monitoring':
                new_body = resource_body + "\n  monitoring = true"
                new_block = resource_block.replace(resource_body, new_body)
                code = code.replace(resource_block, new_block)
                return code, True

        elif resource_type == 'aws_lambda_function':
            if rule == 'no_tracing':
                tracing_config = """
  tracing_config {
    mode = "Active"
  }
"""
                new_body = resource_body + tracing_config
                new_block = resource_block.replace(resource_body, new_body)
                code = code.replace(resource_block, new_block)
                return code, True

        return code, False

    def generate_security_report(
        self,
        vulnerabilities: List[Dict],
        applied_fixes: List[Dict]
    ) -> str:
        """
        Generate human-readable security report

        Args:
            vulnerabilities: List of detected vulnerabilities
            applied_fixes: List of applied fixes

        Returns:
            Formatted security report
        """
        report = "# Terraform Security Scan Report\n\n"
        report += f"**Total Vulnerabilities Found:** {len(vulnerabilities)}\n"
        report += f"**Automatically Fixed:** {len(applied_fixes)}\n\n"

        # Summary by severity
        severity_counts = {}
        for vuln in vulnerabilities:
            severity = vuln['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        report += "## Severity Summary\n\n"
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity in severity_counts:
                report += f"- **{severity}**: {severity_counts[severity]}\n"

        # Detailed vulnerabilities
        report += "\n## Detailed Findings\n\n"
        for i, vuln in enumerate(vulnerabilities, 1):
            report += f"### {i}. {vuln['description']}\n\n"
            report += f"- **Resource**: `{vuln['resource_type']}.{vuln['resource_name']}`\n"
            report += f"- **Severity**: {vuln['severity']}\n"
            report += f"- **CWE**: {vuln['cwe']}\n"
            report += f"- **Fix**: {vuln['fix']}\n\n"

        # Applied fixes
        if applied_fixes:
            report += "\n## Auto-Applied Fixes\n\n"
            for fix in applied_fixes:
                vuln = fix['vulnerability']
                report += f"- **{vuln['resource_type']}.{vuln['resource_name']}**: {fix['fix_applied']}\n"

        return report
