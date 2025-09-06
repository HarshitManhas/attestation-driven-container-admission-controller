#!/usr/bin/env python3
"""
Policy Configuration System for Image Attestation
Provides flexible policy management for attestation requirements
"""

import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path
from image_attestation import AttestationPolicy

logger = logging.getLogger(__name__)

@dataclass
class NamespacePolicy:
    """Policy configuration for specific namespaces"""
    namespace: str
    require_signature: bool = True
    allowed_signers: Optional[List[str]] = None
    allowed_registries: Optional[List[str]] = None
    require_transparency_log: bool = True
    min_slsa_level: Optional[int] = None
    require_provenance: bool = False
    custom_rules: Optional[Dict[str, Any]] = None

@dataclass
class ImagePolicy:
    """Policy configuration for specific images or image patterns"""
    image_pattern: str  # e.g., "nginx:*", "myregistry.io/*", "*"
    require_signature: bool = True
    allowed_signers: Optional[List[str]] = None
    priority: int = 0  # Higher priority overrides lower priority
    description: Optional[str] = None

@dataclass
class GlobalPolicy:
    """Global policy configuration"""
    default_require_signature: bool = True
    default_allowed_registries: Optional[List[str]] = None
    default_allowed_signers: Optional[List[str]] = None
    require_transparency_log: bool = True
    require_certificate_chain: bool = False
    min_slsa_level: int = 0
    require_provenance: bool = False
    
    # Exemptions
    exempt_namespaces: List[str] = field(default_factory=lambda: ["kube-system", "kube-public", "kube-node-lease"])
    exempt_images: List[str] = field(default_factory=list)
    
    # Emergency settings
    emergency_bypass: bool = False
    emergency_bypass_token: Optional[str] = None

@dataclass 
class PolicyConfiguration:
    """Complete policy configuration"""
    global_policy: GlobalPolicy = field(default_factory=GlobalPolicy)
    namespace_policies: List[NamespacePolicy] = field(default_factory=list)
    image_policies: List[ImagePolicy] = field(default_factory=list)
    version: str = "1.0"
    last_updated: Optional[str] = None

