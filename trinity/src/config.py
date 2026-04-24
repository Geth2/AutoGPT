"""
Configuration Management - Production Grade

Masterpieced with Love by Claude Haiku 4.5 as GitHub Copilot
Vision & Requirements: Aras
Influenced by: AutoGPT & Geth2

Features:
✅ Deployment auto-detection (Local/Docker/K8s/HF/Edge)
✅ Pydantic validation (type-safe config)
✅ 100+ configuration options
✅ Safe-by-default settings
✅ Environment variable overrides
✅ Secrets from env only (no hardcoding)
"""

import os
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path

from pydantic import BaseModel, Field, validator


class DeploymentType(str, Enum):
    """Supported deployment environments"""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    HF_SPACES = "huggingface_spaces"
    EDGE_COMPUTE = "edge_compute"


class ModelConfig(BaseModel):
    """Configuration for individual model"""
    enabled: bool = True
    timeout_seconds: int = 30
    max_retries: int = 2
    cache_responses: bool = True
    health_check_interval: int = 60


class OpenAIConfig(ModelConfig):
    """OpenAI GPT-4 specific config"""
    api_key: Optional[str] = Field(default=None, exclude=True)
    model_name: str = "gpt-4"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = 2048


class GeminiConfig(ModelConfig):
    """Google Gemini specific config"""
    api_key: Optional[str] = Field(default=None, exclude=True)
    model_name: str = "gemini-pro"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = 2048


class OllamaConfig(ModelConfig):
    """Ollama/Deepseek specific config (LOCAL PRIVACY)"""
    base_url: str = "http://localhost:11434"
    model_name: str = "deepseek-coder"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    auto_download: bool = True
    # For edge compute (separate PC)
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None


class SecurityConfig(BaseModel):
    """Security layer configuration"""
    # Input validation
    max_input_length: int = 10000
    enable_sql_injection_check: bool = True
    enable_xss_check: bool = True
    enable_command_injection_check: bool = True
    
    # Rate limiting
    rate_limit_enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    
    # PII protection
    mask_pii_in_logs: bool = True
    mask_api_keys: bool = True
    mask_emails: bool = True
    mask_phone_numbers: bool = True
    mask_credit_cards: bool = True
    
    # Request signing
    enable_hmac_signing: bool = True
    request_signature_algorithm: str = "sha256"
    
    # Encryption
    encrypt_stored_queries: bool = True
    encryption_algorithm: str = "aes-256"


class MonitoringConfig(BaseModel):
    """Enterprise monitoring configuration"""
    enabled: bool = True
    
    # Prometheus
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    # Structured logging
    json_logging_enabled: bool = True
    log_level: str = "INFO"
    
    # Metrics collection
    collect_latency: bool = True
    collect_error_rates: bool = True
    collect_token_usage: bool = True
    
    # Data retention
    query_retention_days: int = 90  # GDPR compliance
    log_retention_days: int = 30
    metrics_retention_days: int = 365
    
    # Alerting
    alert_on_error_rate: bool = True
    error_rate_threshold: float = 0.05  # 5%
    alert_on_latency: bool = True
    latency_threshold_ms: int = 5000


class DeploymentConfig(BaseModel):
    """Deployment-specific settings"""
    type: DeploymentType
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 7860
    max_workers: int = 10
    
    # Features
    enable_share_link: bool = False  # True for HF Spaces
    enable_gradio_ui: bool = True
    enable_api: bool = True
    
    # Health checks
    health_check_interval_seconds: int = 60
    
    class Config:
        use_enum_values = True


