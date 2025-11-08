"""
C2PA (Content Authenticity Initiative) Validation Utilities

Implements C2PA provenance support per TAMS App Note 0011.
"""

import logging
import json
from typing import Dict, Optional, Any
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class C2PAAssertion(BaseModel):
    """C2PA assertion metadata"""
    
    assertion_type: str
    assertion_data: Dict[str, Any]
    signature: Optional[str] = None


class C2PAManifest(BaseModel):
    """C2PA manifest for provenance"""
    
    version: str = "1.0"
    assertions: list[C2PAAssertion] = []
    metadata: Dict[str, Any] = {}


class C2PAValidator:
    """Validate C2PA provenance metadata"""
    
    @staticmethod
    def validate_c2pa_metadata(metadata: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate C2PA metadata structure
        
        Args:
            metadata: Metadata dictionary that may contain C2PA data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for C2PA-specific fields
            c2pa_data = metadata.get('c2pa', metadata.get('C2PA'))
            
            if not c2pa_data:
                return True, None  # No C2PA data is acceptable
            
            # Validate C2PA manifest structure
            if isinstance(c2pa_data, dict):
                # Check for required fields
                if 'version' in c2pa_data and 'assertions' in c2pa_data:
                    assertions = c2pa_data.get('assertions', [])
                    
                    # Validate each assertion
                    for assertion in assertions:
                        if not isinstance(assertion, dict):
                            return False, "C2PA assertion must be an object"
                        
                        if 'assertion_type' not in assertion:
                            return False, "C2PA assertion missing 'assertion_type'"
                        
                        if 'assertion_data' not in assertion:
                            return False, "C2PA assertion missing 'assertion_data'"
                    
                    return True, None
                else:
                    return False, "C2PA manifest missing 'version' or 'assertions'"
            else:
                return False, "C2PA data must be an object"
                
        except Exception as e:
            logger.error(f"Error validating C2PA metadata: {e}")
            return False, str(e)
    
    @staticmethod
    def extract_c2pa_from_tags(tags: Dict[str, Any]) -> Optional[C2PAManifest]:
        """
        Extract C2PA manifest from TAMS tags
        
        Args:
            tags: Tags dictionary
            
        Returns:
            C2PAManifest if found, None otherwise
        """
        try:
            # Look for C2PA data in tags
            c2pa_tag = tags.get('c2pa') or tags.get('C2PA') or tags.get('c2pa_manifest')
            
            if not c2pa_tag:
                return None
            
            # Parse JSON if it's a string
            if isinstance(c2pa_tag, str):
                c2pa_data = json.loads(c2pa_tag)
            else:
                c2pa_data = c2pa_tag
            
            # Convert to C2PAManifest
            assertions = []
            for assertion in c2pa_data.get('assertions', []):
                assertions.append(C2PAAssertion(**assertion))
            
            manifest = C2PAManifest(
                version=c2pa_data.get('version', '1.0'),
                assertions=assertions,
                metadata=c2pa_data.get('metadata', {})
            )
            
            return manifest
            
        except Exception as e:
            logger.warning(f"Failed to extract C2PA from tags: {e}")
            return None
    
    @staticmethod
    def create_c2pa_tag(manifest: C2PAManifest) -> Dict[str, Any]:
        """
        Create C2PA tag for storage in TAMS
        
        Args:
            manifest: C2PA manifest
            
        Returns:
            Dictionary with C2PA tag data
        """
        return {
            'c2pa': {
                'version': manifest.version,
                'assertions': [assertion.model_dump() for assertion in manifest.assertions],
                'metadata': manifest.metadata
            }
        }
    
    @staticmethod
    def validate_c2pa_chain(manifest: C2PAManifest) -> tuple[bool, Optional[str]]:
        """
        Validate C2PA assertion chain
        
        Args:
            manifest: C2PA manifest
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic chain validation
            if not manifest.assertions:
                return True, None  # Empty chain is valid
            
            # Check for claim and signature assertions
            has_claim = False
            has_signature = False
            
            for assertion in manifest.assertions:
                if assertion.assertion_type == 'claim':
                    has_claim = True
                if assertion.assertion_type == 'signature' or assertion.signature:
                    has_signature = True
            
            if not has_claim:
                return False, "C2PA manifest must contain at least one claim"
            
            # Signature validation would require cryptographic verification
            # This is a placeholder for future implementation
            if has_signature:
                logger.debug("C2PA signature present but not cryptographically verified")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating C2PA chain: {e}")
            return False, str(e)


def validate_c2pa_in_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Convenience function to validate C2PA in metadata
    
    Args:
        metadata: Metadata dictionary
        
    Returns:
        True if valid or no C2PA data, False if invalid
    """
    is_valid, _ = C2PAValidator.validate_c2pa_metadata(metadata)
    return is_valid


def extract_c2pa_provenance(source_id: str, flow_id: str, tags: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract C2PA provenance from flow/source tags
    
    Args:
        source_id: Source identifier
        flow_id: Flow identifier
        tags: Tags dictionary
        
    Returns:
        C2PA provenance data or None
    """
    try:
        validator = C2PAValidator()
        manifest = validator.extract_c2pa_from_tags(tags)
        
        if manifest:
            # Validate the manifest
            is_valid, error = validator.validate_c2pa_chain(manifest)
            if not is_valid:
                logger.warning(f"C2PA validation failed: {error}")
                return None
            
            return {
                'source_id': source_id,
                'flow_id': flow_id,
                'manifest': manifest.model_dump(),
                'valid': True
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to extract C2PA provenance: {e}")
        return None