class PolicyManager:
    """Manages policy configuration and evaluation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize policy manager
        
        Args:
            config_path: Path to policy configuration file
        """
        self.config_path = config_path or os.getenv('POLICY_CONFIG_PATH', '/etc/attestation/policy.yaml')
        self.policy_config: PolicyConfiguration = PolicyConfiguration()
        self._load_policy()
    
    def _load_policy(self):
        """Load policy configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                self._parse_config(config_data)
                logger.info(f"Loaded policy configuration from {self.config_path}")
            else:
                logger.warning(f"Policy config file not found: {self.config_path}. Using default policy.")
                self._load_default_policy()
        except Exception as e:
            logger.error(f"Failed to load policy configuration: {e}")
            self._load_default_policy()
    
    def _parse_config(self, config_data: Dict[str, Any]):
        """Parse configuration data into PolicyConfiguration"""
        try:
            # Parse global policy
            if 'global' in config_data:
                global_data = config_data['global']
                self.policy_config.global_policy = GlobalPolicy(
                    default_require_signature=global_data.get('default_require_signature', True),
                    default_allowed_registries=global_data.get('default_allowed_registries'),
                    default_allowed_signers=global_data.get('default_allowed_signers'),
                    require_transparency_log=global_data.get('require_transparency_log', True),
                    require_certificate_chain=global_data.get('require_certificate_chain', False),
                    min_slsa_level=global_data.get('min_slsa_level', 0),
                    require_provenance=global_data.get('require_provenance', False),
                    exempt_namespaces=global_data.get('exempt_namespaces', ["kube-system", "kube-public", "kube-node-lease"]),
                    exempt_images=global_data.get('exempt_images', []),
                    emergency_bypass=global_data.get('emergency_bypass', False),
                    emergency_bypass_token=global_data.get('emergency_bypass_token')
                )
            
            # Parse namespace policies
            if 'namespaces' in config_data:
                namespace_policies = []
                for ns_data in config_data['namespaces']:
                    ns_policy = NamespacePolicy(
                        namespace=ns_data['namespace'],
                        require_signature=ns_data.get('require_signature', True),
                        allowed_signers=ns_data.get('allowed_signers'),
                        allowed_registries=ns_data.get('allowed_registries'),
                        require_transparency_log=ns_data.get('require_transparency_log', True),
                        min_slsa_level=ns_data.get('min_slsa_level'),
                        require_provenance=ns_data.get('require_provenance', False),
                        custom_rules=ns_data.get('custom_rules')
                    )
                    namespace_policies.append(ns_policy)
                self.policy_config.namespace_policies = namespace_policies
            
            # Parse image policies
            if 'images' in config_data:
                image_policies = []
                for img_data in config_data['images']:
                    img_policy = ImagePolicy(
                        image_pattern=img_data['image_pattern'],
                        require_signature=img_data.get('require_signature', True),
                        allowed_signers=img_data.get('allowed_signers'),
                        priority=img_data.get('priority', 0),
                        description=img_data.get('description')
                    )
                    image_policies.append(img_policy)
                
                # Sort by priority (highest first)
                image_policies.sort(key=lambda x: x.priority, reverse=True)
                self.policy_config.image_policies = image_policies
            
            self.policy_config.version = config_data.get('version', '1.0')
            self.policy_config.last_updated = config_data.get('last_updated')
            
        except Exception as e:
            logger.error(f"Error parsing policy configuration: {e}")
            raise
    
    def _load_default_policy(self):
        """Load default policy from environment variables"""
        self.policy_config = PolicyConfiguration(
            global_policy=GlobalPolicy(
                default_require_signature=os.getenv('ATTESTATION_REQUIRE_SIGNATURE', 'true').lower() == 'true',
                default_allowed_registries=self._parse_env_list('ATTESTATION_ALLOWED_REGISTRIES'),
                default_allowed_signers=self._parse_env_list('ATTESTATION_ALLOWED_SIGNERS'),
                require_transparency_log=os.getenv('ATTESTATION_REQUIRE_TRANSPARENCY_LOG', 'true').lower() == 'true',
                require_certificate_chain=os.getenv('ATTESTATION_REQUIRE_CERT_CHAIN', 'false').lower() == 'true',
                min_slsa_level=int(os.getenv('ATTESTATION_MIN_SLSA_LEVEL', '0')),
                require_provenance=os.getenv('ATTESTATION_REQUIRE_PROVENANCE', 'false').lower() == 'true',
                exempt_namespaces=self._parse_env_list('ATTESTATION_EXEMPT_NAMESPACES') or ["kube-system", "kube-public", "kube-node-lease"],
                exempt_images=self._parse_env_list('ATTESTATION_EXEMPT_IMAGES') or [],
                emergency_bypass=os.getenv('ATTESTATION_EMERGENCY_BYPASS', 'false').lower() == 'true',
                emergency_bypass_token=os.getenv('ATTESTATION_EMERGENCY_BYPASS_TOKEN')
            )
        )
        logger.info("Loaded default policy configuration from environment variables")
    
    def _parse_env_list(self, env_var: str) -> Optional[List[str]]:
        """Parse comma-separated environment variable into list"""
        value = os.getenv(env_var, '').strip()
        if value:
            return [item.strip() for item in value.split(',') if item.strip()]
        return None
    
    def get_policy_for_request(self, namespace: str, image: str) -> AttestationPolicy:
        """
        Get the applicable policy for a specific namespace and image
        
        Args:
            namespace: Kubernetes namespace
            image: Container image reference
            
        Returns:
            AttestationPolicy to apply
        """
        # Check if namespace is exempt
        if namespace in self.policy_config.global_policy.exempt_namespaces:
            logger.debug(f"Namespace {namespace} is exempt from attestation requirements")
            return AttestationPolicy(require_signature=False)
        
        # Check if image is exempt
        if self._is_image_exempt(image):
            logger.debug(f"Image {image} is exempt from attestation requirements")
            return AttestationPolicy(require_signature=False)
        
        # Start with global policy defaults
        policy = AttestationPolicy(
            require_signature=self.policy_config.global_policy.default_require_signature,
            allowed_signers=self.policy_config.global_policy.default_allowed_signers,
            require_transparency_log=self.policy_config.global_policy.require_transparency_log,
            require_certificate_chain=self.policy_config.global_policy.require_certificate_chain,
            allowed_registries=self.policy_config.global_policy.default_allowed_registries,
            min_slsa_level=self.policy_config.global_policy.min_slsa_level,
            require_provenance=self.policy_config.global_policy.require_provenance
        )
        
        # Apply namespace-specific policy overrides
        ns_policy = self._find_namespace_policy(namespace)
        if ns_policy:
            policy = self._merge_namespace_policy(policy, ns_policy)
        
        # Apply image-specific policy overrides
        img_policy = self._find_image_policy(image)
        if img_policy:
            policy = self._merge_image_policy(policy, img_policy)
        
        return policy
    
    def _is_image_exempt(self, image: str) -> bool:
        """Check if image is in the exempt list"""
        for exempt_pattern in self.policy_config.global_policy.exempt_images:
            if self._match_pattern(image, exempt_pattern):
                return True
        return False
    
    def _find_namespace_policy(self, namespace: str) -> Optional[NamespacePolicy]:
        """Find policy for specific namespace"""
        for ns_policy in self.policy_config.namespace_policies:
            if ns_policy.namespace == namespace:
                return ns_policy
        return None
    
    def _find_image_policy(self, image: str) -> Optional[ImagePolicy]:
        """Find the highest priority matching image policy"""
        for img_policy in self.policy_config.image_policies:
            if self._match_pattern(image, img_policy.image_pattern):
                return img_policy
        return None
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Simple pattern matching with wildcards"""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return text == pattern
        
        # Simple wildcard matching
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return text.startswith(prefix) and text.endswith(suffix)
        
        # For more complex patterns, you might want to use fnmatch or regex
        import fnmatch
        return fnmatch.fnmatch(text, pattern)
    
    def _merge_namespace_policy(self, base_policy: AttestationPolicy, ns_policy: NamespacePolicy) -> AttestationPolicy:
        """Merge namespace policy with base policy"""
        return AttestationPolicy(
            require_signature=ns_policy.require_signature,
            allowed_signers=ns_policy.allowed_signers or base_policy.allowed_signers,
            require_transparency_log=ns_policy.require_transparency_log,
            require_certificate_chain=base_policy.require_certificate_chain,
            allowed_registries=ns_policy.allowed_registries or base_policy.allowed_registries,
            min_slsa_level=ns_policy.min_slsa_level or base_policy.min_slsa_level,
            require_provenance=ns_policy.require_provenance
        )
    
    def _merge_image_policy(self, base_policy: AttestationPolicy, img_policy: ImagePolicy) -> AttestationPolicy:
        """Merge image policy with base policy"""
        return AttestationPolicy(
            require_signature=img_policy.require_signature,
            allowed_signers=img_policy.allowed_signers or base_policy.allowed_signers,
            require_transparency_log=base_policy.require_transparency_log,
            require_certificate_chain=base_policy.require_certificate_chain,
            allowed_registries=base_policy.allowed_registries,
            min_slsa_level=base_policy.min_slsa_level,
            require_provenance=base_policy.require_provenance
        )
    
    def is_emergency_bypass_enabled(self, bypass_token: Optional[str] = None) -> bool:
        """Check if emergency bypass is enabled and token matches"""
        if not self.policy_config.global_policy.emergency_bypass:
            return False
        
        if self.policy_config.global_policy.emergency_bypass_token:
            return bypass_token == self.policy_config.global_policy.emergency_bypass_token
        
        return True  # Emergency bypass enabled without token
    
    def reload_policy(self):
        """Reload policy configuration from file"""
        logger.info("Reloading policy configuration")
        self._load_policy()
    
    def save_policy(self, output_path: Optional[str] = None):
        """Save current policy configuration to file"""
        output_path = output_path or self.config_path
        
        config_data = {
            'version': self.policy_config.version,
            'last_updated': self.policy_config.last_updated,
            'global': asdict(self.policy_config.global_policy),
            'namespaces': [asdict(ns) for ns in self.policy_config.namespace_policies],
            'images': [asdict(img) for img in self.policy_config.image_policies]
        }
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                if output_path.endswith('.yaml') or output_path.endswith('.yml'):
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2)
            
            logger.info(f"Policy configuration saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save policy configuration: {e}")
            raise
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get a summary of the current policy configuration"""
        return {
            'version': self.policy_config.version,
            'global_policy': {
                'require_signature': self.policy_config.global_policy.default_require_signature,
                'exempt_namespaces': self.policy_config.global_policy.exempt_namespaces,
                'exempt_images': self.policy_config.global_policy.exempt_images
            },
            'namespace_policies_count': len(self.policy_config.namespace_policies),
            'image_policies_count': len(self.policy_config.image_policies),
            'emergency_bypass': self.policy_config.global_policy.emergency_bypass
        }


def create_sample_policy_config() -> Dict[str, Any]:
    """Create a sample policy configuration for reference"""
    return {
        "version": "1.0",
        "last_updated": "2024-01-01T00:00:00Z",
        "global": {
            "default_require_signature": True,
            "default_allowed_registries": ["docker.io", "gcr.io", "quay.io"],
            "default_allowed_signers": ["security@company.com", "ci-system@company.com"],
            "require_transparency_log": True,
            "require_certificate_chain": False,
            "min_slsa_level": 1,
            "require_provenance": False,
            "exempt_namespaces": ["kube-system", "kube-public", "kube-node-lease"],
            "exempt_images": ["pause:*", "coredns:*"],
            "emergency_bypass": False,
            "emergency_bypass_token": "emergency-token-123"
        },
        "namespaces": [
            {
                "namespace": "production",
                "require_signature": True,
                "allowed_signers": ["production@company.com"],
                "require_transparency_log": True,
                "min_slsa_level": 3,
                "require_provenance": True
            },
            {
                "namespace": "development",
                "require_signature": False,
                "allowed_registries": ["localhost:5000", "docker.io"]
            }
        ],
        "images": [
            {
                "image_pattern": "nginx:*",
                "require_signature": True,
                "allowed_signers": ["nginx-maintainer@nginx.org"],
                "priority": 10,
                "description": "Official nginx images require signature"
            },
            {
                "image_pattern": "localhost:5000/*",
                "require_signature": False,
                "priority": 5,
                "description": "Local development registry"
            }
        ]
    }
