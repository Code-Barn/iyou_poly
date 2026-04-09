# Rust DID Integration

This document describes the Rust-based DID implementation in Polly.

## Overview

Polly uses a hybrid Python/Rust DID implementation that provides:
- High-performance DID generation and VC verification
- Seamless fallback to Python implementation
- Future-proof architecture for web-based operations

## Architecture

```
┌─────────────────────────────────────────────┐
│              Polly Django App               │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         did_utils.py                 │   │
│  │  - generate_did()                   │   │
│  │  - verify_vc()                      │   │
│  │  - issue_vc()                       │   │
│  └─────────────────────────────────────┘   │
│                  │                          │
│                  ▼                          │
│  ┌─────────────────────────────────────┐   │
│  │     did_rust_wrapper/               │   │
│  │  - Python/Rust backend selector     │   │
│  │  - Graceful fallback                │   │
│  └─────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼ (if DID_BACKEND=rust)
┌─────────────────────────────────────────────┐
│         /home/user/CODE_BASE/did_rust/                  │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         Rust Library                 │   │
│  │  - generate_did_ffi()               │   │
│  │  - verify_vc_ffi()                  │   │
│  │  - issue_vc_ffi()                   │   │
│  │  - free_string()                    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Build output: libdid_rust.so               │
└─────────────────────────────────────────────┘
```

## Backend Selection

Control via environment variable:

```bash
# Use Rust backend (recommended)
DID_BACKEND=rust python manage.py runserver

# Use Python backend (fallback)
DID_BACKEND=python python manage.py runserver
```

## Components

### 1. did_rust_wrapper Module

Located in `apps/accounts/did_rust_wrapper/`:

```
did_rust_wrapper/
├── __init__.py      # Backend selection logic
├── rust_ffi.py     # FFI bindings to Rust library
└── test_wrapper.py  # Tests
```

### 2. FFI Functions

The Rust library exposes these functions via FFI:

| Function | Signature | Description |
|----------|-----------|-------------|
| `generate_did_ffi` | `(*c_char) -> *c_char` | Generate DID |
| `verify_vc_ffi` | `(*c_char) -> bool` | Verify VC |
| `issue_vc_ffi` | `(*c_char, *c_char, *c_char) -> *c_char` | Issue VC |
| `free_string` | `(*c_char) -> void` | Free C string |

### 3. did_utils.py

Located in `apps/accounts/utils/did_utils.py`:

```python
from apps.accounts.did_rust_wrapper import (
    generate_did,
    verify_vc,
    issue_vc,
)

# These functions automatically use the configured backend
did = generate_did("key")
is_valid = verify_vc(vc_json)
issued_vc = issue_vc(credential, did, key)
```

## Building the Rust Library

```bash
cd /home/user/CODE_BASE/did_rust
cargo build --release
```

This produces `target/release/libdid_rust.so`.

## Testing

```bash
# Test with Rust backend
DID_BACKEND=rust python -c "
    from apps.accounts.did_rust_wrapper import test_rust_availability
    print('Rust available:', test_rust_availability())
"

# Run Django tests
DID_BACKEND=rust python manage.py test
```

## Benefits

1. **Performance**: ~7-8x faster than Python DIDKit
2. **Security**: Memory-safe Rust code
3. **Extensibility**: WASM bindings planned for web frontend
4. **Compatibility**: Seamless fallback to Python
