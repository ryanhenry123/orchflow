from __future__ import annotations
import re
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict
from boto3 import client
from mypy_boto3_bedrock import BedrockClient
from utils.log import get_logger

CLIENT: BedrockClient | None = None
LOGGER = get_logger(__file__)

CustomizationType = Literal["FINE_TUNING", "CONTINUED_PRE_TRAINING", "DISTILLATION"]
OutputModality = Literal["TEXT", "IMAGE", "EMBEDDING"]
InferenceType = Literal["ON_DEMAND", "PROVISIONED"]


class ModelLifecycle(TypedDict, total=False):
    status: Literal["ACTIVE", "LEGACY"]
    startOfLifeTime: str
    endOfLifeTime: str
    legacyTime: str
    publicExtendedAccessTime: str


class ModelSummary(TypedDict, total=False):
    modelArn: str
    modelId: str
    modelName: str
    providerName: str
    inputModalities: list[OutputModality]
    outputModalities: list[OutputModality]
    responseStreamingSupported: bool
    customizationsSupported: list[CustomizationType]
    inferenceTypesSupported: list[InferenceType]
    modelLifecycle: ModelLifecycle


class ListFoundationModelsFilters(TypedDict, total=False):
    byProvider: str
    byCustomizationType: CustomizationType
    byOutputModality: OutputModality
    byInferenceType: InferenceType


def _get_client(boto3_name: str = "bedrock") -> BedrockClient:
    global CLIENT
    if CLIENT is None:
        CLIENT = client(boto3_name)
    return CLIENT


def _class_name(name: str) -> str:
    parts = re.sub(r"[^a-zA-Z0-9]+", " ", name).split()
    return "".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts)


def _member_name(model_id: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]", "_", model_id).upper()
    name = re.sub(r"_+", "_", name).strip("_")
    if not name or name[0].isdigit():
        name = f"M_{name}"
    return name


class BedrockClass:
    def __init__(
        self,
        boto3_name: str = "bedrock",
        filters: ListFoundationModelsFilters | None = None,
    ):
        self._client = _get_client(boto3_name)
        self.filters = filters or {}
        self.model_summaries: list[ModelSummary] = self.list_foundation_models()

    def list_foundation_models(
        self, filters: ListFoundationModelsFilters | None = None
    ) -> list[ModelSummary]:
        kwargs = filters if filters is not None else self.filters
        response = self._client.list_foundation_models(**kwargs)
        return response.get("modelSummaries", [])

    @property
    def providers(self) -> set[str]:
        return {s["providerName"] for s in self.model_summaries if "providerName" in s}

    def models_by_provider(
        self, filters: ListFoundationModelsFilters | None = None
    ) -> dict[str, list[ModelSummary]]:
        grouped: dict[str, list[ModelSummary]] = {}
        for summary in self.list_foundation_models(filters):
            provider = summary.get("providerName")
            if provider is None:
                continue
            grouped.setdefault(provider, []).append(summary)
        return grouped

    def generate_modelproviders_source(
        self, filters: ListFoundationModelsFilters | None = None
    ) -> str:
        grouped = self.models_by_provider(filters)
        lines = [
            '"""Auto-generated from Bedrock list_foundation_models. Do not edit manually."""',
            "",
            "from enum import StrEnum",
            "",
            "",
            "class Provider(StrEnum):",
        ]

        provider_class_names: list[tuple[str, str, str]] = []
        for provider in sorted(grouped):
            provider_enum = _member_name(provider)
            class_name = _class_name(provider)
            provider_class_names.append((provider, provider_enum, class_name))
            lines.append(f'    {provider_enum} = "{provider}"')

        lines.extend(["", ""])
        for provider, _provider_enum, class_name in provider_class_names:
            lines.append(f"class {class_name}(StrEnum):")
            seen: set[str] = set()
            for summary in sorted(grouped[provider], key=lambda s: s.get("modelId", "")):
                model_id = summary.get("modelId")
                if model_id is None:
                    continue
                member = _member_name(model_id)
                if member in seen:
                    suffix = 2
                    candidate = f"{member}_{suffix}"
                    while candidate in seen:
                        suffix += 1
                        candidate = f"{member}_{suffix}"
                    member = candidate
                seen.add(member)
                lines.append(f'    {member} = "{model_id}"')
            lines.extend(["", ""])

        lines.extend(
            [
                "PROVIDER_MODELS: dict[Provider, type[StrEnum]] = {",
            ]
        )
        for provider, provider_enum, class_name in provider_class_names:
            lines.append(f"    Provider.{provider_enum}: {class_name},")
        lines.append("}")

        return "\n".join(lines) + "\n"

    def write_modelproviders(
        self,
        path: Path | str | None = None,
        filters: ListFoundationModelsFilters | None = None,
    ) -> Path:
        target = Path(path) if path is not None else Path(__file__).with_name("modelproviders.py")
        target.write_text(self.generate_modelproviders_source(filters), encoding="utf-8")
        return target


if __name__ == "__main__":
    bedrock = BedrockClass()
    out = bedrock.write_modelproviders()
    LOGGER.info(f"Wrote {out} ({len(bedrock.model_summaries)} models, {len(bedrock.providers)} providers)")
