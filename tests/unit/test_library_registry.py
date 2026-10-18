"""The library's registry entries fit their workflows (D-008, D-022): every mapped input and output names a
node and an input that exist, so a broken mapping is caught without a GPU."""

import json
import tomllib

import pytest

from hone_music_video.adapters.hone_models import LIBRARY_REGISTRY, load_registry

OWN = tomllib.loads(LIBRARY_REGISTRY.read_text())["models"]
REGISTRY = load_registry()
WITH_WORKFLOWS = [m for m in OWN if REGISTRY.get(m).workflow]


def targets(mapping: object) -> list[str]:
    """`"node.input"` paths of one input mapping: a path, a list of paths, or `{path, per_second, add}`."""
    if isinstance(mapping, str):
        return [mapping]
    if isinstance(mapping, list):
        return [t for m in mapping for t in targets(m)]
    path = getattr(mapping, "path", None) or (mapping.get("path") if isinstance(mapping, dict) else None)
    return [str(path)] if path else []


def test_every_library_entry_with_a_workflow_is_checked() -> None:
    assert {
        "qwen-image-edit-2511-4step",
        "qwen-image-2.1-turbo",
        "wan2.2-i2v-14b",
        "esrgan-rife-x2",
    } <= set(WITH_WORKFLOWS)


def test_qwen_image_turbo_takes_six_references_read_at_768_and_forbids_commercial_use() -> None:
    config = REGISTRY.get("qwen-image-2.1-turbo")
    assert config.capabilities.max_references == 6
    assert config.defaults == {"size": "1024x1024", "steps": 8, "cfg": 1.0, "ref_resolution": 768}
    assert (config.capabilities.license, config.capabilities.commercial_use) == (
        "Qwen research license",
        False,
    )
    assert len(config.install.files) == 4


@pytest.mark.parametrize("model_id", list(OWN))
def test_every_library_entry_records_its_license_and_commercial_use(model_id: str) -> None:
    capabilities = REGISTRY.get(model_id).capabilities
    assert capabilities.license and capabilities.commercial_use is not None


@pytest.mark.parametrize("model_id", WITH_WORKFLOWS)
def test_every_mapped_input_and_output_exists_in_the_workflow(model_id: str) -> None:
    config = REGISTRY.get(model_id)
    workflow = json.loads(open(str(config.workflow), encoding="utf-8").read())  # noqa: SIM115
    inputs = config.inputs if isinstance(config.inputs, dict) else {}
    for name, mapping in inputs.items():
        for target in targets(mapping):
            node, field = target.split(".", 1)
            assert node in workflow, f"{model_id}: {name} maps to node {node}, which the workflow lacks"
            assert field in workflow[node]["inputs"], f"{model_id}: {name}: node {node} has no {field}"
    for output in config.outputs or []:
        assert output in workflow, f"{model_id}: output node {output} is not in the workflow"
