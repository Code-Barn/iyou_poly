{
  "credential": {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential", "MembershipCredential"],
    "issuer": "did:key:z6MkexampleDID",
    "issuanceDate": "2023-01-01T00:00:00Z",
    "credentialSubject": {
      "id": "did:key:z6MkexampleDID",
      "name": "username",
      "description": "Credential description"
    },
    "proof": {
      "type": "Ed25519Signature2018",
      "proofPurpose": "assertionMethod",
      "verificationMethod": "did:key:z6MkexampleDID#key-1",
      "created": "2023-01-01T00:00:00Z",
      "jws": "exampleJWS"
    }
  },
  "name": "Custom Credential Name",
  "added_date": "2023-01-01T00:00:00.000000Z"
}
```

## Features

### Custom Naming
Users can assign meaningful, descriptive names to credentials for easy identification and organization.

### Added Date Tracking
Each credential displays when it was added to the user's wallet, helping users track credential history.

### Credential Generation
Users can generate new credentials with custom types and attributes:
- Membership credentials
- Professional credentials
- Certification credentials
- Role credentials
- Attribute credentials

### Credential Import
Existing credentials can be imported from JSON data with optional custom naming.

### Credential Deletion
Users can delete credentials they no longer need:
- Delete button appears next to each credential
- Confirmation dialog prevents accidental deletion
- Authentication credentials cannot be deleted
- UI updates automatically after deletion

### Format Migration
The system automatically migrates legacy credentials (without metadata) to the new format with metadata.

## VC Management Interface

### Authentication Credential
- Displayed separately from other credentials
- Cannot be deleted (used for authentication)
- Can be copied and downloaded

### Other Credentials
- Displayed in a list with names and added dates
- Can be copied, downloaded, or deleted
- Can be generated or imported

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/accounts/vcs/` | GET | View VC management page |
| `/accounts/generate_credential/` | GET/POST | Generate new credential |
| `/accounts/import_credential/` | GET/POST | Import existing credential |
| `/accounts/update_vc_name/` | POST | Update credential name |
| `/accounts/delete_credential/` | POST | Delete a credential |

## Security Considerations

1. **Authentication**: All VC management endpoints require authentication
2. **CSRF Protection**: All POST requests are protected with CSRF tokens
3. **Input Validation**: All credential data is validated before processing
4. **Data Isolation**: Each user can only access their own credentials
5. **Secure Storage**: Credentials are stored securely in the database
6. **Protection**: Authentication credentials cannot be deleted

## Usage

### Generating a Credential
1. Navigate to the VC management page
2. Click "Generate Credential"
3. Enter a descriptive name for the credential
4. Select the appropriate credential type
5. Click "Generate Credential"

### Importing a Credential
1. Navigate to the VC management page
2. Click "Import Credential"
3. (Optional) Enter a custom name for the credential
4. Paste the credential JSON data into the text area
5. Click "Import Credential"

### Deleting a Credential
1. Find the credential you want to delete in the list
2. Click the "Delete" button next to the credential
3. Confirm the deletion in the confirmation dialog
4. The credential will be removed from your wallet

### Downloading a Credential
1. Find the credential you want to download
2. Click the "Download" button next to the credential
3. The credential will be saved as a JSON file

## Best Practices

1. **Descriptive Naming**: Use clear, descriptive names that help identify the purpose of each credential
2. **Regular Review**: Periodically review and organize your credentials
3. **Backup Important Credentials**: Download and backup important credentials as JSON files
4. **Security**: Never share private keys or sensitive credential data
5. **Organization**: Use the delete functionality to remove credentials you no longer need
6. **Authentication Credential**: Keep your authentication credential secure as it's required for login

## Implementation Details

### Model Methods
- `add_vc()`: Adds a new credential with metadata
- `get_vcs_by_type()`: Retrieves credentials by type
- `get_authentication_vc()`: Retrieves the authentication credential
- `get_other_vcs()`: Retrieves non-authentication credentials
- `get_vc_metadata()`: Retrieves metadata for a specific credential
- `ensure_vcs_migrated()`: Ensures all credentials are in the new format

### Views
- `VCManagementView`: Displays the VC management interface
- `GenerateCredentialView`: Handles generation of new credentials
- `ImportCredentialView`: Handles import of existing credentials
- `UpdateVCNameView`: Handles renaming of credentials
- `DeleteCredentialView`: Handles deletion of credentials

### Templates
- `vc_management.html`: Main VC management page
- `import_credential.html`: Import credential form
- `partials/vc_container.html`: VC display partial template
- `partials/generate_credential_form.html`: Generate credential modal form

### JavaScript Functions
- `copyToClipboard()`: Copies credential data to clipboard
- `confirmDelete()`: Handles the delete functionality with confirmation
- Modal management for credential generation