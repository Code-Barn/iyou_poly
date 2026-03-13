"""
Serializers for the core app.

These serializers handle DID, VC, scope, and credential data.
"""

import datetime
import uuid
from rest_framework import serializers
from .models import (
    ScopeType,
    Scope,
    CredentialType,
    CredentialIssuance,
    IssuerAuthorization,
    DIDMethod,
    DID,
    DIDDocument,
    FederatedNode,
    FederatedData,
    SyncMessage,
    SyncMessageType,
    DataSyncLog,
    IssuerMetrics,
    IssuerEndorsement,
)


class ScopeTypeSerializer(serializers.ModelSerializer):
    """Serializer for ScopeType model."""

    class Meta:
        model = ScopeType
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "parent_type",
            "hierarchy_depth",
            "is_self_authorizing",
            "requires_proof",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    parent_type = serializers.SlugRelatedField(
        slug_field="name",
        queryset=ScopeType.objects.all(),
        required=False,
        allow_null=True,
    )


class ScopeSerializer(serializers.ModelSerializer):
    """Serializer for Scope model."""

    scope_type_name = serializers.CharField(source="scope_type.name", read_only=True)
    parent_scope_value = serializers.CharField(
        source="parent_scope.value", read_only=True
    )

    class Meta:
        model = Scope
        fields = [
            "id",
            "scope_type",
            "scope_type_name",
            "value",
            "parent_scope",
            "parent_scope_value",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    scope_type = serializers.SlugRelatedField(
        slug_field="name", queryset=ScopeType.objects.all()
    )
    parent_scope = serializers.SlugRelatedField(
        slug_field="value",
        queryset=Scope.objects.all(),
        required=False,
        allow_null=True,
    )


class CredentialTypeSerializer(serializers.ModelSerializer):
    """Serializer for CredentialType model."""

    scope_type_name = serializers.CharField(source="scope_type.name", read_only=True)

    class Meta:
        model = CredentialType
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "scope_type",
            "scope_type_name",
            "parent_credential_type",
            "max_issuers_per_scope",
            "requires_approval",
            "min_approvals",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    scope_type = serializers.SlugRelatedField(
        slug_field="name", queryset=ScopeType.objects.all()
    )
    parent_credential_type = serializers.SlugRelatedField(
        slug_field="name",
        queryset=CredentialType.objects.all(),
        required=False,
        allow_null=True,
    )


class CredentialIssuanceSerializer(serializers.ModelSerializer):
    """Serializer for CredentialIssuance model."""

    credential_type_name = serializers.CharField(
        source="credential_type.name", read_only=True
    )
    scope_value = serializers.CharField(source="scope.value", read_only=True)

    class Meta:
        model = CredentialIssuance
        fields = [
            "id",
            "credential",
            "holder_did",
            "issuer_did",
            "credential_type",
            "credential_type_name",
            "scope",
            "scope_value",
            "ipfs_cid",
            "blockchain_tx",
            "status",
            "issued_at",
            "revoked_at",
            "expires_at",
        ]
        read_only_fields = [
            "id",
            "ipfs_cid",
            "blockchain_tx",
            "issued_at",
        ]

    credential_type = serializers.SlugRelatedField(
        slug_field="name", queryset=CredentialType.objects.all()
    )
    scope = ScopeSerializer()


class IssuerAuthorizationSerializer(serializers.ModelSerializer):
    """Serializer for IssuerAuthorization model."""

    credential_type_name = serializers.CharField(
        source="credential_type.name", read_only=True
    )
    scope_value = serializers.CharField(source="scope.value", read_only=True)

    class Meta:
        model = IssuerAuthorization
        fields = [
            "id",
            "issuer_did",
            "credential_type",
            "credential_type_name",
            "scope",
            "scope_value",
            "authorized_by",
            "authorization_credential",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    credential_type = serializers.SlugRelatedField(
        slug_field="name", queryset=CredentialType.objects.all()
    )
    scope = ScopeSerializer()


class DIDMethodSerializer(serializers.ModelSerializer):
    """Serializer for DIDMethod model."""

    class Meta:
        model = DIDMethod
        fields = ["id", "name", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class DIDSerializer(serializers.ModelSerializer):
    """Serializer for DID model."""

    method_name = serializers.CharField(source="method.name", read_only=True)

    class Meta:
        model = DID
        fields = [
            "id",
            "user",
            "method",
            "method_name",
            "identifier",
            "did_uri",
            "is_primary",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "did_uri", "created_at"]

    method = serializers.SlugRelatedField(
        slug_field="name", queryset=DIDMethod.objects.all()
    )


class DIDDocumentSerializer(serializers.ModelSerializer):
    """Serializer for DIDDocument model."""

    did_uri = serializers.CharField(source="did.did_uri", read_only=True)

    class Meta:
        model = DIDDocument
        fields = ["id", "did", "did_uri", "document", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    did = serializers.PrimaryKeyRelatedField(queryset=DID.objects.all())


class CredentialIssueRequestSerializer(serializers.Serializer):
    """Serializer for credential issuance requests."""

    holder_did = serializers.CharField(max_length=255)
    credential_type = serializers.CharField(max_length=100)
    scope_type = serializers.CharField(max_length=50)
    scope_value = serializers.CharField(max_length=255)
    issuer_did = serializers.CharField(max_length=255, required=False)
    proof_of_verification = serializers.JSONField(required=False)
    expiration_days = serializers.IntegerField(default=365, required=False)

    def validate_credential_type(self, value):
        try:
            CredentialType.objects.get(name=value, is_active=True)
        except CredentialType.DoesNotExist:
            raise serializers.ValidationError(
                f"Credential type '{value}' not found or inactive."
            )
        return value

    def validate_scope_type(self, value):
        try:
            ScopeType.objects.get(name=value, is_active=True)
        except ScopeType.DoesNotExist:
            raise serializers.ValidationError(
                f"Scope type '{value}' not found or inactive."
            )
        return value


class CredentialVerifyRequestSerializer(serializers.Serializer):
    """Serializer for credential verification requests."""

    credential = serializers.JSONField()
    required_scope_type = serializers.CharField(max_length=50, required=False)
    required_scope_value = serializers.CharField(max_length=255, required=False)
    poll_id = serializers.CharField(required=False)


class ScopeTypeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing scope types with child info."""

    child_types = serializers.SerializerMethodField()

    class Meta:
        model = ScopeType
        fields = [
            "name",
            "display_name",
            "description",
            "parent_type",
            "hierarchy_depth",
            "is_self_authorizing",
            "child_types",
        ]

    def get_child_types(self, obj):
        return list(obj.child_types.values_list("name", flat=True))


class ScopeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing scopes."""

    child_count = serializers.SerializerMethodField()
    parent_value = serializers.CharField(source="parent_scope.value", read_only=True)

    class Meta:
        model = Scope
        fields = ["scope_type", "value", "parent_value", "child_count", "is_active"]

    def get_child_count(self, obj):
        return obj.child_scopes.count()


class FederatedNodeSerializer(serializers.ModelSerializer):
    """Serializer for FederatedNode model."""

    class Meta:
        model = FederatedNode
        fields = [
            "id",
            "name",
            "endpoint",
            "public_key",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FederatedDataSerializer(serializers.ModelSerializer):
    """Serializer for FederatedData model."""

    node_name = serializers.CharField(source="node.name", read_only=True)

    class Meta:
        model = FederatedData
        fields = [
            "id",
            "node",
            "node_name",
            "data_type",
            "data_id",
            "data",
            "version",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    node = serializers.SlugRelatedField(
        slug_field="name", queryset=FederatedNode.objects.all()
    )


class SyncMessageSerializer(serializers.ModelSerializer):
    """Serializer for SyncMessage model."""

    sender_node_name = serializers.CharField(source="sender_node.name", read_only=True)
    message_type_display = serializers.CharField(
        source="get_message_type_display", read_only=True
    )

    class Meta:
        model = SyncMessage
        fields = [
            "id",
            "message_id",
            "message_type",
            "message_type_display",
            "sender_node",
            "sender_node_name",
            "sender_endpoint",
            "timestamp",
            "signature",
            "payload",
            "previous_hash",
            "proof_of_work",
            "is_processed",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "message_id",
            "timestamp",
            "proof_of_work",
            "is_processed",
            "created_at",
        ]

    sender_node = serializers.SlugRelatedField(
        slug_field="name", queryset=FederatedNode.objects.all()
    )


class SyncMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating sync messages."""

    message_type = serializers.ChoiceField(choices=SyncMessageType.choices)
    sender_endpoint = serializers.URLField(required=False, allow_blank=True)
    payload = serializers.JSONField()
    previous_hash = serializers.CharField(required=False, allow_blank=True)
    signature = serializers.CharField(required=False, allow_blank=True)


class DataSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for DataSyncLog model."""

    source_node_name = serializers.CharField(source="source_node.name", read_only=True)
    target_node_name = serializers.CharField(source="target_node.name", read_only=True)

    class Meta:
        model = DataSyncLog
        fields = [
            "id",
            "source_node",
            "source_node_name",
            "target_node",
            "target_node_name",
            "data_type",
            "data_id",
            "version",
            "status",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SyncRequestSerializer(serializers.Serializer):
    """Serializer for sync requests."""

    since_version = serializers.IntegerField(default=0, required=False)
    data_types = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )


class AnnounceRequestSerializer(serializers.Serializer):
    """Serializer for announce requests."""

    message_type = serializers.ChoiceField(choices=SyncMessageType.choices)
    payload = serializers.JSONField()
    previous_hash = serializers.CharField(required=False, allow_blank=True)
    signature = serializers.CharField(required=False, allow_blank=True)


class IssuerMetricsSerializer(serializers.ModelSerializer):
    """Serializer for IssuerMetrics model."""

    scope_value = serializers.CharField(source="scope.value", read_only=True)
    scope_type_name = serializers.CharField(
        source="scope.scope_type.name", read_only=True
    )
    trust_score = serializers.SerializerMethodField()
    trust_level = serializers.SerializerMethodField()

    class Meta:
        model = IssuerMetrics
        fields = [
            "id",
            "issuer_did",
            "scope",
            "scope_value",
            "scope_type_name",
            "total_credentials_issued",
            "unique_holders",
            "credentials_this_month",
            "credentials_revoked",
            "verifications_attempted",
            "verifications_successful",
            "scope_violations",
            "first_issuance",
            "last_updated",
            "revocation_rate",
            "verification_success_rate",
            "trust_score",
            "trust_level",
        ]
        read_only_fields = ["id", "last_updated"]

    scope = serializers.SlugRelatedField(
        slug_field="value", queryset=Scope.objects.all()
    )

    def get_trust_score(self, obj):
        from apps.core.utils import TrustScorer

        return TrustScorer.calculate_score(obj)

    def get_trust_level(self, obj):
        from apps.core.utils import TrustScorer

        score = TrustScorer.calculate_score(obj)
        return TrustScorer.get_trust_level(score)


class IssuerMetricsCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating IssuerMetrics."""

    class Meta:
        model = IssuerMetrics
        fields = [
            "issuer_did",
            "scope",
            "total_credentials_issued",
            "unique_holders",
            "credentials_this_month",
            "credentials_revoked",
            "verifications_attempted",
            "verifications_successful",
            "scope_violations",
            "first_issuance",
        ]

    scope = serializers.SlugRelatedField(
        slug_field="value", queryset=Scope.objects.all()
    )


class IssuerEndorsementSerializer(serializers.ModelSerializer):
    """Serializer for IssuerEndorsement model."""

    scope_value = serializers.CharField(source="scope.value", read_only=True)
    scope_type_name = serializers.CharField(
        source="scope.scope_type.name", read_only=True
    )

    class Meta:
        model = IssuerEndorsement
        fields = [
            "id",
            "endorser_did",
            "endorsed_issuer_did",
            "scope",
            "scope_value",
            "scope_type_name",
            "is_positive",
            "comment",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    scope = serializers.SlugRelatedField(
        slug_field="value", queryset=Scope.objects.all()
    )


class IssuerEndorsementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating IssuerEndorsement."""

    class Meta:
        model = IssuerEndorsement
        fields = [
            "endorsed_issuer_did",
            "scope",
            "is_positive",
            "comment",
        ]

    scope = serializers.SlugRelatedField(
        slug_field="value", queryset=Scope.objects.all()
    )


class TrustScoreRequestSerializer(serializers.Serializer):
    """Serializer for trust score requests."""

    issuer_did = serializers.CharField(max_length=255)
    scope_value = serializers.CharField(max_length=255)
    scope_type = serializers.CharField(max_length=50, required=False)


class TrustScoreResponseSerializer(serializers.Serializer):
    """Serializer for trust score responses."""

    issuer_did = serializers.CharField()
    scope = serializers.CharField()
    trust_score = serializers.FloatField()
    trust_level = serializers.CharField()
    meets_threshold = serializers.BooleanField()
    threshold = serializers.CharField()
    metrics = IssuerMetricsSerializer()
