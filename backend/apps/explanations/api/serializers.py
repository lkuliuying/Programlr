from typing import Any

from rest_framework import serializers

from apps.analysis.api.serializers import SourceRefSerializer
from apps.explanations.models import ContextConsent, Explanation
from common.serializers import StrictInputSerializer


class PreviewInputSerializer(StrictInputSerializer):
    analysis_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0, max_value=9999)
    node_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=50, required=False
    )
    excluded_snippets = serializers.ListField(
        child=serializers.RegexField(r"^[0-9a-f]{64}$"), max_length=50, required=False
    )


class ConsentInputSerializer(StrictInputSerializer):
    accepted = serializers.BooleanField()

    def validate_accepted(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("拒绝外发时无需提交确认；不会发送请求。")
        return value


class ExplanationInputSerializer(StrictInputSerializer):
    consent_id = serializers.UUIDField()


class ModelTargetSerializer(serializers.Serializer[dict[str, Any]]):
    base_url = serializers.CharField()
    model = serializers.CharField()
    # 仅用于读取历史预览；新预览的配置只包含地址和模型。
    timeout = serializers.IntegerField(required=False)
    context_bytes = serializers.IntegerField(required=False)
    output_tokens = serializers.IntegerField(required=False)
    token_field = serializers.CharField(required=False)


class PreviewMessageSerializer(serializers.Serializer[dict[str, Any]]):
    role = serializers.ChoiceField(choices=["system", "user"])
    content = serializers.CharField()


class PreviewSnippetSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    source_ref = SourceRefSerializer()
    sha256 = serializers.CharField()
    content = serializers.CharField()


class PreviewNodeSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    name = serializers.CharField()
    kind = serializers.CharField()


class PreviewKnowledgeCardSerializer(serializers.Serializer[dict[str, Any]]):
    card_id = serializers.UUIDField()
    slug = serializers.CharField()
    version = serializers.CharField()
    content_digest = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    source_refs = SourceRefSerializer(many=True)


class ContextPreviewSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0)
    payload_digest = serializers.CharField()
    configuration = ModelTargetSerializer()
    template_version = serializers.CharField()
    messages = PreviewMessageSerializer(many=True)
    snippets = PreviewSnippetSerializer(many=True)
    excluded_snippets = serializers.ListField(child=serializers.CharField())
    nodes = PreviewNodeSerializer(many=True)
    omissions = serializers.ListField(child=serializers.CharField())
    context_bytes = serializers.IntegerField()
    knowledge_cards = PreviewKnowledgeCardSerializer(many=True, default=list)
    created_at = serializers.DateTimeField()


class ContextConsentSerializer(serializers.ModelSerializer[ContextConsent]):
    preview_id = serializers.UUIDField()

    class Meta:
        model = ContextConsent
        fields = ["id", "preview_id", "created_at"]
        read_only_fields = fields


class ExplanationClaimSerializer(serializers.Serializer[dict[str, Any]]):
    kind = serializers.ChoiceField(
        choices=["source_fact", "static_inference", "general_principle"]
    )
    text = serializers.CharField()
    source_refs = SourceRefSerializer(many=True)


class ExplanationContentSerializer(serializers.Serializer[dict[str, Any]]):
    purpose = ExplanationClaimSerializer(many=True)
    evidence = ExplanationClaimSerializer(many=True)
    mechanism = ExplanationClaimSerializer(many=True)
    knowledge = ExplanationClaimSerializer(many=True)
    verification = ExplanationClaimSerializer(many=True)


class ModelUsageSerializer(serializers.Serializer[dict[str, Any]]):
    prompt_tokens = serializers.IntegerField(min_value=0)
    completion_tokens = serializers.IntegerField(min_value=0)
    total_tokens = serializers.IntegerField(min_value=0)


class ExplanationSerializer(serializers.ModelSerializer[Explanation]):
    job_id = serializers.UUIDField()
    preview_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField(source="preview.analysis_id")
    snapshot_id = serializers.UUIDField(source="preview.snapshot_id")
    endpoint_index = serializers.IntegerField(source="preview.endpoint_index")
    template_version = serializers.CharField(source="preview.payload.template_version")
    content = ExplanationContentSerializer()
    usage = ModelUsageSerializer(allow_null=True)

    class Meta:
        model = Explanation
        fields = [
            "id",
            "job_id",
            "preview_id",
            "analysis_id",
            "snapshot_id",
            "endpoint_index",
            "template_version",
            "model",
            "usage",
            "content",
            "created_at",
        ]
        read_only_fields = fields


class ExplanationPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ExplanationSerializer(many=True)
