"""
Architecture Schema - Normalized representation of infrastructure intent
This schema is the single source of truth for Terraform generation
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class Environment(str, Enum):
    """Environment types"""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class ServiceCategory(str, Enum):
    """AWS Service Categories"""
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORKING = "networking"
    SECURITY = "security"
    ANALYTICS = "analytics"
    ML_AI = "ml_ai"
    CONTAINER = "container"
    SERVERLESS = "serverless"
    MESSAGING = "messaging"


class NetworkExposure(str, Enum):
    """Service network exposure"""
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"


class HighAvailability(str, Enum):
    """HA configuration"""
    SINGLE_AZ = "single_az"
    MULTI_AZ = "multi_az"
    MULTI_REGION = "multi_region"


class Connection(BaseModel):
    """Connection between services"""
    source: str = Field(..., description="Source service ID")
    target: str = Field(..., description="Target service ID")
    protocol: Optional[str] = Field(None, description="Protocol (e.g., HTTPS, TCP)")
    port: Optional[int] = Field(None, description="Port number")
    description: Optional[str] = Field(None, description="Connection description")


class ServiceIntent(BaseModel):
    """Normalized service intent"""
    id: str = Field(..., description="Unique service identifier")
    service_type: str = Field(..., description="AWS service type (e.g., ec2, s3, rds)")
    name: str = Field(..., description="Service name")
    category: ServiceCategory

    # Configuration intent
    environment: Environment = Environment.DEV
    network_exposure: NetworkExposure = NetworkExposure.PRIVATE
    high_availability: HighAvailability = HighAvailability.SINGLE_AZ

    # Service-specific configuration
    configuration: Dict = Field(default_factory=dict, description="Service-specific config")

    # Metadata
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class NetworkIntent(BaseModel):
    """Network configuration intent"""
    vpc_cidr: str = Field(default="10.0.0.0/16", description="VPC CIDR block")
    availability_zones: int = Field(default=2, ge=1, le=6, description="Number of AZs")
    enable_nat_gateway: bool = Field(default=True, description="Enable NAT Gateway")
    enable_vpn: bool = Field(default=False, description="Enable VPN")
    enable_transit_gateway: bool = Field(default=False, description="Enable Transit Gateway")


class SecurityIntent(BaseModel):
    """Security configuration intent"""
    enable_encryption_at_rest: bool = Field(default=True)
    enable_encryption_in_transit: bool = Field(default=True)
    enable_logging: bool = Field(default=True)
    enable_monitoring: bool = Field(default=True)
    enable_backup: bool = Field(default=True)
    compliance_frameworks: List[str] = Field(default_factory=list, description="e.g., HIPAA, PCI-DSS")


class CostIntent(BaseModel):
    """Cost and FinOps configuration"""
    budget_limit: Optional[float] = Field(None, description="Monthly budget limit in USD")
    cost_allocation_tags: Dict[str, str] = Field(default_factory=dict)
    enable_cost_optimization: bool = Field(default=True)
    enable_auto_scaling: bool = Field(default=False)


class ArchitectureIntent(BaseModel):
    """
    Complete normalized architecture intent
    This is the single source of truth for infrastructure generation
    """
    # Metadata
    architecture_name: str
    description: str
    version: str = "1.0.0"

    # Global configuration
    environment: Environment = Environment.DEV
    aws_region: str = Field(default="us-east-1")

    # Intent layers
    network: NetworkIntent = Field(default_factory=NetworkIntent)
    security: SecurityIntent = Field(default_factory=SecurityIntent)
    cost: CostIntent = Field(default_factory=CostIntent)

    # Services and connections
    services: List[ServiceIntent] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)

    # Additional metadata
    tags: Dict[str, str] = Field(default_factory=dict)

    def get_service_by_id(self, service_id: str) -> Optional[ServiceIntent]:
        """Get service by ID"""
        for service in self.services:
            if service.id == service_id:
                return service
        return None

    def get_services_by_category(self, category: ServiceCategory) -> List[ServiceIntent]:
        """Get all services in a category"""
        return [s for s in self.services if s.category == category]

    def get_connections_for_service(self, service_id: str) -> List[Connection]:
        """Get all connections involving a service"""
        return [c for c in self.connections if c.source == service_id or c.target == service_id]

    def validate_architecture(self) -> tuple[bool, List[str]]:
        """
        Validate architecture intent
        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Validate all service IDs are unique
        service_ids = [s.id for s in self.services]
        if len(service_ids) != len(set(service_ids)):
            errors.append("Duplicate service IDs found")

        # Validate connections reference existing services
        for conn in self.connections:
            if not self.get_service_by_id(conn.source):
                errors.append(f"Connection references non-existent source: {conn.source}")
            if not self.get_service_by_id(conn.target):
                errors.append(f"Connection references non-existent target: {conn.target}")

        # Validate HA requirements for production
        if self.environment == Environment.PROD:
            for service in self.services:
                if service.high_availability == HighAvailability.SINGLE_AZ:
                    errors.append(f"Service {service.id} requires Multi-AZ for production")

        return len(errors) == 0, errors


class VisionDetectionResult(BaseModel):
    """Result from Vision AI - what was detected in the diagram"""
    detected_services: List[Dict] = Field(default_factory=list,
                                          description="Raw services detected from image")
    detected_connections: List[Dict] = Field(default_factory=list,
                                            description="Raw connections detected")
    textual_hints: List[str] = Field(default_factory=list,
                                     description="Text extracted from diagram")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_analysis: str = Field(default="", description="Raw vision AI output")