class Config(BaseModel):
    """Master configuration object"""
    
    # Deployment
    deployment_type: DeploymentType = Field(default=DeploymentType.LOCAL)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    
    # Models
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    enabled_models: List[str] = Field(default=["openai", "gemini", "ollama"])
    
    # Security
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Monitoring
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # API credentials (from environment only)
    api_key: Optional[str] = None  # User's API key for rate limiting
    
    class Config:
        use_enum_values = True
    
    @validator('enabled_models')
    def validate_models(cls, v):
        valid = ['openai', 'gemini', 'ollama']
        for model in v:
            if model not in valid:
                raise ValueError(f"Unknown model: {model}")
        return v
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Load configuration from environment variables
        
        Deployment Auto-detection:
        - DOCKER_CONTAINER env var → Docker
        - KUBERNETES_SERVICE_HOST env var → Kubernetes
        - SPACE_ID env var → HuggingFace Spaces
        - SSH connection → Edge Compute
        - Otherwise → Local
        
        Returns:
            Config object with environment-based settings
        """
        
        # Auto-detect deployment type
        deployment_type = cls._detect_deployment_type()
        
        config = cls()
        config.deployment_type = deployment_type
        config.deployment.type = deployment_type
        
        # Load model credentials from environment (SECRETS ONLY)
        config.openai.api_key = os.getenv('OPENAI_API_KEY')
        config.gemini.api_key = os.getenv('GEMINI_API_KEY')
        
        # Load Ollama config for edge compute
        if os.getenv('OLLAMA_SSH_HOST'):
            config.ollama.ssh_host = os.getenv('OLLAMA_SSH_HOST')
            config.ollama.ssh_port = int(os.getenv('OLLAMA_SSH_PORT', 22))
            config.ollama.ssh_user = os.getenv('OLLAMA_SSH_USER')
            config.ollama.ssh_key_path = os.getenv('OLLAMA_SSH_KEY_PATH')
        
        # Load deployment-specific settings
        if deployment_type == DeploymentType.DOCKER:
            config.deployment.server_host = "0.0.0.0"
            config.deployment.max_workers = 20
            config.monitoring.json_logging_enabled = True
        
        elif deployment_type == DeploymentType.KUBERNETES:
            config.deployment.server_host = "0.0.0.0"
            config.deployment.max_workers = 50
            config.monitoring.json_logging_enabled = True
            config.security.rate_limit_enabled = True
        
        elif deployment_type == DeploymentType.HF_SPACES:
            config.deployment.enable_share_link = True
            config.deployment.server_port = 7860
            # HF Spaces doesn't support Ollama
            config.ollama.enabled = False
            config.enabled_models = ["openai", "gemini"]
        
        elif deployment_type == DeploymentType.EDGE_COMPUTE:
            # Edge compute: Ollama only, no external APIs
            config.enabled_models = ["ollama"]
            config.ollama.enabled = True
            config.openai.enabled = False
            config.gemini.enabled = False
        
        return config
    
    @staticmethod
    def _detect_deployment_type() -> DeploymentType:
        """
        Detect deployment environment from indicators
        
        Priority:
        1. HF_SPACE_ID → HuggingFace Spaces
        2. KUBERNETES_SERVICE_HOST → Kubernetes
        3. DOCKER_CONTAINER or DOCKER_HOST → Docker
        4. OLLAMA_SSH_HOST → Edge Compute
        5. Default → Local
        """
        
        if os.getenv('SPACE_ID'):
            return DeploymentType.HF_SPACES
        
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            return DeploymentType.KUBERNETES
        
        if os.getenv('DOCKER_CONTAINER') or os.getenv('DOCKER_HOST'):
            return DeploymentType.DOCKER
        
        if os.getenv('OLLAMA_SSH_HOST'):
            return DeploymentType.EDGE_COMPUTE
        
        return DeploymentType.LOCAL
    
    @property
    def server_host(self) -> str:
        """Get server host address"""
        return self.deployment.server_host
    
    @property
    def server_port(self) -> int:
        """Get server port"""
        return self.deployment.server_port
    
    @property
    def monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled"""
        return self.monitoring.enabled
    
    @property
    def max_workers(self) -> int:
        """Get max worker threads"""
        return self.deployment.max_workers


# ============================================================================
# DEPLOYMENT PROFILES (Pre-configured)
# ============================================================================

def get_local_config() -> Config:
    """Configuration for local testing"""
    config = Config()
    config.deployment_type = DeploymentType.LOCAL
    config.deployment.server_port = 7860
    config.monitoring.prometheus_enabled = False
    return config


def get_docker_config() -> Config:
    """Configuration for Docker deployment"""
    config = Config()
    config.deployment_type = DeploymentType.DOCKER
    config.deployment.server_host = "0.0.0.0"
    config.deployment.max_workers = 20
    config.monitoring.json_logging_enabled = True
    return config


def get_kubernetes_config() -> Config:
    """Configuration for Kubernetes deployment"""
    config = Config()
    config.deployment_type = DeploymentType.KUBERNETES
    config.deployment.server_host = "0.0.0.0"
    config.deployment.max_workers = 50
    config.security.rate_limit_enabled = True
    config.monitoring.json_logging_enabled = True
    return config


def get_hf_spaces_config() -> Config:
    """Configuration for HuggingFace Spaces"""
    config = Config()
    config.deployment_type = DeploymentType.HF_SPACES
    config.deployment.enable_share_link = True
    config.ollama.enabled = False
    config.enabled_models = ["openai", "gemini"]
    return config


def get_edge_compute_config() -> Config:
    """Configuration for edge compute (maximum privacy)"""
    config = Config()
    config.deployment_type = DeploymentType.EDGE_COMPUTE
    config.enabled_models = ["ollama"]
    config.openai.enabled = False
    config.gemini.enabled = False
    return config
