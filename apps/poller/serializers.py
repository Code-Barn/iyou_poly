# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Serializers for the poller app.

These serializers handle poll, poll option, and vote data.
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import Poll, PollOption, Vote


class PollOptionSerializer(serializers.ModelSerializer):
    """Serializer for PollOption model."""

    class Meta:
        model = PollOption
        fields = ["id", "text", "votes", "created_at", "updated_at"]
        read_only_fields = ["id", "votes", "created_at", "updated_at"]


class PollSerializer(serializers.ModelSerializer):
    """Serializer for Poll model."""

    options = PollOptionSerializer(many=True, read_only=True)
    required_scope_type_name = serializers.CharField(
        source="required_scope_type.name", read_only=True, allow_null=True
    )
    required_scope_value = serializers.CharField(
        source="required_scope.value", read_only=True, allow_null=True
    )
    required_credential_type_name = serializers.CharField(
        source="required_credential_type.name", read_only=True, allow_null=True
    )
    total_votes = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_active_now = serializers.BooleanField(read_only=True)
    funding_progress = serializers.FloatField(read_only=True)

    class Meta:
        model = Poll
        fields = [
            "id",
            "poll_type",
            "parent_poll",
            "embedding_app",
            "title",
            "description",
            "created_by",
            "required_scope_type",
            "required_scope_type_name",
            "required_scope",
            "required_scope_value",
            "required_credential_type",
            "required_credential_type_name",
            "min_issuer_trust_score",
            "require_multiple_issuers",
            "vote_weight",
            "starts_at",
            "ends_at",
            "is_proposal",
            "funding_goal",
            "funding_current",
            "funding_progress",
            "funding_deadline",
            "ipfs_cid",
            "blockchain_anchor",
            "votes_merkle_root",
            "vote_count_anchor",
            "options",
            "total_votes",
            "is_active",
            "is_active_now",
            "is_expired",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "funding_current",
            "ipfs_cid",
            "blockchain_anchor",
            "votes_merkle_root",
            "vote_count_anchor",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        options_data = validated_data.pop("options", [])
        poll = Poll.objects.create(**validated_data)
        for option_data in options_data:
            PollOption.objects.create(poll=poll, **option_data)
        return poll


class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating polls."""

    options = serializers.ListField(
        child=serializers.CharField(max_length=255),
        min_length=2,
        help_text=_("List of poll options."),
    )

    class Meta:
        model = Poll
        fields = [
            "poll_type",
            "parent_poll",
            "embedding_app",
            "title",
            "description",
            "required_scope_type",
            "required_scope",
            "required_credential_type",
            "min_issuer_trust_score",
            "require_multiple_issuers",
            "starts_at",
            "ends_at",
            "is_proposal",
            "funding_goal",
            "funding_deadline",
            "options",
        ]

    def create(self, validated_data):
        options_texts = validated_data.pop("options", [])
        user = self.context["request"].user

        poll = Poll.objects.create(created_by=user, **validated_data)

        for option_text in options_texts:
            PollOption.objects.create(poll=poll, text=option_text)

        return poll


class VoteSerializer(serializers.ModelSerializer):
    """Serializer for Vote model."""

    voter_did = serializers.CharField(max_length=255, allow_blank=True)
    option_text = serializers.CharField(source="option.text", read_only=True)
    poll_title = serializers.CharField(source="poll.title", read_only=True)

    class Meta:
        model = Vote
        fields = [
            "id",
            "poll",
            "poll_title",
            "option",
            "option_text",
            "user",
            "voter_did",
            "signature",
            "credential_cid",
            "credential_proof",
            "weight",
            "ipfs_cid",
            "blockchain_tx",
            "is_verified",
            "verification_details",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "weight",
            "ipfs_cid",
            "blockchain_tx",
            "is_verified",
            "verification_details",
            "created_at",
        ]


class VoteCreateSerializer(serializers.Serializer):
    """Serializer for creating votes."""

    poll_id = serializers.IntegerField()
    option_id = serializers.IntegerField()
    voter_did = serializers.CharField(max_length=255)
    signature = serializers.CharField(required=False, allow_blank=True)
    credential = serializers.JSONField(required=False)
    credential_cid = serializers.CharField(required=False, allow_blank=True)


class PollResultsSerializer(serializers.ModelSerializer):
    """Serializer for poll results."""

    options = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            "id",
            "title",
            "description",
            "ipfs_cid",
            "votes_merkle_root",
            "vote_count_anchor",
            "options",
            "total_votes",
            "created_at",
        ]

    def get_options(self, obj):
        options = obj.options.all()
        results = []
        total = sum(opt.votes for opt in options)
        for option in options:
            percentage = (option.votes / total * 100) if total > 0 else 0
            results.append(
                {
                    "option": option.text,
                    "vote_count": option.votes,
                    "percentage": round(percentage, 2),
                }
            )
        return results

    def get_total_votes(self, obj):
        return sum(opt.votes for opt in obj.options.all())


from django.utils.translation import gettext_lazy as _
