"""
Intent Normalization Engine
Converts ambiguous vision detection results into strict, normalized architecture schema
This is the CRITICAL layer that ensures deterministic Terraform generation
"""

import yaml
import re
from typing import Dict, List, Optional, Tuple
from schemas.architecture_schema import (
    ArchitectureIntent,
    ServiceIntent,
    Connection,
    Environment,
    ServiceCategory,
    NetworkExposure,
    HighAvailability,
    NetworkIntent,
    SecurityIntent,
    CostIntent,
    VisionDetectionResult
)


class IntentNormalizer:
    """
    Converts vision detection results + user clarifications into normalized architecture intent
    This ensures deterministic and consistent Terraform generation
    """

    def __init__(self, service_registry_path: str = "registry/service_registry.yaml"):
        """Initialize with service registry"""
        with open(service_registry_path, 'r') as f:
            self.service_registry = yaml.safe_load(f)

    def normalize(
        self,
        vision_result: VisionDetectionResult,
        user_clarifications: Optional[Dict] = None,
        architecture_name: str = "aws-architecture"
    ) -> Tuple[ArchitectureIntent, List[str]]:
        """
        Normalize vision detection + user input into strict architecture intent

        Args:
            vision_result: Output from Vision AI
            user_clarifications: User-provided clarifications (environment, HA, etc.)
            architecture_name: Name of the architecture

        Returns:
            Tuple of (ArchitectureIntent, list of questions needing clarification)
        """

        user_clarifications = user_clarifications or {}

        # Initialize architecture intent
        architecture = ArchitectureIntent(
            architecture_name=architecture_name,
            description=user_clarifications.get('description', 'Generated AWS architecture'),
            environment=self._determine_environment(vision_result, user_clarifications),
            aws_region=user_clarifications.get('aws_region', 'us-east-1')
        )

        # Normalize network intent
        architecture.network = self._normalize_network_intent(
            vision_result,
            user_clarifications
        )

        # Normalize security intent
        architecture.security = self._normalize_security_intent(
            vision_result,
            user_clarifications
        )

        # Normalize cost intent
        architecture.cost = self._normalize_cost_intent(user_clarifications)

        # Normalize services
        normalized_services, service_questions = self._normalize_services(
            vision_result,
            user_clarifications,
            architecture.environment
        )
        architecture.services = normalized_services

        # Normalize connections
        architecture.connections = self._normalize_connections(
            vision_result,
            normalized_services
        )

        # Collect all questions that need user clarification
        questions = service_questions

        # Add global architecture questions if needed
        if not user_clarifications.get('environment'):
            questions.insert(0, "What environment is this for? (dev/staging/prod)")

        return architecture, questions

    def _determine_environment(
        self,
        vision_result: VisionDetectionResult,
        user_clarifications: Dict
    ) -> Environment:
        """Determine environment from hints or user input"""

        # User explicitly specified
        if 'environment' in user_clarifications:
            env_str = user_clarifications['environment'].lower()
            if env_str in ['dev', 'development']:
                return Environment.DEV
            elif env_str in ['staging', 'stage']:
                return Environment.STAGING
            elif env_str in ['prod', 'production']:
                return Environment.PROD

        # Try to detect from textual hints
        hints_lower = [h.lower() for h in vision_result.textual_hints]
        if any('prod' in h or 'production' in h for h in hints_lower):
            return Environment.PROD
        elif any('staging' in h or 'stage' in h for h in hints_lower):
            return Environment.STAGING

        # Default to dev for safety (cheaper resources)
        return Environment.DEV

    def _normalize_network_intent(
        self,
        vision_result: VisionDetectionResult,
        user_clarifications: Dict
    ) -> NetworkIntent:
        """Normalize network configuration"""

        network = NetworkIntent()

        # VPC CIDR
        if 'vpc_cidr' in user_clarifications:
            network.vpc_cidr = user_clarifications['vpc_cidr']

        # Availability zones
        if 'availability_zones' in user_clarifications:
            network.availability_zones = int(user_clarifications['availability_zones'])
        else:
            # Detect from hints or default based on environment
            env = self._determine_environment(vision_result, user_clarifications)
            network.availability_zones = 3 if env == Environment.PROD else 2

        # NAT Gateway
        if 'enable_nat_gateway' in user_clarifications:
            network.enable_nat_gateway = user_clarifications['enable_nat_gateway']

        # VPN
        hints_lower = [h.lower() for h in vision_result.textual_hints]
        network.enable_vpn = any('vpn' in h for h in hints_lower)

        return network

    def _normalize_security_intent(
        self,
        vision_result: VisionDetectionResult,
        user_clarifications: Dict
    ) -> SecurityIntent:
        """Normalize security configuration"""

        security = SecurityIntent()

        # Apply user clarifications
        if 'enable_encryption_at_rest' in user_clarifications:
            security.enable_encryption_at_rest = user_clarifications['enable_encryption_at_rest']

        if 'enable_encryption_in_transit' in user_clarifications:
            security.enable_encryption_in_transit = user_clarifications['enable_encryption_in_transit']

        if 'compliance_frameworks' in user_clarifications:
            security.compliance_frameworks = user_clarifications['compliance_frameworks']

        # Detect from hints
        hints_lower = [h.lower() for h in vision_result.textual_hints]
        if any('hipaa' in h for h in hints_lower):
            if 'HIPAA' not in security.compliance_frameworks:
                security.compliance_frameworks.append('HIPAA')
        if any('pci' in h for h in hints_lower):
            if 'PCI-DSS' not in security.compliance_frameworks:
                security.compliance_frameworks.append('PCI-DSS')

        return security

    def _normalize_cost_intent(self, user_clarifications: Dict) -> CostIntent:
        """Normalize cost configuration"""

        cost = CostIntent()

        if 'budget_limit' in user_clarifications:
            cost.budget_limit = float(user_clarifications['budget_limit'])

        if 'cost_allocation_tags' in user_clarifications:
            cost.cost_allocation_tags = user_clarifications['cost_allocation_tags']

        if 'enable_auto_scaling' in user_clarifications:
            cost.enable_auto_scaling = user_clarifications['enable_auto_scaling']

        return cost

    def _normalize_services(
        self,
        vision_result: VisionDetectionResult,
        user_clarifications: Dict,
        environment: Environment
    ) -> Tuple[List[ServiceIntent], List[str]]:
        """
        Normalize detected services into ServiceIntent objects

        Returns:
            Tuple of (list of ServiceIntent, list of clarification questions)
        """

        services = []
        questions = []

        for idx, detected_service in enumerate(vision_result.detected_services):
            service_type = detected_service.get('service_type', '').lower()

            # Validate service type exists in registry
            if service_type not in self.service_registry['services']:
                questions.append(
                    f"Detected '{service_type}' but it's not in registry. "
                    f"Did you mean one of: {', '.join(list(self.service_registry['services'].keys())[:5])}?"
                )
                continue

            # Get service metadata from registry
            service_meta = self.service_registry['services'][service_type]

            # Generate unique service ID
            label = detected_service.get('label', service_type)
            service_id = self._generate_service_id(service_type, label, idx)

            # Determine service category
            category = ServiceCategory(service_meta['category'])

            # Determine network exposure
            network_exposure = self._determine_network_exposure(
                detected_service,
                user_clarifications.get(service_id, {})
            )

            # Determine HA requirements
            high_availability = self._determine_ha(
                environment,
                service_type,
                user_clarifications.get(service_id, {})
            )

            # Build service configuration
            configuration = self._build_service_configuration(
                service_type,
                service_meta,
                detected_service,
                user_clarifications.get(service_id, {})
            )

            # Create ServiceIntent
            service = ServiceIntent(
                id=service_id,
                service_type=service_type,
                name=label,
                category=category,
                environment=environment,
                network_exposure=network_exposure,
                high_availability=high_availability,
                configuration=configuration,
                description=f"{service_meta['name']} - {service_meta['description']}"
            )

            services.append(service)

        return services, questions

    def _generate_service_id(self, service_type: str, label: str, index: int) -> str:
        """Generate unique service identifier"""
        # Clean label to make it valid identifier
        clean_label = re.sub(r'[^a-zA-Z0-9_-]', '', label.replace(' ', '-'))
        if clean_label and clean_label != service_type:
            return f"{service_type}-{clean_label}".lower()
        else:
            return f"{service_type}-{index + 1}"

    def _determine_network_exposure(
        self,
        detected_service: Dict,
        user_clarifications: Dict
    ) -> NetworkExposure:
        """Determine if service should be public, private, or internal"""

        # User explicitly specified
        if 'network_exposure' in user_clarifications:
            exposure = user_clarifications['network_exposure'].lower()
            if exposure == 'public':
                return NetworkExposure.PUBLIC
            elif exposure == 'private':
                return NetworkExposure.PRIVATE
            else:
                return NetworkExposure.INTERNAL

        # Detect from hints
        hints = [h.lower() for h in detected_service.get('hints', [])]

        if any('public' in h or 'internet' in h for h in hints):
            return NetworkExposure.PUBLIC
        elif any('private' in h for h in hints):
            return NetworkExposure.PRIVATE

        # Default based on service type
        service_type = detected_service.get('service_type', '')
        if service_type in ['alb', 'cloudfront', 'api_gateway']:
            return NetworkExposure.PUBLIC  # These are typically public-facing
        elif service_type in ['rds', 'dynamodb', 'elasticache']:
            return NetworkExposure.PRIVATE  # Databases should be private
        else:
            return NetworkExposure.PRIVATE  # Default to private for security

    def _determine_ha(
        self,
        environment: Environment,
        service_type: str,
        user_clarifications: Dict
    ) -> HighAvailability:
        """Determine high availability configuration"""

        # User explicitly specified
        if 'high_availability' in user_clarifications:
            ha = user_clarifications['high_availability'].lower()
            if ha in ['multi_az', 'multi-az']:
                return HighAvailability.MULTI_AZ
            elif ha in ['multi_region', 'multi-region']:
                return HighAvailability.MULTI_REGION
            else:
                return HighAvailability.SINGLE_AZ

        # Production requires multi-AZ for stateful services
        if environment == Environment.PROD:
            if service_type in ['rds', 'elasticache', 'efs']:
                return HighAvailability.MULTI_AZ

        return HighAvailability.SINGLE_AZ

    def _build_service_configuration(
        self,
        service_type: str,
        service_meta: Dict,
        detected_service: Dict,
        user_clarifications: Dict
    ) -> Dict:
        """Build service-specific configuration"""

        # Start with defaults from registry
        config = service_meta.get('default_configuration', {}).copy()

        # Apply user clarifications
        config.update(user_clarifications.get('configuration', {}))

        # Service-specific logic
        if service_type == 'rds':
            # Ensure database name is valid
            if 'database_name' not in config:
                config['database_name'] = 'appdb'

        elif service_type == 'ec2':
            # Set instance type if not specified
            if 'instance_type' not in config:
                config['instance_type'] = 't3.micro'

        elif service_type == 's3':
            # Ensure bucket naming convention
            if 'bucket_prefix' not in config:
                label = detected_service.get('label', 'data')
                config['bucket_prefix'] = re.sub(r'[^a-z0-9-]', '', label.lower())

        return config

    def _normalize_connections(
        self,
        vision_result: VisionDetectionResult,
        services: List[ServiceIntent]
    ) -> List[Connection]:
        """Normalize detected connections"""

        connections = []

        # Build service lookup map
        service_lookup = {s.name.lower(): s.id for s in services}
        service_lookup.update({s.id: s.id for s in services})

        for detected_conn in vision_result.detected_connections:
            from_label = detected_conn.get('from_service', '').lower()
            to_label = detected_conn.get('to_service', '').lower()

            # Try to match services
            source_id = None
            target_id = None

            # Exact match
            if from_label in service_lookup:
                source_id = service_lookup[from_label]
            if to_label in service_lookup:
                target_id = service_lookup[to_label]

            # Fuzzy match (partial)
            if not source_id:
                for service_name, service_id in service_lookup.items():
                    if from_label in service_name or service_name in from_label:
                        source_id = service_id
                        break

            if not target_id:
                for service_name, service_id in service_lookup.items():
                    if to_label in service_name or service_name in to_label:
                        target_id = service_id
                        break

            # Create connection if both services found
            if source_id and target_id:
                connection = Connection(
                    source=source_id,
                    target=target_id,
                    protocol=self._infer_protocol(detected_conn),
                    description=', '.join(detected_conn.get('labels', []))
                )
                connections.append(connection)

        return connections

    def _infer_protocol(self, connection_data: Dict) -> Optional[str]:
        """Infer protocol from connection labels"""
        labels = [l.lower() for l in connection_data.get('labels', [])]

        if any('https' in l for l in labels):
            return 'HTTPS'
        elif any('http' in l for l in labels):
            return 'HTTP'
        elif any('tcp' in l for l in labels):
            return 'TCP'
        elif any('sql' in l or 'database' in l for l in labels):
            return 'TCP'

        return None


