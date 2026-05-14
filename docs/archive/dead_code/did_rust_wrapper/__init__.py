"""
DID Rust Wrapper - Hybrid Python/Rust DID Implementation

This module provides a unified interface for DID operations that can switch
between Python and Rust implementations. Currently uses Python as fallback.
"""

import os
import json
from typing import Optional, Dict, Any

# Environment variable to control which implementation to use
DID_BACKEND = os.environ.get('DID_BACKEND', 'python')  # 'python' or 'rust'


class DIDBackend:
    """Base class for DID backends"""
    
    def generate_did(self, method: str = "key") -> str:
        """Generate a new DID"""
        raise NotImplementedError
    
    def verify_vc(self, vc_json: str) -> bool:
        """Verify a verifiable credential"""
        raise NotImplementedError
    
    def issue_vc(self, credential: Dict, did: str, key: str) -> Optional[str]:
        """Issue a verifiable credential"""
        raise NotImplementedError


class PythonDIDBackend(DIDBackend):
    """Python implementation using didkit (current fallback)"""
    
    def __init__(self):
        self.didkit_available = False
        try:
            import didkit
            self.didkit = didkit
            self.didkit_available = True
        except ImportError:
            print("didkit not available, using mock implementation")
            self.didkit_available = False
    
    def generate_did(self, method: str = "key") -> str:
        """Generate DID using didkit or mock"""
        if self.didkit_available and method == "key":
            key = self.didkit.generateEd25519Key()
            return self.didkit.keyToDID("key", key)
        # Mock implementation for testing
        import uuid
        return f"did:key:test-{uuid.uuid4().hex[:16]}"
    
    def verify_vc(self, vc_json: str) -> bool:
        """Verify VC using didkit or mock"""
        if self.didkit_available:
            try:
                result = self.didkit.verifyCredential(vc_json, '{"proofPurpose": "assertionMethod"}')
                verification_result = json.loads(result)
                return not verification_result.get("errors")
            except Exception:
                return False
        # Mock implementation - accept any non-empty JSON
        try:
            data = json.loads(vc_json)
            return bool(data and isinstance(data, dict))
        except Exception:
            return False
    
    def issue_vc(self, credential: Dict, did: str, key: str) -> Optional[str]:
        """Issue VC using didkit or mock"""
        if self.didkit_available:
            try:
                options = {
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": f"{did}#{did.split(':')[-1]}"
                }
                return self.didkit.issueCredential(
                    json.dumps(credential),
                    json.dumps(options),
                    key
                )
            except Exception as e:
                print(f"Failed to issue VC: {e}")
                return None
        # Mock implementation - return credential with mock proof
        mock_vc = dict(credential)
        mock_vc["proof"] = {
            "type": "MockProof",
            "created": "2023-01-01T00:00:00Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"{did}#mock-key",
            "jws": "mock-signature"
        }
        return json.dumps(mock_vc)


class RustDIDBackend(DIDBackend):
    """Rust implementation using FFI (future implementation)"""
    
    def __init__(self):
        self._loaded = False
        try:
            from .rust_ffi import RustDIDFFI
            self.ffi = RustDIDFFI()
            self._loaded = True
        except ImportError:
            print("Rust DID backend not available, falling back to Python")
            self._loaded = False
    
    def _ensure_loaded(self):
        if not self._loaded:
            raise RuntimeError("Rust backend not available")
    
    def generate_did(self, method: str = "key") -> str:
        self._ensure_loaded()
        return self.ffi.generate_did(method)
    
    def verify_vc(self, vc_json: str) -> bool:
        self._ensure_loaded()
        return self.ffi.verify_vc(vc_json)
    
    def issue_vc(self, credential: Dict, did: str, key: str) -> Optional[str]:
        self._ensure_loaded()
        return self.ffi.issue_vc(credential, did, key)


def get_did_backend() -> DIDBackend:
    """Get the appropriate DID backend based on configuration"""
    if DID_BACKEND == "rust":
        try:
            return RustDIDBackend()
        except Exception:
            print("Failed to load Rust backend, falling back to Python")
    
    return PythonDIDBackend()


# Global backend instance
backend = get_did_backend()

# Export test function for external use
from .rust_ffi import test_rust_availability


def generate_did(method: str = "key") -> str:
    """Generate a new DID using the configured backend"""
    return backend.generate_did(method)


def verify_vc(vc_json: str) -> bool:
    """Verify a verifiable credential using the configured backend"""
    return backend.verify_vc(vc_json)


def issue_vc(credential: Dict, did: str, key: str) -> Optional[str]:
    """Issue a verifiable credential using the configured backend"""
    return backend.issue_vc(credential, did, key)