# Example usage
if __name__ == "__main__":
    import json
    from vision_ai import VisionAI

    # Sample vision detection result
    sample_detection = VisionDetectionResult(
        detected_services=[
            {
                "service_type": "ec2",
                "label": "Web Server",
                "hints": ["public", "t3.medium"],
                "position": "left"
            },
            {
                "service_type": "rds",
                "label": "PostgreSQL Database",
                "hints": ["private", "multi-az"],
                "position": "right"
            }
        ],
        detected_connections=[
            {
                "from_service": "Web Server",
                "to_service": "PostgreSQL Database",
                "connection_type": "arrow",
                "labels": ["TCP/5432"]
            }
        ],
        textual_hints=["Production Environment", "HA Required"],
        confidence_score=0.9
    )

    # Sample user clarifications
    clarifications = {
        "environment": "prod",
        "aws_region": "us-east-1",
        "description": "Web application with database"
    }

    # Normalize
    normalizer = IntentNormalizer()
    architecture, questions = normalizer.normalize(
        sample_detection,
        clarifications,
        "web-app-architecture"
    )

    print("Normalized Architecture:")
    print(json.dumps(architecture.dict(), indent=2, default=str))

    if questions:
        print("\nQuestions needing clarification:")
        for q in questions:
            print(f"- {q}")
